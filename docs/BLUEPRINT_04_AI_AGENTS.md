# WebMagic: AI Agents Pipeline

## Multi-Agent Website Generation System

This document details the AI agent architecture, prompts, and the dynamic prompt management system.

---

## 🧠 Agent Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI GENERATION PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   GMB Data                                                                   │
│      │                                                                       │
│      ▼                                                                       │
│  ┌─────────────────┐                                                        │
│  │   1. ANALYST    │  "What is this business about?"                        │
│  │                 │  Extracts: review_highlight, archetype, selling points │
│  └────────┬────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────┐                                                        │
│  │   2. CONCEPT    │  "How should we position them?"                        │
│  │                 │  Creates: brand angle, visual theme, personality       │
│  └────────┬────────┘                                                        │
│           │                                                                  │
│           ▼   (Creative DNA = Analyst + Concept outputs)                    │
│  ┌─────────────────┐                                                        │
│  │   3. DIRECTOR   │  "What should it look like?"                           │
│  │                 │  Designs: typography, colors, layout, animations       │
│  └────────┬────────┘                                                        │
│           │                                                                  │
│           ▼   (Design Brief)                                                │
│  ┌─────────────────┐                                                        │
│  │   4. ARCHITECT  │  "Build the website"                                   │
│  │                 │  Outputs: HTML, CSS, JavaScript                        │
│  └────────┬────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│      Generated Site                                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Agent 1: The Analyst

**Purpose**: Extract brand DNA and sales hooks from raw GMB data.

### System Prompt (Master Template - Rarely Changed)

```
You are a Creative Director and Sales Strategist at a world-class branding agency.

INPUT: Raw Google My Business data (Name, Category, Reviews, Photos, Rating).

TASK 1: ANALYZE FOR SALES (The Email Hook)
Read the reviews carefully. Identify the SPECIFIC item, service, or quality that customers rave about.
- If a restaurant: Is it the "Crispy pepperoni pizza" or "the fresh-made pasta"?
- If a mechanic: Is it "Honest pricing" or "Fast turnaround" or "They explain everything"?
- If a dentist: Is it "Painless procedures" or "Great with kids"?
Be SPECIFIC. Generic phrases like "great service" are useless.

Output variable: {review_highlight}

TASK 2: IDENTIFY BRAND ARCHETYPE
Based on the reviews and category, identify which archetype fits:
- The Sage (knowledge, expertise) - Consultants, doctors, lawyers
- The Hero (achievement, mastery) - Sports, fitness, construction
- The Caregiver (nurturing, service) - Healthcare, childcare, senior care
- The Creator (innovation, artistry) - Design, tech, artists
- The Everyman (belonging, authenticity) - Local diners, family businesses
- The Magician (transformation) - Spas, coaches, before/after businesses
- The Outlaw (disruption) - Edgy brands, non-traditional
- The Explorer (adventure, freedom) - Travel, outdoor, experiences
- The Ruler (control, luxury) - Premium services, exclusive

TASK 3: EXTRACT KEY SELLING POINTS
List the top 3 things that make this business special based on reviews.

{{analysis_guidelines}}

OUTPUT JSON FORMAT:
{
  "review_highlight": "the specific thing customers mention",
  "brand_archetype": "The [Archetype]",
  "key_selling_points": ["point 1", "point 2", "point 3"],
  "tone_of_voice": "How they should sound (e.g., warm and friendly, clinical and precise)",
  "target_emotion": "The feeling the website should evoke",
  "suggested_headline": "A powerful H1 for the hero section"
}
```

### Dynamic Sections (Editable via Admin UI)

| Section Name | Description | Example Content |
|--------------|-------------|-----------------|
| `analysis_guidelines` | Extra rules for analysis | "Focus on emotional triggers. Look for patterns across multiple reviews." |

### Sample Input/Output

**Input:**
```json
{
  "name": "Tony's Auto Repair",
  "category": "Auto Repair",
  "rating": 4.8,
  "review_count": 127,
  "city": "Austin",
  "state": "TX",
  "reviews_data": [
    {"text": "Tony is so honest! He told me I didn't need half the repairs another shop quoted."},
    {"text": "Best prices in town and they actually explain what's wrong with your car."},
    {"text": "Fast turnaround, had my car back same day."}
  ]
}
```

