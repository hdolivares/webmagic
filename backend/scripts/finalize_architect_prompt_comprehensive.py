"""
Final comprehensive update to Architect prompt with ALL guidance placeholders.
Ensures form_styling_guidance and layout_spacing_guidance are both included.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import get_settings
from models.prompt import PromptTemplate

settings = get_settings()


async def finalize_architect_placeholders():
    """Ensure all guidance placeholders are properly included."""
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        print("=" * 70)
        print("Finalizing Architect Prompt Placeholders")
        print("=" * 70)
        print()
        
        # Find the architect template
        result = await session.execute(
            select(PromptTemplate).where(PromptTemplate.agent_name == "architect")
        )
        architect = result.scalar_one_or_none()
        
        if not architect:
            print("❌ Architect template not found!")
            await engine.dispose()
            return
        
        print("📝 Current template found")
        print(f"   Current placeholders: {architect.placeholder_sections}")
        print()
        
        # Ensure ALL required placeholders are present
        required_placeholders = [
            "technical_requirements",
            "section_templates",
            "form_styling_guidance",
            "layout_spacing_guidance"
        ]
        
        # Start fresh to avoid duplicates
        architect.placeholder_sections = required_placeholders
        
        await session.commit()
        
        print("✅ Architect placeholders updated successfully!")
        print()
        print(f"   Final placeholder sections: {architect.placeholder_sections}")
        print()
        print("🎯 All guidance now included:")
        print("   ✅ form_styling_guidance - Form/dropdown readability")
        print("   ✅ layout_spacing_guidance - Container/spacing best practices")
        print("   ✅ technical_requirements - General technical guidance")
        print("   ✅ section_templates - Section structure templates")
        print()
        print("🚀 Architect is now fully configured!")
        print()
        
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(finalize_architect_placeholders())

