"""
LabsMobile Webhook Endpoints.

Handles incoming callbacks from LabsMobile for:
- SMS delivery status updates  → GET  /webhooks/labsmobile/status
- Incoming SMS replies          → POST /webhooks/labsmobile/reply

LabsMobile callback formats (verified Feb 2026):

  Status (GET, query params):
    ?acklevel=handset&msisdn=502...&status=ok&desc=DELIVRD
    &subid=69a0b164a0e7b&timestamp=2026-02-26%2012:00:00

  Reply (POST, JSON body):
    {
      "inbound_number": "12015576234",
      "service_number": "12015576234",
      "msisdn": "50230110906",
      "message": "STOP",
      "timestamp": "2026-02-26 12:00:00"
    }

Author: WebMagic Team
Date: February 2026
"""
from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional
import logging
from datetime import datetime

from api.deps import get_db
from models.campaign import Campaign
from models.sms_message import SMSMessage
from services.sms import SMSComplianceService
from services.sms.conversation_service import ConversationService
from services.pitcher.sms_campaign_helper import SMSCampaignHelper
from services.pitcher.email_sender import EmailSender
from services.crm import BusinessLifecycleService
from core.config import get_settings

_settings = get_settings()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/labsmobile", tags=["LabsMobile Webhooks"])

# LabsMobile desc values → internal campaign status
# acklevel: operator | handset | error
# desc: DELIVRD | REJECTD | UNDELIV | EXPIRED | BLOCKED | UNKNOWN
_STATUS_MAP: dict[str, str] = {
    "DELIVRD": "delivered",
    "REJECTD": "failed",
    "UNDELIV": "failed",
    "EXPIRED": "failed",
    "BLOCKED": "failed",
    "UNKNOWN": "failed",
    "READ":    "delivered",
}


# ============================================================================
# DELIVERY STATUS CALLBACKS
# ============================================================================

