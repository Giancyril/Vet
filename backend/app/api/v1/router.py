from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.webhooks import router as webhooks_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="", tags=["Health"])
api_router.include_router(webhooks_router, prefix="", tags=["Webhooks"])
