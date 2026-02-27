"""
Human Verification Queue API.

Exposes borderline validation cases — businesses where a real website was found
but the LLM could not confirm it belongs to that specific business — to an admin
who can make the final call in ~30 seconds per item.

Two endpoints:
  GET  /verification/queue        — paginated list of pending items
  POST /verification/{id}/decide  — submit admin decision
"""
import copy
import logging
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from core.database import get_db
from core.validation_enums import ValidationState
from models.business import Business
from models.site import GeneratedSite
from models.user import AdminUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verification", tags=["verification"])


# ─── Response schemas ────────────────────────────────────────────────────────

class MatchSignals(BaseModel):
    phone_match: bool = False
    address_match: bool = False
    name_match: bool = False


class VerificationQueueItem(BaseModel):
    # Identity
    id: str
    name: str

    # Google Business contact / location
    address: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[float] = None
    review_count: int = 0

    # What Outscraper originally returned for the website field
    outscraper_website: Optional[str] = None

    # Candidate URL that needs review (business.website_url)
    candidate_url: Optional[str] = None

    # What Playwright scraped from the candidate URL
    candidate_title: Optional[str] = None
    candidate_phones: list[str] = []
    candidate_emails: list[str] = []
    candidate_content_preview: Optional[str] = None
    candidate_quality_score: Optional[int] = None

    # LLM analysis
    llm_reasoning: Optional[str] = None
    llm_confidence: Optional[float] = None
    invalid_reason: Optional[str] = None  # 'wrong_business' | 'no_contact'
    match_signals: Optional[MatchSignals] = None

    # Generated site (if one was built for this business)
    has_generated_site: bool = False
    generated_site_subdomain: Optional[str] = None
    generated_site_url: Optional[str] = None

    # Timing
    website_validated_at: Optional[str] = None


class VerificationQueueResponse(BaseModel):
    items: list[VerificationQueueItem]
    total: int
    page: int
    page_size: int
    pages: int


class VerificationDecision(BaseModel):
    decision: Literal["valid_website", "no_website", "re_run"] = Field(
        description=(
            "valid_website → mark as valid_manual and exclude from campaigns; "
            "no_website → mark as confirmed_no_website and include in campaigns; "
            "re_run → reset to needs_discovery and re-queue ScrapingDog"
        )
    )
    website_url: Optional[str] = Field(
        default=None,
        description="Admin-confirmed or corrected URL (only used for valid_website decision)"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional admin notes stored in validation_history"
    )


# ─── Helpers ────────────────────────────────────────────────────────────────

