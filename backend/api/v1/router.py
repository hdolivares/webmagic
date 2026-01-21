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
    customer_auth,  # Phase 2: Customer authentication
    site_purchase,  # Phase 2: Site purchase
    webhooks,  # Phase 2: Payment webhooks
    subscriptions  # Phase 3: Subscriptions
)

api_router = APIRouter()

# Include all v1 routers
api_router.include_router(auth.router)  # Admin authentication
api_router.include_router(customer_auth.router)  # Customer authentication (Phase 2)
api_router.include_router(site_purchase.router)  # Site purchase (Phase 2)
api_router.include_router(subscriptions.router)  # Subscriptions (Phase 3)
api_router.include_router(webhooks.router)  # Webhooks (Phase 2)
api_router.include_router(businesses.router)
api_router.include_router(coverage.router)
api_router.include_router(coverage_campaigns.router)
api_router.include_router(sites.router)
api_router.include_router(settings.router)
api_router.include_router(system.router)
api_router.include_router(campaigns.router)
api_router.include_router(payments.router)