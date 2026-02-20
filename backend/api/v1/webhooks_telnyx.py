"""
Telnyx Webhook Endpoints.

Handles incoming webhooks from Telnyx for:
- SMS delivery status updates (message.sent, message.finalized)
- Incoming SMS replies (message.received) - opt-outs, feedback

Updated: February 2026
- Migrated from Twilio to Telnyx
- JSON payload format (not form-encoded)
- Integrated CRM lifecycle service for automated status tracking

Author: WebMagic Team
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Dict, Any
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

router = APIRouter(prefix="/telnyx", tags=["Telnyx Webhooks"])


async def _notify_admin_reply(
    from_phone: str,
    message_body: str,
    business_name: str | None,
    action: str
) -> None:
    """Fire-and-forget email to admin when an SMS reply is received."""
    try:
        admin_email = _settings.SUPPORT_ADMIN_EMAIL
        action_label = {
            "opt_out": "🚫 Opt-out (STOP)",
            "reply": "💬 Reply",
        }.get(action, f"ℹ️ {action.capitalize()}")

        subject = f"SMS Reply Received — {from_phone}"
        if business_name:
            subject = f"SMS Reply from {business_name} — {from_phone}"

        body_html = f"""
<div style="font-family: sans-serif; max-width: 560px; margin: 0 auto; background: #f9fafb; padding: 24px; border-radius: 8px;">
  <h2 style="margin: 0 0 16px; color: #111827;">📱 New SMS Reply Received</h2>
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
        logger.info(f"Admin reply notification sent to {admin_email} for {from_phone}")
    except Exception as e:
        logger.error(f"Failed to send admin reply notification: {e}", exc_info=True)

# Telnyx status mapping to internal status
TELNYX_STATUS_MAP = {
    "queued": "pending",
    "sending": "sent",
    "sent": "sent",
    "delivered": "delivered",
    "sending_failed": "failed",
    "delivery_failed": "failed",
    "delivery_unconfirmed": "sent",  # Carrier didn't confirm but likely delivered
}


# ============================================================================
# SMS STATUS CALLBACKS
# ============================================================================

