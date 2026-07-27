from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import require_learner
from ..learning_spaces import ensure_class_space, ensure_self_space
from ..models import ClassMember, Classroom, LearningSpace, User, utc_now
from ..schemas import (
    LearningSpaceJoinRequest,
    LearningSpaceListResponse,
    LearningSpaceModeUpdate,
    LearningSpaceResponse,
)

router = APIRouter(prefix="/learning-spaces", tags=["learning spaces"])


def _response(space: LearningSpace) -> LearningSpaceResponse:
    return LearningSpaceResponse.model_validate(space)


@router.get("", response_model=LearningSpaceListResponse)
def list_learning_spaces(
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    existing_self = db.scalar(
        select(LearningSpace).where(
            LearningSpace.user_id == user.id,
            LearningSpace.kind == "self",
            LearningSpace.class_id.is_(None),
        )
    )
    self_space = ensure_self_space(db, user)
    memberships = db.execute(
        select(ClassMember, Classroom)
        .join(Classroom, Classroom.id == ClassMember.class_id)
        .where(ClassMember.learner_id == user.id)
        .order_by(Classroom.created_at)
    ).all()
    spaces = [self_space]
    changed = existing_self is None
    for _, classroom in memberships:
        before = db.scalar(
            select(LearningSpace).where(
                LearningSpace.user_id == user.id,
                LearningSpace.kind == "class",
                LearningSpace.class_id == classroom.id,
            )
        )
        spaces.append(ensure_class_space(db, user, classroom))
        changed = changed or before is None
    if changed:
        db.commit()
    return LearningSpaceListResponse(items=[_response(space) for space in spaces], total=len(spaces))


@router.post("/self", response_model=LearningSpaceResponse)
def choose_self_learning_space(
    request: LearningSpaceModeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    _ = request
    space = ensure_self_space(db, user)
    space.mode_selected_at = space.mode_selected_at or utc_now()
    space.updated_at = utc_now()
    db.commit()
    db.refresh(space)
    return _response(space)


@router.post("/join", response_model=LearningSpaceResponse, status_code=status.HTTP_201_CREATED)
def join_learning_space(
    request: LearningSpaceJoinRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    classroom = db.scalar(select(Classroom).where(Classroom.invite_code == request.invite_code))
    if classroom is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite code is invalid")
    membership = db.scalar(
        select(ClassMember).where(
            ClassMember.class_id == classroom.id,
            ClassMember.learner_id == user.id,
        )
    )
    if membership is None:
        db.add(ClassMember(class_id=classroom.id, learner_id=user.id))
    space = ensure_class_space(db, user, classroom)
    space.mode_selected_at = space.mode_selected_at or utc_now()
    space.updated_at = utc_now()
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not join this class") from exc
    db.refresh(space)
    return _response(space)
