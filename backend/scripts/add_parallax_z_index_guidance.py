"""
Add parallax/z-index guidance to prevent section overlap issues.
Addresses: hero text moving on top of other sections, z-index stacking problems.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import get_settings
from models.prompt import PromptSetting

settings = get_settings()


PARALLAX_GUIDANCE = """
CRITICAL Z-INDEX & SECTION STACKING REQUIREMENTS:

## 1. HERO SECTION ISOLATION (MANDATORY)

**RULE**: Hero sections MUST be isolated to prevent content bleeding into other sections.

```css
.hero {
    position: relative;
    overflow: hidden;
    isolation: isolate; /* CRITICAL: Create new stacking context */
    contain: layout style; /* CRITICAL: Contain layout calculations */
    z-index: 1; /* Base z-index */
}
```

**Why This Matters**:
- `isolation: isolate` creates a new stacking context
- Prevents hero elements from appearing above subsequent sections
- Ensures proper layering when scrolling

---

## 2. SECTION Z-INDEX STACKING (MANDATORY)

**RULE**: All sections must have explicit z-index to ensure proper stacking order.

```css
/* Hero section - lowest z-index */
.hero {
    position: relative;
    z-index: 1;
    isolation: isolate;
}

/* Content sections - higher z-index */
.about-section,
.services-section,
.testimonials-section,
.process-section,
.contact-section {
    position: relative;
    z-index: 10; /* Higher than hero */
    background: var(--color-bg); /* Ensure opaque background */
}

/* Navigation - highest z-index */
.nav {
    position: sticky;
    top: 0;
    z-index: 1000; /* Always on top */
}

/* Modals, popovers - even higher */
.modal,
.popover {
    z-index: 9999;
}
```

**Z-Index Hierarchy**:
1. Base content: `z-index: 1`
2. Sections: `z-index: 10`
3. Sticky nav: `z-index: 1000`
4. Modals: `z-index: 9999`

---

## 3. PARALLAX EFFECTS (USE WITH EXTREME CAUTION)

**RULE**: If you MUST use parallax, constrain it within the hero section.

### ❌ BAD - Parallax That Breaks Layout:
```css
/* DON'T DO THIS */
.hero-element {
    position: fixed; /* Breaks out of container */
    transform: translateY(calc(var(--scroll) * 0.5)); /* Uncontrolled movement */
}
```

### ✅ GOOD - Constrained Parallax:
```css
.hero {
    position: relative;
    overflow: hidden; /* CRITICAL */
    isolation: isolate; /* CRITICAL */
}

.hero-background {
    position: absolute;
    top: -10%;
    left: 0;
    right: 0;
    bottom: -10%;
    transform: translateY(0); /* Can be animated with scroll */
    will-change: transform; /* Optimize performance */
    backface-visibility: hidden; /* Prevent rendering glitches */
}

/* If using scroll-based animation */
@supports (animation-timeline: scroll()) {
    .hero-background {
        animation: parallax-scroll linear;
        animation-timeline: scroll();
    }
}

@keyframes parallax-scroll {
    to {
        transform: translateY(20%); /* Stays within overflow: hidden */
    }
}
```

**BEST PRACTICE**: Avoid parallax entirely. Use gradients, shapes, or static backgrounds instead.

---

## 4. STICKY HEADER BEST PRACTICES (REVISITED FOR Z-INDEX)

**RULE**: Sticky headers must have proper z-index and NOT have hardcoded offsets.

### ❌ BAD - Multiple Sticky Elements with Hardcoded Offsets:
```css
.top-bar {
    position: sticky;
    top: 0;
    z-index: 1000;
}

.nav {
    position: sticky;
    top: 52px; /* ❌ Fixed offset creates blank space */
    z-index: 999;
}
```

**Problem**: When `top-bar` scrolls away, `nav` keeps 52px gap.

### ✅ GOOD - Single Sticky Header:
```css
.top-bar {
    position: relative; /* NOT sticky */
}

.nav {
    position: sticky;
    top: 0; /* Clean, no offset */
    z-index: 1000;
}
```

### ✅ ACCEPTABLE - Both Sticky (Advanced):
```css
.top-bar {
    position: sticky;
    top: 0;
    z-index: 1001; /* Higher than nav */
}

.nav {
    position: sticky;
    top: 0; /* NOT a fixed offset */
    z-index: 1000;
}
```

**Note**: When both are sticky and both have `top: 0`, they naturally stack.

---

## 5. PSEUDO-ELEMENTS & OVERLAYS

**RULE**: Pseudo-elements must respect the hero's isolation.

```css
.hero::before,
.hero::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none; /* CRITICAL: Don't block interactions */
    z-index: -1; /* Behind hero content */
}

.hero-content {
    position: relative;
    z-index: 1; /* Above pseudo-elements */
}
```

**Common Mistake to AVOID**:
❌ Don't use `z-index: 9999` on pseudo-elements - they should be BEHIND content

