"""
Automated campaign sending tasks.
Handles email generation and sending for completed sites.
"""
from celery import Task
from celery_app import celery_app
from sqlalchemy import select, update
from datetime import datetime
import logging

from core.database import get_db_session
from models.campaign import Campaign
from models.site import GeneratedSite
from models.business import Business
from services.pitcher.campaign_service import CampaignService
from services.pitcher.email_generator import EmailGenerator
from services.pitcher.email_sender import EmailSender

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
async def send_campaign(self, campaign_id: str):
    """
    Send a specific campaign email.
    
    Args:
        campaign_id: Campaign UUID
    """
    logger.info(f"Sending campaign: {campaign_id}")
    
    try:
        async with get_db_session() as db:
            # Get campaign
            result = await db.execute(
                select(Campaign).where(Campaign.id == campaign_id)
            )
            campaign = result.scalar_one_or_none()
            
            if not campaign:
                logger.error(f"Campaign not found: {campaign_id}")
                return {"status": "error", "message": "Campaign not found"}
            
            if campaign.status == "sent":
                logger.info(f"Campaign {campaign_id} already sent")
                return {"status": "skipped", "message": "Already sent"}
            
            # Update status
            await db.execute(
                update(Campaign)
                .where(Campaign.id == campaign_id)
                .values(status="sending", updated_at=datetime.utcnow())
            )
            await db.commit()
            
            # Send email
            email_sender = EmailSender()
            tracking_info = await email_sender.send_campaign_email(
                campaign_id=str(campaign.id),
                recipient_email=campaign.recipient_email,
                recipient_name=campaign.recipient_name,
                subject=campaign.subject_line,
                body=campaign.email_body,
                tracking_pixel_id=campaign.tracking_pixel_id
            )
            
            # Update campaign
            await db.execute(
                update(Campaign)
                .where(Campaign.id == campaign_id)
                .values(
                    status="sent",
                    sent_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
            
            logger.info(f"Successfully sent campaign {campaign_id}")
            return {
                "status": "completed",
                "campaign_id": campaign_id,
                "tracking_info": tracking_info
            }
            
    except Exception as e:
        logger.error(f"Error sending campaign {campaign_id}: {str(e)}", exc_info=True)
        
        # Mark as failed
        async with get_db_session() as db:
            await db.execute(
                update(Campaign)
                .where(Campaign.id == campaign_id)
                .values(
                    status="failed",
                    error_message=str(e),
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
        
        # Retry
        raise self.retry(exc=e)


@celery_app.task(bind=True)
async def create_campaign_for_site(self, site_id: str):
    """
    Create and send a campaign for a published site.
    
    Args:
        site_id: Site UUID
    """
    logger.info(f"Creating campaign for site: {site_id}")
    
    try:
        async with get_db_session() as db:
            # Get site and business
            site_result = await db.execute(
                select(GeneratedSite).where(GeneratedSite.id == site_id)
            )
            site = site_result.scalar_one_or_none()
            
            if not site or site.status != "published":
                logger.error(f"Site not ready: {site_id}")
                return {"status": "error", "message": "Site not ready"}
            
            business_result = await db.execute(
                select(Business).where(Business.id == site.business_id)
            )
            business = business_result.scalar_one_or_none()
            
            if not business or not business.phone:
                logger.error(f"Business info incomplete: {site.business_id}")
                return {"status": "error", "message": "Business info incomplete"}
            
            # Check if campaign already exists
            campaign_result = await db.execute(
                select(Campaign).where(Campaign.site_id == site_id)
            )
            existing_campaign = campaign_result.scalar_one_or_none()
            
            if existing_campaign:
                logger.info(f"Campaign already exists for site {site_id}")
                return {"status": "skipped", "message": "Campaign exists"}
            
            # Generate email content
            email_generator = EmailGenerator(db)
            email_content = await email_generator.generate_cold_email(
                business_name=business.name,
                business_category=business.category or "business",
                recipient_name=business.name.split()[0]  # First word of business name
            )
            
            # Create campaign
            campaign_service = CampaignService(db)
            campaign = await campaign_service.create_campaign(
                site_id=site.id,
                business_id=business.id,
                recipient_email=business.phone,  # In real app, use email field
                recipient_name=business.name,
                subject_line=email_content["subject"],
                email_body=email_content["body"]
            )
            
            # Queue sending
            send_campaign.delay(str(campaign.id))
            
            logger.info(f"Created and queued campaign for site {site_id}")
            return {
                "status": "completed",
                "campaign_id": str(campaign.id),
                "site_id": site_id
            }
            
    except Exception as e:
        logger.error(f"Error creating campaign for site {site_id}: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True)
async def send_pending_campaigns(self):
    """
    Send all pending/scheduled campaigns.
    Scheduled task that runs periodically.
    """
    logger.info("Starting send_pending_campaigns task")
    
    try:
        async with get_db_session() as db:
            # Find draft/scheduled campaigns
            result = await db.execute(
                select(Campaign)
                .where(Campaign.status.in_(["draft", "scheduled"]))
                .limit(20)  # Send up to 20 per run to avoid rate limits
            )
            campaigns = result.scalars().all()
            
            if not campaigns:
                logger.info("No pending campaigns to send")
                return {"status": "completed", "campaigns_queued": 0}
            
            # Queue sending tasks
            campaigns_queued = 0
            for campaign in campaigns:
                send_campaign.delay(str(campaign.id))
                campaigns_queued += 1
            
            logger.info(f"Queued {campaigns_queued} campaign sending tasks")
            return {
                "status": "completed",
                "campaigns_queued": campaigns_queued
            }
            
    except Exception as e:
        logger.error(f"Error in send_pending_campaigns: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True)
async def create_campaigns_for_new_sites(self):
    """
    Create campaigns for newly published sites.
    """
    logger.info("Starting create_campaigns_for_new_sites task")
    
    try:
        async with get_db_session() as db:
            # Find published sites without campaigns
            result = await db.execute(
                select(GeneratedSite)
                .where(GeneratedSite.status == "published")
                .outerjoin(Campaign, GeneratedSite.id == Campaign.site_id)
                .where(Campaign.id == None)
                .limit(10)  # Create up to 10 campaigns per run
            )
            sites = result.scalars().all()
            
            if not sites:
                logger.info("No new sites needing campaigns")
                return {"status": "completed", "campaigns_created": 0}
            
            # Queue campaign creation
            campaigns_created = 0
            for site in sites:
                create_campaign_for_site.delay(str(site.id))
                campaigns_created += 1
            
            logger.info(f"Queued {campaigns_created} campaign creation tasks")
            return {
                "status": "completed",
                "campaigns_created": campaigns_created
            }
            
    except Exception as e:
        logger.error(f"Error in create_campaigns_for_new_sites: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True)
async def retry_failed_campaigns(self):
    """
    Retry failed campaign sends.
    """
    logger.info("Starting retry_failed_campaigns task")
    
    try:
        async with get_db_session() as db:
            # Find failed campaigns
            result = await db.execute(
                select(Campaign)
                .where(Campaign.status == "failed")
                .limit(5)  # Retry up to 5 per run
            )
            campaigns = result.scalars().all()
            
            if not campaigns:
                logger.info("No failed campaigns to retry")
                return {"status": "completed", "retries_queued": 0}
            
            # Reset and queue
            retries_queued = 0
            for campaign in campaigns:
                await db.execute(
                    update(Campaign)
                    .where(Campaign.id == campaign.id)
                    .values(
                        status="draft",
                        error_message=None,
                        updated_at=datetime.utcnow()
                    )
                )
                send_campaign.delay(str(campaign.id))
                retries_queued += 1
            
            await db.commit()
            
            logger.info(f"Queued {retries_queued} campaign retries")
            return {
                "status": "completed",
                "retries_queued": retries_queued
            }
            
    except Exception as e:
        logger.error(f"Error in retry_failed_campaigns: {str(e)}", exc_info=True)
        raise