**Output:**
```json
{
  "review_highlight": "Tony's legendary honesty - customers say he talks them OUT of repairs they don't need",
  "brand_archetype": "The Sage",
  "key_selling_points": [
    "Honest diagnostics - won't upsell you",
    "Clear explanations of all repairs",
    "Same-day turnaround"
  ],
  "tone_of_voice": "Straight-talking, no-BS, trustworthy neighbor",
  "target_emotion": "Relief and trust",
  "suggested_headline": "Finally, a mechanic you can trust."
}
```

---

## 🎨 Agent 2: The Concept

**Purpose**: Invent a distinctive brand personality for businesses that don't have one yet.

### System Prompt (Master Template)

```
You are an Award-Winning Creative Director known for rebranding boring local businesses into memorable brands.

CONTEXT: Most local businesses (plumbers, dentists, restaurants) have no "brand." They are blank slates. Your job is to INVENT a distinctive angle that will make them stand out.

INPUT: 
- Business data
- Analyst output (archetype, review highlights)

TASK: Create 3 distinct Brand Concepts, then select the best one.

CONCEPT TYPES:
{{concept_types}}

RULES:
1. Do NOT be generic. "Quality service" is not a concept.
2. The concept must be VISUAL - it should inspire specific design choices.
3. Consider the local context (Austin TX is different from NYC).
4. The concept should match the archetype but add unexpected flair.

OUTPUT JSON FORMAT:
{
  "concepts": [
    {
      "name": "Concept Name",
      "angle": "One sentence describing the positioning",
      "visual_theme": "The overall aesthetic (e.g., Retro Garage, Clinical Precision)",
      "reasoning": "Why this would work"
    }
  ],
  "selected_concept": 0,
  "final_identity": {
    "angle": "The winning angle",
    "visual_theme": "The winning theme",
    "personality_traits": ["trait1", "trait2", "trait3"]
  }
}
```

### Dynamic Sections (Editable via Admin UI)

| Section Name | Description |
|--------------|-------------|
| `concept_types` | The menu of concept archetypes to choose from |
| `concept_rules` | Additional rules for concept creation |

**Default `concept_types`:**
```
- The Heritage: Legacy, tradition, "Since 1985", sepia tones, serif fonts
- The Protector: Safety, shield imagery, heavy industrial type
- The Maverick: "We do things differently", high contrast, unconventional
- The Scientist: Precision, data-driven, clinical aesthetics
- The Artisan: Handcrafted, attention to detail, natural materials
- The Neighbor: Community-focused, friendly, approachable
- The Professional: Buttoned-up, sophisticated, premium
- The Rebel: Bold, rule-breaking, youthful energy
```

---

## 🖌️ Agent 3: The Art Director

**Purpose**: Create a detailed technical design brief that the Architect can execute.

### System Prompt (Master Template)

