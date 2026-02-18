"""
Ticket Processing Tasks

Celery tasks for asynchronous AI processing of support tickets.

Flow:
  1. Customer submits ticket → saved to DB → 201 returned immediately
  2. This task is queued → Celery worker picks it up
  3. AI analyses the ticket (category, priority, suggested response)
  4. For simple 'question' tickets: AI posts a reply + emails the customer
  5. For 'site_edit' tickets: SiteEditProcessor runs the 3-stage edit pipeline
  6. All other tickets: marked in_progress for staff review

IMPORTANT: Celery tasks must be synchronous. async helpers run via asyncio.run().
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from celery_app import celery_app

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Celery entry-point
# ---------------------------------------------------------------------------

@celery_app.task(
    name="tasks.ticket_tasks.process_ticket_with_ai",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_ticket_with_ai(self, ticket_id: str):
    """
    Background task: AI analysis + optional auto-reply for a support ticket.

    Args:
        ticket_id: UUID string of the SupportTicket to process.
    """
    logger.info(f"[TicketTask] Starting AI processing for ticket {ticket_id}")
    try:
        asyncio.run(_process_ticket_async(UUID(ticket_id)))
        logger.info(f"[TicketTask] Completed AI processing for ticket {ticket_id}")
    except Exception as exc:
        logger.error(f"[TicketTask] Failed for ticket {ticket_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Async implementation
# ---------------------------------------------------------------------------

async def _process_ticket_async(ticket_id: UUID) -> None:
    """Full async pipeline for ticket AI processing."""
    from core.database import AsyncSessionLocal
    from models.support_ticket import SupportTicket, TicketMessage
    from models.site_models import CustomerUser
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async with AsyncSessionLocal() as db:
        # Load ticket with customer and messages
        stmt = (
            select(SupportTicket)
            .options(
                selectinload(SupportTicket.customer_user),
                selectinload(SupportTicket.messages),
            )
            .where(SupportTicket.id == ticket_id)
        )
        result = await db.execute(stmt)
        ticket = result.scalar_one_or_none()

        if not ticket:
            logger.error(f"[TicketTask] Ticket {ticket_id} not found – aborting")
            return

        customer = ticket.customer_user

        # ----------------------------------------------------------------
        # Stage 1: AI analysis (category, priority, suggested response)
        # ----------------------------------------------------------------
        ai_analysis = await _run_ai_analysis(ticket)

        # Apply AI insights to ticket
        if ai_analysis:
            ticket.ai_processed = True
            ticket.ai_category_confidence = ai_analysis.get("category_confidence", {})
            ticket.ai_suggested_response = ai_analysis.get("suggested_response", "")
            ticket.ai_processing_notes = {
                "priority_reasoning": ai_analysis.get("priority_reasoning", ""),
                "requires_human_review": ai_analysis.get("requires_human_review", True),
                "processing_notes": ai_analysis.get("processing_notes", ""),
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }

            # Update priority
            suggested_priority = ai_analysis.get("priority", "medium")
            PRIORITIES = ["low", "medium", "high", "urgent"]
            if suggested_priority in PRIORITIES:
                ticket.priority = suggested_priority

            # Update category if AI is very confident
            CATEGORIES = ["billing", "technical_support", "site_edit", "question", "other"]
            suggested_category = ai_analysis.get("suggested_category")
            if suggested_category and suggested_category in CATEGORIES:
                confidence = ai_analysis.get("category_confidence", {}).get(suggested_category, 0)
                if confidence > 0.8 and suggested_category != ticket.category:
                    logger.info(
                        f"[TicketTask] Recategorising {ticket.ticket_number}: "
                        f"{ticket.category} → {suggested_category} (conf={confidence:.2f})"
                    )
                    ticket.category = suggested_category

            # ----------------------------------------------------------------
            # Stage 2a: Auto-reply for simple 'question' tickets
            # ----------------------------------------------------------------
            can_auto_reply = (
                ticket.category == "question"
                and not ai_analysis.get("requires_human_review", True)
                and ai_analysis.get("category_confidence", {}).get("question", 0) > 0.9
                and ticket.ai_suggested_response
            )

            if can_auto_reply:
                ai_message = TicketMessage(
                    ticket_id=ticket.id,
                    message=ticket.ai_suggested_response,
                    message_type="ai",
                    ai_generated=True,
                    ai_model="claude-sonnet-4-5",
                    ai_confidence=ai_analysis.get("category_confidence", {}),
                )
                db.add(ai_message)
                ticket.status = "waiting_customer"
                ticket.first_response_at = datetime.now(timezone.utc)
                ticket.last_staff_message_at = datetime.now(timezone.utc)

                # Email customer with AI reply
                await _email_customer_reply(
                    customer=customer,
                    ticket=ticket,
                    reply_message=ticket.ai_suggested_response,
                    is_ai_reply=True,
                )
            else:
                ticket.status = "in_progress"

        await db.commit()
        await db.refresh(ticket)

        # ----------------------------------------------------------------
        # Stage 2b: Site-edit pipeline (3-stage processor)
        # ----------------------------------------------------------------
        if ticket.category == "site_edit" and ticket.site_id:
            await _run_site_edit_pipeline(db, ticket)


async def _run_ai_analysis(ticket) -> dict | None:
    """Call Claude to analyse the ticket and return structured JSON."""
    from anthropic import AsyncAnthropic
    from core.config import get_settings

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""You are a customer support AI assistant. Analyse this support ticket and respond ONLY with valid JSON.

Ticket:
Subject: {ticket.subject}
Description: {ticket.description}
Category (customer-selected): {ticket.category}

JSON format:
{{
    "category_confidence": {{
        "billing": 0.0,
        "technical_support": 0.0,
        "site_edit": 0.0,
        "question": 0.0,
        "other": 0.0
    }},
    "suggested_category": "category_name",
    "priority": "low|medium|high|urgent",
    "priority_reasoning": "brief explanation",
    "suggested_response": "Professional, helpful reply to the customer",
    "requires_human_review": true,
    "processing_notes": "Any important notes for staff"
}}"""

    try:
        async with client.messages.stream(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            temperature=0.3,
            system="You are a helpful customer support assistant. Always respond with valid JSON only.",
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            response_text = await stream.get_final_text()

        # Strip markdown fences if present
        text = response_text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"[TicketTask] Could not parse AI JSON for {ticket.ticket_number}")
        return None
    except Exception as exc:
        logger.error(f"[TicketTask] AI analysis failed for {ticket.ticket_number}: {exc}")
        return None


