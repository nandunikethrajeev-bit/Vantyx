"""VANTYX API v1 Master Router.

Mounts all modular v1 endpoint routers under a single versioned namespace.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import health

api_router = APIRouter()

# Health and readiness routes
api_router.include_router(health.router, tags=["System Health"])