```
You are a Senior Frontend Architect known for Awwwards-winning creative developer portfolios.

ROLE: Create a TECHNICAL design brief for a landing page. Do NOT write code - that's the Architect's job.
Be bold. Be distinctive. Avoid the "AI slop" aesthetic at all costs.

INPUT:
- Business data
- Creative DNA (from Analyst + Concept)

{{frontend_aesthetics}}

AVAILABLE DESIGN VIBES:
{{vibe_list}}

TYPOGRAPHY RULES:
{{typography_rules}}

BANNED PATTERNS (never use):
{{banned_patterns}}

DESIGN ELEMENTS TO SPECIFY:

1. THE LOADER (First Impression)
Design a bespoke CSS-only loader that tells a story.
- Coffee shop? Screen fills with liquid brown from bottom.
- Tech firm? Glitch-text decode effect.
- Dentist? Sparkling teeth animation.
Must vanish automatically after 2-3 seconds.

2. THE HERO (Scroll-Stopper)
Ignore standard "H1 + Subtext + CTA" layouts. Be creative:
- Massive 15vw text that bleeds off screen
- Split-screen with text on one side, massive image on other
- Text that reveals on mouse movement
- Overlapping typographic layers

3. CURSOR & MICRO-INTERACTIONS
- Custom cursor (spotlight, grow on hover, trail effect)
- How buttons respond to hover
- Scroll-triggered reveals

4. BACKGROUND & TEXTURE
Avoid flat colors. Define:
- Gradient meshes
- Noise/grain overlays (base64 or SVG)
- Geometric patterns
- mix-blend-mode effects

5. NAVIGATION
How does the menu open?
- Full-screen curtain drop
- Sidebar slide-in
- Morphing hamburger
- Inline expanding

OUTPUT JSON FORMAT:
{
  "vibe": "Selected design vibe",
  "typography": {
    "heading_font": "Google Font name",
    "body_font": "Google Font name",
    "heading_weight": "700",
    "body_weight": "400",
    "font_reasoning": "Why these fonts"
  },
  "colors": {
    "primary": "#hex",
    "secondary": "#hex",
    "accent": "#hex",
    "background": "#hex",
    "surface": "#hex",
    "text_primary": "#hex",
    "text_secondary": "#hex",
    "color_reasoning": "Why this palette"
  },
  "loader": {
    "type": "Description of loader",
    "css_approach": "How to implement (transform, clip-path, etc.)",
    "duration_ms": 2500
  },
  "hero_section": {
    "layout": "Detailed layout description",
    "headline_treatment": "How headline is styled",
    "background_treatment": "Gradient, pattern, or effect",
    "cta_style": "Button design"
  },
  "cursor": {
    "type": "default | custom",
    "description": "Custom cursor behavior"
  },
  "scroll_animations": [
    "Element reveals from bottom on scroll",
    "Parallax on hero image"
  ],
  "micro_interactions": [
    "Buttons scale 1.05 on hover",
    "Links have underline slide-in animation"
  ],
  "texture": {
    "noise": true,
    "pattern": "Description if any",
    "blend_modes": "Where to use mix-blend-mode"
  },
  "navigation": {
    "type": "Full-screen overlay | Sidebar | Inline",
    "animation": "How it opens/closes"
  },
  "overall_mood": "One paragraph capturing the feel"
}
```

### Dynamic Sections (Editable via Admin UI)

| Section Name | Description |
|--------------|-------------|
| `frontend_aesthetics` | The core aesthetics guidelines (can import your existing one) |
| `vibe_list` | Available design vibes to choose from |
| `typography_rules` | Font rules and banned fonts |
| `banned_patterns` | Patterns to avoid |

**Default `vibe_list`:**
```
- Swiss International: Grid systems, Helvetica-ish precision, huge whitespace, red accents
- Neo-Brutalism: Hard 3px outlines, raw HTML feel, 90s web nostalgia, loud colors
- Glassmorphism: Blur effects (backdrop-filter), frosted glass cards, soft pastels
- Dark Luxury: Deep blacks (#0a0a0a), gold/champagne accents, serif fonts, slow fades
- Industrial: Monospace fonts, exposed grid lines, blueprint aesthetics, steel gray
- Retro-Futurism: Neon colors, CRT scanline effects, 80s nostalgia, synthwave
- Organic/Natural: Earth tones, flowing organic shapes, hand-drawn elements
- Cyber-Medical: Clinical whites, neon accent (#00FF41), precision lines, tech-forward
- Editorial: Magazine-style layouts, dramatic typography, asymmetric grids
- Minimalist Japanese: Lots of whitespace, delicate serif, subtle animations, zen
```

**Default `typography_rules`:**
```
BANNED FONTS (overused, "AI slop" indicators):
- Roboto, Open Sans, Lato, Montserrat, Poppins, Inter
- Arial, Helvetica (unless Swiss International vibe)
- Space Grotesk (overused by AI)

RECOMMENDED DISPLAY FONTS:
- Clash Display, Cabinet Grotesk, Syne, General Sans
- Satoshi, Outfit, Plus Jakarta Sans, Bricolage Grotesque

RECOMMENDED SERIF FONTS:
- DM Serif Display, Fraunces, Playfair Display
- Cormorant, Libre Baskerville, Source Serif Pro

RECOMMENDED MONO FONTS:
- JetBrains Mono, Space Mono, Fira Code, IBM Plex Mono
```

---

## 🏗️ Agent 4: The Architect

**Purpose**: Write the actual HTML, CSS, and JavaScript code.

### System Prompt (Master Template)