@router.get("/status")
async def handle_sms_status_callback(
    subid: Optional[str] = Query(None),
    acklevel: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    desc: Optional[str] = Query(None),
    msisdn: Optional[str] = Query(None),
    timestamp: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle LabsMobile delivery status GET callback.

    LabsMobile makes a GET request to this URL with query params when a
    message is delivered, fails, or times out.

    Endpoint: GET /api/v1/webhooks/labsmobile/status
    """
    try:
        if not subid:
            logger.warning("LabsMobile status callback missing subid")
            return {"status": "ok", "message": "Missing subid"}

        logger.info(
            "LabsMobile status callback: subid=%s acklevel=%s desc=%s msisdn=%s",
            subid, acklevel, desc, msisdn,
        )

        # Find campaign by LabsMobile subid (stored in sms_sid column)
        result = await db.execute(
            select(Campaign).where(Campaign.sms_sid == subid)
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            logger.warning("Campaign not found for LabsMobile subid: %s", subid)
            # Return 200 to prevent LabsMobile retries
            return {"status": "ok", "message": "Campaign not found"}

        # Map LabsMobile desc to internal status
        desc_upper = (desc or "").upper()
        new_status = _STATUS_MAP.get(desc_upper, campaign.status)

        # If acklevel is "error" and no desc provided, mark failed
        if acklevel == "error" and not desc:
            new_status = "failed"

        update_values: dict = {
            "status": new_status,
            "updated_at": datetime.utcnow(),
        }

        if desc_upper == "DELIVRD" and not campaign.delivered_at:
            update_values["delivered_at"] = datetime.utcnow()

        if acklevel == "error" or new_status == "failed":
            update_values["error_message"] = (
                f"LabsMobile delivery failed: {desc or acklevel or 'unknown'}"
            )

        await db.execute(
            update(Campaign).where(Campaign.id == campaign.id).values(**update_values)
        )
        await db.commit()

        logger.info(
            "Updated campaign %s: %s → %s (desc=%s)",
            campaign.id, campaign.status, new_status, desc,
        )

        # CRM Integration
        if campaign.business_id:
            lifecycle_service = BusinessLifecycleService(db)
            try:
                if desc_upper == "DELIVRD":
                    await lifecycle_service.mark_campaign_sent(
                        campaign.business_id, channel="sms"
                    )
                elif new_status == "failed":
                    await lifecycle_service.mark_bounced(campaign.business_id)
                await db.commit()
            except Exception as exc:
                logger.error(
                    "CRM update error for business %s: %s",
                    campaign.business_id, exc, exc_info=True,
                )

        return {"status": "ok", "campaign_id": str(campaign.id), "new_status": new_status}

    except Exception as exc:
        logger.error("LabsMobile status callback error: %s", exc, exc_info=True)
        return {"status": "error", "message": "Internal server error"}


# ============================================================================
# INCOMING SMS REPLIES
# ============================================================================

@router.post("/reply")
async def handle_incoming_sms(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle incoming SMS replies from LabsMobile virtual numbers.

    LabsMobile sends a POST JSON body when a recipient replies.

    Endpoint: POST /api/v1/webhooks/labsmobile/reply
    """
    try:
        payload = await request.json()

        from_phone: str = payload.get("msisdn", "")
        to_phone: str = payload.get("service_number") or payload.get("inbound_number", "")
        message_body: str = payload.get("message", "")

        if not from_phone or not message_body:
            logger.warning("LabsMobile reply missing msisdn or message")
            return {"status": "ok", "message": "Missing required fields"}

        # Normalise to E.164 (add + if not present)
        if from_phone and not from_phone.startswith("+"):
            from_phone = f"+{from_phone}"

        logger.info("Incoming SMS via LabsMobile from %s: %s", from_phone, message_body[:50])

        inbound_message = SMSMessage.create_inbound(
            from_phone=from_phone,
            to_phone=to_phone,
            body=message_body,
            telnyx_message_id=None,
        )

        # Find the most recent outbound campaign to this phone
        result = await db.execute(
            select(Campaign)
            .where(Campaign.recipient_phone == from_phone)
            .order_by(Campaign.sent_at.desc())
        )
        campaigns = result.scalars().all()

        if not campaigns:
            logger.warning("No campaign found for reply phone: %s", from_phone)

            matched_business = await ConversationService().match_phone_to_business(
                db=db, phone=from_phone
            )
            if matched_business:
                inbound_message.business_id = (
                    matched_business.business_id
                    if hasattr(matched_business, "business_id")
                    else matched_business.id
                )

            db.add(inbound_message)
            await db.commit()

            await _notify_admin_reply(
                from_phone=from_phone,
                message_body=message_body,
                business_name=matched_business.name if matched_business else None,
                action="reply",
            )

            compliance = SMSComplianceService(db)
            await compliance.process_reply(
                phone_number=from_phone,
                reply_message=message_body,
                campaign_id=None,
            )

            return {"status": "ok", "message": "Processed (no campaign found)"}

        latest_campaign = campaigns[0]
        inbound_message.campaign_id = latest_campaign.id
        inbound_message.business_id = latest_campaign.business_id
        db.add(inbound_message)

        compliance = SMSComplianceService(db)
        reply_result = await SMSCampaignHelper.handle_sms_reply(
            phone_number=from_phone,
            message_body=message_body,
            campaign_id=latest_campaign.id,
            sms_compliance=compliance,
            db=db,
        )

        logger.info("LabsMobile reply processed: %s from %s", reply_result["action"], from_phone)

        await _notify_admin_reply(
            from_phone=from_phone,
            message_body=message_body,
            business_name=latest_campaign.business_name if latest_campaign else None,
            action=reply_result["action"],
        )

        if latest_campaign.business_id:
            lifecycle_service = BusinessLifecycleService(db)
            try:
                if reply_result["action"] == "opt_out":
                    await lifecycle_service.mark_unsubscribed(latest_campaign.business_id)
                elif reply_result["action"] == "reply":
                    await lifecycle_service.mark_replied(latest_campaign.business_id)
                await db.commit()
            except Exception as exc:
                logger.error(
                    "CRM update error for business %s: %s",
                    latest_campaign.business_id, exc, exc_info=True,
                )

        return {
            "status": "ok",
            "action": reply_result["action"],
            "campaign_id": str(latest_campaign.id),
        }

    except Exception as exc:
        logger.error("LabsMobile reply handling error: %s", exc, exc_info=True)
        return {"status": "error", "message": "Internal server error"}


# ============================================================================
# ADMIN NOTIFICATION HELPER
# ============================================================================

async def _notify_admin_reply(
    from_phone: str,
    message_body: str,
    business_name: Optional[str],
    action: str,
) -> None:
    """Fire-and-forget email to admin when an SMS reply is received."""
    try:
        admin_email = _settings.SUPPORT_ADMIN_EMAIL
        action_label = {
            "opt_out": "Opt-out (STOP)",
            "reply": "Reply",
        }.get(action, action.capitalize())

        subject = f"SMS Reply Received — {from_phone}"
        if business_name:
            subject = f"SMS Reply from {business_name} — {from_phone}"

        body_html = f"""
<div style="font-family: sans-serif; max-width: 560px; margin: 0 auto; background: #f9fafb; padding: 24px; border-radius: 8px;">
  <h2 style="margin: 0 0 16px; color: #111827;">New SMS Reply Received</h2>
  <table style="width:100%; border-collapse:collapse; background:#fff; border-radius:6px; overflow:hidden; border:1px solid #e5e7eb;">
    <tr><td style="padding:10px 14px; background:#f3f4f6; font-weight:600; width:140px; color:#374151;">From</td>
        <td style="padding:10px 14px; color:#111827;">{from_phone}</td></tr>
    {'<tr><td style="padding:10px 14px; background:#f3f4f6; font-weight:600; color:#374151;">Business</td><td style="padding:10px 14px; color:#111827;">' + business_name + '</td></tr>' if business_name else ''}
    <tr><td style="padding:10px 14px; background:#f3f4f6; font-weight:600; color:#374151;">Action</td>
        <td style="padding:10px 14px; color:#111827;">{action_label}</td></tr>
    <tr><td style="padding:10px 14px; background:#f3f4f6; font-weight:600; color:#374151; vertical-align:top;">Message</td>
        <td style="padding:10px 14px; color:#111827; font-style:italic;">"{message_body}"</td></tr>
  </table>
  <p style="margin:16px 0 0; font-size:13px; color:#6b7280;">
    View all messages at <a href="https://web.lavish.solutions/messages" style="color:#7c3aed;">web.lavish.solutions/messages</a>
  </p>
</div>
"""
        body_text = (
            f"New SMS reply received\n\n"
            f"From: {from_phone}\n"
            + (f"Business: {business_name}\n" if business_name else "")
            + f"Action: {action_label}\n"
            f"Message: {message_body}\n\n"
            f"View: https://web.lavish.solutions/messages"
        )

        sender = EmailSender()
        await sender.provider.send_email(
            to_email=admin_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )
    except Exception as exc:
        logger.error("Failed to send admin reply notification: %s", exc, exc_info=True)
