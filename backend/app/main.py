from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .config import get_settings
from .db import Base, engine
from .rate_limit import RequestRateLimiter
from .routers import (
    admin,
    analyses,
    analysis_jobs,
    auth,
    classes,
    content,
    dictionary,
    health,
    home,
    learning_path_jobs,
    learning_paths,
    learning_spaces,
    notifications,
    onboarding,
    placement,
    study_groups,
    teacher_applications,
    vocabulary,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend for the LearnMate AI formative English-learning application.",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Range",
            "X-Dev-User",
            "X-Learning-Space-ID",
            "Idempotency-Key",
        ],
        expose_headers=["Accept-Ranges", "Content-Length", "Content-Range"],
    )
    limiter = RequestRateLimiter(settings.rate_limit_window_seconds)

    @application.middleware("http")
    async def rate_limit(request: Request, call_next) -> Response:
        if settings.rate_limit_enabled and settings.app_env.strip().lower() != "test":
            allowed, retry_after = limiter.check(request)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests"},
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)

    @application.middleware("http")
    async def security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    application.include_router(health.router)
    application.include_router(auth.router, prefix="/api/v1")
    application.include_router(analyses.router, prefix="/api/v1")
    application.include_router(analysis_jobs.router, prefix="/api/v1")
    application.include_router(learning_paths.router, prefix="/api/v1")
    application.include_router(learning_path_jobs.router, prefix="/api/v1")
    application.include_router(learning_spaces.router, prefix="/api/v1")
    application.include_router(notifications.router, prefix="/api/v1")
    application.include_router(placement.router, prefix="/api/v1")
    application.include_router(vocabulary.router, prefix="/api/v1")
    application.include_router(dictionary.router, prefix="/api/v1")
    application.include_router(content.router, prefix="/api/v1")
    application.include_router(onboarding.router, prefix="/api/v1")
    application.include_router(teacher_applications.router, prefix="/api/v1")
    application.include_router(classes.router, prefix="/api/v1")
    application.include_router(study_groups.router, prefix="/api/v1")
    application.include_router(home.router, prefix="/api/v1")
    application.include_router(admin.router, prefix="/api/v1")
    return application


app = create_app()
