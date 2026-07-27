from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .config import get_settings
from .db import Base, engine
from .routers import (
    admin,
    analyses,
    auth,
    classes,
    content,
    dictionary,
    health,
    home,
    learning_paths,
    learning_spaces,
    onboarding,
    placement,
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
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Dev-User"],
    )

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
    application.include_router(learning_paths.router, prefix="/api/v1")
    application.include_router(learning_spaces.router, prefix="/api/v1")
    application.include_router(placement.router, prefix="/api/v1")
    application.include_router(vocabulary.router, prefix="/api/v1")
    application.include_router(dictionary.router, prefix="/api/v1")
    application.include_router(content.router, prefix="/api/v1")
    application.include_router(onboarding.router, prefix="/api/v1")
    application.include_router(teacher_applications.router, prefix="/api/v1")
    application.include_router(classes.router, prefix="/api/v1")
    application.include_router(home.router, prefix="/api/v1")
    application.include_router(admin.router, prefix="/api/v1")
    return application


app = create_app()
