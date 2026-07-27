from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..learning_spaces import get_learning_space
from ..models import Analysis, LearningSpace, User, VocabularyItem, utc_now
from ..schemas import (
    VocabularyCreateRequest,
    VocabularyListResponse,
    VocabularyResponse,
    VocabularyUpdateRequest,
)

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


def _find_item(db: Session, user_id: str, space_id: str, item_id: str) -> VocabularyItem | None:
    return db.scalar(
        select(VocabularyItem).where(
            VocabularyItem.id == item_id,
            VocabularyItem.user_id == user_id,
            VocabularyItem.space_id == space_id,
        )
    )


def _validate_analysis(
    db: Session,
    user: User,
    space: LearningSpace,
    analysis_id: str | None,
) -> Analysis | None:
    if analysis_id is None:
        return None
    analysis = db.scalar(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == user.id,
            Analysis.space_id == space.id,
        )
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis


def upsert_analysis_vocabulary(
    db: Session,
    user: User,
    analysis: Analysis,
) -> None:
    """Persist reading vocabulary while keeping repeated analyses idempotent."""
    for raw_item in analysis.result.get("vocabulary", []):
        if not isinstance(raw_item, dict):
            continue
        word = str(raw_item.get("word", "")).strip()
        meaning = str(raw_item.get("meaning", "")).strip()
        if not word or not meaning:
            continue
        item = db.scalar(
            select(VocabularyItem).where(
                VocabularyItem.user_id == user.id,
                VocabularyItem.space_id == analysis.space_id,
                func.lower(VocabularyItem.word) == word.lower(),
            )
        )
        if item is None:
            db.add(
                VocabularyItem(
                    user_id=user.id,
                    space_id=analysis.space_id,
                    analysis_id=analysis.id,
                    word=word,
                    meaning=meaning,
                    example=str(raw_item.get("example", "")).strip() or None,
                )
            )
        else:
            item.analysis_id = analysis.id
            item.meaning = meaning
            example = str(raw_item.get("example", "")).strip()
            if example:
                item.example = example
            item.updated_at = utc_now()


@router.get("", response_model=VocabularyListResponse)
def list_vocabulary(
    item_status: str | None = Query(default=None, alias="status", pattern="^(new|learning|mastered)$"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    filters = [VocabularyItem.user_id == user.id, VocabularyItem.space_id == space.id]
    if item_status:
        filters.append(VocabularyItem.status == item_status)
    total = db.scalar(select(func.count()).select_from(VocabularyItem).where(*filters)) or 0
    rows = db.scalars(
        select(VocabularyItem)
        .where(*filters)
        .order_by(VocabularyItem.updated_at.desc(), VocabularyItem.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return VocabularyListResponse(
        items=[VocabularyResponse.model_validate(row) for row in rows],
        total=total,
    )


@router.post("", response_model=VocabularyResponse, status_code=status.HTTP_201_CREATED)
def create_vocabulary(
    request: VocabularyCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    _validate_analysis(db, user, space, request.analysis_id)
    word = request.word.strip()
    item = db.scalar(
        select(VocabularyItem).where(
            VocabularyItem.user_id == user.id,
            VocabularyItem.space_id == space.id,
            func.lower(VocabularyItem.word) == word.lower(),
        )
    )
    if item is None:
        item = VocabularyItem(
            user_id=user.id,
            space_id=space.id,
            analysis_id=request.analysis_id,
            word=word,
            meaning=request.meaning,
            example=request.example,
        )
        db.add(item)
    else:
        item.analysis_id = request.analysis_id or item.analysis_id
        item.meaning = request.meaning
        item.example = request.example
        item.updated_at = utc_now()
    db.commit()
    db.refresh(item)
    return VocabularyResponse.model_validate(item)


@router.post("/from-analysis/{analysis_id}", response_model=VocabularyListResponse)
def save_analysis_vocabulary(
    analysis_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    analysis = _validate_analysis(db, user, space, analysis_id)
    assert analysis is not None
    upsert_analysis_vocabulary(db, user, analysis)
    db.commit()
    items = db.scalars(
        select(VocabularyItem)
        .where(
            VocabularyItem.user_id == user.id,
            VocabularyItem.space_id == space.id,
            VocabularyItem.analysis_id == analysis.id,
        )
        .order_by(VocabularyItem.created_at.desc())
    ).all()
    return VocabularyListResponse(
        items=[VocabularyResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.patch("/{item_id}", response_model=VocabularyResponse)
def update_vocabulary(
    item_id: str,
    request: VocabularyUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    item = _find_item(db, user.id, space.id, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary item not found")
    if request.status is not None and request.status != item.status:
        item.status = request.status
        item.review_count += 1
    if request.example is not None:
        item.example = request.example
    item.updated_at = utc_now()
    db.commit()
    db.refresh(item)
    return VocabularyResponse.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vocabulary(
    item_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    item = _find_item(db, user.id, space.id, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary item not found")
    db.delete(item)
    db.commit()
