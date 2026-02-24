"""
Abandoned cart coupon creation for Recurrente.

Creates a single-use 10% coupon with a code derived from business name
(business name capped at 6 chars + 2 random chars for deduplication).
Duration "once" and max_redemptions 1 so it applies only to the first payment.
"""
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models.checkout_session import CheckoutSession
from models.site_models import Site
from models.business import Business
from services.payments.recurrente_client import RecurrenteClient

logger = logging.getLogger(__name__)

COUPON_PREFIX = "SAVE10"
BASE_LENGTH = 6
RANDOM_LENGTH = 2
PERCENT_OFF = 10


def _sanitize_base(text: str, max_len: int = BASE_LENGTH) -> str:
    """Extract up to max_len alphanumeric chars, uppercase."""
    if not text:
        return ""
    alphanumeric = re.sub(r"[^A-Za-z0-9]", "", text)
    return (alphanumeric.upper() or "SITE")[:max_len]


def _random_suffix(length: int = RANDOM_LENGTH) -> str:
    """Two random alphanumeric characters (uppercase)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def build_coupon_code(business_name: Optional[str], site_slug: str) -> str:
    """
    Build coupon code SAVE10-{base6}{random2}.

    Base from business name (first 6 alphanumeric, uppercase) or from site_slug if no name.
    """
    if business_name and business_name.strip():
        base = _sanitize_base(business_name.strip(), BASE_LENGTH)
    else:
        base = _sanitize_base(site_slug.replace("-", ""), BASE_LENGTH)
    if not base:
        base = "SITE"
    return f"{COUPON_PREFIX}-{base}{_random_suffix()}"


async def create_abandoned_cart_coupon(
    session: CheckoutSession,
    db: AsyncSession,
    validity_hours: int,
) -> Tuple[str, Optional[str]]:
    """
    Create a Recurrente coupon for abandoned cart recovery.

    Resolves business name from session.site_id -> Site -> Business.name.
    Builds code SAVE10-{base6}{random2}, creates coupon with percent_off=10,
    duration="once", max_redemptions=1, optional expires_at.

    Returns:
        (discount_code, recurrente_coupon_id). coupon_id is None if Recurrente API fails.
    """
    business_name: Optional[str] = None
    if session.site_id:
        site_result = await db.execute(select(Site).where(Site.id == session.site_id))
        site = site_result.scalar_one_or_none()
        if site and site.business_id:
            biz_result = await db.execute(select(Business).where(Business.id == site.business_id))
            business = biz_result.scalar_one_or_none()
            if business and business.name:
                business_name = business.name.strip()
    code = build_coupon_code(business_name, session.site_slug)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=validity_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    client = RecurrenteClient()
    try:
        coupon = await client.create_coupon(
            name=code,
            percent_off=PERCENT_OFF,
            duration="once",
            expires_at=expires_at,
            max_redemptions=1,
        )
        logger.info(f"Created Recurrente coupon {coupon.id} for abandoned cart: {code}")
        return code, coupon.id
    except Exception as e:
        logger.warning(f"Recurrente coupon create failed for session {session.session_id}: {e}. Email will still send code {code}.")
        return code, None
