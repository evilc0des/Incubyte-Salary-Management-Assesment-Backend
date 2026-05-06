from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.config import settings

OPENAPI_TAGS = [
    {
        "name": "root",
        "description": "Application entrypoint and basic service metadata.",
    },
    {
        "name": "health",
        "description": "Operational health endpoints for service monitoring.",
    },
    {
        "name": "employees",
        "description": "Employee CRUD endpoints.",
    },
    {
        "name": "insights",
        "description": "Salary analytics and reporting endpoints.",
    },
]


app = FastAPI(
    title="Salary Management HR Dashboard API",
    description=(
        "Live API documentation for employee management and salary insights endpoints "
        "used by HR managers overseeing large organizations."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=OPENAPI_TAGS,
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {"message": f"Welcome to {settings.app_name}"}

