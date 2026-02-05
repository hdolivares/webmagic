"""
Add form styling guidance to Architect prompt to fix dropdown readability issues.
Ensures select/option elements have proper text color contrast.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import get_settings
from models.prompt import PromptTemplate, PromptSetting

settings = get_settings()


FORM_STYLING_GUIDANCE = """
CRITICAL FORM STYLING REQUIREMENTS:

**Select Dropdowns & Options:**
- ALWAYS set explicit color for select elements and their options
- NEVER rely on browser defaults for dropdown text color
- Ensure WCAG AA contrast (4.5:1 minimum) for all form text

**Required CSS for Forms:**
```css
.form-input,
select.form-input {
    width: 100%;
    padding: var(--spacing-md);
    background: var(--color-bg);  /* Usually white or off-white */
    color: var(--color-text);     /* CRITICAL: Dark text for readability */
    border: 1px solid #e5e7eb;
    border-radius: var(--border-radius);
    font-family: var(--font-body);
    font-size: 1rem;
    transition: var(--transition);
}

/* CRITICAL: Style select options explicitly */
select.form-input option {
    background: var(--color-bg);  /* White/off-white background */
    color: var(--color-text);     /* Dark text (e.g., #1f2937, #333) */
    padding: 0.5rem;
}

/* Focus states */
.form-input:focus,
select.form-input:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px rgba(var(--color-primary-rgb), 0.1);
}

/* Placeholder styling */
.form-input::placeholder {
    color: var(--color-text-muted);  /* Lighter gray for placeholders */
    opacity: 0.6;
}
```

**Common Mistakes to AVOID:**
❌ Setting background: white and forgetting to set color: dark
❌ Using white text on white background in dropdowns
❌ Relying on browser default styles for select/option
❌ Not testing contrast ratios

**Testing Checklist:**
✅ Can you read the dropdown placeholder text?
✅ Can you read the dropdown options when opened?
✅ Does the selected option have good contrast?
✅ Are disabled options visually distinct?
"""


async def add_form_styling_guidance():
    """Add form styling guidance to Architect prompt settings."""
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        print("=" * 70)
        print("Adding Form Styling Guidance to Architect")
        print("=" * 70)
        print()
        
        # Check if setting already exists
        result = await session.execute(
            select(PromptSetting).where(
                PromptSetting.agent_name == "architect",
                PromptSetting.section_name == "form_styling_guidance"
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print("⚠️  Form styling guidance already exists. Updating...")
            existing.content = FORM_STYLING_GUIDANCE
            existing.version += 1
            await session.commit()
            print("✅ Updated existing form styling guidance")
        else:
            print("📝 Creating new form styling guidance setting...")
            
            form_styling_setting = PromptSetting(
                agent_name="architect",
                section_name="form_styling_guidance",
                content=FORM_STYLING_GUIDANCE,
                description="Critical CSS guidance for form inputs and select dropdowns to ensure readability",
                version=1,
                is_active=True
            )
            session.add(form_styling_setting)
            await session.commit()
            
            print("✅ Form styling guidance added successfully!")
        
        print()
        print("🎯 This guidance ensures:")
        print("   - Select dropdowns have readable text")
        print("   - Options have proper contrast (no white-on-white)")
        print("   - All form elements meet WCAG AA standards")
        print()
        print("🔄 Next steps:")
        print("   1. Update Architect system prompt to include {{form_styling_guidance}}")
        print("   2. Regenerate sites to apply the fix")
        print()
        
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(add_form_styling_guidance())

