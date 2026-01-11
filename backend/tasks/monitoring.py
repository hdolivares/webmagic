"""
Monitoring and health check tasks.
Tracks system health, task status, and sends notifications.
"""
from celery_app import celery_app
from sqlalchemy import select, func
from datetime import datetime, timedelta
import logging

from core.database import get_db_session
from models.business import Business
from models.site import GeneratedSite
from models.campaign import Campaign
from models.customer import Customer, Subscription, Payment
from models.coverage import CoverageGrid

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
async def health_check(self):
    """
    Perform system health check.
    Checks database connectivity and basic metrics.
    """
    logger.info("Starting health_check task")
    
    try:
        async with get_db_session() as db:
            # Test database connection
            await db.execute(select(1))
            
            # Collect basic metrics
            metrics = {}
            
            # Business metrics
            total_businesses = await db.execute(select(func.count(Business.id)))
            metrics["total_businesses"] = total_businesses.scalar()
            
            qualified_leads = await db.execute(
                select(func.count(Business.id)).where(Business.status == "qualified")
            )
            metrics["qualified_leads"] = qualified_leads.scalar()
            
            # Site metrics
            total_sites = await db.execute(select(func.count(GeneratedSite.id)))
            metrics["total_sites"] = total_sites.scalar()
            
            generating_sites = await db.execute(
                select(func.count(GeneratedSite.id)).where(GeneratedSite.status == "generating")
            )
            metrics["generating_sites"] = generating_sites.scalar()
            
            failed_sites = await db.execute(
                select(func.count(GeneratedSite.id)).where(GeneratedSite.status == "failed")
            )
            metrics["failed_sites"] = failed_sites.scalar()
            
            # Campaign metrics
            total_campaigns = await db.execute(select(func.count(Campaign.id)))
            metrics["total_campaigns"] = total_campaigns.scalar()
            
            sent_campaigns = await db.execute(
                select(func.count(Campaign.id)).where(Campaign.status == "sent")
            )
            metrics["sent_campaigns"] = sent_campaigns.scalar()
            
            # Customer metrics
            total_customers = await db.execute(select(func.count(Customer.id)))
            metrics["total_customers"] = total_customers.scalar()
            
            active_subscriptions = await db.execute(
                select(func.count(Subscription.id)).where(Subscription.status == "active")
            )
            metrics["active_subscriptions"] = active_subscriptions.scalar()
            
            # Health status
            health_status = "healthy"
            issues = []
            
            # Check for stuck generations
            if metrics["generating_sites"] > 10:
                issues.append(f"{metrics['generating_sites']} sites stuck in generating")
                health_status = "degraded"
            
            # Check for high failure rate
            if metrics["failed_sites"] > 50:
                issues.append(f"{metrics['failed_sites']} failed site generations")
                health_status = "degraded"
            
            logger.info(f"Health check completed: {health_status}")
            return {
                "status": health_status,
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": metrics,
                "issues": issues
            }
            
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@celery_app.task(bind=True)
async def cleanup_stuck_tasks(self):
    """
    Clean up tasks that have been stuck in processing state too long.
    """
    logger.info("Starting cleanup_stuck_tasks task")
    
    try:
        async with get_db_session() as db:
            cutoff_time = datetime.utcnow() - timedelta(hours=2)
            
            # Find stuck coverage grids
            stuck_grids = await db.execute(
                select(CoverageGrid).where(
                    CoverageGrid.status == "processing",
                    CoverageGrid.updated_at < cutoff_time
                )
            )
            grids = stuck_grids.scalars().all()
            
            # Reset to pending
            for grid in grids:
                from sqlalchemy import update
                await db.execute(
                    update(CoverageGrid)
                    .where(CoverageGrid.id == grid.id)
                    .values(status="pending", updated_at=datetime.utcnow())
                )
            
            # Find stuck site generations
            stuck_sites = await db.execute(
                select(GeneratedSite).where(
                    GeneratedSite.status == "generating",
                    GeneratedSite.generation_started_at < cutoff_time
                )
            )
            sites = stuck_sites.scalars().all()
            
            # Mark as failed
            for site in sites:
                from sqlalchemy import update
                await db.execute(
                    update(GeneratedSite)
                    .where(GeneratedSite.id == site.id)
                    .values(
                        status="failed",
                        error_message="Task timeout - stuck in generating",
                        updated_at=datetime.utcnow()
                    )
                )
            
            # Find stuck campaigns
            stuck_campaigns = await db.execute(
                select(Campaign).where(
                    Campaign.status == "sending",
                    Campaign.updated_at < cutoff_time
                )
            )
            campaigns = stuck_campaigns.scalars().all()
            
            # Reset to draft
            for campaign in campaigns:
                from sqlalchemy import update
                await db.execute(
                    update(Campaign)
                    .where(Campaign.id == campaign.id)
                    .values(status="draft", updated_at=datetime.utcnow())
                )
            
            await db.commit()
            
            logger.info(
                f"Cleaned up {len(grids)} grids, {len(sites)} sites, {len(campaigns)} campaigns"
            )
            return {
                "status": "completed",
                "grids_reset": len(grids),
                "sites_failed": len(sites),
                "campaigns_reset": len(campaigns)
            }
            
    except Exception as e:
        logger.error(f"Error in cleanup_stuck_tasks: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True)
async def generate_daily_report(self):
    """
    Generate daily performance report.
    """
    logger.info("Starting generate_daily_report task")
    
    try:
        async with get_db_session() as db:
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            # Businesses scraped yesterday
            businesses_scraped = await db.execute(
                select(func.count(Business.id)).where(
                    Business.created_at >= yesterday
                )
            )
            
            # Sites generated yesterday
            sites_generated = await db.execute(
                select(func.count(GeneratedSite.id)).where(
                    GeneratedSite.generation_completed_at >= yesterday
                )
            )
            
            # Campaigns sent yesterday
            campaigns_sent = await db.execute(
                select(func.count(Campaign.id)).where(
                    Campaign.sent_at >= yesterday
                )
            )
            
            # Payments received yesterday
            payments_received = await db.execute(
                select(func.count(Payment.id)).where(
                    Payment.paid_at >= yesterday,
                    Payment.status == "completed"
                )
            )
            
            # Revenue yesterday
            revenue = await db.execute(
                select(func.sum(Payment.amount_cents)).where(
                    Payment.paid_at >= yesterday,
                    Payment.status == "completed"
                )
            )
            
            report = {
                "date": yesterday.date().isoformat(),
                "businesses_scraped": businesses_scraped.scalar() or 0,
                "sites_generated": sites_generated.scalar() or 0,
                "campaigns_sent": campaigns_sent.scalar() or 0,
                "payments_received": payments_received.scalar() or 0,
                "revenue_cents": revenue.scalar() or 0
            }
            
            logger.info(f"Daily report generated: {report}")
            # TODO: Send report via email/Slack
            
            return {"status": "completed", "report": report}
            
    except Exception as e:
        logger.error(f"Error generating daily report: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True)
async def alert_on_failures(self):
    """
    Send alerts if failure rates are too high.
    """
    logger.info("Starting alert_on_failures task")
    
    try:
        async with get_db_session() as db:
            last_hour = datetime.utcnow() - timedelta(hours=1)
            
            # Check site generation failures
            recent_sites = await db.execute(
                select(func.count(GeneratedSite.id)).where(
                    GeneratedSite.updated_at >= last_hour
                )
            )
            total_recent = recent_sites.scalar() or 0
            
            failed_sites = await db.execute(
                select(func.count(GeneratedSite.id)).where(
                    GeneratedSite.updated_at >= last_hour,
                    GeneratedSite.status == "failed"
                )
            )
            failed_count = failed_sites.scalar() or 0
            
            alerts = []
            
            if total_recent > 0:
                failure_rate = failed_count / total_recent
                if failure_rate > 0.5:  # More than 50% failure rate
                    alerts.append({
                        "type": "site_generation_failures",
                        "message": f"High site generation failure rate: {failure_rate*100:.1f}%",
                        "failed_count": failed_count,
                        "total_count": total_recent
                    })
            
            # Check campaign send failures
            recent_campaigns = await db.execute(
                select(func.count(Campaign.id)).where(
                    Campaign.updated_at >= last_hour
                )
            )
            total_campaigns = recent_campaigns.scalar() or 0
            
            failed_campaigns = await db.execute(
                select(func.count(Campaign.id)).where(
                    Campaign.updated_at >= last_hour,
                    Campaign.status == "failed"
                )
            )
            failed_campaign_count = failed_campaigns.scalar() or 0
            
            if total_campaigns > 0:
                campaign_failure_rate = failed_campaign_count / total_campaigns
                if campaign_failure_rate > 0.3:  # More than 30% failure rate
                    alerts.append({
                        "type": "campaign_send_failures",
                        "message": f"High campaign failure rate: {campaign_failure_rate*100:.1f}%",
                        "failed_count": failed_campaign_count,
                        "total_count": total_campaigns
                    })
            
            if alerts:
                logger.warning(f"Alerts triggered: {alerts}")
                # TODO: Send alerts via email/Slack/PagerDuty
            else:
                logger.info("No alerts to send")
            
            return {
                "status": "completed",
                "alerts_count": len(alerts),
                "alerts": alerts
            }
            
    except Exception as e:
        logger.error(f"Error in alert_on_failures: {str(e)}", exc_info=True)
        raise
