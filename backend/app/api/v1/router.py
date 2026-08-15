from fastapi import APIRouter
from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router
from app.api.v1.repos import router as repos_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.webhooks import router as webhooks_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="", tags=["Health"])
api_router.include_router(repos_router, prefix="", tags=["Repositories"])
api_router.include_router(reviews_router, prefix="", tags=["Reviews"])
api_router.include_router(webhooks_router, prefix="", tags=["Webhooks"])
api_router.include_router(chat_router, prefix="", tags=["Chat"])
