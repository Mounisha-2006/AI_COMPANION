import sys
import logging
import traceback
from pathlib import Path

# Ensure 'backend' directory is in sys.path so 'import app...' works from any working directory
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.session import engine
from app.database.base import Base
import app.models # noqa: F401
from app.routers import (
    auth_router,
    spaces_router,
    projects_router,
    materials_router,
    activity_router,
    tutor_router,
    quiz_router,
    assessment_router,
    mastery_router,
    growth_router,
    recommendation_router,
    analytics_router,
    admin_router
)

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables and migrations are initialized on startup
    from app.database.init_db import init_db
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI Study Companion - Day 1 MVP Foundation API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permissive for easy prototype development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logger.info(f"HTTP {request.method} {request.url.path} -> {response.status_code} ({process_time:.1f}ms)")
        return response
    except Exception as exc:
        process_time = (time.time() - start_time) * 1000
        logger.error(f"HTTP {request.method} {request.url.path} FAILED after {process_time:.1f}ms: {exc}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error."}
        )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled exception on {request.method} {request.url.path}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."}
    )


# Root health check
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}

# Mount routers directly matching specification
app.include_router(auth_router)
app.include_router(spaces_router)
app.include_router(projects_router)
app.include_router(materials_router)
app.include_router(activity_router)
app.include_router(tutor_router)
app.include_router(quiz_router)
app.include_router(assessment_router)
app.include_router(mastery_router)
app.include_router(growth_router)
app.include_router(recommendation_router)
app.include_router(analytics_router)
app.include_router(admin_router)

# Also mount under /api prefix for API client flexibility
api_prefix = "/api"
app.include_router(auth_router, prefix=api_prefix)
app.include_router(spaces_router, prefix=api_prefix)
app.include_router(projects_router, prefix=api_prefix)
app.include_router(materials_router, prefix=api_prefix)
app.include_router(activity_router, prefix=api_prefix)
app.include_router(tutor_router, prefix=api_prefix)
app.include_router(quiz_router, prefix=api_prefix)
app.include_router(assessment_router, prefix=api_prefix)
app.include_router(mastery_router, prefix=api_prefix)
app.include_router(growth_router, prefix=api_prefix)
app.include_router(recommendation_router, prefix=api_prefix)
app.include_router(analytics_router, prefix=api_prefix)
app.include_router(admin_router, prefix=api_prefix)

