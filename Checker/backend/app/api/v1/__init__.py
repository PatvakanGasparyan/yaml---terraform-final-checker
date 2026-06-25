"""
API v1 router aggregation.

Combines all v1 endpoint routers into a single router.
"""

from fastapi import APIRouter

from app.api.v1 import auth, dashboard, github, system, validations

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(validations.router)
api_router.include_router(dashboard.router)
api_router.include_router(github.router)
api_router.include_router(system.router)
