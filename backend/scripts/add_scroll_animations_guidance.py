"""
Add scroll animation and image generation guidance to Architect agent prompts.
"""
import asyncio
import logging
from sqlalchemy import select, update
from core.database import get_db_session_sync
from models.prompt import PromptSetting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCROLL_ANIMATION_GUIDANCE = """
## Scroll-Triggered Animations

**REQUIRED**: Every website MUST include smooth scroll-triggered animations for a professional, modern feel.

### Implementation Requirements:

1. **Intersection Observer API** (preferred for performance):
```javascript
const observerOptions = {
    root: null,
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate-in');
        }
    });
}, observerOptions);

// Observe all sections and elements
document.querySelectorAll('section, .card, .service-item, .testimonial').forEach(el => {
    observer.observe(el);
});
```

2. **CSS Animation Classes**:
```css
/* Elements start hidden and below viewport */
section, .card, .service-item, .testimonial {
    opacity: 0;
    transform: translateY(30px);
    transition: opacity 0.6s ease-out, transform 0.6s ease-out;
}

/* Animate in when visible */
.animate-in {
    opacity: 1;
    transform: translateY(0);
}

/* Stagger animations for lists */
.service-item:nth-child(1) { transition-delay: 0.1s; }
.service-item:nth-child(2) { transition-delay: 0.2s; }
.service-item:nth-child(3) { transition-delay: 0.3s; }
```

3. **Animation Patterns**:
   - **Sections**: Fade in + slide up (30px)
   - **Cards/Services**: Fade in + slide up with stagger
   - **Testimonials**: Fade in + slight scale (0.95 → 1.0)
   - **CTAs**: Fade in + slide up + subtle pulse
   - **Images**: Fade in + slight zoom out (1.05 → 1.0)

4. **Performance**:
   - Use `transform` and `opacity` only (GPU-accelerated)
   - Add `will-change: transform, opacity` to animating elements
   - Clean up observer when done: `observer.disconnect()`

5. **Accessibility**:
   - Respect prefers-reduced-motion:
```css
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}
```

**Example Full Implementation**:
```javascript
// Wait for DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Check for reduced motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    
    if (!prefersReducedMotion) {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -100px 0px'
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                    // Optionally unobserve after animation
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);
        
        // Observe all animated elements
        document.querySelectorAll('.animate-on-scroll').forEach(el => {
            observer.observe(el);
        });
    } else {
        // If reduced motion, add animate-in immediately
        document.querySelectorAll('.animate-on-scroll').forEach(el => {
            el.classList.add('animate-in');
        });
    }
});
```

**CRITICAL**: Every section, card, and major element should have the `animate-on-scroll` class and proper CSS transitions.
"""

IMAGE_GENERATION_GUIDANCE = """
## AI-Generated Images with Nano Banana

**PRIORITY**: Use AI-generated images (Nano Banana/Gemini) when business photos are unavailable or insufficient.

### Image Integration Requirements:

1. **Hero Image** (ALWAYS generate if no hero photo):
   - Path: `assets/images/hero.png`
   - Use as hero background: `background-image: url('assets/images/hero.png')`
   - Apply overlay for text readability: `linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4))`
   - Ensure high-resolution and relevant to business category

2. **Section Backgrounds** (optional):
   - Path: `assets/images/section-bg.png`
   - Subtle, abstract backgrounds for About/Services sections
   - Light overlay to prevent text readability issues

3. **Image Quality Standards**:
   - **Professional**: Images must look like professional photography, not AI-generated
   - **Relevant**: Must accurately represent the business category and services
   - **Brand-Aligned**: Use the site's color palette and brand archetype
   - **Web-Optimized**: High resolution but appropriate file sizes

4. **HTML Integration**:
```html
<!-- Hero with AI-generated background -->
<section class="hero" style="background-image: linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)), url('assets/images/hero.png');">
    <div class="hero-content">
        <h1>Business Name</h1>
        <p>Tagline</p>
    </div>
</section>

<!-- Or as <img> tag for better SEO -->
<section class="hero">
    <img src="assets/images/hero.png" alt="Business Name - Professional Service" class="hero-image">
    <div class="hero-content">
        <h1>Business Name</h1>
    </div>
</section>
```

5. **CSS Best Practices**:
```css
.hero {
    position: relative;
    min-height: 600px;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}

.hero-image {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    z-index: -1;
}
```

6. **Fallback Strategy**:
   - If AI generation fails, use CSS gradients with brand colors
   - Never leave hero section empty or with broken image links
   - Example fallback:
```css
.hero {
    background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
}
```

**CRITICAL**: 
- ALWAYS check if `assets/images/hero.png` exists in generated_images
- If it exists, integrate it into the hero section HTML/CSS
- Ensure proper alt text for SEO and accessibility
- Test image loading and provide graceful fallbacks
"""

async def add_scroll_animations_guidance():
    """Add scroll animations and image generation guidance to database."""
    logger.info("Adding scroll animations and image generation guidance...")
    
    with get_db_session_sync() as db:
        # 1. Add scroll animations guidance
        result = db.execute(
            select(PromptSetting).where(
                PromptSetting.agent_name == "architect",
                PromptSetting.section_name == "scroll_animations_guidance"
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.content = SCROLL_ANIMATION_GUIDANCE
            logger.info("Updated existing scroll_animations_guidance")
        else:
            scroll_setting = PromptSetting(
                agent_name="architect",
                section_name="scroll_animations_guidance",
                content=SCROLL_ANIMATION_GUIDANCE,
                description="Guidance for implementing scroll-triggered animations on all websites",
                is_active=True,
                weight=100
            )
            db.add(scroll_setting)
            logger.info("Created new scroll_animations_guidance")
        
        # 2. Add image generation guidance
        result = db.execute(
            select(PromptSetting).where(
                PromptSetting.agent_name == "architect",
                PromptSetting.section_name == "image_generation_guidance"
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.content = IMAGE_GENERATION_GUIDANCE
            logger.info("Updated existing image_generation_guidance")
        else:
            image_setting = PromptSetting(
                agent_name="architect",
                section_name="image_generation_guidance",
                content=IMAGE_GENERATION_GUIDANCE,
                description="Guidance for integrating AI-generated images (Nano Banana) into websites",
                is_active=True,
                weight=100
            )
            db.add(image_setting)
            logger.info("Created new image_generation_guidance")
        
        db.commit()
        logger.info("✅ Successfully added/updated guidance settings")

if __name__ == "__main__":
    asyncio.run(add_scroll_animations_guidance())

