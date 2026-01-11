"""
Main router for API v1.
Aggregates all v1 route modules.
"""
from fastapi import APIRouter
from api.v1 import auth, businesses, coverage, sites, settings, campaigns

api_router = APIRouter()

# Include all v1 routers
api_router.include_router(auth.router)
api_router.include_router(businesses.router)
api_router.include_router(coverage.router)
api_router.include_router(sites.router)
api_router.include_router(settings.router)
api_router.include_router(campaigns.router)
