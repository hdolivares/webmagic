"""
Campaign management service.
Orchestrates multi-channel (email + SMS) generation, sending, and tracking.

Updated: January 22, 2026
- Integrated CRM lifecycle service for automated status tracking
- Campaign sends now update business contact_status automatically
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from uuid import UUID
from datetime import datetime, timedelta
import logging

from models.campaign import Campaign
from models.business import Business
from models.site import GeneratedSite
from services.pitcher.email_generator import EmailGenerator
from services.pitcher.email_sender import EmailSender
from services.pitcher.tracking import EmailTracker
from services.pitcher.sms_campaign_helper import SMSCampaignHelper
from services.sms import SMSGenerator, SMSSender, PhoneValidator, SMSComplianceService
from services.crm import BusinessLifecycleService
from core.exceptions import DatabaseException, ValidationException
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CampaignService:
    """
    Multi-channel campaign management service.
    
    Supports:
    - Email campaigns (primary)
    - SMS campaigns (for businesses without email)
    - Intelligent channel selection (auto)
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Email services (lazy-loaded)
        self.email_generator = EmailGenerator()
        self._email_sender = None
        self.tracker = EmailTracker(db)
        
        # SMS services (lazy-loaded)
        self._sms_generator = None
        self._sms_sender = None
        self._sms_compliance = None
    
    @property
    def email_sender(self) -> EmailSender:
        """Lazy-load email sender only when needed."""
        if self._email_sender is None:
            try:
                self._email_sender = EmailSender()
            except Exception as e:
                logger.error(f"Failed to initialize email sender: {e}")
                raise ValueError(
                    "Email sender not configured. Set BREVO_API_KEY, SENDGRID_API_KEY, "
                    "or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY in .env to send emails."
                )
        return self._email_sender
    
    @property
    def sms_generator(self) -> SMSGenerator:
        """Lazy-load SMS generator only when needed."""
        if self._sms_generator is None:
            try:
                self._sms_generator = SMSGenerator()
            except Exception as e:
                logger.error(f"Failed to initialize SMS generator: {e}")
                raise ValueError(
                    "SMS generator not configured. Set ANTHROPIC_API_KEY in .env."
                )
        return self._sms_generator
    
    @property
    def sms_sender(self) -> SMSSender:
        """Lazy-load SMS sender only when needed."""
        if self._sms_sender is None:
            try:
                self._sms_sender = SMSSender()
            except Exception as e:
                logger.error(f"Failed to initialize SMS sender: {e}")
                raise ValueError(
                    "SMS sender not configured. Set TWILIO_ACCOUNT_SID, "
                    "TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in .env to send SMS."
                )
        return self._sms_sender
    
    @property
    def sms_compliance(self) -> SMSComplianceService:
        """Lazy-load SMS compliance service only when needed."""
        if self._sms_compliance is None:
            self._sms_compliance = SMSComplianceService(self.db)
        return self._sms_compliance
    
    async def create_campaign(
        self,
        business_id: UUID,
        site_id: Optional[UUID] = None,
        channel: str = "auto",
        variant: str = "default",
        scheduled_for: Optional[datetime] = None
    ) -> Campaign:
        """
        Create a new multi-channel campaign for a business.
        
        Args:
            business_id: Business UUID
            site_id: Optional generated site UUID
            channel: Channel selection ("auto", "email", "sms", "both")
            variant: Campaign variant (default, direct, story, value, professional, friendly, urgent)
            scheduled_for: Optional schedule time
            
        Returns:
            Created Campaign instance
            
        Raises:
            ValidationException: If business not found or no contact method available
        """
        logger.info(f"Creating {channel} campaign for business: {business_id}")
        
        # Get business
        business = await self._get_business(business_id)
        
        # Determine channel based on available contact methods
        selected_channel = self._select_channel(channel, business)
        
        # Get site URL if provided
        site_url = await self._get_site_url(site_id) if site_id else None
        
        # Create campaign based on selected channel
        if selected_channel == "email":
            return await self._create_email_campaign(
                business=business,
                site_id=site_id,
                site_url=site_url,
                variant=variant,
                scheduled_for=scheduled_for
            )
        elif selected_channel == "sms":
            return await self._create_sms_campaign(
                business=business,
                site_id=site_id,
                site_url=site_url,
                variant=variant,
                scheduled_for=scheduled_for
            )
        else:
            raise ValidationException(f"Invalid channel: {selected_channel}")
    
    # ========================================================================
    # HELPER METHODS - Channel Selection & Campaign Creation
    # ========================================================================
    
    async def _get_business(self, business_id: UUID) -> Business:
        """Get business by ID."""
        result = await self.db.execute(
            select(Business).where(Business.id == business_id)
        )
        business = result.scalar_one_or_none()
        
        if not business:
            raise ValidationException(f"Business not found: {business_id}")
        
        return business
    
    async def _get_site_url(self, site_id: UUID) -> Optional[str]:
        """Get site URL by ID."""
        result = await self.db.execute(
            select(GeneratedSite).where(GeneratedSite.id == site_id)
        )
        site = result.scalar_one_or_none()
        return site.full_url if site else None
    
    def _select_channel(self, requested_channel: str, business: Business) -> str:
        """
        Select appropriate channel based on request and business contact info.
        
        Args:
            requested_channel: User's channel preference (auto, email, sms, both)
            business: Business instance
        
        Returns:
            Selected channel: "email" or "sms"
        
        Raises:
            ValidationException: If no valid channel available
        """
        has_email = bool(business.email)
        has_phone = bool(business.phone)
        
        if requested_channel == "auto":
            # Prefer email (free), fallback to SMS
            if has_email:
                logger.info(f"Auto-selected email for {business.name}")
                return "email"
            elif has_phone:
                logger.info(f"Auto-selected SMS for {business.name} (no email)")
                return "sms"
            else:
                raise ValidationException(
                    f"Business {business.name} has no email or phone"
                )
        
        elif requested_channel == "email":
            if not has_email:
                raise ValidationException(
                    f"Business {business.name} has no email address"
                )
            return "email"
        
        elif requested_channel == "sms":
            if not has_phone:
                raise ValidationException(
                    f"Business {business.name} has no phone number"
                )
            return "sms"
        
        else:
            raise ValidationException(
                f"Invalid channel: {requested_channel}. "
                "Valid options: auto, email, sms"
            )
    
    async def _create_email_campaign(
        self,
        business: Business,
        site_id: Optional[UUID],
        site_url: Optional[str],
        variant: str,
        scheduled_for: Optional[datetime]
    ) -> Campaign:
        """Create email campaign."""
        # Prepare business data
        business_data = {
            "name": business.name,
            "category": business.category,
            "city": business.city,
            "state": business.state,
            "rating": float(business.rating) if business.rating else 0,
            "review_count": business.review_count
        }
        
        # Generate email content
        email = await self.email_generator.generate_email(
            business_data=business_data,
            site_url=site_url,
            review_highlight=business.review_highlight,
            variant=variant
        )
        
        # Create campaign
        campaign = Campaign(
            business_id=business.id,
            site_id=site_id,
            channel="email",
            subject_line=email["subject_line"],
            email_body=email["email_body"],
            preview_text=email.get("preview_text"),
            review_highlight=business.review_highlight,
            business_name=business.name,
            recipient_email=business.email,
            variant=variant,
            scheduled_for=scheduled_for,
            status="scheduled" if scheduled_for else "pending"
        )
        
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        
        logger.info(f"Email campaign created: {campaign.id}")
        return campaign
    
    async def _create_sms_campaign(
        self,
        business: Business,
        site_id: Optional[UUID],
        site_url: Optional[str],
        variant: str,
        scheduled_for: Optional[datetime]
    ) -> Campaign:
        """Create SMS campaign with compliance checks."""
        # Validate phone number
        is_valid, formatted_phone, error = PhoneValidator.validate_and_format(
            business.phone
        )
        
        if not is_valid:
            raise ValidationException(f"Invalid phone number: {error}")
        
        # Check compliance (opt-out, business hours)
        can_send, reason = await self.sms_compliance.check_can_send(
            phone_number=formatted_phone,
            timezone_str="America/Chicago"  # TODO: Get from business location
        )
        
        if not can_send:
            raise ValidationException(f"Cannot send SMS: {reason}")
        
        # Prepare business data
        business_data = {
            "name": business.name,
            "category": business.category,
            "city": business.city,
            "state": business.state,
            "rating": float(business.rating) if business.rating else 0
        }
        
        # Generate SMS content
        sms_body = await self.sms_generator.generate_sms(
            business_data=business_data,
            site_url=site_url,
            variant=variant
        )
        
        # Create campaign
        campaign = Campaign(
            business_id=business.id,
            site_id=site_id,
            channel="sms",
            sms_body=sms_body,
            business_name=business.name,
            recipient_phone=formatted_phone,
            variant=variant,
            scheduled_for=scheduled_for,
            status="scheduled" if scheduled_for else "pending"
        )
        
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        
        logger.info(f"SMS campaign created: {campaign.id} ({len(sms_body)} chars)")
        return campaign
    
    # ========================================================================
    # SENDING METHODS
    # ========================================================================
    
    async def send_campaign(self, campaign_id: UUID) -> bool:
        """
        Send a campaign (email or SMS based on channel).
        
        Args:
            campaign_id: Campaign UUID
            
        Returns:
            True if sent successfully
        
        Raises:
            ValidationException: If campaign not found or invalid status
        """
        logger.info(f"Sending campaign: {campaign_id}")
        
        # Get campaign
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            raise ValidationException(f"Campaign not found: {campaign_id}")
        
        if campaign.status not in ["pending", "scheduled"]:
            raise ValidationException(
                f"Campaign already sent or invalid status: {campaign.status}"
            )
        
        # Send based on channel
        if campaign.channel == "email":
            return await self._send_email_campaign(campaign)
        elif campaign.channel == "sms":
            return await self._send_sms_campaign(campaign)
        else:
            raise ValidationException(f"Unsupported channel: {campaign.channel}")
    
    async def _send_email_campaign(self, campaign: Campaign) -> bool:
        """Send email campaign (extracted from original send_campaign)."""
        try:
            # Generate tracking pixel
            tracking_pixel = self.tracker.generate_tracking_pixel_url(campaign.id)
            
            # Convert to HTML
            body_html = self.email_sender.generate_html_from_text(campaign.email_body)
            
            # Send email
            send_result = await self.email_sender.send_campaign_email(
                to_email=campaign.recipient_email,
                subject=campaign.subject_line,
                body_text=campaign.email_body,
                body_html=body_html,
                tracking_pixel=tracking_pixel
            )
            
            # Update campaign
            await self.db.execute(
                update(Campaign)
                .where(Campaign.id == campaign.id)
                .values(
                    status="sent",
                    sent_at=datetime.utcnow(),
                    email_provider=send_result.get("provider"),
                    message_id=send_result.get("message_id"),
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.commit()
            
            # CRM Integration: Update business contact status
            if campaign.business_id:
                lifecycle_service = BusinessLifecycleService(self.db)
                try:
                    await lifecycle_service.mark_campaign_sent(
                        campaign.business_id,
                        channel="email"
                    )
                    await self.db.commit()
                    logger.info(
                        f"Updated business {campaign.business_id}: "
                        f"contact_status=emailed (campaign sent)"
                    )
                except Exception as e:
                    logger.error(
                        f"Error updating CRM status for business {campaign.business_id}: {e}",
                        exc_info=True
                    )
                    # Don't fail the campaign - email was already sent
            else:
                logger.warning(
                    f"Campaign {campaign.id} has no business_id for CRM tracking"
                )
            
            logger.info(f"Email campaign sent successfully: {campaign.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email campaign: {str(e)}")
            
            # Update campaign with error
            await self.db.execute(
                update(Campaign)
                .where(Campaign.id == campaign.id)
                .values(
                    status="failed",
                    error_message=str(e),
                    retry_count=campaign.retry_count + 1,
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.commit()
            
            return False
    
    async def _send_sms_campaign(self, campaign: Campaign) -> bool:
        """Send SMS campaign with compliance checks and tracking."""
        return await SMSCampaignHelper.send_sms_campaign(
            campaign=campaign,
            sms_sender=self.sms_sender,
            sms_compliance=self.sms_compliance,
            db=self.db
        )
    
    # ========================================================================
    # CAMPAIGN RETRIEVAL METHODS
    # ========================================================================
    
    async def get_campaign(self, campaign_id: UUID) -> Optional[Campaign]:
        """Get campaign by ID."""
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        return result.scalar_one_or_none()
    
    async def list_campaigns(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        business_id: Optional[UUID] = None
    ) -> tuple[List[Campaign], int]:
        """List campaigns with pagination."""
        query = select(Campaign)
        count_query = select(func.count(Campaign.id))
        
        conditions = []
        if status:
            conditions.append(Campaign.status == status)
        if business_id:
            conditions.append(Campaign.business_id == business_id)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        query = query.order_by(Campaign.created_at.desc())
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        campaigns = result.scalars().all()
        
        return list(campaigns), total
    
    async def get_pending_campaigns(self, limit: int = 10) -> List[Campaign]:
        """
        Get campaigns ready to be sent.
        Includes pending and scheduled campaigns whose time has come.
        
        Args:
            limit: Maximum number of campaigns to return
            
        Returns:
            List of Campaign instances
        """
        now = datetime.utcnow()
        
        result = await self.db.execute(
            select(Campaign)
            .where(
                or_(
                    Campaign.status == "pending",
                    and_(
                        Campaign.status == "scheduled",
                        Campaign.scheduled_for <= now
                    )
                )
            )
            .order_by(Campaign.scheduled_for.asc().nullsfirst())
            .limit(limit)
        )
        
        return list(result.scalars().all())
    
    async def bulk_create_campaigns(
        self,
        business_ids: List[UUID],
        variant: str = "default"
    ) -> List[Campaign]:
        """
        Create campaigns for multiple businesses.
        
        Args:
            business_ids: List of business UUIDs
            variant: Email variant
            
        Returns:
            List of created campaigns
        """
        campaigns = []
        
        for business_id in business_ids:
            try:
                campaign = await self.create_campaign(
                    business_id=business_id,
                    variant=variant
                )
                campaigns.append(campaign)
            except Exception as e:
                logger.warning(f"Failed to create campaign for {business_id}: {str(e)}")
                continue
        
        await self.db.commit()
        logger.info(f"Created {len(campaigns)} campaigns")
        
        return campaigns
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get campaign statistics."""
        # Total campaigns
        total_result = await self.db.execute(
            select(func.count(Campaign.id))
        )
        total = total_result.scalar()
        
        # By status
        by_status = {}
        status_result = await self.db.execute(
            select(Campaign.status, func.count(Campaign.id))
            .group_by(Campaign.status)
        )
        for status, count in status_result:
            by_status[status] = count
        
        # Sent in last 24h
        yesterday = datetime.utcnow() - timedelta(days=1)
        sent_24h_result = await self.db.execute(
            select(func.count(Campaign.id))
            .where(Campaign.sent_at >= yesterday)
        )
        sent_24h = sent_24h_result.scalar()
        
        # Open rate
        opened_result = await self.db.execute(
            select(func.count(Campaign.id))
            .where(Campaign.opened_at.isnot(None))
        )
        opened = opened_result.scalar()
        
        sent_count = by_status.get("sent", 0) + by_status.get("delivered", 0) + by_status.get("opened", 0) + by_status.get("clicked", 0)
        open_rate = (opened / sent_count * 100) if sent_count > 0 else 0
        
        # Click rate
        clicked_result = await self.db.execute(
            select(func.count(Campaign.id))
            .where(Campaign.clicked_at.isnot(None))
        )
        clicked = clicked_result.scalar()
        click_rate = (clicked / sent_count * 100) if sent_count > 0 else 0
        
        # Reply rate
        replied_result = await self.db.execute(
            select(func.count(Campaign.id))
            .where(Campaign.replied_at.isnot(None))
        )
        replied = replied_result.scalar()
        reply_rate = (replied / sent_count * 100) if sent_count > 0 else 0
        
        return {
            "total_campaigns": total,
            "by_status": by_status,
            "sent_24h": sent_24h,
            "total_sent": sent_count,
            "total_opened": opened,
            "total_clicked": clicked,
            "total_replied": replied,
            "open_rate": round(open_rate, 2),
            "click_rate": round(click_rate, 2),
            "reply_rate": round(reply_rate, 2)
        }


from sqlalchemy import or_
