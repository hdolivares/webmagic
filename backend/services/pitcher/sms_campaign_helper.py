"""
SMS Campaign Helper Methods.

Separated helper methods for SMS campaign sending to keep CampaignService modular.

Updated: January 22, 2026
- Integrated CRM lifecycle service for automated status tracking

Author: WebMagic Team
Date: January 21, 2026
"""
import logging
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from models.campaign import Campaign
from models.sms_message import SMSMessage
from services.sms import SMSSender, SMSComplianceService
from services.crm import BusinessLifecycleService
from core.config import get_settings
from core.exceptions import ExternalAPIException, ValidationException

logger = logging.getLogger(__name__)
settings = get_settings()


class SMSCampaignHelper:
    """Helper class for SMS campaign operations."""
    
    @staticmethod
    async def send_sms_campaign(
        campaign: Campaign,
        sms_sender: SMSSender,
        sms_compliance: SMSComplianceService,
        db: AsyncSession,
        timezone_str: str = "America/Chicago",
        preferred_only: bool = False,
    ) -> bool:
        """
        Send SMS campaign with full compliance checks and tracking.

        Args:
            campaign:       Campaign instance
            sms_sender:     SMS sender service
            sms_compliance: Compliance service
            db:             Database session
            timezone_str:   Recipient's IANA timezone (use business state, not Chicago default)
            preferred_only: When True (autopilot), enforce preferred engagement windows
                            (1–5 PM, 7–9 PM, 10 AM–12 PM) in addition to TCPA quiet hours.

        Returns:
            True if sent successfully (False if compliance skipped, not a hard failure)
        """
        try:
            # Final compliance check before sending
            can_send, reason = await sms_compliance.check_can_send(
                phone_number=campaign.recipient_phone,
                timezone_str=timezone_str,
                preferred_only=preferred_only,
            )
            
            if not can_send:
                is_window_skip = reason and "preferred send window" in reason
                if is_window_skip:
                    # Outside preferred window (autopilot only) — silently skip,
                    # leave campaign status as "scheduled" so the next tick retries
                    logger.info(f"Campaign {campaign.id} deferred: {reason}")
                    return False

                # Hard compliance failure (quiet hours, opt-out) — mark as failed
                error_msg = f"Compliance check failed: {reason}"
                logger.warning(f"Campaign {campaign.id}: {error_msg}")
                await db.execute(
                    update(Campaign)
                    .where(Campaign.id == campaign.id)
                    .values(status="failed", error_message=error_msg)
                )
                await db.commit()
                raise ValidationException(error_msg)
            
            # Build status callback URL for delivery tracking (Telnyx)
            callback_url = (
                f"{settings.API_URL}/api/v1/webhooks/telnyx/status"
                if settings.API_URL
                else None
            )
            
            # Send SMS
            logger.info(
                f"Sending SMS campaign {campaign.id} to {campaign.recipient_phone}"
            )
            
            result = await sms_sender.send(
                to_phone=campaign.recipient_phone,
                body=campaign.sms_body,
                status_callback=callback_url
            )
            
            # Update campaign with success data
            await db.execute(
                update(Campaign)
                .where(Campaign.id == campaign.id)
                .values(
                    status="sent",
                    sent_at=datetime.utcnow(),
                    sms_provider=result.get("provider"),
                    sms_sid=result.get("message_id"),
                    sms_segments=result.get("segments", 1),
                    sms_cost=result.get("cost")
                )
            )
            
            # Store outbound message in sms_messages table
            outbound_message = SMSMessage.create_outbound(
                to_phone=campaign.recipient_phone,
                from_phone=result.get("from", settings.TELNYX_PHONE_NUMBER),
                body=campaign.sms_body,
                campaign_id=campaign.id,
                business_id=campaign.business_id,
                telnyx_message_id=result.get("message_id")
            )
            outbound_message.status = "sent"
            outbound_message.segments = result.get("segments", 1)
            outbound_message.cost = result.get("cost")
            db.add(outbound_message)
            
            await db.commit()
            
            # CRM Integration: Update business contact status
            # Note: SMS status will be updated to "delivered" by Twilio webhook
            # Here we just mark it as sent (pending → sms_sent happens on delivery)
            if campaign.business_id:
                lifecycle_service = BusinessLifecycleService(db)
                try:
                    # Mark as sent - will be updated to delivered/failed by webhook
                    await lifecycle_service.mark_campaign_sent(
                        campaign.business_id,
                        channel="sms"
                    )
                    await db.commit()
                    logger.info(
                        f"Updated business {campaign.business_id}: "
                        f"contact_status=sms_sent (SMS queued at Twilio)"
                    )
                except Exception as e:
                    logger.error(
                        f"Error updating CRM status for business {campaign.business_id}: {e}",
                        exc_info=True
                    )
                    # Don't fail the campaign - SMS was already sent
            else:
                logger.warning(
                    f"Campaign {campaign.id} has no business_id for CRM tracking"
                )
            
            logger.info(
                f"SMS campaign {campaign.id} sent successfully "
                f"(SID: {result.get('message_id')}, "
                f"segments: {result.get('segments')}, "
                f"cost: ${result.get('cost', 0):.4f})"
            )
            
            return True
        
        except ExternalAPIException as e:
            # SMS provider error
            error_msg = str(e)
            logger.error(f"SMS send failed for campaign {campaign.id}: {error_msg}")
            
            await db.execute(
                update(Campaign)
                .where(Campaign.id == campaign.id)
                .values(
                    status="failed",
                    error_message=error_msg,
                    retry_count=campaign.retry_count + 1
                )
            )
            await db.commit()
            
            raise
        
        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"SMS campaign {campaign.id} failed: {error_msg}")
            
            await db.execute(
                update(Campaign)
                .where(Campaign.id == campaign.id)
                .values(
                    status="failed",
                    error_message=error_msg,
                    retry_count=campaign.retry_count + 1
                )
            )
            await db.commit()
            
            raise
    
    @staticmethod
    async def handle_sms_reply(
        phone_number: str,
        message_body: str,
        campaign_id: UUID,
        sms_compliance: SMSComplianceService,
        db: AsyncSession
    ) -> dict:
        """
        Handle incoming SMS reply (opt-out, feedback, etc.).
        
        Args:
            phone_number: Phone that replied
            message_body: Reply message
            campaign_id: Campaign being replied to
            sms_compliance: Compliance service
            db: Database session
        
        Returns:
            Dict with action taken and response
        """
        action, is_opt_out = await sms_compliance.process_reply(
            phone_number=phone_number,
            reply_message=message_body,
            campaign_id=campaign_id
        )
        
        if is_opt_out:
            logger.info(f"Phone {phone_number} opted out via reply")
            
            return {
                "action": "opt_out",
                "message": "You have been unsubscribed. You will not receive any more messages."
            }
        
        # Regular reply - update campaign status
        await db.execute(
            update(Campaign)
            .where(Campaign.id == campaign_id)
            .values(
                status="replied",
                replied_at=datetime.utcnow()
            )
        )
        await db.commit()
        
        logger.info(f"Reply received from {phone_number} for campaign {campaign_id}")
        
        return {
            "action": "reply",
            "message": "Thank you for your reply! We'll get back to you soon."
        }

