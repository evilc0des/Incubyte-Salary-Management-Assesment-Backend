from fastapi import APIRouter

from app.api.v1.routes.employees import router as employees_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.insights import router as insights_router

api_router = APIRouter()
api_router.include_router(employees_router)
api_router.include_router(health_router)
api_router.include_router(insights_router)

