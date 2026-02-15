#!/usr/bin/env python3
"""
Test the fixed validation on a single business.
This will validate McComb Plumbing with the FIXED orchestrator.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_db
from models.business import Business
from services.validation.validation_orchestrator import ValidationOrchestrator
from services.validation.url_prescreener import URLPrescreener
from services.validation.playwright_service import PlaywrightValidationService
from services.validation.llm_validator import LLMWebsiteValidator
from core.config import Settings
settings = Settings()
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_validation():
    """Test validation with the fixed orchestrator."""
    
    # Get McComb Plumbing business
    business_id = "88162f51-8452-4e61-a882-526cd74fb5bb"
    
    async for db in get_db():
        # Fetch business using ORM
        from sqlalchemy import select
        stmt = select(Business).where(Business.id == business_id)
        result = await db.execute(stmt)
        business = result.scalar_one_or_none()
        
        if not business:
            logger.error(f"Business {business_id} not found")
            return
        
        logger.info(f"Testing validation for: {business.name}")
        logger.info(f"Website URL: {business.website_url}")
        
        # Initialize services
        prescreener = URLPrescreener()
        playwright_service = PlaywrightValidationService()
        llm_validator = LLMWebsiteValidator(settings.ANTHROPIC_API_KEY)
        
        orchestrator = ValidationOrchestrator(
            prescreener=prescreener,
            playwright_service=playwright_service,
            llm_validator=llm_validator
        )
        
        # Run validation
        logger.info("Starting validation with FIXED orchestrator...")
        result = await orchestrator.validate_website(
            url=business.website_url,
            business_name=business.name,
            business_phone=business.phone or "",
            business_email=business.email or "",
            business_address=business.address or "",
            business_city=business.city,
            business_state=business.state,
            business_country=business.country or "US"
        )
        
        logger.info(f"\n{'='*60}")
        logger.info(f"VALIDATION RESULTS:")
        logger.info(f"{'='*60}")
        logger.info(f"Is Valid: {result.get('is_valid')}")
        logger.info(f"Verdict: {result.get('verdict')}")
        logger.info(f"Confidence: {result.get('confidence')}")
        logger.info(f"Recommendation: {result.get('recommendation')}")
        
        # Check LLM stage
        llm_stage = result.get('stages', {}).get('llm', {})
        logger.info(f"\nLLM Analysis:")
        logger.info(f"  Verdict: {llm_stage.get('verdict')}")
        logger.info(f"  Reasoning: {llm_stage.get('reasoning')}")
        logger.info(f"  Phone Match: {llm_stage.get('match_signals', {}).get('phone_match')}")
        logger.info(f"  Name Match: {llm_stage.get('match_signals', {}).get('name_match')}")
        
        # Check Playwright stage
        playwright_stage = result.get('stages', {}).get('playwright', {})
        logger.info(f"\nPlaywright Extracted Data:")
        logger.info(f"  Phones: {playwright_stage.get('phones')}")
        logger.info(f"  Emails: {playwright_stage.get('emails')}")
        logger.info(f"  Title: {playwright_stage.get('title')}")
        logger.info(f"  Has Contact: {playwright_stage.get('has_contact_info')}")
        
        logger.info(f"{'='*60}\n")
        
        # Verify the fix worked
        if playwright_stage.get('phones') and llm_stage.get('verdict') == 'valid':
            logger.info("✅ FIX CONFIRMED: LLM received contact data and made correct decision!")
        elif not playwright_stage.get('phones'):
            logger.warning("⚠️ Playwright didn't extract phones - website might not have them")
        else:
            logger.error("❌ LLM still rejecting despite contact info - needs investigation")
        
        break

if __name__ == "__main__":
    asyncio.run(test_validation())
