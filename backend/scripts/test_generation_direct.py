"""
Test script to directly run generation logic (not via Celery) for debugging.
"""
import asyncio
import logging
from uuid import UUID
from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.business import Business
from models.site import GeneratedSite
from services.creative.orchestrator import CreativeOrchestrator

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_direct_generation():
    """Test generation directly without Celery."""
    async with AsyncSessionLocal() as db:
        # Get the business we just queued
        business_id = UUID('6746e631-0f6f-4779-803e-de4d8317c80a')
        
        result = await db.execute(
            select(Business).where(Business.id == business_id)
        )
        business = result.scalar_one_or_none()
        
        if not business:
            logger.error(f"Business {business_id} not found")
            return
        
        logger.info(f"Starting generation for: {business.name}")
        logger.info(f"  - Category: {business.category}")
        logger.info(f"  - City: {business.city}, State: {business.state}")
        logger.info(f"  - Rating: {business.rating}, Reviews: {business.review_count}")
        
        try:
            # Create generated_sites record
            logger.info("Creating GeneratedSite record...")
            site = GeneratedSite(
                business_id=business.id,
                status="pending",
                subdomain=f"{business.name.lower().replace(' ', '-').replace('\'', '')}-test",
            )
            db.add(site)
            await db.commit()
            await db.refresh(site)
            logger.info(f"✅ Created site record: {site.id}, subdomain: {site.subdomain}")
            
            # Initialize orchestrator
            logger.info("Initializing Creative Orchestrator...")
            orchestrator = CreativeOrchestrator(db)
            
            # Generate website
            logger.info("Calling orchestrator.generate_website()...")
            website_data = await orchestrator.generate_website(
                business_name=business.name,
                category=business.category or "service business",
                city=business.city or "City",
                state=business.state or "State",
                phone=business.phone,
                email=business.email,
                address=business.address,
                rating=business.rating,
                review_count=business.review_count,
                description=business.description
            )
            
            logger.info("✅ Website generation completed!")
            logger.info(f"Generated sections: {list(website_data.keys())}")
            
            # Update site record
            site.html_content = website_data.get("html", "")
            site.css_content = website_data.get("css", "")
            site.js_content = website_data.get("javascript", "")
            site.status = "completed"
            await db.commit()
            
            logger.info("✅ Site record updated successfully")
            
        except Exception as e:
            logger.error(f"❌ Generation failed: {e}", exc_info=True)
            return
        
        logger.info(f"\n🎉 Generation test completed successfully for {business.name}")

if __name__ == "__main__":
    asyncio.run(test_direct_generation())

