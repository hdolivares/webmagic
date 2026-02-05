"""
Update Architect prompt template to include parallax_z_index_guidance placeholder.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import get_settings
from models.prompt import PromptTemplate

settings = get_settings()


async def update_architect_placeholders():
    """Add parallax_z_index_guidance to Architect placeholder sections."""
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        print("=" * 70)
        print("Updating Architect with Parallax Z-Index Guidance Placeholder")
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
        
        # Add parallax_z_index_guidance if not already present
        if architect.placeholder_sections is None:
            architect.placeholder_sections = []
        
        if "parallax_z_index_guidance" not in architect.placeholder_sections:
            architect.placeholder_sections.append("parallax_z_index_guidance")
            await session.commit()
            print("✅ Added parallax_z_index_guidance placeholder!")
        else:
            print("⚠️  parallax_z_index_guidance already in placeholders")
        
        print()
        print(f"   Final placeholder sections: {architect.placeholder_sections}")
        print()
        print("🎯 Architect will now include:")
        print("   ✅ parallax_z_index_guidance - Z-index stacking & section isolation")
        print("   ✅ form_styling_guidance - Form/dropdown readability")
        print("   ✅ layout_spacing_guidance - Container/spacing best practices")
        print()
        print("🚀 All guidance is now active!")
        print()
        
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(update_architect_placeholders())

