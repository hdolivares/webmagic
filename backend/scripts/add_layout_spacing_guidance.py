"""
Add layout and spacing guidance to prevent common CSS/layout mistakes.
Addresses: hero text flush to edges, sticky header spacing issues, container usage.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import get_settings
from models.prompt import PromptSetting

settings = get_settings()


LAYOUT_SPACING_GUIDANCE = """
CRITICAL LAYOUT & SPACING REQUIREMENTS:

## 1. CONTAINER USAGE (MANDATORY)
**RULE**: ALL content MUST be wrapped in a container with proper horizontal padding.

```css
.container {
    max-width: 1280px;
    margin: 0 auto;
    padding: 0 var(--spacing-xl); /* CRITICAL: Horizontal padding */
}

@media (max-width: 768px) {
    .container {
        padding: 0 var(--spacing-md); /* Reduce on mobile */
    }
}
```

**Common Mistake to AVOID**:
❌ `.hero-content { padding: 2rem 0; }` - NO horizontal padding!
✅ `.hero-content { padding: 2rem var(--spacing-xl); }` - Has horizontal padding

**Rule of Thumb**: 
- If it has text/content, it needs LEFT and RIGHT padding (not just top/bottom)
- Never let text touch the screen edges

---

## 2. STICKY/FIXED HEADER BEST PRACTICES

**CRITICAL**: When using sticky headers, you MUST handle spacing correctly.

### Option A: Single Sticky Header (RECOMMENDED)
```css
/* Main nav only - clean and simple */
.nav {
    position: sticky;
    top: 0;
    z-index: 1000;
    background: white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* Top announcement bar - NOT sticky */
.top-bar {
    position: relative; /* NOT sticky */
    background: var(--color-primary);
    padding: 0.5rem 0;
}
```

### Option B: Both Sticky (Advanced)
```css
/* Top bar sticky */
.top-bar {
    position: sticky;
    top: 0;
    z-index: 1001; /* Higher than nav */
}

/* Nav sticky below top bar */
.nav {
    position: sticky;
    top: 0; /* Start at 0, will push down by top-bar naturally */
    z-index: 1000;
}

/* Alternative: Use JavaScript to calculate offset */
.nav {
    position: sticky;
    top: var(--top-bar-height, 0); /* Dynamic */
    z-index: 1000;
}
```

**Common Mistakes to AVOID**:
❌ Top bar sticky, nav with fixed `top: 52px` - Creates blank space when scrolling
❌ Both sticky with wrong z-index order
❌ Forgetting to account for sticky header height in scroll calculations

**BEST PRACTICE**: Keep it simple - only make the MAIN NAV sticky, not announcement bars.

---

## 3. HERO SECTION LAYOUT

**RULE**: Hero sections MUST have proper padding on ALL sides.

```css
.hero {
    min-height: 100vh;
    padding: 5rem var(--spacing-xl); /* Top/bottom AND left/right */
    display: flex;
    align-items: center;
}

.hero-content {
    max-width: 1280px;
    margin: 0 auto;
    padding: 2rem var(--spacing-xl); /* Horizontal padding REQUIRED */
    width: 100%;
}

@media (max-width: 768px) {
    .hero {
        padding: 3rem var(--spacing-md); /* Reduce on mobile */
    }
    
    .hero-content {
        padding: 1rem var(--spacing-md);
    }
}
```

**Split Hero Layout** (Text left, Visual right):
```css
.hero-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-2xl);
    max-width: 1280px;
    margin: 0 auto;
    padding: 0 var(--spacing-xl); /* Horizontal padding */
}

.hero-left,
.hero-right {
    padding: var(--spacing-lg); /* Additional padding */
}
```

---

## 4. SECTION SPACING CONSISTENCY

**RULE**: All sections should have consistent vertical and horizontal spacing.

