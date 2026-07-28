from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..content_catalog import recommended_course_code
from ..db import get_db
from ..dependencies import require_learner
from ..learning_spaces import ensure_self_space, get_learning_space
from ..models import LearnerProfile, LearningPath, LearningSpace, PlacementAttempt, User, utc_now
from ..schemas import (
    LearningPathResponse,
    LearningSpaceModeUpdate,
    OnboardingPreferencesUpdate,
    OnboardingResponse,
    PlacementResultResponse,
)
from .learning_paths import create_learning_path_record

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

GOAL_LABELS = {
    "ielts": "Prepare for the IELTS exam",
    "communication": "Improve everyday English communication",
    "study_abroad": "Prepare English for studying abroad",
    "work": "Improve English for work and career",
}


def _latest_placement(db: Session, user_id: str, space_id: str) -> PlacementAttempt | None:
    return db.scalar(
        select(PlacementAttempt)
        .where(PlacementAttempt.user_id == user_id, PlacementAttempt.space_id == space_id)
        .order_by(PlacementAttempt.completed_at.desc())
        .limit(1)
    )


def _latest_path(db: Session, user_id: str, space_id: str) -> LearningPath | None:
    return db.scalar(
        select(LearningPath)
        .where(LearningPath.user_id == user_id, LearningPath.space_id == space_id)
        .order_by(LearningPath.created_at.desc())
        .limit(1)
    )


def _legacy_goal_code(goal: str) -> str:
    normalized = goal.strip().lower()
    if normalized in GOAL_LABELS:
        return normalized
    if "ielts" in normalized:
        return "ielts"
    if "abroad" in normalized or "du học" in normalized:
        return "study_abroad"
    if any(word in normalized for word in ("work", "career", "job", "interview")):
        return "work"
    return "communication"


def _ensure_profile(db: Session, user: User, learning_path: LearningPath | None) -> LearnerProfile:
    profile = db.get(LearnerProfile, user.id)
    if profile is None:
        profile = LearnerProfile(user_id=user.id)
        db.add(profile)
    changed = False
    if learning_path is not None:
        if profile.goal is None:
            profile.goal = _legacy_goal_code(learning_path.goal)
            changed = True
        if profile.daily_minutes is None:
            profile.daily_minutes = learning_path.minutes_per_day
            changed = True
        if profile.onboarding_completed_at is None:
            profile.onboarding_completed_at = learning_path.created_at
            changed = True
    if changed:
        profile.updated_at = utc_now()
    return profile


def _available_spaces(db: Session, user: User) -> list[LearningSpace]:
    return db.scalars(
        select(LearningSpace)
        .where(LearningSpace.user_id == user.id)
        .order_by(LearningSpace.kind, LearningSpace.created_at)
    ).all()


def _response(
    profile: LearnerProfile,
    placement: PlacementAttempt | None,
    learning_path: LearningPath | None,
    space: LearningSpace,
    available_spaces: list[LearningSpace],
) -> OnboardingResponse:
    if space.kind == "class":
        onboarding_status = "class_ready"
    elif space.mode_selected_at is None:
        onboarding_status = "needs_mode"
    elif learning_path is not None:
        onboarding_status = "completed"
    elif not space.goal:
        onboarding_status = "needs_goal"
    elif space.daily_minutes is None:
        onboarding_status = "needs_daily_time"
    elif placement is None:
        onboarding_status = "needs_placement"
    else:
        onboarding_status = "needs_learning_path"
    return OnboardingResponse(
        status=onboarding_status,
        space=space,
        available_spaces=available_spaces,
        goal=space.goal if space.kind == "self" else None,
        daily_minutes=space.daily_minutes if space.kind == "self" else None,
        onboarding_completed_at=(
            space.mode_selected_at if space.kind == "class" else profile.onboarding_completed_at
        ),
        updated_at=space.updated_at or profile.updated_at,
        placement_result=(
            PlacementResultResponse.model_validate(placement) if placement is not None else None
        ),
        learning_path=(
            LearningPathResponse.model_validate(learning_path) if learning_path is not None else None
        ),
    )


