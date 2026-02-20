"""
Conversation Service.

Single responsibility: group SMS messages into per-contact conversation threads
and resolve anonymous inbound phone numbers back to known Business records.

A "conversation" is all messages exchanged with one external phone number,
regardless of direction.  The contact_phone is:
  - outbound message → to_phone   (we sent to them)
  - inbound  message → from_phone (they replied to us)

Author: WebMagic Team
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, case, desc, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.business import Business
from models.sms_message import SMSMessage

logger = logging.getLogger(__name__)

# Regex to strip everything except digits (used for fuzzy phone matching)
_NON_DIGITS = re.compile(r"\D")


def _digits_only(phone: str) -> str:
    """Return only the digit characters of a phone string."""
    return _NON_DIGITS.sub("", phone or "")


@dataclass
class ConversationSummary:
    """One row in the conversation list — latest message + aggregate counts."""

    contact_phone: str
    business_id: Optional[UUID]
    business_name: Optional[str]
    business_category: Optional[str]
    business_city: Optional[str]
    last_message_body: str
    last_message_direction: str   # 'inbound' | 'outbound'
    last_message_at: datetime
    message_count: int
    inbound_count: int            # used as proxy for "replies received"


class ConversationService:
    """
    Groups SMS messages into conversations and resolves phone → Business.

    All methods receive an AsyncSession so callers control transaction scope.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_conversations(
        self,
        db: AsyncSession,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> list[ConversationSummary]:
        """
        Return one ConversationSummary per unique external phone number,
        ordered by most-recent message first.

        Args:
            db:     Async database session.
            search: Optional substring filter on phone or business name.
            limit:  Max number of conversations to return.
        """
        # Derive the "contact phone" for each message row
        contact_phone_expr = case(
            (SMSMessage.direction == "outbound", SMSMessage.to_phone),
            else_=SMSMessage.from_phone,
        ).label("contact_phone")

        subq = (
            select(
                contact_phone_expr,
                SMSMessage.business_id,
                SMSMessage.body,
                SMSMessage.direction,
                SMSMessage.created_at,
                func.count(SMSMessage.id).over(
                    partition_by=contact_phone_expr
                ).label("message_count"),
                func.sum(
                    case((SMSMessage.direction == "inbound", 1), else_=0)
                ).over(partition_by=contact_phone_expr).label("inbound_count"),
                func.row_number().over(
                    partition_by=contact_phone_expr,
                    order_by=desc(SMSMessage.created_at),
                ).label("rn"),
            )
            .subquery()
        )

        # Keep only the latest message per contact
        latest_q = (
            select(subq)
            .where(subq.c.rn == 1)
            .order_by(desc(subq.c.created_at))
            .limit(limit)
        )

        result = await db.execute(latest_q)
        rows = result.fetchall()

        # Resolve business details in one query
        business_ids = {r.business_id for r in rows if r.business_id}
        businesses: dict[UUID, Business] = {}
        if business_ids:
            biz_result = await db.execute(
                select(Business).where(Business.id.in_(business_ids))
            )
            for biz in biz_result.scalars().all():
                businesses[biz.id] = biz

        summaries: list[ConversationSummary] = []
        for row in rows:
            biz = businesses.get(row.business_id) if row.business_id else None

            # Apply optional search filter (post-query for simplicity)
            if search:
                needle = search.lower()
                name_match = biz and needle in (biz.name or "").lower()
                phone_match = needle in (row.contact_phone or "").lower()
                if not name_match and not phone_match:
                    continue

            summaries.append(
                ConversationSummary(
                    contact_phone=row.contact_phone,
                    business_id=row.business_id,
                    business_name=biz.name if biz else None,
                    business_category=biz.category if biz else None,
                    business_city=biz.city if biz else None,
                    last_message_body=row.body,
                    last_message_direction=row.direction,
                    last_message_at=row.created_at,
                    message_count=row.message_count,
                    inbound_count=row.inbound_count,
                )
            )

        return summaries

    async def get_thread(
        self,
        db: AsyncSession,
        contact_phone: str,
    ) -> list[SMSMessage]:
        """
        Return all messages for a single conversation thread, oldest first.

        Args:
            db:            Async database session.
            contact_phone: The external phone number (E.164 or local format).
        """
        result = await db.execute(
            select(SMSMessage)
            .where(
                or_(
                    SMSMessage.from_phone == contact_phone,
                    SMSMessage.to_phone == contact_phone,
                )
            )
            .order_by(SMSMessage.created_at)
        )
        return list(result.scalars().all())

    async def match_phone_to_business(
        self,
        db: AsyncSession,
        phone: str,
    ) -> Optional[Business]:
        """
        Attempt to resolve an unknown inbound phone number to a Business record.

        Strategy (in order):
        1. Exact E.164 match on businesses.phone
        2. Digit-only match — strips formatting from both sides
           (handles "+1 (555) 123-4567" vs "+15551234567")

        Args:
            db:    Async database session.
            phone: Inbound phone number in any format.

        Returns:
            Matching Business if found, else None.
        """
        normalized = _digits_only(phone)
        if len(normalized) < 7:
            return None

        # Exact match first (fast index hit)
        result = await db.execute(
            select(Business).where(Business.phone == phone).limit(1)
        )
        business = result.scalar_one_or_none()
        if business:
            logger.info("Exact phone match: %s → %s", phone, business.name)
            return business

        # Digit-only fuzzy match via PostgreSQL REGEXP_REPLACE
        result = await db.execute(
            select(Business)
            .where(
                func.regexp_replace(Business.phone, r"\D", "", "g") == normalized
            )
            .limit(1)
        )
        business = result.scalar_one_or_none()
        if business:
            logger.info("Fuzzy phone match: %s → %s", phone, business.name)

        return business
