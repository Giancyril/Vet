"""
Central API v1 router — includes all feature routers.
"""
from fastapi import APIRouter
from app.api.v1 import (
    health, webhooks, reviews, repos, chat, remediation,
    blast_radius, changelog, test_gen, policy
)
from app.api.v1 import ws_stream

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(webhooks.router, tags=["webhooks"])
api_router.include_router(reviews.router, tags=["reviews"])
api_router.include_router(repos.router, tags=["repos"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(remediation.router, tags=["remediation"])
api_router.include_router(blast_radius.router, tags=["blast-radius"])
api_router.include_router(changelog.router, tags=["changelog"])
api_router.include_router(test_gen.router, tags=["test-generator"])
api_router.include_router(policy.router, tags=["policy"])
api_router.include_router(ws_stream.router, tags=["websocket"])
