"""
Twilio Webhook Endpoints.

Handles incoming webhooks from Twilio for:
- SMS delivery status updates
- Incoming SMS replies (opt-outs, feedback)

Author: WebMagic Team  
Date: January 21, 2026
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Dict, Any
import logging
from datetime import datetime

from api.deps import get_db
from models.campaign import Campaign
from services.sms import SMSComplianceService
from services.pitcher.sms_campaign_helper import SMSCampaignHelper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/twilio", tags=["Twilio Webhooks"])


# ============================================================================
# SMS STATUS CALLBACKS
# ============================================================================

@router.post("/status")
async def handle_sms_status_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Twilio SMS status callback.
    
    Twilio sends status updates as the SMS is processed:
    - queued: Message queued at Twilio
    - sent: Sent to carrier
    - delivered: Delivered to recipient
    - undelivered: Failed to deliver
    - failed: Permanent failure
    
    Endpoint: POST /api/v1/webhooks/twilio/status
    
    Returns:
        200: Status updated successfully
        400: Missing required fields
        404: Campaign not found
    """
    try:
        # Parse form data from Twilio
        form_data = await request.form()
        
        message_sid = form_data.get("MessageSid")
        message_status = form_data.get("MessageStatus")
        error_code = form_data.get("ErrorCode")
        error_message = form_data.get("ErrorMessage")
        
        if not message_sid:
            logger.warning("Twilio callback missing MessageSid")
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Missing MessageSid"
            )
        
        logger.info(f"Twilio status callback: {message_sid} -> {message_status}")
        
        # Find campaign by Twilio message SID
        result = await db.execute(
            select(Campaign).where(Campaign.sms_sid == message_sid)
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            logger.warning(f"Campaign not found for Twilio SID: {message_sid}")
            # Return 200 anyway to prevent Twilio retries
            return {
                "status": "ok",
                "message": "Campaign not found (may have been deleted)"
            }
        
        # Map Twilio status to campaign status
        status_map = {
            "queued": "pending",
            "sending": "sent",
            "sent": "sent",
            "delivered": "delivered",
            "undelivered": "failed",
            "failed": "failed"
        }
        
        new_status = status_map.get(message_status, campaign.status)
        
        # Build update values
        update_values = {
            "status": new_status,
            "updated_at": datetime.utcnow()
        }
        
        # Add delivered timestamp
        if message_status == "delivered" and not campaign.delivered_at:
            update_values["delivered_at"] = datetime.utcnow()
        
        # Add error information
        if error_code:
            update_values["error_message"] = (
                f"Twilio Error {error_code}: {error_message or 'Unknown error'}"
            )
        
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
        
        return {
            "status": "ok",
            "campaign_id": str(campaign.id),
            "new_status": new_status
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Twilio status callback error: {e}", exc_info=True)
        # Return 200 to prevent Twilio retries on our errors
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
    
    Processes:
    - STOP keywords (opt-out)
    - Regular replies (feedback, questions)
    
    Endpoint: POST /api/v1/webhooks/twilio/reply
    
    Twilio Form Data:
    - MessageSid: Unique message ID
    - From: Sender phone number (E.164 format)
    - To: Your Twilio number
    - Body: Message text
    
    Returns:
        TwiML response (empty - no auto-reply)
    """
    try:
        # Parse form data from Twilio
        form_data = await request.form()
        
        from_phone = form_data.get("From")  # Sender's phone
        message_body = form_data.get("Body")  # Message text
        message_sid = form_data.get("MessageSid")
        
        if not from_phone or not message_body:
            logger.warning("Twilio reply missing From or Body")
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Missing From or Body"
            )
        
        logger.info(f"Incoming SMS from {from_phone}: {message_body[:50]}...")
        
        # Find campaign(s) sent to this phone number
        result = await db.execute(
            select(Campaign)
            .where(Campaign.recipient_phone == from_phone)
            .order_by(Campaign.sent_at.desc())
        )
        campaigns = result.scalars().all()
        
        if not campaigns:
            logger.warning(f"No campaigns found for phone: {from_phone}")
            # Still process opt-out if needed
            compliance = SMSComplianceService(db)
            await compliance.process_reply(
                phone_number=from_phone,
                reply_message=message_body,
                campaign_id=None
            )
            
            # Return empty TwiML (no auto-reply)
            return _generate_twiml_response()
        
        # Process reply with most recent campaign
        latest_campaign = campaigns[0]
        
        compliance = SMSComplianceService(db)
        result = await SMSCampaignHelper.handle_sms_reply(
            phone_number=from_phone,
            message_body=message_body,
            campaign_id=latest_campaign.id,
            sms_compliance=compliance,
            db=db
        )
        
        logger.info(f"Reply processed: {result['action']} from {from_phone}")
        
        # Return empty TwiML (no auto-reply)
        # In production, you might want to send a confirmation
        return _generate_twiml_response()
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Twilio reply handling error: {e}", exc_info=True)
        # Return empty TwiML to prevent errors on Twilio's side
        return _generate_twiml_response()


def _generate_twiml_response(message: str = None) -> Dict[str, str]:
    """
    Generate TwiML response for Twilio.
    
    Args:
        message: Optional message to send back to user
    
    Returns:
        Dict with TwiML XML
    """
    if message:
        # Send a reply
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{message}</Message>
</Response>"""
    else:
        # No reply (silent)
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response></Response>"""
    
    # Return as XML content type
    from fastapi.responses import Response
    return Response(content=twiml, media_type="application/xml")