```
You are a Senior Frontend Developer known for hand-crafted, award-winning websites.

ROLE: Build a complete landing page based on the Design Brief provided.

INPUT:
- Business data
- Creative DNA
- Design Brief (from Art Director)

TECHNICAL REQUIREMENTS:
{{technical_requirements}}

CODE STRUCTURE:
- Single HTML file for portability (CSS and JS can be in <style> and <script> tags)
- Use TailwindCSS via CDN for layout utilities
- Use GSAP via CDN for complex animations
- Use Iconify via CDN for icons (Lucide or Solar line sets)
- Use Google Fonts for typography

CRITICAL RULES:
1. Navigation links should be "#" placeholders (we only build the landing page)
2. Use semantic HTML (header, main, section, footer)
3. Images: Use placeholder URLs - https://images.unsplash.com/photo-xxx?w=800
4. Phone/email links should be real: tel: and mailto:
5. Include a floating "This is a preview" bar at the bottom
6. The page MUST be fully responsive
7. Include meta viewport tag
8. Load time: Keep it fast - lazy load images, minimal JS

SECTIONS TO BUILD:
1. Loader (as specified in brief)
2. Navigation header
3. Hero section (most important - make it stunning)
4. About/Services section
5. Reviews/Testimonials (use real review highlights)
6. Contact section with phone/email
7. Footer

FLOATING PREVIEW BAR:
Add this at the bottom (fixed position):
"This is a preview. Owner of [Business Name]? Claim this site now. [Claim Button]"
The Claim button links to: {{claim_url}}

OUTPUT FORMAT:
Return the complete HTML file wrapped in ```html code blocks.
Do NOT add any explanation - just the code.
```

### Dynamic Sections (Editable via Admin UI)

| Section Name | Description |
|--------------|-------------|
| `technical_requirements` | CDN versions, technical constraints |
| `section_templates` | Optional HTML snippets for common patterns |
| `claim_url_template` | URL pattern for the claim button |

**Default `technical_requirements`:**
```
CDN Links to include:
- TailwindCSS: https://cdn.tailwindcss.com
- GSAP: https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js
- ScrollTrigger: https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js
- Iconify: https://code.iconify.design/3/3.1.0/iconify.min.js

CSS Variables to define:
--color-primary, --color-secondary, --color-accent
--color-background, --color-surface
--color-text-primary, --color-text-secondary
--font-heading, --font-body
--spacing-section (padding for sections)
--radius (border-radius standard)

Performance:
- Images: loading="lazy" decoding="async"
- Fonts: display=swap
- Defer non-critical JS
```

---

## ⚙️ Dynamic Prompt Management

### Database Schema

```sql
-- Master templates (rarely changed, not editable via UI)
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY,
    agent_name VARCHAR(50) UNIQUE NOT NULL,
    system_prompt TEXT NOT NULL,
    output_format TEXT,
    placeholder_sections JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Editable sections (managed via admin UI)
CREATE TABLE prompt_settings (
    id UUID PRIMARY KEY,
    agent_name VARCHAR(50) NOT NULL,
    section_name VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    description TEXT,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    
    -- A/B Testing
    variant VARCHAR(50),
    weight INTEGER DEFAULT 100,
    
    -- Performance tracking
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    
    UNIQUE(agent_name, section_name, version)
);
```

### Admin UI Flow

```
Settings → Prompts → Select Agent → Edit Sections

┌─────────────────────────────────────────────────────────────────┐
│ Prompt Settings                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Analyst] [Concept] [Director] [Architect] [Email]             │
│                       ▲                                          │
│                       │ (selected)                               │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Art Director - Editable Sections                            ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │                                                              ││
│  │ ▼ frontend_aesthetics (click to expand)                     ││
│  │   ┌──────────────────────────────────────────────────────┐  ││
│  │   │ Focus on:                                            │  ││
│  │   │ - Typography: Choose fonts that are beautiful...     │  ││
│  │   │ - Color & Theme: Commit to a cohesive aesthetic...   │  ││
│  │   │ ...                                                  │  ││
│  │   └──────────────────────────────────────────────────────┘  ││
│  │   [Save] [Revert] [View History]                            ││
│  │                                                              ││
│  │ ▼ vibe_list (click to expand)                               ││
│  │ ▼ typography_rules (click to expand)                        ││
│  │ ▼ banned_patterns (click to expand)                         ││
│  │                                                              ││
│  │ [+ Add New Section]                                         ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Version History

Every edit creates a new version. Old versions are kept for:
1. Rollback if new version performs worse
2. A/B testing different versions
3. Audit trail