---

## 6. ANIMATED ELEMENTS

**RULE**: Elements with animations must be contained.

```css
.animated-shape {
    position: absolute; /* NOT fixed */
    will-change: transform; /* Performance hint */
    backface-visibility: hidden; /* Prevent rendering issues */
    transform: translateZ(0); /* Force GPU acceleration */
}

/* Parent container MUST have */
.animation-container {
    position: relative;
    overflow: hidden; /* CRITICAL */
    isolation: isolate; /* CRITICAL */
}
```

---

## 7. SCROLL-TRIGGERED ANIMATIONS (PREFERRED OVER PARALLAX)

**RULE**: Use CSS `@scroll-timeline` or simple transforms instead of parallax.

```css
@supports (animation-timeline: view()) {
    .fade-in-section {
        animation: fade-in linear;
        animation-timeline: view();
        animation-range: entry 0% cover 30%;
    }
}

@keyframes fade-in {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

**Benefits**:
- No JavaScript required
- Respects section boundaries
- Better performance
- No z-index issues

---

## 8. DEBUGGING Z-INDEX ISSUES

**If sections overlap**, check:

1. ✅ Does hero have `isolation: isolate`?
2. ✅ Do sections have `position: relative`?
3. ✅ Do sections have explicit `z-index`?
4. ✅ Does hero have `overflow: hidden`?
5. ✅ Are z-index values in correct hierarchy?
6. ✅ Do sections have opaque backgrounds?

---

## 9. MOBILE CONSIDERATIONS

**RULE**: Z-index and stacking must work on mobile too.

```css
@media (max-width: 768px) {
    /* Ensure mobile nav is on top */
    .mobile-menu {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 2000; /* Above everything */
        background: var(--color-bg);
    }
    
    /* Ensure sticky nav doesn't conflict */
    .nav {
        position: sticky;
        top: 0;
        z-index: 1000;
    }
}
```

---

## TESTING CHECKLIST

Before finalizing ANY design with hero sections or animations:

✅ Hero section has `isolation: isolate`
✅ Hero section has `overflow: hidden`
✅ Hero section has `position: relative; z-index: 1`
✅ All content sections have `position: relative; z-index: 10`
✅ Sticky nav has `z-index: 1000`
✅ No elements use `position: fixed` for parallax
✅ No hardcoded sticky offsets (e.g., `top: 52px`)
✅ Text doesn't move on top of other sections when scrolling
✅ No blank spaces appear when scrolling past sticky headers
✅ Mobile menu appears above all other content

---

## SUMMARY: THE GOLDEN RULES

1. **Hero**: `isolation: isolate` + `overflow: hidden` + `z-index: 1`
2. **Sections**: `position: relative` + `z-index: 10` + opaque background
3. **Nav**: `position: sticky` + `top: 0` + `z-index: 1000`
4. **Parallax**: Avoid it. If you must, constrain within `overflow: hidden` container
5. **Animations**: Use CSS scroll-timeline, not JavaScript parallax
6. **Sticky Headers**: Single sticky element (nav only), or both with `top: 0`

**NEVER**:
❌ Use `position: fixed` for parallax effects
❌ Use hardcoded `top` offsets on sticky nav (e.g., `top: 52px`)
❌ Forget `isolation: isolate` on hero sections
❌ Leave z-index undefined on sections
"""


async def add_parallax_guidance():
    """Add parallax and z-index guidance to Architect prompt settings."""
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        print("=" * 70)
        print("Adding Parallax & Z-Index Guidance to Architect")
        print("=" * 70)
        print()
        
        # Check if setting already exists
        result = await session.execute(
            select(PromptSetting).where(
                PromptSetting.agent_name == "architect",
                PromptSetting.section_name == "parallax_z_index_guidance"
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print("⚠️  Parallax guidance already exists. Updating...")
            existing.content = PARALLAX_GUIDANCE
            existing.version += 1
            await session.commit()
            print("✅ Updated existing parallax guidance")
        else:
            print("📝 Creating new parallax guidance setting...")
            
            parallax_setting = PromptSetting(
                agent_name="architect",
                section_name="parallax_z_index_guidance",
                content=PARALLAX_GUIDANCE,
                description="Critical z-index stacking and parallax rules to prevent section overlap",
                version=1,
                is_active=True
            )
            session.add(parallax_setting)
            await session.commit()
            
            print("✅ Parallax guidance added successfully!")
        
        print()
        print("🎯 This guidance prevents:")
        print("   - Hero text moving on top of other sections")
        print("   - Z-index stacking conflicts")
        print("   - Sticky header blank spaces")
        print("   - Uncontrolled parallax effects")
        print()
        print("🔄 Next step:")
        print("   - Update Architect system prompt to include {{parallax_z_index_guidance}}")
        print()
        
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(add_parallax_guidance())

