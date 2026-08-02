from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..learning_spaces import get_learning_space
from ..models import Analysis, LearningSpace, User
from ..routers.analysis_jobs import enqueue_analysis_job
from ..schemas import (
    AnalysisJobResponse,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisType,
    HistoryResponse,
    MessageResponse,
)

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post(
    "/{analysis_type}",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_analysis(
    analysis_type: AnalysisType,
    request: AnalysisRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    """Compatibility alias for clients that still post to /analyses/{type}."""
    return enqueue_analysis_job(analysis_type, request, idempotency_key, db, user, space)


@router.get("", response_model=HistoryResponse)
def list_analyses(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    filters = (Analysis.user_id == user.id) & (Analysis.space_id == space.id)
    total = db.scalar(select(func.count()).select_from(Analysis).where(filters)) or 0
    rows = db.scalars(
        select(Analysis).where(filters).order_by(Analysis.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return HistoryResponse(
        items=[AnalysisResponse.model_validate(row) for row in rows],
        total=total,
    )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    analysis = db.scalar(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == user.id,
            Analysis.space_id == space.id,
        )
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return AnalysisResponse.model_validate(analysis)


@router.delete("/{analysis_id}", response_model=MessageResponse)
def delete_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    analysis = db.scalar(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == user.id,
            Analysis.space_id == space.id,
        )
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    db.delete(analysis)
    db.commit()
    return MessageResponse(message="Analysis deleted")
