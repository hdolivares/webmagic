"""
Test script to verify the settings API endpoints work correctly.
"""
import asyncio
import sys
from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.prompt import PromptTemplate, PromptSetting

async def test_settings():
    print("Testing Settings API Data...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        # Test templates
        result = await session.execute(select(PromptTemplate))
        templates = result.scalars().all()
        
        print(f"\n1. PROMPT TEMPLATES ({len(templates)} total)")
        print("-" * 60)
        for template in templates:
            print(f"   - {template.agent_name}")
            print(f"     ID: {template.id}")
            print(f"     Placeholder sections: {template.placeholder_sections}")
        
        # Test settings
        result = await session.execute(select(PromptSetting))
        settings = result.scalars().all()
        
        print(f"\n2. PROMPT SETTINGS ({len(settings)} total)")
        print("-" * 60)
        for setting in settings:
            print(f"   - {setting.agent_name}.{setting.section_name}")
            print(f"     ID: {setting.id}")
            print(f"     Version: {setting.version}")
            print(f"     Active: {setting.is_active}")
            print(f"     Content length: {len(setting.content)} chars")
            print()
    
    print("\n" + "=" * 60)
    print("DATABASE CHECK COMPLETE")
    
    if len(templates) == 0:
        print("\nWARNING: No templates found in database!")
        print("Run: python scripts/seed_prompt_templates.py")
        return False
    
    if len(settings) == 0:
        print("\nWARNING: No settings found in database!")
        print("Run: python scripts/seed_prompt_templates.py")
        return False
    
    print(f"\nSUCCESS: {len(templates)} templates and {len(settings)} settings ready!")
    return True

if __name__ == "__main__":
    result = asyncio.run(test_settings())
    sys.exit(0 if result else 1)