@router.get("", response_model=OnboardingResponse)
def get_onboarding(
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
    space: LearningSpace = Depends(get_learning_space),
):
    if space.kind == "class":
        profile = db.get(LearnerProfile, user.id) or LearnerProfile(user_id=user.id)
        return _response(profile, None, None, space, _available_spaces(db, user))
    learning_path = _latest_path(db, user.id, space.id)
    profile = _ensure_profile(db, user, learning_path)
    if space.goal is None and profile.goal is not None:
        space.goal = profile.goal
    if space.daily_minutes is None and profile.daily_minutes is not None:
        space.daily_minutes = profile.daily_minutes
    db.commit()
    db.refresh(profile)
    db.refresh(space)
    return _response(
        profile,
        _latest_placement(db, user.id, space.id),
        learning_path,
        space,
        _available_spaces(db, user),
    )


@router.patch("/mode", response_model=OnboardingResponse)
def choose_self_mode(
    request: LearningSpaceModeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    _ = request
    space = ensure_self_space(db, user)
    space.mode_selected_at = space.mode_selected_at or utc_now()
    space.updated_at = utc_now()
    profile = _ensure_profile(db, user, _latest_path(db, user.id, space.id))
    db.commit()
    db.refresh(profile)
    db.refresh(space)
    return _response(
        profile,
        _latest_placement(db, user.id, space.id),
        _latest_path(db, user.id, space.id),
        space,
        _available_spaces(db, user),
    )


@router.patch("/preferences", response_model=OnboardingResponse)
def update_preferences(
    request: OnboardingPreferencesUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
    space: LearningSpace = Depends(get_learning_space),
):
    if space.kind != "self":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Class spaces use teacher-assigned content",
        )
    learning_path = _latest_path(db, user.id, space.id)
    profile = _ensure_profile(db, user, learning_path)
    space.mode_selected_at = space.mode_selected_at or utc_now()
    if "goal" in request.model_fields_set:
        profile.goal = request.goal
        space.goal = request.goal
    if "daily_minutes" in request.model_fields_set:
        profile.daily_minutes = request.daily_minutes
        space.daily_minutes = request.daily_minutes
    profile.updated_at = utc_now()
    space.updated_at = utc_now()
    db.commit()
    db.refresh(profile)
    db.refresh(space)
    return _response(
        profile,
        _latest_placement(db, user.id, space.id),
        learning_path,
        space,
        _available_spaces(db, user),
    )


@router.post("/complete", response_model=OnboardingResponse)
async def complete_onboarding(
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
    space: LearningSpace = Depends(get_learning_space),
    settings: Settings = Depends(get_settings),
):
    if space.kind == "class":
        profile = db.get(LearnerProfile, user.id) or LearnerProfile(user_id=user.id)
        return _response(profile, None, None, space, _available_spaces(db, user))

    learning_path = _latest_path(db, user.id, space.id)
    profile = _ensure_profile(db, user, learning_path)
    placement = _latest_placement(db, user.id, space.id)

    if learning_path is not None:
        if profile.onboarding_completed_at is None:
            profile.onboarding_completed_at = learning_path.created_at
            profile.updated_at = utc_now()
        db.commit()
        db.refresh(profile)
        return _response(profile, placement, learning_path, space, _available_spaces(db, user))
    if not profile.goal or profile.daily_minutes is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Goal and daily_minutes are required before completing onboarding",
        )
    if placement is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Placement test is required before completing onboarding",
        )

    learning_path = await create_learning_path_record(
        db,
        user,
        space=space,
        goal=GOAL_LABELS.get(profile.goal, profile.goal),
        current_level=placement.level,
        minutes_per_day=profile.daily_minutes,
        settings=settings,
    )
    profile.onboarding_completed_at = utc_now()
    profile.updated_at = utc_now()
    space.course_code = recommended_course_code(placement.level, profile.goal)
    space.current_level = placement.level
    space.goal = profile.goal
    space.daily_minutes = profile.daily_minutes
    space.updated_at = utc_now()
    db.commit()
    db.refresh(profile)
    db.refresh(learning_path)
    db.refresh(space)
    return _response(profile, placement, learning_path, space, _available_spaces(db, user))
