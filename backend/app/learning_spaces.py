from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .dependencies import require_learner
from .models import ClassMember, Classroom, LearningSpace, User, utc_now

SELF_SPACE_KIND = "self"
CLASS_SPACE_KIND = "class"


def ensure_self_space(db: Session, user: User, *, commit: bool = False) -> LearningSpace:
    space = db.scalar(
        select(LearningSpace).where(
            LearningSpace.user_id == user.id,
            LearningSpace.kind == SELF_SPACE_KIND,
            LearningSpace.class_id.is_(None),
        )
    )
    if space is None:
        space = LearningSpace(
            user_id=user.id,
            kind=SELF_SPACE_KIND,
            name="Tự học",
        )
        db.add(space)
        db.flush()
        if commit:
            db.commit()
            db.refresh(space)
    return space


def ensure_class_space(
    db: Session,
    user: User,
    classroom: Classroom,
    *,
    commit: bool = False,
) -> LearningSpace:
    space = db.scalar(
        select(LearningSpace).where(
            LearningSpace.user_id == user.id,
            LearningSpace.kind == CLASS_SPACE_KIND,
            LearningSpace.class_id == classroom.id,
        )
    )
    if space is None:
        space = LearningSpace(
            user_id=user.id,
            kind=CLASS_SPACE_KIND,
            class_id=classroom.id,
            name=f"Lớp · {classroom.name}",
            daily_minutes=30,
            current_level=user.level,
            mode_selected_at=utc_now(),
        )
        db.add(space)
        db.flush()
        if commit:
            db.commit()
            db.refresh(space)
    return space


def get_learning_space(
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
    requested_id: str | None = Header(default=None, alias="X-Learning-Space-ID"),
) -> LearningSpace:
    if requested_id:
        space = db.scalar(
            select(LearningSpace).where(
                LearningSpace.id == requested_id,
                LearningSpace.user_id == user.id,
            )
        )
        if space is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning space not found",
            )
    else:
        space = ensure_self_space(db, user, commit=True)
    space.last_active_at = utc_now()
    return space


def require_space_membership(db: Session, user: User, space: LearningSpace) -> None:
    if space.kind != CLASS_SPACE_KIND:
        return
    membership = db.scalar(
        select(ClassMember.id).where(
            ClassMember.class_id == space.class_id,
            ClassMember.learner_id == user.id,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning space not found",
        )


def current_space_for_user(db: Session, user: User, space_id: str | None) -> LearningSpace:
    """Resolve a space for service functions that already have the user/session."""
    if space_id:
        space = db.scalar(
            select(LearningSpace).where(
                LearningSpace.id == space_id,
                LearningSpace.user_id == user.id,
            )
        )
        if space is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning space not found")
        return space
    return ensure_self_space(db, user, commit=True)
