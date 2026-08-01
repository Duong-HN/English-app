"""Application service for generating and persisting learning paths."""

from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .ai import build_provider
from .ai_schemas import LearningPathResult
from .config import Settings
from .content_catalog import recommended_course_code
from .models import Analysis, LearningPath, LearningSpace, PlacementAttempt, User, utc_now


class LearningPathGenerationError(RuntimeError):
    """Raised when the AI provider cannot generate a valid learning path."""


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def activity_profile(analyses: list[Analysis], now: datetime | None = None) -> dict:
    """Build a recency-weighted profile for the next learning decision."""
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


def recent_profile(db: Session, user_id: str, space_id: str, progress: dict | None = None) -> dict:
    recent = db.scalars(
        select(Analysis)
        .where(Analysis.user_id == user_id, Analysis.space_id == space_id)
        .order_by(Analysis.created_at.desc())
        .limit(20)
    ).all()
    profile = activity_profile(list(recent))
    profile["daily_progress"] = progress or {}
    return profile


def latest_placement(db: Session, user: User, space_id: str) -> PlacementAttempt | None:
    return db.scalar(
        select(PlacementAttempt)
        .where(PlacementAttempt.user_id == user.id, PlacementAttempt.space_id == space_id)
        .order_by(PlacementAttempt.completed_at.desc())
        .limit(1)
    )


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
    placement = latest_placement(db, user, space.id)
    effective_level = placement.level if placement else current_level
    level_source = "placement" if placement else "self_reported"
    profile = recent_profile(db, user.id, space.id)
    profile["level_source"] = level_source
    provider = build_provider(settings)
    try:
        raw_plan = await provider.generate_learning_path(
            {
                "goal": goal,
                "current_level": effective_level,
                "minutes_per_day": minutes_per_day,
            },
            profile,
        )
        plan = LearningPathResult.model_validate(raw_plan).model_dump()
    except Exception as exc:
        raise LearningPathGenerationError from exc

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
