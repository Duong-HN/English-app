from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai import build_provider
from ..config import Settings, get_settings
from ..db import get_db
from ..dependencies import get_current_user
from ..models import Analysis, LearningPath, User, utc_now
from ..schemas import (
    LearningPathGenerateRequest,
    LearningPathListResponse,
    LearningPathResponse,
    MessageResponse,
)

router = APIRouter(prefix="/learning-paths", tags=["learning paths"])


def _activity_profile(analyses: list[Analysis]) -> dict:
    counts = {kind: 0 for kind in ("reading", "writing", "speaking")}
    scores: dict[str, list[float]] = {kind: [] for kind in counts}
    issues: Counter[str] = Counter()
    for analysis in analyses:
        if analysis.type in counts:
            counts[analysis.type] += 1
            if analysis.score is not None:
                scores[analysis.type].append(float(analysis.score))
        for issue in analysis.result.get("issues", []):
            if isinstance(issue, dict) and issue.get("title"):
                issues[str(issue["title"]).strip()] += 1

    missing = [kind for kind, count in counts.items() if count == 0]
    averages = {kind: round(sum(values) / len(values), 2) for kind, values in scores.items() if values}
    if missing:
        recommended_focus = missing[0]
    elif averages:
        recommended_focus = min(averages, key=averages.get)
    elif analyses:
        recommended_focus = min(counts, key=counts.get)
    else:
        recommended_focus = "mixed"

    return {
        "sample_size": len(analyses),
        "analysis_counts": counts,
        "average_scores": averages,
        "recurring_issues": [title for title, _ in issues.most_common(5)],
        "recommended_focus": recommended_focus,
    }


@router.post("/generate", response_model=LearningPathResponse, status_code=status.HTTP_201_CREATED)
async def generate_learning_path(
    request: LearningPathGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    recent = db.scalars(
        select(Analysis).where(Analysis.user_id == user.id).order_by(Analysis.created_at.desc()).limit(20)
    ).all()
    profile = _activity_profile(list(recent))
    provider = build_provider(settings)
    try:
        plan = await provider.generate_learning_path(request.model_dump(), profile)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI provider failed") from exc

    learning_path = LearningPath(
        user_id=user.id,
        goal=request.goal,
        current_level=request.current_level,
        minutes_per_day=request.minutes_per_day,
        plan=plan,
        provider=provider.name,
    )
    user.level = request.current_level
    user.updated_at = utc_now()
    db.add(learning_path)
    db.commit()
    db.refresh(learning_path)
    return LearningPathResponse.model_validate(learning_path)


@router.get("/current", response_model=LearningPathResponse)
def current_learning_path(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    learning_path = db.scalar(
        select(LearningPath)
        .where(LearningPath.user_id == user.id)
        .order_by(LearningPath.created_at.desc())
        .limit(1)
    )
    if learning_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    return LearningPathResponse.model_validate(learning_path)


@router.get("", response_model=LearningPathListResponse)
def list_learning_paths(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    filters = LearningPath.user_id == user.id
    total = db.scalar(select(func.count()).select_from(LearningPath).where(filters)) or 0
    rows = db.scalars(
        select(LearningPath)
        .where(filters)
        .order_by(LearningPath.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return LearningPathListResponse(
        items=[LearningPathResponse.model_validate(row) for row in rows],
        total=total,
    )


@router.delete("/{learning_path_id}", response_model=MessageResponse)
def delete_learning_path(
    learning_path_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    learning_path = db.scalar(
        select(LearningPath).where(
            LearningPath.id == learning_path_id,
            LearningPath.user_id == user.id,
        )
    )
    if learning_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    db.delete(learning_path)
    db.commit()
    return MessageResponse(message="Learning path deleted")