```css
section {
    padding: 5rem var(--spacing-xl); /* Top/bottom AND left/right */
}

section .container {
    max-width: 1280px;
    margin: 0 auto;
    /* Container already has horizontal padding */
}

@media (max-width: 768px) {
    section {
        padding: 3rem var(--spacing-md);
    }
}
```

---

## 5. MOBILE RESPONSIVENESS

**CRITICAL**: Test all spacing at mobile breakpoints.

```css
/* Desktop: generous spacing */
@media (min-width: 1024px) {
    .container {
        padding: 0 3rem;
    }
}

/* Tablet: moderate spacing */
@media (min-width: 768px) and (max-width: 1023px) {
    .container {
        padding: 0 2rem;
    }
}

/* Mobile: compact but not cramped */
@media (max-width: 767px) {
    .container {
        padding: 0 1rem; /* Minimum 1rem on mobile */
    }
    
    .hero {
        padding: 2rem 1rem; /* Reduce hero padding */
    }
}
```

**NEVER**:
❌ Use `padding: 0;` on mobile (text will touch edges)
❌ Use fixed pixel values without responsive adjustments
❌ Forget to test at 375px width (iPhone SE)

---

## 6. SCROLL OFFSET FOR STICKY HEADERS

**RULE**: When using smooth scroll with sticky headers, account for header height.

```javascript
// Calculate offset for sticky headers
const headerHeight = document.querySelector('.nav').offsetHeight;

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            const offsetTop = target.offsetTop - headerHeight - 20; // 20px buffer
            window.scrollTo({
                top: offsetTop,
                behavior: 'smooth'
            });
        }
    });
});
```

---

## TESTING CHECKLIST

Before finalizing any layout, verify:

✅ Text has at least 1rem (16px) padding from screen edges on mobile
✅ Hero content is not flush to the left/right edges
✅ Sticky headers don't create blank space when scrolling
✅ All sections have consistent horizontal padding
✅ Content is centered and has max-width on large screens
✅ Spacing scales down appropriately on mobile (not too cramped)
✅ No horizontal scrolling at any breakpoint
✅ Smooth scroll accounts for sticky header height

---

## COMMON ANTI-PATTERNS TO AVOID

❌ `padding: 2rem 0;` on hero content (no horizontal padding)
❌ Multiple sticky elements with hardcoded offsets
❌ Text flush against screen edges on mobile
❌ Inconsistent container usage across sections
❌ Forgetting to test on actual mobile devices (not just browser resize)
"""


async def add_layout_guidance():
    """Add layout and spacing guidance to Architect prompt settings."""
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        print("=" * 70)
        print("Adding Layout & Spacing Guidance to Architect")
        print("=" * 70)
        print()
        
        # Check if setting already exists
        result = await session.execute(
            select(PromptSetting).where(
                PromptSetting.agent_name == "architect",
                PromptSetting.section_name == "layout_spacing_guidance"
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print("⚠️  Layout spacing guidance already exists. Updating...")
            existing.content = LAYOUT_SPACING_GUIDANCE
            existing.version += 1
            await session.commit()
            print("✅ Updated existing layout spacing guidance")
        else:
            print("📝 Creating new layout spacing guidance setting...")
            
            layout_setting = PromptSetting(
                agent_name="architect",
                section_name="layout_spacing_guidance",
                content=LAYOUT_SPACING_GUIDANCE,
                description="Critical layout and spacing rules to prevent common CSS mistakes",
                version=1,
                is_active=True
            )
            session.add(layout_setting)
            await session.commit()
            
            print("✅ Layout spacing guidance added successfully!")
        
        print()
        print("🎯 This guidance prevents:")
        print("   - Hero text flush to screen edges")
        print("   - Sticky header spacing issues")
        print("   - Inconsistent container usage")
        print("   - Mobile spacing problems")
        print()
        print("🔄 Next step:")
        print("   - Update Architect system prompt to include {{layout_spacing_guidance}}")
        print()
        
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(add_layout_guidance())

