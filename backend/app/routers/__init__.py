from app.routers.auth import router as auth_router
from app.routers.spaces import router as spaces_router
from app.routers.projects import router as projects_router
from app.routers.materials import router as materials_router
from app.routers.activity import router as activity_router
from app.routers.tutor import router as tutor_router
from app.routers.quiz import router as quiz_router
from app.routers.assessment import router as assessment_router
from app.routers.mastery import router as mastery_router
from app.routers.growth import router as growth_router
from app.routers.recommendation import router as recommendation_router
from app.routers.analytics import router as analytics_router
from app.routers.admin import router as admin_router

__all__ = [
    "auth_router",
    "spaces_router",
    "projects_router",
    "materials_router",
    "activity_router",
    "tutor_router",
    "quiz_router",
    "assessment_router",
    "mastery_router",
    "growth_router",
    "recommendation_router",
    "analytics_router",
    "admin_router",
]

