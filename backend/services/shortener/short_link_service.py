"""
Short Link Service - Core URL shortener logic.

Handles creation, resolution, deactivation, and analytics for short links.
Designed to be used by any module (SMS, email, etc.) without coupling.
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, desc

from models.short_link import ShortLink
from services.shortener.slug_generator import generate_slug
from services.system_settings_service import SystemSettingsService

logger = logging.getLogger(__name__)

# Maximum retries when a slug collision occurs
MAX_SLUG_RETRIES = 5


class ShortLinkService:
    """
    URL Shortener service.

    Usage (from any module):
        from services.shortener import ShortLinkService

        short_url = await ShortLinkService.create_short_link(
            db,
            destination_url="https://sites.lavish.solutions/my-business-123",
            link_type="site_preview",
            site_id=some_uuid,
        )
        # Returns: "https://wm.gt/a1B2c3"
    """

    # ── Construction helpers ─────────────────────────────────────

    @staticmethod
    async def _get_shortener_config(db: AsyncSession) -> Dict[str, Any]:
        """Read shortener settings from the database (with sane defaults)."""
        domain = await SystemSettingsService.get_setting(
            db, "shortener_domain", default=""
        )
        protocol = await SystemSettingsService.get_setting(
            db, "shortener_protocol", default="https"
        )
        slug_length = await SystemSettingsService.get_setting(
            db, "shortener_slug_length", default=6
        )
        enabled = await SystemSettingsService.get_setting(
            db, "shortener_enabled", default=True
        )
        default_expiry_days = await SystemSettingsService.get_setting(
            db, "shortener_default_expiry_days", default=0
        )
        return {
            "domain": domain,
            "protocol": protocol,
            "slug_length": int(slug_length) if slug_length else 6,
            "enabled": str(enabled).lower() in ("true", "1", "yes") if isinstance(enabled, str) else bool(enabled),
            "default_expiry_days": int(default_expiry_days) if default_expiry_days else 0,
        }

    @staticmethod
    def _build_short_url(slug: str, domain: str, protocol: str = "https") -> str:
        """Construct the full short URL from slug + config."""
        return f"{protocol}://{domain}/{slug}"

    @staticmethod
    async def _generate_unique_slug(db: AsyncSession, length: int = 6) -> str:
        """Generate a slug that does not collide with existing ones."""
        for attempt in range(MAX_SLUG_RETRIES):
            slug = generate_slug(length)
            exists = await db.execute(
                select(ShortLink.id).where(ShortLink.slug == slug)
            )
            if exists.scalar_one_or_none() is None:
                return slug
            logger.warning(
                "Slug collision on attempt %d/%d: %s", attempt + 1, MAX_SLUG_RETRIES, slug
            )
        raise RuntimeError(
            f"Failed to generate unique slug after {MAX_SLUG_RETRIES} attempts"
        )

    # ── Public API ───────────────────────────────────────────────

    @staticmethod
    async def create_short_link(
        db: AsyncSession,
        destination_url: str,
        link_type: str = "other",
        business_id: Optional[UUID] = None,
        site_id: Optional[UUID] = None,
        campaign_id: Optional[UUID] = None,
        custom_slug: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new short link and return the full short URL.

        If the shortener is disabled or the domain is not configured,
        returns the original *destination_url* unchanged (graceful fallback).

        Args:
            db: Database session.
            destination_url: The full URL to redirect to.
            link_type: "site_preview", "campaign", "custom", "other".
            business_id: Optional FK to businesses table.
            site_id: Optional FK to generated_sites table.
            campaign_id: Optional FK to campaigns table.
            custom_slug: Use a specific slug instead of generating one.
            expires_at: Explicit expiry. If None, uses defaults by link_type.
            metadata: Optional JSONB metadata.

        Returns:
            The full short URL (e.g., "https://wm.gt/a1B2c3"), or
            the original URL if the shortener is not configured.
        """
        config = await ShortLinkService._get_shortener_config(db)

        if not config["enabled"] or not config["domain"]:
            logger.debug("Shortener disabled or domain not set — returning original URL")
            return destination_url

        # Determine slug
        if custom_slug:
            slug = custom_slug
            # Check uniqueness
            exists = await db.execute(
                select(ShortLink.id).where(ShortLink.slug == slug)
            )
            if exists.scalar_one_or_none() is not None:
                raise ValueError(f"Custom slug already in use: {slug}")
        else:
            slug = await ShortLinkService._generate_unique_slug(
                db, config["slug_length"]
            )

        # Determine expiration
        if expires_at is None and link_type != "site_preview":
            expiry_days = config["default_expiry_days"]
            if expiry_days and expiry_days > 0:
                expires_at = datetime.utcnow() + timedelta(days=expiry_days)

        # Create record
        short_link = ShortLink(
            slug=slug,
            destination_url=destination_url,
            link_type=link_type,
            business_id=business_id,
            site_id=site_id,
            campaign_id=campaign_id,
            expires_at=expires_at,
            metadata=metadata,
        )
        db.add(short_link)
        await db.flush()  # Get the ID without committing (caller controls transaction)

        short_url = ShortLinkService._build_short_url(
            slug, config["domain"], config["protocol"]
        )
        logger.info("Created short link: %s -> %s", short_url, destination_url[:80])
        return short_url

    @staticmethod
    async def get_or_create_short_link(
        db: AsyncSession,
        destination_url: str,
        link_type: str = "other",
        business_id: Optional[UUID] = None,
        site_id: Optional[UUID] = None,
        campaign_id: Optional[UUID] = None,
    ) -> str:
        """
        Return an existing short link for the destination URL, or create one.

        Useful for site_preview links where the same site URL should always
        map to the same short link.
        """
        config = await ShortLinkService._get_shortener_config(db)
        if not config["enabled"] or not config["domain"]:
            return destination_url

        # Check for existing active link
        result = await db.execute(
            select(ShortLink).where(
                ShortLink.destination_url == destination_url,
                ShortLink.is_active == True,  # noqa: E712
                ShortLink.link_type == link_type,
            )
        )
        existing = result.scalar_one_or_none()

        if existing and existing.is_resolvable:
            return ShortLinkService._build_short_url(
                existing.slug, config["domain"], config["protocol"]
            )

        # Create new
        return await ShortLinkService.create_short_link(
            db,
            destination_url=destination_url,
            link_type=link_type,
            business_id=business_id,
            site_id=site_id,
            campaign_id=campaign_id,
        )

    @staticmethod
    async def resolve(db: AsyncSession, slug: str) -> Optional[str]:
        """
        Resolve a slug to its destination URL.

        Increments click_count and updates last_clicked_at atomically.
        Returns None if the slug is not found, inactive, or expired.
        """
        result = await db.execute(
            select(ShortLink).where(ShortLink.slug == slug)
        )
        link = result.scalar_one_or_none()

        if link is None:
            return None

        if not link.is_resolvable:
            logger.debug("Link %s is not resolvable (active=%s, expired=%s)", slug, link.is_active, link.is_expired)
            return None

        # Increment click count atomically
        await db.execute(
            update(ShortLink)
            .where(ShortLink.id == link.id)
            .values(
                click_count=ShortLink.click_count + 1,
                last_clicked_at=datetime.utcnow(),
            )
        )
        await db.commit()

        return link.destination_url

    @staticmethod
    async def deactivate(db: AsyncSession, link_id: UUID) -> bool:
        """Soft-deactivate a short link. Returns True if found and updated."""
        result = await db.execute(
            update(ShortLink)
            .where(ShortLink.id == link_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def get_link_by_id(db: AsyncSession, link_id: UUID) -> Optional[ShortLink]:
        """Get a short link by its primary key."""
        result = await db.execute(
            select(ShortLink).where(ShortLink.id == link_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_links(
        db: AsyncSession,
        link_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> Dict[str, Any]:
        """
        List short links with pagination and optional filters.

        Returns:
            { "items": [...], "total": int, "page": int, "page_size": int }
        """
        query = select(ShortLink)
        count_query = select(func.count(ShortLink.id))

        if link_type is not None:
            query = query.where(ShortLink.link_type == link_type)
            count_query = count_query.where(ShortLink.link_type == link_type)

        if is_active is not None:
            query = query.where(ShortLink.is_active == is_active)
            count_query = count_query.where(ShortLink.is_active == is_active)

        # Total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginated items
        offset = (page - 1) * page_size
        query = query.order_by(desc(ShortLink.created_at)).offset(offset).limit(page_size)
        result = await db.execute(query)
        items = result.scalars().all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def get_stats(db: AsyncSession) -> Dict[str, Any]:
        """Get aggregate shortener statistics."""
        total_links = await db.execute(select(func.count(ShortLink.id)))
        active_links = await db.execute(
            select(func.count(ShortLink.id)).where(ShortLink.is_active == True)  # noqa: E712
        )
        total_clicks = await db.execute(select(func.coalesce(func.sum(ShortLink.click_count), 0)))

        # Breakdown by type
        type_counts_result = await db.execute(
            select(ShortLink.link_type, func.count(ShortLink.id))
            .group_by(ShortLink.link_type)
        )
        type_counts = {row[0]: row[1] for row in type_counts_result.all()}

        return {
            "total_links": total_links.scalar() or 0,
            "active_links": active_links.scalar() or 0,
            "total_clicks": total_clicks.scalar() or 0,
            "links_by_type": type_counts,
        }
