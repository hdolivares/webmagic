"""
Main router for API v1.
Aggregates all v1 route modules.
"""
from fastapi import APIRouter
from api.v1 import (
    auth,
    businesses,
    coverage,
    coverage_campaigns,
    sites,
    settings,
    campaigns,
    payments,
    system,
    customer_auth  # Phase 2: Customer authentication
)

api_router = APIRouter()

# Include all v1 routers
api_router.include_router(auth.router)  # Admin authentication
api_router.include_router(customer_auth.router)  # Customer authentication (Phase 2)
api_router.include_router(businesses.router)
api_router.include_router(coverage.router)
api_router.include_router(coverage_campaigns.router)
api_router.include_router(sites.router)
api_router.include_router(settings.router)
api_router.include_router(system.router)
api_router.include_router(campaigns.router)
api_router.include_router(payments.router)