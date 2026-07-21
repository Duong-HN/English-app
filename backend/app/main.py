from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .ai import build_provider
from .config import get_settings
from .db import Base, engine, get_db
from .models import Analysis, User
from .schemas import AnalysisRequest, AnalysisResponse, AnalysisType, HistoryResponse


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()
app = FastAPI(title="LearnMate AI API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def current_user(
    db: Session = Depends(get_db),
    dev_user: str | None = Header(default=None, alias="X-Dev-User"),
) -> User:
    if settings.app_env != "development" and not dev_user:
        raise HTTPException(status_code=401, detail="Authentication is required")
    user_id = dev_user or "demo-user"
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id, email=f"{user_id}@example.local", display_name="Demo learner")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.post("/api/v1/analyses/{analysis_type}", response_model=AnalysisResponse)
async def create_analysis(
    analysis_type: AnalysisType,
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    provider = build_provider(settings)
    try:
        result = await provider.analyze(analysis_type, request.input_text.strip())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI provider failed: {exc}") from exc
    score = result.get("score")
    analysis = Analysis(
        user_id=user.id,
        type=analysis_type,
        input_text=request.input_text.strip(),
        result=result,
        score=float(score) if score is not None else None,
        provider=provider.name,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return AnalysisResponse(
        id=analysis.id,
        type=analysis.type,
        input_text=analysis.input_text,
        result=analysis.result,
        score=analysis.score,
        provider=analysis.provider,
        created_at=analysis.created_at,
    )


@app.get("/api/v1/analyses", response_model=HistoryResponse)
def list_analyses(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    rows = db.scalars(
        select(Analysis).where(Analysis.user_id == user.id).order_by(Analysis.created_at.desc()).limit(limit)
    ).all()
    return HistoryResponse(items=[
        AnalysisResponse(
            id=row.id,
            type=row.type,
            input_text=row.input_text,
            result=row.result,
            score=row.score,
            provider=row.provider,
            created_at=row.created_at,
        ) for row in rows
    ])
