"""
Seed prompt templates for AI agents.
Run this to initialize the database with default prompts.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from core.config import get_settings
from models.prompt import PromptTemplate

settings = get_settings()


async def seed_templates():
    """Seed prompt templates."""
    # Create engine and session
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # Analyst template
        analyst = PromptTemplate(
            agent_name="analyst",
            system_prompt="""You are a strategic business analyst and brand strategist.

Your job is to analyze a business based on its Google My Business data, reviews, and photos.

Extract insights about:
1. Customer sentiment and emotions
2. Brand personality and archetype
3. Key differentiators and unique selling points
4. Tone and communication style
5. Main themes customers care about

Be specific and extract concrete examples from reviews. Avoid generic observations.

{{analysis_guidelines}}

Output your analysis as JSON in the exact format specified.""",
            output_format="""{
  "review_highlight": "Best customer quote (1-2 sentences)",
  "brand_archetype": "One of: The Hero, The Creator, The Sage, The Caregiver, The Explorer, The Rebel, The Magician, The Lover, The Jester, The Everyman, The Ruler, The Innocent",
  "emotional_triggers": ["trigger1", "trigger2", "trigger3"],
  "key_differentiators": ["differentiator1", "differentiator2"],
  "customer_sentiment": "positive/mixed/negative",
  "tone_descriptors": ["tone1", "tone2", "tone3"],
  "content_themes": ["theme1", "theme2", "theme3"]
}""",
            placeholder_sections=["analysis_guidelines"]
        )
        
        # Concept template
        concept = PromptTemplate(
            agent_name="concept",
            system_prompt="""You are a creative brand strategist and conceptual thinker.

Your job is to generate 3 distinct brand personality concepts based on the business analysis.

Each concept should have:
- A unique name
- Clear personality traits
- Communication style
- Differentiation angle
- Brand story
- Value proposition

Then select the BEST concept that fits the business and create a complete "Creative DNA" blueprint.

Output as JSON in the exact format specified.""",
            output_format="""{
  "concepts": [
    {
      "name": "Concept Name",
      "personality": "description",
      "tone": "tone description",
      "differentiation_angle": "what makes it unique",
      "brand_story": "compelling narrative",
      "personality_traits": ["trait1", "trait2"],
      "communication_style": "style",
      "tone_of_voice": "tone",
      "value_proposition": "value prop",
      "target_emotion": "emotion",
      "keywords": ["keyword1", "keyword2"]
    }
  ],
  "selected_concept_index": 0,
  "creative_dna": {
    "concept_name": "name",
    "personality_traits": ["trait1", "trait2"],
    "communication_style": "style",
    "tone_of_voice": "tone",
    "brand_story": "story",
    "value_proposition": "proposition",
    "differentiation_angle": "angle",
    "emotional_core": "emotion",
    "target_emotion": "emotion",
    "content_pillars": ["pillar1", "pillar2"],
    "keywords": ["keyword1", "keyword2"],
    "avoid": ["what to avoid"]
  }
}""",
            placeholder_sections=[]
        )
        
        # Director template
        director = PromptTemplate(
            agent_name="director",
            system_prompt="""You are an expert art director and visual designer.

Your job is to create a comprehensive design brief based on the Creative DNA.

{{frontend_aesthetics}}

{{vibe_list}}

Typography Rules:
{{typography_rules}}

BANNED Patterns:
{{banned_patterns}}

Create a design brief that includes:
- Vibe/aesthetic style
- Typography selections (NO BANNED FONTS!)
- Color palette (with light/dark mode)
- Layout approach
- Hero section design
- Interactions and animations
- Image treatment style

Output as JSON in the exact format specified.""",
            output_format="""{
  "vibe": "Design vibe name",
  "typography": {
    "display": "Display font",
    "body": "Body font",
    "accent": "Accent/mono font"
  },
  "colors": {
    "primary": "#hex",
    "secondary": "#hex",
    "accent": "#hex",
    "background": "#hex",
    "surface": "#hex",
    "text": "#hex",
    "text_muted": "#hex"
  },
  "layout": {
    "type": "single-page",
    "sections": ["hero", "about", "services"],
    "max_width": "1280px"
  },
  "hero": {
    "layout": "split-screen",
    "headline_style": "bold-large",
    "cta_style": "primary-button"
  },
  "interactions": ["smooth-scroll", "fade-in", "hover-lift"],
  "imagery": {
    "treatment": "natural",
    "border_radius": "medium"
  },
  "spacing": "comfortable",
  "border_style": "rounded"
}""",
            placeholder_sections=["frontend_aesthetics", "vibe_list", "typography_rules", "banned_patterns"]
        )
        
        # Architect template
        architect = PromptTemplate(
            agent_name="architect",
            system_prompt="""You are an expert frontend developer specializing in beautiful, responsive websites.

Your job is to generate complete HTML, CSS, and JavaScript code based on the design brief.

Requirements:
- Use Tailwind CSS CDN for styling
- Add custom CSS with semantic class names
- Include GSAP for animations (from CDN)
- Make it fully responsive (mobile-first)
- Use semantic HTML5
- Add a "Claim This Site" bar at the bottom
- Include all meta tags for SEO

Output as JSON with html, css, and js fields.

IMPORTANT: Generate COMPLETE, VALID, PRODUCTION-READY CODE. No placeholders or TODO comments.""",
            output_format="""{
  "html": "Complete HTML document",
  "css": "Complete CSS code",
  "js": "Complete JavaScript code",
  "assets_needed": [
    {"type": "image", "name": "hero.jpg", "usage": "hero section"}
  ],
  "meta": {
    "title": "Page title",
    "description": "Meta description"
  }
}""",
            placeholder_sections=[]
        )
        
        # Add all templates
        session.add_all([analyst, concept, director, architect])
        
        try:
            await session.commit()
            print("✅ Prompt templates seeded successfully!")
            print(f"   - Analyst template")
            print(f"   - Concept template")
            print(f"   - Director template")
            print(f"   - Architect template")
        except Exception as e:
            await session.rollback()
            print(f"❌ Error seeding templates: {str(e)}")
            raise
    
    await engine.dispose()


if __name__ == "__main__":
    print("Seeding prompt templates...")
    asyncio.run(seed_templates())