def _extract_playwright_fields(validation_result: dict) -> dict:
    """Pull the fields we need from the nested validation_result JSONB."""
    playwright = (validation_result or {}).get("stages", {}).get("playwright", {})
    llm = (validation_result or {}).get("stages", {}).get("llm", {})
    match_signals_raw = llm.get("match_signals", {}) or {}

    return {
        "candidate_title": playwright.get("title"),
        "candidate_phones": playwright.get("phones") or [],
        "candidate_emails": playwright.get("emails") or [],
        "candidate_content_preview": playwright.get("content_preview"),
        "candidate_quality_score": playwright.get("quality_score"),
        "llm_reasoning": (validation_result or {}).get("reasoning") or llm.get("reasoning"),
        "llm_confidence": (validation_result or {}).get("confidence"),
        "invalid_reason": (validation_result or {}).get("invalid_reason"),
        "match_signals": MatchSignals(
            phone_match=bool(match_signals_raw.get("phone_match")),
            address_match=bool(match_signals_raw.get("address_match")),
            name_match=bool(match_signals_raw.get("name_match")),
        ) if match_signals_raw else None,
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/queue", response_model=VerificationQueueResponse)
async def get_verification_queue(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    has_generated_site: Optional[bool] = Query(
        default=None,
        description="Filter to only businesses that already have a generated site"
    ),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_user),
):
    """
    List businesses waiting for human verification.

    Ordered so that businesses with an existing generated site appear first
    (since generating a site for a business that actually has one is the
    highest-risk case), then by most-recently validated descending.
    """
    # Base filter: only needs_human_review
    base_filter = Business.website_validation_status == ValidationState.NEEDS_HUMAN_REVIEW.value

    # Count total matching rows (before pagination)
    count_query = select(func.count(Business.id)).where(base_filter)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Subquery: does this business have at least one non-failed generated site?
    has_site_subq = (
        select(func.count(GeneratedSite.id))
        .where(
            GeneratedSite.business_id == Business.id,
            GeneratedSite.status.notin_(["failed"]),
        )
        .correlate(Business)
        .scalar_subquery()
    )

    # Fetch page
    query = (
        select(Business, has_site_subq.label("site_count"))
        .where(base_filter)
        .order_by(
            # Businesses with a generated site surface first
            desc(case((has_site_subq > 0, 1), else_=0)),
            desc(Business.website_validated_at),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    rows = await db.execute(query)
    results = rows.fetchall()

    # Resolve generated site details for businesses that have one
    business_ids_with_sites = [
        row.Business.id for row in results if row.site_count > 0
    ]
    site_map: dict[UUID, GeneratedSite] = {}
    if business_ids_with_sites:
        site_query = (
            select(GeneratedSite)
            .where(
                GeneratedSite.business_id.in_(business_ids_with_sites),
                GeneratedSite.status.notin_(["failed"]),
            )
        )
        site_rows = await db.execute(site_query)
        for site in site_rows.scalars():
            # Keep the most recent site per business
            if site.business_id not in site_map:
                site_map[site.business_id] = site

    # Build response items
    items: list[VerificationQueueItem] = []
    for row in results:
        business: Business = row.Business
        site_count: int = row.site_count
        validation_result = business.website_validation_result or {}

        if has_generated_site is not None and bool(site_count) != has_generated_site:
            continue

        extracted = _extract_playwright_fields(validation_result)

        site = site_map.get(business.id)
        subdomain = site.subdomain if site else None
        generated_url = f"https://sites.lavish.solutions/{subdomain}" if subdomain else None

        outscraper_website = None
        raw = business.raw_data or {}
        for field in ("website", "site", "url", "domain"):
            val = raw.get(field)
            if val and isinstance(val, str) and len(val) > 5:
                outscraper_website = val
                break

        items.append(
            VerificationQueueItem(
                id=str(business.id),
                name=business.name,
                address=business.address,
                phone=business.phone,
                city=business.city,
                state=business.state,
                category=business.category,
                rating=float(business.rating) if business.rating else None,
                review_count=business.review_count or 0,
                outscraper_website=outscraper_website,
                candidate_url=business.website_url,
                has_generated_site=bool(site_count),
                generated_site_subdomain=subdomain,
                generated_site_url=generated_url,
                website_validated_at=(
                    business.website_validated_at.isoformat()
                    if business.website_validated_at else None
                ),
                **extracted,
            )
        )

    pages = max(1, (total + page_size - 1) // page_size)

    return VerificationQueueResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/{business_id}/decide", status_code=200)
async def submit_verification_decision(
    business_id: UUID,
    body: VerificationDecision,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Record an admin decision for a business in the verification queue.

    - valid_website: confirm the business has a valid website; exclude from campaigns.
    - no_website:    confirm no website exists; include in campaigns.
    - re_run:        clear URL and re-queue ScrapingDog discovery.
    """
    result = await db.execute(
        select(Business).where(Business.id == business_id)
    )
    business = result.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    if business.website_validation_status != ValidationState.NEEDS_HUMAN_REVIEW.value:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Business is not in needs_human_review status "
                f"(current: {business.website_validation_status})"
            )
        )

    # Append decision to validation_history for a full audit trail
    meta = copy.deepcopy(business.website_metadata or {})
    history = meta.get("validation_history", [])
    history.append({
        "timestamp": datetime.utcnow().isoformat(),
        "action": "human_verification_decision",
        "decision": body.decision,
        "decided_by": current_user.email,
        "website_url": body.website_url or business.website_url,
        "notes": body.notes,
    })
    meta["validation_history"] = history
    business.website_metadata = meta

    if body.decision == "valid_website":
        final_url = body.website_url or business.website_url
        if not final_url:
            raise HTTPException(
                status_code=422,
                detail="website_url is required for valid_website decision"
            )
        business.website_url = final_url
        business.website_validation_status = ValidationState.VALID_MANUAL.value
        business.website_validated_at = datetime.utcnow()

        # Supersede any completed/published generated sites — the business has
        # its own website so our generated version is no longer needed for campaigns.
        supersede_result = await db.execute(
            update(GeneratedSite)
            .where(
                GeneratedSite.business_id == business_id,
                GeneratedSite.status.in_(["completed", "published"]),
            )
            .values(status="superseded")
            .returning(GeneratedSite.id, GeneratedSite.subdomain)
        )
        superseded_sites = supersede_result.fetchall()
        if superseded_sites:
            logger.info(
                f"  ↳ Superseded {len(superseded_sites)} generated site(s): "
                f"{[row.subdomain for row in superseded_sites]}"
            )

        logger.info(
            f"✅ Human review: {business.name!r} confirmed as having website {final_url!r} "
            f"(by {current_user.email})"
        )

    elif body.decision == "no_website":
        business.website_url = None
        business.website_validation_status = ValidationState.CONFIRMED_NO_WEBSITE.value
        business.website_validated_at = datetime.utcnow()
        logger.info(
            f"❌ Human review: {business.name!r} confirmed as having no website "
            f"(by {current_user.email})"
        )

    elif body.decision == "re_run":
        business.website_url = None
        business.website_validation_status = ValidationState.NEEDS_DISCOVERY.value
        business.website_validation_result = None
        business.website_validated_at = None

        # Reset ScrapingDog attempt so the task won't skip
        attempts = meta.get("discovery_attempts", {})
        attempts["scrapingdog"] = {}
        meta["discovery_attempts"] = attempts
        business.website_metadata = meta

        await db.commit()

        from celery_app import celery_app
        celery_app.send_task(
            "tasks.discovery.discover_missing_websites_v2",
            args=[str(business_id)],
            queue="discovery",
        )
        logger.info(
            f"🔄 Human review: re-queued ScrapingDog discovery for {business.name!r} "
            f"(by {current_user.email})"
        )
        return {"status": "re_run_queued", "business_id": str(business_id)}

    await db.commit()
    return {"status": "ok", "decision": body.decision, "business_id": str(business_id)}
