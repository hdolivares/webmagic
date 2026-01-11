"""
WebMagic Conductor - Autopilot Orchestration Script
Coordinates all automated workflows: scraping, generation, campaigns.
Run this script to start the full automation pipeline.
"""
import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, Any

from sqlalchemy import select, func
from core.database import get_db_session
from models.business import Business
from models.site import GeneratedSite
from models.campaign import Campaign
from models.coverage import CoverageGrid
from models.customer import Customer

# Import tasks
from tasks.scraping import (
    scrape_pending_territories,
    qualify_new_leads,
    cleanup_expired_cooldowns
)
from tasks.generation import (
    generate_pending_sites,
    publish_completed_sites,
    retry_failed_generations
)
from tasks.campaigns import (
    create_campaigns_for_new_sites,
    send_pending_campaigns,
    retry_failed_campaigns
)
from tasks.monitoring import (
    health_check,
    cleanup_stuck_tasks,
    generate_daily_report
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('conductor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class Conductor:
    """
    Main orchestration engine for WebMagic automation.
    Coordinates the entire pipeline from scraping to sales.
    """
    
    def __init__(self):
        self.running = False
        self.cycle_count = 0
    
    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current status of the entire pipeline."""
        async with get_db_session() as db:
            # Coverage status
            pending_grids = await db.execute(
                select(func.count(CoverageGrid.id)).where(CoverageGrid.status == "pending")
            )
            
            # Business status
            total_businesses = await db.execute(select(func.count(Business.id)))
            qualified_leads = await db.execute(
                select(func.count(Business.id)).where(Business.status == "qualified")
            )
            
            # Site status
            total_sites = await db.execute(select(func.count(GeneratedSite.id)))
            generating = await db.execute(
                select(func.count(GeneratedSite.id)).where(GeneratedSite.status == "generating")
            )
            completed_sites = await db.execute(
                select(func.count(GeneratedSite.id)).where(GeneratedSite.status == "completed")
            )
            published_sites = await db.execute(
                select(func.count(GeneratedSite.id)).where(GeneratedSite.status == "published")
            )
            
            # Campaign status
            total_campaigns = await db.execute(select(func.count(Campaign.id)))
            sent_campaigns = await db.execute(
                select(func.count(Campaign.id)).where(Campaign.status == "sent")
            )
            opened_campaigns = await db.execute(
                select(func.count(Campaign.id)).where(Campaign.status == "opened")
            )
            
            # Customer status
            total_customers = await db.execute(select(func.count(Customer.id)))
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "coverage": {
                    "pending_territories": pending_grids.scalar() or 0,
                },
                "businesses": {
                    "total": total_businesses.scalar() or 0,
                    "qualified": qualified_leads.scalar() or 0,
                },
                "sites": {
                    "total": total_sites.scalar() or 0,
                    "generating": generating.scalar() or 0,
                    "completed": completed_sites.scalar() or 0,
                    "published": published_sites.scalar() or 0,
                },
                "campaigns": {
                    "total": total_campaigns.scalar() or 0,
                    "sent": sent_campaigns.scalar() or 0,
                    "opened": opened_campaigns.scalar() or 0,
                },
                "customers": {
                    "total": total_customers.scalar() or 0,
                }
            }
    
    async def run_cycle(self) -> Dict[str, Any]:
        """Run one complete automation cycle."""
        self.cycle_count += 1
        logger.info(f"========== CYCLE {self.cycle_count} STARTING ==========")
        
        results = {
            "cycle": self.cycle_count,
            "timestamp": datetime.utcnow().isoformat(),
            "tasks_run": []
        }
        
        try:
            # 1. Health check first
            logger.info("Running health check...")
            health = await health_check()
            results["health_status"] = health
            
            if health.get("status") == "unhealthy":
                logger.error("System unhealthy, skipping cycle")
                return results
            
            # 2. Clean up stuck tasks
            logger.info("Cleaning up stuck tasks...")
            cleanup_result = await cleanup_stuck_tasks()
            results["tasks_run"].append({"task": "cleanup_stuck_tasks", "result": cleanup_result})
            
            # 3. Scraping phase
            logger.info("Phase 1: SCRAPING")
            
            # Clean up expired cooldowns
            cooldown_result = await cleanup_expired_cooldowns()
            results["tasks_run"].append({"task": "cleanup_expired_cooldowns", "result": cooldown_result})
            
            # Scrape pending territories
            scrape_result = await scrape_pending_territories()
            results["tasks_run"].append({"task": "scrape_pending_territories", "result": scrape_result})
            
            # Qualify new leads
            qualify_result = await qualify_new_leads()
            results["tasks_run"].append({"task": "qualify_new_leads", "result": qualify_result})
            
            # 4. Generation phase
            logger.info("Phase 2: SITE GENERATION")
            
            # Retry failed generations
            retry_gen_result = await retry_failed_generations()
            results["tasks_run"].append({"task": "retry_failed_generations", "result": retry_gen_result})
            
            # Generate new sites
            gen_result = await generate_pending_sites()
            results["tasks_run"].append({"task": "generate_pending_sites", "result": gen_result})
            
            # Publish completed sites
            publish_result = await publish_completed_sites()
            results["tasks_run"].append({"task": "publish_completed_sites", "result": publish_result})
            
            # 5. Campaign phase
            logger.info("Phase 3: EMAIL CAMPAIGNS")
            
            # Create campaigns for new sites
            create_campaign_result = await create_campaigns_for_new_sites()
            results["tasks_run"].append({"task": "create_campaigns_for_new_sites", "result": create_campaign_result})
            
            # Retry failed campaigns
            retry_campaign_result = await retry_failed_campaigns()
            results["tasks_run"].append({"task": "retry_failed_campaigns", "result": retry_campaign_result})
            
            # Send pending campaigns
            send_result = await send_pending_campaigns()
            results["tasks_run"].append({"task": "send_pending_campaigns", "result": send_result})
            
            # 6. Get pipeline status
            status = await self.get_pipeline_status()
            results["pipeline_status"] = status
            
            logger.info(f"========== CYCLE {self.cycle_count} COMPLETED ==========")
            logger.info(f"Pipeline Status: {status}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in cycle {self.cycle_count}: {str(e)}", exc_info=True)
            results["error"] = str(e)
            return results
    
    async def run_continuous(self, interval_seconds: int = 300):
        """
        Run continuously with specified interval between cycles.
        
        Args:
            interval_seconds: Seconds to wait between cycles (default: 5 minutes)
        """
        logger.info(f"Starting WebMagic Conductor in continuous mode")
        logger.info(f"Cycle interval: {interval_seconds} seconds")
        
        self.running = True
        
        try:
            while self.running:
                # Run cycle
                results = await self.run_cycle()
                
                # Log results
                logger.info(f"Cycle {self.cycle_count} results: {results}")
                
                # Wait for next cycle
                if self.running:
                    logger.info(f"Waiting {interval_seconds} seconds until next cycle...")
                    await asyncio.sleep(interval_seconds)
                    
        except KeyboardInterrupt:
            logger.info("Received stop signal, shutting down...")
            self.running = False
        except Exception as e:
            logger.error(f"Fatal error in conductor: {str(e)}", exc_info=True)
            raise
    
    async def run_once(self):
        """Run a single cycle and exit."""
        logger.info("Running WebMagic Conductor in single-cycle mode")
        results = await self.run_cycle()
        logger.info(f"Cycle completed: {results}")
        return results
    
    def stop(self):
        """Stop the conductor."""
        logger.info("Stopping conductor...")
        self.running = False


async def main():
    """Main entry point for the conductor script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WebMagic Conductor - Autopilot Orchestration")
    parser.add_argument(
        "--mode",
        choices=["once", "continuous"],
        default="once",
        help="Run mode: 'once' for single cycle, 'continuous' for autopilot"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Interval between cycles in seconds (continuous mode only)"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show pipeline status only"
    )
    
    args = parser.parse_args()
    
    conductor = Conductor()
    
    try:
        if args.status:
            # Show status only
            status = await conductor.get_pipeline_status()
            print("\n========== WEBMAGIC PIPELINE STATUS ==========")
            print(f"Timestamp: {status['timestamp']}")
            print(f"\nCoverage:")
            print(f"  Pending territories: {status['coverage']['pending_territories']}")
            print(f"\nBusinesses:")
            print(f"  Total: {status['businesses']['total']}")
            print(f"  Qualified: {status['businesses']['qualified']}")
            print(f"\nSites:")
            print(f"  Total: {status['sites']['total']}")
            print(f"  Generating: {status['sites']['generating']}")
            print(f"  Completed: {status['sites']['completed']}")
            print(f"  Published: {status['sites']['published']}")
            print(f"\nCampaigns:")
            print(f"  Total: {status['campaigns']['total']}")
            print(f"  Sent: {status['campaigns']['sent']}")
            print(f"  Opened: {status['campaigns']['opened']}")
            print(f"\nCustomers:")
            print(f"  Total: {status['customers']['total']}")
            print("=" * 47)
        
        elif args.mode == "once":
            # Run single cycle
            await conductor.run_once()
        
        else:
            # Run continuous autopilot
            await conductor.run_continuous(interval_seconds=args.interval)
            
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        conductor.stop()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
