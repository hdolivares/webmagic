"""
Update prompt settings with new industry style guidance and gradient best practices.
Run this script to add the new Art Director settings without resetting existing data.

This script adds:
1. industry_style_guidance - Color psychology per industry
2. gradient_best_practices - Anti-banding techniques for smooth gradients

Usage:
    python scripts/update_prompt_settings_art.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text
from core.config import get_settings
from models.prompt import PromptTemplate, PromptSetting

settings = get_settings()


async def update_settings():
    """Add new Art Director settings for industry styling and gradients."""
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        print("=" * 70)
        print("Updating Art Director Prompt Settings")
        print("=" * 70)
        print()
        
        # Check if settings already exist
        existing_industry = await session.execute(
            select(PromptSetting).where(
                PromptSetting.agent_name == "art_director",
                PromptSetting.section_name == "industry_style_guidance"
            )
        )
        existing_gradient = await session.execute(
            select(PromptSetting).where(
                PromptSetting.agent_name == "art_director",
                PromptSetting.section_name == "gradient_best_practices"
            )
        )
        
        added_count = 0
        
        # Add industry_style_guidance if not exists
        if not existing_industry.scalar_one_or_none():
            industry_setting = PromptSetting(
                agent_name="art_director",
                section_name="industry_style_guidance",
                content="""INDUSTRY-SPECIFIC COLOR PSYCHOLOGY:

When industry guidance is provided below, follow it carefully. The recommended colors 
and fonts are based on neuromarketing research showing that specific industries 
trigger specific psychological responses:

- LEGAL/FINANCE: Navy + Gold = "My money is safe" (Heritage & Trust)
- HEALTHCARE/DENTAL: Teal + White = "I won't be hurt here" (Clinical Precision)
- PLUMBING/HVAC/AUTO: Red + Yellow = "Help is coming fast" (Rapid Response)
- CONTRACTORS/LANDSCAPING: Green + Orange = "They'll build it right" (Craft & Structure)
- SALONS/SPAS/EVENTS: Charcoal + Rose = "I want that lifestyle" (Aesthetic & Wellness)
- PETS/EDUCATION/CAFES: Orange + Green = "The Connection" (Community & Nurture)

You can apply creative vibes ON TOP of these industry palettes, but the core 
colors should align with psychological expectations for conversion optimization.""",
                description="Industry-specific color psychology and typography guidance",
                version=1,
                is_active=True
            )
            session.add(industry_setting)
            added_count += 1
            print("✅ Added: industry_style_guidance")
        else:
            print("⏭️  Skipped: industry_style_guidance (already exists)")
        
        # Add gradient_best_practices if not exists
        if not existing_gradient.scalar_one_or_none():
            gradient_setting = PromptSetting(
                agent_name="art_director",
                section_name="gradient_best_practices",
                content="""GRADIENT ANTI-BANDING (CRITICAL):

CSS gradients often display visible "bands" instead of smooth transitions.
To prevent this:

1. USE OFF-COLORS: Never pure #FFFFFF or #000000
   - Use #FAFAFA or #FFFFF0 instead of pure white
   - Use #0a0a0f or #1a1a1a instead of pure black

2. ADD NOISE OVERLAY: Specify that gradients should include a subtle 
   SVG noise pattern overlay with 5% opacity

3. MULTIPLE COLOR STOPS: Use 3-5 color stops for smooth eased transitions
   instead of just start/end colors

4. BLUR TECHNIQUE: Large gradient backgrounds can use a pseudo-element 
   with filter: blur(1px) for smoother appearance

When specifying colors, always include gradient_start and gradient_end 
colors that work well together with anti-banding techniques.""",
                description="CSS gradient best practices to prevent color banding",
                version=1,
                is_active=True
            )
            session.add(gradient_setting)
            added_count += 1
            print("✅ Added: gradient_best_practices")
        else:
            print("⏭️  Skipped: gradient_best_practices (already exists)")
        
        # Update art_director template placeholder_sections if needed
        template_result = await session.execute(
            select(PromptTemplate).where(
                PromptTemplate.agent_name == "art_director"
            )
        )
        template = template_result.scalar_one_or_none()
        
        if template:
            current_sections = template.placeholder_sections or []
            new_sections = list(current_sections)
            updated = False
            
            if "industry_style_guidance" not in new_sections:
                new_sections.append("industry_style_guidance")
                updated = True
            if "gradient_best_practices" not in new_sections:
                new_sections.append("gradient_best_practices")
                updated = True
            
            if updated:
                template.placeholder_sections = new_sections
                print(f"✅ Updated template placeholder_sections: {new_sections}")
        
        # Commit changes
        if added_count > 0:
            await session.commit()
            print()
            print(f"SUCCESS! Added {added_count} new prompt setting(s)")
        else:
            print()
            print("No changes needed - all settings already exist")
        
        print("=" * 70)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(update_settings())

