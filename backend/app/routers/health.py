from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..models import AnalysisJob, AssignmentGradingJob, LearningPathJob
from ..observability import metrics

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/health/live")
def liveness(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env, "version": settings.app_version}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc
    return {"status": "ready"}


@router.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics(db: Session = Depends(get_db)) -> PlainTextResponse:
    for queue_name, model in (
        ("analysis", AnalysisJob),
        ("learning_path", LearningPathJob),
        ("assignment_grading", AssignmentGradingJob),
    ):
        queued = db.scalar(
            select(func.count()).select_from(model).where(model.status.in_(["queued", "processing"]))
        )
        metrics.set_gauge("learnmate_queue_depth", float(queued or 0), {"queue": queue_name})
    return PlainTextResponse(metrics.render_prometheus(), media_type="text/plain; version=0.0.4")