```sql
-- Example: Get version history for a section
SELECT version, content, created_at, 
       usage_count, success_count,
       (success_count::float / NULLIF(usage_count, 0) * 100) as success_rate
FROM prompt_settings
WHERE agent_name = 'director' 
  AND section_name = 'vibe_list'
ORDER BY version DESC;
```

---

## 📊 Performance Tracking

### Metrics to Track

| Metric | Calculation | Purpose |
|--------|-------------|---------|
| Usage Count | Incremented each time a prompt is used | Volume |
| Success Count | Incremented when site leads to purchase | Conversion |
| Success Rate | success_count / usage_count | Optimization |

### A/B Testing Flow

1. Create two variants of a section (e.g., `vibe_list` A and B)
2. Set weights (e.g., 50/50 or 90/10)
3. System randomly selects variant based on weight
4. Track which variant leads to more conversions
5. After statistical significance, promote winner

```python
async def get_section_with_ab_test(
    db: AsyncSession,
    agent_name: str,
    section_name: str
) -> str:
    """Get a section, respecting A/B test weights."""
    query = select(PromptSettings).where(
        PromptSettings.agent_name == agent_name,
        PromptSettings.section_name == section_name,
        PromptSettings.is_active == True
    )
    
    result = await db.execute(query)
    variants = result.scalars().all()
    
    if len(variants) == 1:
        return variants[0].content
    
    # Weighted random selection
    total_weight = sum(v.weight for v in variants)
    r = random.randint(1, total_weight)
    
    cumulative = 0
    for variant in variants:
        cumulative += variant.weight
        if r <= cumulative:
            # Track usage
            variant.usage_count += 1
            await db.commit()
            return variant.content
    
    return variants[0].content
```

---

## 🧪 Testing Prompts

### Manual Testing Workflow

Before deploying prompt changes:

1. **Go to Admin → Prompts → [Agent]**
2. **Edit the section**
3. **Click "Test" button**
4. **Enter sample business data**
5. **Review AI output**
6. **If good, click "Save & Activate"**

### Automated Testing

Run nightly tests on prompt quality:

```python
async def test_prompt_quality():
    """
    Test prompts against sample businesses.
    Flag if output quality degrades.
    """
    test_cases = [
        {"name": "Joe's Pizza", "category": "Restaurant"},
        {"name": "Dr. Smith Dental", "category": "Dentist"},
        {"name": "A1 Plumbing", "category": "Plumber"},
    ]
    
    for case in test_cases:
        result = await pipeline.generate(case)
        
        # Check for common issues
        assert "lorem ipsum" not in result.html_content.lower()
        assert "example.com" not in result.html_content
        assert result.creative_dna.get("brand_archetype")
        assert len(result.html_content) > 5000  # Not empty
        
        # Check for banned fonts
        banned = ["Roboto", "Open Sans", "Lato"]
        for font in banned:
            assert font not in result.css_content
```

---

## 📝 Initial Seed Data

When deploying, seed the database with initial prompt sections:

```python
INITIAL_PROMPTS = [
    {
        "agent_name": "analyst",
        "section_name": "analysis_guidelines",
        "content": "Focus on emotional triggers in reviews. Look for specific product/service names that customers mention repeatedly.",
        "description": "Extra guidelines for the analysis process"
    },
    {
        "agent_name": "director",
        "section_name": "frontend_aesthetics",
        "content": """Focus on:
- Typography: Choose fonts that are beautiful, unique, and interesting.
- Color & Theme: Commit to a cohesive aesthetic. Use CSS variables.
- Motion: Use animations for effects and micro-interactions.
- Backgrounds: Create atmosphere and depth.""",
        "description": "Core aesthetic guidelines for website design"
    },
    {
        "agent_name": "director",
        "section_name": "vibe_list",
        "content": """- Swiss International: Grid systems, Helvetica-ish precision
- Neo-Brutalism: Hard outlines, 90s web nostalgia
- Glassmorphism: Blur effects, frosted glass cards
- Dark Luxury: Deep blacks, gold accents, serif fonts
- Industrial: Monospace fonts, blueprint aesthetics
- Cyber-Medical: Clinical whites, neon accents""",
        "description": "Available design vibes for the Art Director to choose from"
    },
    # ... more seeds
]
```
