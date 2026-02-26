"""
Main router for API v1.
Aggregates all v1 route modules.
"""
from fastapi import APIRouter
from api.v1 import (
    auth,
    businesses,
    business_categories,  # Business categories list
    coverage,
    coverage_campaigns,
    geo_grid,  # Geo-grid scraping system
    intelligent_campaigns,  # Claude-powered intelligent strategies
    draft_campaigns,  # Draft mode campaign review workflow
    sites,
    generated_preview,  # PUBLIC: Serves generated site HTML content
    settings,
    campaigns,
    payments,
    system,
    customer_auth,  # Phase 2: Customer authentication
    site_purchase,  # Phase 2: Site purchase
    webhooks,  # Phase 2: Payment webhooks
    subscriptions,  # Phase 3: Subscriptions
    edit_requests,  # Phase 4: AI-powered edits
    preview,  # Phase 4: Preview system
    domains,  # Phase 5: Custom domains
    tickets,  # Phase 6: Support tickets (customer-facing)
    admin_tickets,  # Phase 6: Support tickets (admin)
    validation,  # Playwright website validation
    shortener,  # URL Shortener admin API
)
from api.v1.endpoints import scrapes  # Phase 2: Async scraping with SSE progress
from api.v1 import webhooks_telnyx as telnyx  # Phase 7: SMS webhooks (Telnyx, kept for rollback)
from api.v1 import webhooks_labsmobile as labsmobile  # Phase 7: SMS webhooks (LabsMobile)
from api.v1 import messages  # Phase 7: SMS Messages inbox

api_router = APIRouter()

# Include all v1 routers
api_router.include_router(auth.router)  # Admin authentication
api_router.include_router(customer_auth.router)  # Customer authentication (Phase 2)
api_router.include_router(site_purchase.router)  # Site purchase (Phase 2)
api_router.include_router(subscriptions.router)  # Subscriptions (Phase 3)
api_router.include_router(edit_requests.router)  # AI-powered edits (Phase 4)
api_router.include_router(preview.router)  # Preview system (Phase 4)
api_router.include_router(domains.router)  # Custom domains (Phase 5)
api_router.include_router(tickets.router)  # Support tickets customer-facing (Phase 6)
api_router.include_router(admin_tickets.router)  # Support tickets admin (Phase 6)
api_router.include_router(webhooks.router)  # Webhooks (Phase 2)
api_router.include_router(telnyx.router)       # SMS webhooks - Telnyx (Phase 7, kept for rollback)
api_router.include_router(labsmobile.router)   # SMS webhooks - LabsMobile (Phase 7)
api_router.include_router(messages.router)     # SMS Messages inbox (Phase 7)
api_router.include_router(businesses.router)
api_router.include_router(business_categories.router)  # Business categories
api_router.include_router(coverage.router)
api_router.include_router(coverage_campaigns.router)
api_router.include_router(geo_grid.router)  # Geo-grid scraping
api_router.include_router(intelligent_campaigns.router)  # Claude-powered intelligent strategies
api_router.include_router(draft_campaigns.router)  # Draft campaign review workflow
api_router.include_router(sites.router)
api_router.include_router(settings.router)
api_router.include_router(system.router)
api_router.include_router(campaigns.router)
api_router.include_router(payments.router)
api_router.include_router(validation.router)  # Website validation
api_router.include_router(scrapes.router)  # Phase 2: Async scraping with SSE progress
api_router.include_router(shortener.router)  # URL Shortener admin API

# NOTE: generated_preview.router removed from API router - it has a catch-all /{subdomain}
# route that was causing 502 errors by matching all /api/v1/* paths.
# TODO: Register generated_preview separately if needed for sites.lavish.solutions subdomain