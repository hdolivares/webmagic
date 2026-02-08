"""
Test script to verify LLM model configuration from system settings.

This tests the complete integration:
1. System settings database table
2. Config fallback
3. ValidationOrchestrator reads correct model
4. LLM validator uses the model
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import AsyncSessionLocal
from services.system_settings_service import SystemSettingsService
from services.validation.validation_orchestrator import ValidationOrchestrator
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_settings_integration():
    """Test that LLM model is correctly loaded from system settings."""
    
    logger.info("\n" + "=" * 70)
    logger.info("LLM MODEL SETTINGS INTEGRATION TEST")
    logger.info("=" * 70 + "\n")
    
    # Test 1: Check system settings database
    logger.info("1. Checking system settings database...")
    async with AsyncSessionLocal() as db:
        try:
            llm_model = await SystemSettingsService.get_setting(db, "llm_model", "NOT_FOUND")
            logger.info(f"   ✓ System setting 'llm_model': {llm_model}")
            
            ai_config = await SystemSettingsService.get_ai_config(db)
            logger.info(f"   ✓ AI config provider: {ai_config['llm']['provider']}")
            logger.info(f"   ✓ AI config model: {ai_config['llm']['model']}")
        except Exception as e:
            logger.warning(f"   ⚠ System settings not available: {e}")
            llm_model = "NOT_FOUND"
    
    # Test 2: Check config fallback
    logger.info("\n2. Checking config fallback...")
    from core.config import get_settings
    settings = get_settings()
    config_model = getattr(settings, 'LLM_MODEL', 'NOT_SET')
    logger.info(f"   ✓ Config LLM_MODEL: {config_model}")
    
    # Test 3: Test ValidationOrchestrator without database
    logger.info("\n3. Testing ValidationOrchestrator WITHOUT database session...")
    orchestrator_no_db = ValidationOrchestrator()
    model_no_db = await orchestrator_no_db._get_llm_model()
    logger.info(f"   ✓ Orchestrator model (no DB): {model_no_db}")
    logger.info(f"   → Should use config: {config_model}")
    
    if model_no_db == config_model:
        logger.info("   ✅ PASS: Falls back to config correctly")
    else:
        logger.error("   ❌ FAIL: Model mismatch!")
    
    # Test 4: Test ValidationOrchestrator WITH database
    logger.info("\n4. Testing ValidationOrchestrator WITH database session...")
    async with AsyncSessionLocal() as db:
        orchestrator_with_db = ValidationOrchestrator(db=db)
        model_with_db = await orchestrator_with_db._get_llm_model()
        logger.info(f"   ✓ Orchestrator model (with DB): {model_with_db}")
        
        if llm_model != "NOT_FOUND":
            logger.info(f"   → Should use system setting: {llm_model}")
            if model_with_db == llm_model:
                logger.info("   ✅ PASS: Reads from system settings correctly")
            else:
                logger.error("   ❌ FAIL: Model mismatch!")
        else:
            logger.info(f"   → System setting not found, should use config: {config_model}")
            if model_with_db == config_model:
                logger.info("   ✅ PASS: Falls back to config correctly")
            else:
                logger.error("   ❌ FAIL: Model mismatch!")
    
    # Test 5: Test with model override
    logger.info("\n5. Testing model override...")
    async with AsyncSessionLocal() as db:
        override_model = "claude-3-opus-20240229"
        orchestrator_override = ValidationOrchestrator(db=db, model_override=override_model)
        model_override = await orchestrator_override._get_llm_model()
        logger.info(f"   ✓ Orchestrator model (override): {model_override}")
        logger.info(f"   → Should use override: {override_model}")
        
        if model_override == override_model:
            logger.info("   ✅ PASS: Override works correctly")
        else:
            logger.error("   ❌ FAIL: Override not applied!")
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("INTEGRATION TEST SUMMARY")
    logger.info("=" * 70)
    logger.info(f"System Settings Model: {llm_model if llm_model != 'NOT_FOUND' else 'Not configured'}")
    logger.info(f"Config Model: {config_model}")
    logger.info(f"Orchestrator (no DB): {model_no_db}")
    logger.info(f"Orchestrator (with DB): {model_with_db}")
    logger.info(f"Orchestrator (override): {model_override}")
    logger.info("")
    logger.info("✅ Integration test complete!")
    logger.info("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(test_settings_integration())
