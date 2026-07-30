from collections import Counter
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai import build_provider
from ..ai_schemas import LearningPathResult
from ..config import Settings, get_settings
from ..content_catalog import recommended_course_code
from ..db import get_db
from ..dependencies import get_current_user
from ..learning_spaces import get_learning_space
from ..models import Analysis, LearnerProfile, LearningPath, LearningSpace, PlacementAttempt, User, utc_now
from ..schemas import (
    DailyProgressUpdate,
    LearningPathGenerateRequest,
    LearningPathListResponse,
    LearningPathResponse,
    MessageResponse,
)

router = APIRouter(prefix="/learning-paths", tags=["learning paths"])


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _activity_profile(analyses: list[Analysis], now: datetime | None = None) -> dict:
    """Build a recency-weighted profile for the next learning decision.

    A two-week half-life makes a recent result materially more influential than
    an old result, while still keeping enough history to identify persistent
    issues. Missing skills are reported, but never selected as the focus merely
    because the learner has not tried them yet.
    """
    reference = now or utc_now()
    counts = {kind: 0 for kind in ("reading", "writing", "speaking")}
    weighted_counts = {kind: 0.0 for kind in counts}
    score_totals = {kind: 0.0 for kind in counts}
    score_weights = {kind: 0.0 for kind in counts}
    issues: Counter[str] = Counter()
    issue_recent: Counter[str] = Counter()
    score_history: dict[str, list[tuple[datetime, float]]] = {kind: [] for kind in counts}

    for analysis in analyses:
        if analysis.type not in counts:
            continue
        created_at = _as_utc(analysis.created_at)
        age_days = max((reference - created_at).total_seconds() / 86400, 0)
        weight = 0.5 ** (age_days / 14)
        counts[analysis.type] += 1
        weighted_counts[analysis.type] += weight
        if analysis.score is not None:
            score = float(analysis.score)
            score_totals[analysis.type] += score * weight
            score_weights[analysis.type] += weight
            score_history[analysis.type].append((created_at, score))
        for issue in analysis.result.get("issues", []):
            if isinstance(issue, dict) and issue.get("title"):
                title = str(issue["title"]).strip()
                if title:
                    issues[title] += weight
                    if weight >= 0.5:
                        issue_recent[title] += weight

    averages = {
        kind: round(score_totals[kind] / score_weights[kind], 2) for kind in counts if score_weights[kind]
    }
    observed = [kind for kind, count in counts.items() if count]
    if averages:
        recommended_focus = min(averages, key=averages.get)
    elif observed:
        recommended_focus = min(observed, key=lambda kind: weighted_counts[kind])
    else:
        recommended_focus = "mixed"

    score_trends: dict[str, float] = {}
    for kind, history in score_history.items():
        if len(history) >= 2:
            history.sort(key=lambda item: item[0])
            score_trends[kind] = round(history[-1][1] - history[0][1], 2)

    recurring = [title for title, _ in issues.most_common(5)]
    return {
        "sample_size": len(analyses),
        "analysis_counts": counts,
        "recency_weighted_counts": {kind: round(value, 2) for kind, value in weighted_counts.items()},
        "average_scores": averages,
        "score_trends": score_trends,
        "recurring_issues": recurring,
        "recent_recurring_issues": [title for title, _ in issue_recent.most_common(5)],
        "recommended_focus": recommended_focus,
    }


def _recent_profile(db: Session, user_id: str, space_id: str, progress: dict | None = None) -> dict:
    recent = db.scalars(
        select(Analysis)
        .where(Analysis.user_id == user_id, Analysis.space_id == space_id)
        .order_by(Analysis.created_at.desc())
        .limit(20)
    ).all()
    profile = _activity_profile(list(recent))
    profile["daily_progress"] = progress or {}
    return profile


def _latest_placement(db: Session, user: User, space_id: str) -> PlacementAttempt | None:
    return db.scalar(
        select(PlacementAttempt)
        .where(PlacementAttempt.user_id == user.id, PlacementAttempt.space_id == space_id)
        .order_by(PlacementAttempt.completed_at.desc())
        .limit(1)
    )


def _path_response(learning_path: LearningPath) -> LearningPathResponse:
    return LearningPathResponse.model_validate(learning_path)


