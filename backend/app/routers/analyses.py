from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..ai import build_provider
from ..config import Settings, get_settings
from ..db import get_db
from ..dependencies import get_current_user
from ..models import Analysis, AssignmentSubmission, User
from ..schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisType,
    HistoryResponse,
    MessageResponse,
)

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("/{analysis_type}", response_model=AnalysisResponse)
async def create_analysis(
    analysis_type: AnalysisType,
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    try:
        provider = build_provider(settings)
        result = await provider.analyze(analysis_type, request.input_text)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI provider failed") from exc

    score = result.get("score")
    analysis = Analysis(
        user_id=user.id,
        type=analysis_type,
        input_text=request.input_text,
        result=result,
        score=float(score) if score is not None else None,
        provider=provider.name,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return AnalysisResponse.model_validate(analysis)


@router.get("", response_model=HistoryResponse)
def list_analyses(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    filters = Analysis.user_id == user.id
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
):
    analysis = db.scalar(select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user.id))
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return AnalysisResponse.model_validate(analysis)


@router.delete("/{analysis_id}", response_model=MessageResponse)
def delete_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    analysis = db.scalar(select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user.id))
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    linked_submission = db.scalar(
        select(AssignmentSubmission.id).where(AssignmentSubmission.analysis_id == analysis.id).limit(1)
    )
    if linked_submission is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis is linked to an assignment submission",
        )
    db.delete(analysis)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis is linked to an assignment submission",
        ) from exc
    return MessageResponse(message="Analysis deleted")