@router.post("/status")
async def handle_sms_status_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Telnyx SMS status callback.
    
    Telnyx sends status updates as JSON webhooks:
    - message.sent: Message accepted by carrier
    - message.finalized: Final delivery status (delivered/failed)
    
    Endpoint: POST /api/v1/webhooks/telnyx/status
    
    Returns:
        200: Status updated successfully
        400: Invalid payload
        404: Campaign not found
    """
    try:
        # Parse JSON payload from Telnyx
        json_data = await request.json()
        
        # Extract event data
        data = json_data.get("data", {})
        event_type = data.get("event_type", "")
        payload = data.get("payload", {})
        
        # Get message details
        message_id = payload.get("id")
        
        if not message_id:
            logger.warning("Telnyx callback missing message ID")
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Missing message ID in payload"
            )
        
        # Get status from 'to' array
        to_info = payload.get("to", [{}])
        if isinstance(to_info, list) and len(to_info) > 0:
            message_status = to_info[0].get("status", "unknown")
        else:
            message_status = "unknown"
        
        logger.info(
            f"Telnyx status callback: {message_id} -> {message_status} "
            f"(event: {event_type})"
        )
        
        # Find campaign by Telnyx message ID
        # Note: We store the message ID in sms_sid column (reusing existing column)
        result = await db.execute(
            select(Campaign).where(Campaign.sms_sid == message_id)
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            logger.warning(f"Campaign not found for Telnyx ID: {message_id}")
            # Return 200 anyway to prevent Telnyx retries
            return {
                "status": "ok",
                "message": "Campaign not found (may have been deleted)"
            }
        
        # Map Telnyx status to internal status
        new_status = TELNYX_STATUS_MAP.get(message_status, campaign.status)
        
        # Build update values
        update_values = {
            "status": new_status,
            "updated_at": datetime.utcnow()
        }
        
        # Add delivered timestamp for final delivery
        if message_status == "delivered" and not campaign.delivered_at:
            update_values["delivered_at"] = datetime.utcnow()
        
        # Extract error information if present
        errors = payload.get("errors", [])
        if errors:
            error_info = errors[0]
            error_code = error_info.get("code", "unknown")
            error_detail = error_info.get("detail", "Unknown error")
            update_values["error_message"] = f"Telnyx Error {error_code}: {error_detail}"
        
        # Extract cost if provided (Telnyx sends cost in finalized webhook)
        cost_info = payload.get("cost", {})
        if cost_info:
            cost_amount = cost_info.get("amount")
            if cost_amount:
                try:
                    update_values["sms_cost"] = float(cost_amount)
                except (ValueError, TypeError):
                    pass
        
        # Update campaign
        await db.execute(
            update(Campaign)
            .where(Campaign.id == campaign.id)
            .values(**update_values)
        )
        await db.commit()
        
        logger.info(
            f"Updated campaign {campaign.id} status: "
            f"{campaign.status} -> {new_status}"
        )
        
        # CRM Integration: Update business contact status
        if campaign.business_id and message_status in ["delivered", "sending_failed", "delivery_failed"]:
            lifecycle_service = BusinessLifecycleService(db)
            
            try:
                if message_status == "delivered":
                    # SMS was delivered: pending → sms_sent
                    await lifecycle_service.mark_campaign_sent(
                        campaign.business_id,
                        channel="sms"
                    )
                    logger.info(
                        f"Updated business {campaign.business_id}: "
                        f"contact_status=sms_sent (SMS delivered)"
                    )
                elif message_status in ["sending_failed", "delivery_failed"]:
                    # SMS bounced/failed
                    await lifecycle_service.mark_bounced(campaign.business_id)
                    logger.info(
                        f"Updated business {campaign.business_id}: "
                        f"contact_status=bounced (SMS failed)"
                    )
                
                await db.commit()
            except Exception as e:
                logger.error(
                    f"Error updating CRM status for business {campaign.business_id}: {e}",
                    exc_info=True
                )
                # Don't fail the webhook - campaign status was already updated
        elif not campaign.business_id:
            logger.warning(
                f"Campaign {campaign.id} has no business_id for CRM tracking"
            )
        
        return {
            "status": "ok",
            "campaign_id": str(campaign.id),
            "new_status": new_status
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Telnyx status callback error: {e}", exc_info=True)
        # Return 200 to prevent Telnyx retries on our errors
        return {
            "status": "error",
            "message": "Internal server error"
        }


# ============================================================================
# INCOMING SMS REPLIES
# ============================================================================

@router.post("/reply")
async def handle_incoming_sms(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle incoming SMS replies from recipients.
    
    Telnyx sends inbound messages as JSON with event_type: message.received
    
    Processes:
    - STOP keywords (opt-out)
    - Regular replies (feedback, questions)
    
    Endpoint: POST /api/v1/webhooks/telnyx/reply
    
    Telnyx JSON Payload:
    - data.payload.from.phone_number: Sender phone (E.164)
    - data.payload.to[0].phone_number: Your Telnyx number
    - data.payload.text: Message text
    
    Returns:
        200: Reply processed (no auto-response sent)
    """
    try:
        # Parse JSON payload from Telnyx
        json_data = await request.json()
        
        # Extract event data
        data = json_data.get("data", {})
        event_type = data.get("event_type", "")
        payload = data.get("payload", {})
        
        # Validate event type
        if event_type != "message.received":
            logger.info(f"Ignoring Telnyx event type: {event_type}")
            return {"status": "ok", "message": "Event type not handled"}
        
        # Extract message details
        from_info = payload.get("from", {})
        from_phone = from_info.get("phone_number")
        
        to_info = payload.get("to", [{}])
        if isinstance(to_info, list) and len(to_info) > 0:
            to_phone = to_info[0].get("phone_number")
        else:
            to_phone = None
        
        message_body = payload.get("text", "")
        message_id = payload.get("id")
        
        if not from_phone or not message_body:
            logger.warning("Telnyx reply missing from_phone or text")
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Missing from phone or message text"
            )
        
        logger.info(f"Incoming SMS from {from_phone}: {message_body[:50]}...")
        
        # Store the inbound message in sms_messages table
        # (We'll link to campaign/business after finding them)
        inbound_message = SMSMessage.create_inbound(
            from_phone=from_phone,
            to_phone=to_phone or "",
            body=message_body,
            telnyx_message_id=message_id
        )
        
        # Find campaign(s) sent to this phone number
        result = await db.execute(
            select(Campaign)
            .where(Campaign.recipient_phone == from_phone)
            .order_by(Campaign.sent_at.desc())
        )
        campaigns = result.scalars().all()
        
        if not campaigns:
            logger.warning(f"No campaigns found for phone: {from_phone}")

            # Fuzzy-match the phone number to a known business as a fallback
            matched_business = await ConversationService().match_phone_to_business(
                db=db, phone=from_phone
            )
            if matched_business:
                inbound_message.business_id = matched_business.business_id \
                    if hasattr(matched_business, "business_id") \
                    else matched_business.id
                logger.info(
                    f"Fuzzy-matched inbound {from_phone} → {matched_business.name}"
                )

            db.add(inbound_message)
            await db.commit()

            # Notify admin, including business name if we found a fuzzy match
            await _notify_admin_reply(
                from_phone=from_phone,
                message_body=message_body,
                business_name=matched_business.name if matched_business else None,
                action="reply",
            )

            # Still process opt-out if needed
            compliance = SMSComplianceService(db)
            await compliance.process_reply(
                phone_number=from_phone,
                reply_message=message_body,
                campaign_id=None
            )

            return {"status": "ok", "message": "Opt-out processed (no campaign found)"}
        
        # Process reply with most recent campaign
        latest_campaign = campaigns[0]
        
        # Link the inbound message to campaign and business
        inbound_message.campaign_id = latest_campaign.id
        inbound_message.business_id = latest_campaign.business_id
        db.add(inbound_message)
        
        compliance = SMSComplianceService(db)
        result = await SMSCampaignHelper.handle_sms_reply(
            phone_number=from_phone,
            message_body=message_body,
            campaign_id=latest_campaign.id,
            sms_compliance=compliance,
            db=db
        )
        
        logger.info(f"Reply processed: {result['action']} from {from_phone}")

        # Email notification to admin
        business_name = latest_campaign.business_name if latest_campaign else None
        await _notify_admin_reply(
            from_phone=from_phone,
            message_body=message_body,
            business_name=business_name,
            action=result['action'],
        )

        # CRM Integration: Update business contact status based on reply
        if latest_campaign.business_id:
            lifecycle_service = BusinessLifecycleService(db)
            
            try:
                if result['action'] == 'opt_out':
                    # Customer opted out: any → unsubscribed
                    await lifecycle_service.mark_unsubscribed(latest_campaign.business_id)
                    logger.info(
                        f"Updated business {latest_campaign.business_id}: "
                        f"contact_status=unsubscribed (SMS opt-out)"
                    )
                elif result['action'] == 'reply':
                    # Customer replied: any → replied
                    await lifecycle_service.mark_replied(latest_campaign.business_id)
                    logger.info(
                        f"Updated business {latest_campaign.business_id}: "
                        f"contact_status=replied (SMS reply received)"
                    )
                
                await db.commit()
            except Exception as e:
                logger.error(
                    f"Error updating CRM status for business {latest_campaign.business_id}: {e}",
                    exc_info=True
                )
                # Don't fail the webhook
        
        # Return success (Telnyx doesn't expect TwiML, just HTTP 200)
        return {
            "status": "ok",
            "action": result['action'],
            "campaign_id": str(latest_campaign.id)
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Telnyx reply handling error: {e}", exc_info=True)
        # Return 200 to prevent Telnyx retries
        return {
            "status": "error",
            "message": "Internal server error"
        }


# ============================================================================
# COMBINED WEBHOOK ENDPOINT (Optional - for single webhook URL)
# ============================================================================

@router.post("/webhook")
async def handle_telnyx_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Combined webhook endpoint that routes based on event_type.
    
    This allows configuring a single webhook URL in Telnyx portal
    that handles all event types:
    - message.sent / message.finalized → status updates
    - message.received → incoming replies
    
    Endpoint: POST /api/v1/webhooks/telnyx/webhook
    """
    try:
        json_data = await request.json()
        data = json_data.get("data", {})
        event_type = data.get("event_type", "")
        
        logger.info(f"Telnyx webhook received: {event_type}")
        
        # Route to appropriate handler based on event type
        if event_type in ["message.sent", "message.finalized"]:
            # Recreate request with same body for handler
            return await handle_sms_status_callback(request, db)
        
        elif event_type == "message.received":
            return await handle_incoming_sms(request, db)
        
        else:
            logger.info(f"Unhandled Telnyx event type: {event_type}")
            return {"status": "ok", "message": f"Event type {event_type} not handled"}
    
    except Exception as e:
        logger.error(f"Telnyx webhook error: {e}", exc_info=True)
        return {"status": "error", "message": "Internal server error"}