async def create_learning_path_record(
    db: Session,
    user: User,
    *,
    space: LearningSpace,
    goal: str,
    current_level: str,
    minutes_per_day: int,
    settings: Settings,
) -> LearningPath:
    """Build and stage a validated seven-day learning path for a learner."""
    placement = _latest_placement(db, user, space.id)
    effective_level = placement.level if placement else current_level
    level_source = "placement" if placement else "self_reported"
    recent_profile = _recent_profile(db, user.id, space.id)
    recent_profile["level_source"] = level_source
    provider = build_provider(settings)
    try:
        raw_plan = await provider.generate_learning_path(
            {
                "goal": goal,
                "current_level": effective_level,
                "minutes_per_day": minutes_per_day,
            },
            recent_profile,
        )
        plan = LearningPathResult.model_validate(raw_plan).model_dump()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI provider failed") from exc

    learning_path = LearningPath(
        user_id=user.id,
        space_id=space.id,
        goal=goal,
        current_level=effective_level,
        minutes_per_day=minutes_per_day,
        plan=plan,
        daily_progress={},
        level_source=level_source,
        placement_attempt_id=placement.id if placement else None,
        provider=provider.name,
    )
    if space.kind == "self":
        space.mode_selected_at = space.mode_selected_at or utc_now()
        space.current_level = effective_level
        space.course_code = recommended_course_code(effective_level, space.goal)
        space.updated_at = utc_now()
    user.level = effective_level
    user.updated_at = utc_now()
    db.add(learning_path)
    return learning_path


@router.post("/generate", response_model=LearningPathResponse, status_code=status.HTTP_201_CREATED)
async def generate_learning_path(
    request: LearningPathGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
    settings: Settings = Depends(get_settings),
):
    if space.kind != "self":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Class spaces use teacher-assigned content",
        )
    profile = db.get(LearnerProfile, user.id)
    if profile is not None and profile.onboarding_completed_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete onboarding before generating another learning path",
        )
    learning_path = await create_learning_path_record(
        db,
        user,
        space=space,
        goal=request.goal,
        current_level=request.current_level,
        minutes_per_day=request.minutes_per_day,
        settings=settings,
    )
    db.commit()
    db.refresh(learning_path)
    return _path_response(learning_path)


@router.get("/current", response_model=LearningPathResponse)
def current_learning_path(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    learning_path = db.scalar(
        select(LearningPath)
        .where(LearningPath.user_id == user.id, LearningPath.space_id == space.id)
        .order_by(LearningPath.created_at.desc())
        .limit(1)
    )
    if learning_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    return _path_response(learning_path)


@router.get("", response_model=LearningPathListResponse)
def list_learning_paths(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    filters = (LearningPath.user_id == user.id) & (LearningPath.space_id == space.id)
    total = db.scalar(select(func.count()).select_from(LearningPath).where(filters)) or 0
    rows = db.scalars(
        select(LearningPath)
        .where(filters)
        .order_by(LearningPath.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return LearningPathListResponse(
        items=[_path_response(row) for row in rows],
        total=total,
    )


@router.patch("/{learning_path_id}/days/{day}", response_model=LearningPathResponse)
def update_daily_progress(
    learning_path_id: str,
    day: int,
    request: DailyProgressUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    learning_path = db.scalar(
        select(LearningPath).where(
            LearningPath.id == learning_path_id,
            LearningPath.user_id == user.id,
            LearningPath.space_id == space.id,
        )
    )
    if learning_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    task_days = {
        task.get("day") for task in learning_path.plan.get("daily_tasks", []) if isinstance(task, dict)
    }
    if day not in task_days:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Task day not found")

    progress = dict(learning_path.daily_progress or {})
    previous = dict(progress.get(str(day), {}))
    progress[str(day)] = {
        **previous,
        "completed": request.completed,
        "completed_at": utc_now().isoformat() if request.completed else None,
        "note": request.note,
    }
    learning_path.daily_progress = progress
    db.commit()
    db.refresh(learning_path)
    return _path_response(learning_path)


@router.post("/{learning_path_id}/adapt", response_model=LearningPathResponse)
async def adapt_learning_path(
    learning_path_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
    settings: Settings = Depends(get_settings),
):
    learning_path = db.scalar(
        select(LearningPath).where(
            LearningPath.id == learning_path_id,
            LearningPath.user_id == user.id,
            LearningPath.space_id == space.id,
        )
    )
    if learning_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")

    profile = _recent_profile(db, user.id, space.id, learning_path.daily_progress)
    profile["completed_days"] = [
        int(day)
        for day, details in (learning_path.daily_progress or {}).items()
        if isinstance(details, dict) and details.get("completed")
    ]
    provider = build_provider(settings)
    try:
        raw_plan = await provider.generate_learning_path(
            {
                "goal": learning_path.goal,
                "current_level": learning_path.current_level,
                "minutes_per_day": learning_path.minutes_per_day,
            },
            profile,
        )
        plan = LearningPathResult.model_validate(raw_plan).model_dump()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI provider failed") from exc
    learning_path.plan = plan
    db.commit()
    db.refresh(learning_path)
    return _path_response(learning_path)


@router.delete("/{learning_path_id}", response_model=MessageResponse)
def delete_learning_path(
    learning_path_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    learning_path = db.scalar(
        select(LearningPath).where(
            LearningPath.id == learning_path_id,
            LearningPath.user_id == user.id,
            LearningPath.space_id == space.id,
        )
    )
    if learning_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    db.delete(learning_path)
    db.commit()
    return MessageResponse(message="Learning path deleted")