async def _run_site_edit_pipeline(db, ticket) -> None:
    """Run the 3-stage site edit processor for site_edit tickets."""
    from models.support_ticket import TicketMessage

    try:
        from services.support.site_edit_processor import SiteEditProcessor

        processor = SiteEditProcessor()
        edit_result = await processor.process(db=db, ticket=ticket)

        # Refresh ticket after processor's internal commits to get fresh attribute state,
        # then copy to a NEW dict so SQLAlchemy detects the change (avoids MutableDict
        # same-reference issue where assignment of identical object is silently skipped).
        await db.refresh(ticket)
        current_notes = dict(ticket.ai_processing_notes or {})
        current_notes.update(edit_result)
        ticket.ai_processing_notes = current_notes

        preview_id = edit_result.get("preview_version_id")
        edit_summary = edit_result.get("edit_summary", "your requested changes")

        # Post visible AI status message to the ticket thread
        if preview_id:
            status_text = (
                f"✅ We've analysed your request and prepared a preview of the changes.\n\n"
                f"**Edit summary:** {edit_summary}\n\n"
                "Our team is reviewing the proposed edits and will apply them shortly. "
                "You'll receive another notification once the changes are live on your website."
            )
        else:
            status_text = (
                "We've received your site edit request and our team is reviewing it. "
                "We'll get back to you shortly with an update."
            )

        status_message = TicketMessage(
            ticket_id=ticket.id,
            message=status_text,
            message_type="ai",
            ai_generated=True,
            ai_model="claude-sonnet-4-5",
        )
        db.add(status_message)
        ticket.last_staff_message_at = datetime.now(timezone.utc)
        if not ticket.first_response_at:
            ticket.first_response_at = datetime.now(timezone.utc)

        await db.commit()

        logger.info(
            f"[TicketTask][SiteEdit] Completed for {ticket.ticket_number}: "
            f"summary={edit_summary}, preview_id={preview_id}"
        )

        # Email customer
        if ticket.customer_user:
            await _email_customer_reply(
                customer=ticket.customer_user,
                ticket=ticket,
                reply_message=status_text,
                is_ai_reply=True,
            )

    except Exception as exc:
        logger.error(
            f"[TicketTask][SiteEdit] Failed for {ticket.ticket_number}: {exc}",
            exc_info=True,
        )


async def _email_customer_reply(customer, ticket, reply_message: str, is_ai_reply: bool) -> None:
    """Send an email to the customer with the AI/staff reply."""
    try:
        from services.emails.email_service import get_email_service
        from core.config import get_settings

        settings = get_settings()
        email_service = get_email_service()
        portal_link = f"{settings.FRONTEND_URL}/support/tickets/{ticket.id}"

        await email_service.send_ticket_reply_to_customer(
            customer_email=customer.email,
            customer_name=customer.full_name or customer.email,
            ticket_number=ticket.ticket_number,
            subject=ticket.subject,
            reply_message=reply_message,
            portal_link=portal_link,
            is_ai_reply=is_ai_reply,
        )
    except Exception as exc:
        logger.error(f"[TicketTask] Failed to email customer for {ticket.ticket_number}: {exc}")
