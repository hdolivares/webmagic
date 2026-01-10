# WebMagic: Backend Modules

## Python Backend Module Specifications

This document details the implementation of each backend module.

---

## 🏗️ Core Module

### `core/config.py`

```python
"""
Application configuration using Pydantic Settings.
Loads from environment variables with validation.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "WebMagic"
    DEBUG: bool = False
    API_VERSION: str = "v1"
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # External APIs
    ANTHROPIC_API_KEY: str
    OUTSCRAPER_API_KEY: str
    
    # Email
    EMAIL_PROVIDER: str = "ses"  # ses or sendgrid
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    SENDGRID_API_KEY: str = ""
    EMAIL_FROM: str = "hugo@webmagic.com"
    
    # Recurrente
    RECURRENTE_PUBLIC_KEY: str
    RECURRENTE_SECRET_KEY: str
    RECURRENTE_WEBHOOK_SECRET: str = ""
    RECURRENTE_BASE_URL: str = "https://app.recurrente.com"
    
    # Site Hosting
    SITES_DOMAIN: str = "sites.webmagic.com"
    SITES_BASE_PATH: str = "/var/www/sites"
    
    # Celery
    CELERY_BROKER_URL: str = ""
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### `core/database.py`

```python
"""
Database connection and session management.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    echo=settings.DEBUG
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    """Dependency for FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### `core/security.py`

```python
"""
Security utilities: password hashing, JWT tokens, API key validation.
"""
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=60))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None

def generate_api_key() -> str:
    return secrets.token_urlsafe(32)
```

---

## 🔍 Hunter Module (Scraping)

### `services/hunter/scraper.py`

```python
"""
Outscraper API integration for Google My Business data.
"""
from outscraper import ApiClient
from typing import List, Dict, Optional
from ...core.config import get_settings

class OutscraperClient:
    """Wrapper for Outscraper API."""
    
    def __init__(self):
        settings = get_settings()
        self.client = ApiClient(api_key=settings.OUTSCRAPER_API_KEY)
    
    async def search_businesses(
        self,
        query: str,
        city: str,
        state: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search for businesses in a specific location.
        
        Args:
            query: Industry/business type (e.g., "Plumbers")
            city: City name
            state: State abbreviation
            limit: Max results
            
        Returns:
            List of business data dictionaries
        """
        full_query = f"{query} in {city}, {state}"
        
        results = self.client.google_maps_search(
            query=full_query,
            limit=limit,
            drop_duplicates=True,
            language="en"
        )
        
        return self._normalize_results(results)
    
    def _normalize_results(self, raw_results: List) -> List[Dict]:
        """Convert Outscraper format to our internal format."""
        normalized = []
        for item in raw_results:
            normalized.append({
                "gmb_id": item.get("place_id"),
                "name": item.get("name"),
                "email": item.get("email"),
                "phone": item.get("phone"),
                "website": item.get("site"),  # Should be None for our targets
                "address": item.get("full_address"),
                "city": item.get("city"),
                "state": item.get("state"),
                "category": item.get("category"),
                "rating": item.get("rating"),
                "review_count": item.get("reviews"),
                "photos": item.get("photos", []),
                "reviews_data": item.get("reviews_data", [])
            })
        return normalized
```

### `services/hunter/filters.py`

```python
"""
Lead qualification and filtering logic.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class QualificationCriteria:
    """Configurable qualification thresholds."""
    min_rating: float = 4.0
    min_reviews: int = 10
    max_reviews: int = 500  # Too big = probably have website
    require_email: bool = False  # We can use phone too
    require_contact: bool = True  # Need email OR phone
    exclude_chains: bool = True

class LeadQualifier:
    """Scores and filters leads based on criteria."""
    
    def __init__(self, criteria: QualificationCriteria = None):
        self.criteria = criteria or QualificationCriteria()
        
        # Known chains to exclude
        self.chain_patterns = [
            "mcdonald", "subway", "starbucks", "walmart",
            "home depot", "lowe's", "target", "costco"
        ]
    
    def qualify(self, business: Dict) -> tuple[bool, int, str]:
        """
        Determine if a business qualifies as a lead.
        
        Returns:
            (is_qualified, score, reason)
        """
        # Must not have a website
        if business.get("website"):
            return False, 0, "Already has website"
        
        # Must have contact info
        has_email = bool(business.get("email"))
        has_phone = bool(business.get("phone"))
        
        if self.criteria.require_contact and not (has_email or has_phone):
            return False, 0, "No contact info"
        
        if self.criteria.require_email and not has_email:
            return False, 0, "No email"
        
        # Check rating
        rating = business.get("rating", 0)
        if rating < self.criteria.min_rating:
            return False, 0, f"Rating too low: {rating}"
        
        # Check review count
        reviews = business.get("review_count", 0)
        if reviews < self.criteria.min_reviews:
            return False, 0, f"Too few reviews: {reviews}"
        
        if reviews > self.criteria.max_reviews:
            return False, 0, f"Too many reviews (likely chain): {reviews}"
        
        # Check for chains
        if self.criteria.exclude_chains:
            name_lower = business.get("name", "").lower()
            for pattern in self.chain_patterns:
                if pattern in name_lower:
                    return False, 0, f"Chain detected: {pattern}"
        
        # Calculate score
        score = self._calculate_score(business)
        
        return True, score, "Qualified"
    
    def _calculate_score(self, business: Dict) -> int:
        """
        Calculate a 0-100 lead score.
        Higher = more likely to convert.
        """
        score = 50  # Base score
        
        # Rating bonus (4.0 = +0, 5.0 = +20)
        rating = business.get("rating", 4.0)
        score += int((rating - 4.0) * 20)
        
        # Review count bonus (sweet spot: 20-100 reviews)
        reviews = business.get("review_count", 0)
        if 20 <= reviews <= 100:
            score += 15
        elif reviews > 100:
            score += 5
        
        # Email bonus (easier to reach)
        if business.get("email"):
            score += 10
        
        # Photos bonus (care about image)
        photos = business.get("photos", [])
        if len(photos) >= 5:
            score += 5
        
        return min(100, max(0, score))
    
    def filter_batch(self, businesses: List[Dict]) -> List[Dict]:
        """Filter a batch of businesses, return qualified ones with scores."""
        qualified = []
        for biz in businesses:
            is_qualified, score, reason = self.qualify(biz)
            if is_qualified:
                biz["qualification_score"] = score
                biz["qualification_reason"] = reason
                qualified.append(biz)
        
        # Sort by score descending
        return sorted(qualified, key=lambda x: x["qualification_score"], reverse=True)
```

### `services/hunter/conductor.py`

```python
"""
Autopilot conductor - orchestrates the scraping across locations.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ...models.coverage import CoverageGrid
from ...models.business import Business
from .scraper import OutscraperClient
from .filters import LeadQualifier

class AutopilotConductor:
    """
    Manages the systematic coverage of US markets.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scraper = OutscraperClient()
        self.qualifier = LeadQualifier()
    
    async def get_next_target(self) -> Optional[CoverageGrid]:
        """
        Select the next location/industry to scrape.
        Prioritizes by priority score and population.
        """
        query = (
            select(CoverageGrid)
            .where(CoverageGrid.status == "pending")
            .where(
                (CoverageGrid.cooldown_until == None) |
                (CoverageGrid.cooldown_until < func.now())
            )
            .order_by(
                CoverageGrid.priority.desc(),
                CoverageGrid.population.desc()
            )
            .limit(1)
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def process_target(self, target: CoverageGrid) -> dict:
        """
        Scrape and process a single target location.
        
        Returns:
            Stats about the operation
        """
        # Mark as in progress
        target.status = "in_progress"
        await self.db.commit()
        
        try:
            # Scrape
            raw_results = await self.scraper.search_businesses(
                query=target.industry,
                city=target.city,
                state=target.state,
                limit=50
            )
            
            # Filter
            qualified = self.qualifier.filter_batch(raw_results)
            
            # Save to database
            saved_count = 0
            for biz_data in qualified:
                # Check if already exists
                existing = await self._find_existing(biz_data["gmb_id"])
                if not existing:
                    business = Business(
                        gmb_id=biz_data["gmb_id"],
                        name=biz_data["name"],
                        slug=self._generate_slug(biz_data["name"]),
                        email=biz_data.get("email"),
                        phone=biz_data.get("phone"),
                        city=biz_data.get("city"),
                        state=biz_data.get("state"),
                        category=biz_data.get("category"),
                        rating=biz_data.get("rating"),
                        review_count=biz_data.get("review_count"),
                        qualification_score=biz_data.get("qualification_score", 0),
                        coverage_grid_id=target.id
                    )
                    self.db.add(business)
                    saved_count += 1
            
            # Update target stats
            target.status = "completed"
            target.lead_count = len(raw_results)
            target.qualified_count = len(qualified)
            target.last_scraped_at = func.now()
            
            await self.db.commit()
            
            return {
                "target": f"{target.city}, {target.state} - {target.industry}",
                "scraped": len(raw_results),
                "qualified": len(qualified),
                "saved": saved_count
            }
            
        except Exception as e:
            target.status = "pending"  # Reset for retry
            await self.db.commit()
            raise
    
    async def run_autopilot_tick(self) -> Optional[dict]:
        """
        Run one iteration of the autopilot.
        Call this periodically from Celery.
        """
        target = await self.get_next_target()
        if not target:
            return None
        
        return await self.process_target(target)
```

---

## 🎨 Creative Module (AI Generation)

### `services/creative/orchestrator.py`

```python
"""
Creative pipeline orchestrator.
Coordinates the multi-agent website generation process.
"""
from typing import Dict, Any
from dataclasses import dataclass
from .agents.analyst import AnalystAgent
from .agents.concept import ConceptAgent
from .agents.director import ArtDirectorAgent
from .agents.architect import ArchitectAgent
from .prompts.loader import PromptLoader

@dataclass
class GenerationResult:
    """Result of the full generation pipeline."""
    success: bool
    html_content: str
    css_content: str
    js_content: str
    creative_dna: Dict
    design_brief: Dict
    builder_prompt: str
    error: str = None

class CreativePipeline:
    """
    Orchestrates the 4-agent website generation process.
    
    Flow:
    1. Analyst → Extracts brand DNA from business data
    2. Concept → Invents brand personality/angle
    3. Director → Creates detailed design brief
    4. Architect → Writes the actual code
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.prompt_loader = PromptLoader(db_session)
        
        # Initialize agents
        self.analyst = AnalystAgent(self.prompt_loader)
        self.concept = ConceptAgent(self.prompt_loader)
        self.director = ArtDirectorAgent(self.prompt_loader)
        self.architect = ArchitectAgent(self.prompt_loader)
    
    async def generate(self, business: Dict) -> GenerationResult:
        """
        Run the full generation pipeline for a business.
        
        Args:
            business: Business data dict with GMB info
            
        Returns:
            GenerationResult with all outputs
        """
        try:
            # Step 1: Analyze the business
            analysis = await self.analyst.analyze(business)
            
            # Step 2: Generate brand concept
            concept = await self.concept.create_concept(
                business=business,
                analysis=analysis
            )
            
            # Combine into Creative DNA
            creative_dna = {
                **analysis,
                **concept,
                "generated_identity": concept
            }
            
            # Step 3: Create design brief
            design_brief = await self.director.create_brief(
                business=business,
                creative_dna=creative_dna
            )
            
            # Step 4: Build the website
            code_result = await self.architect.build(
                business=business,
                creative_dna=creative_dna,
                design_brief=design_brief
            )
            
            return GenerationResult(
                success=True,
                html_content=code_result["html"],
                css_content=code_result.get("css", ""),
                js_content=code_result.get("js", ""),
                creative_dna=creative_dna,
                design_brief=design_brief,
                builder_prompt=code_result.get("prompt_used", "")
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                html_content="",
                css_content="",
                js_content="",
                creative_dna={},
                design_brief={},
                builder_prompt="",
                error=str(e)
            )
```

### `services/creative/agents/base.py`

```python
"""
Base agent class with common functionality.
"""
from abc import ABC, abstractmethod
from anthropic import Anthropic
from typing import Dict, Any
from ....core.config import get_settings

class BaseAgent(ABC):
    """Base class for all AI agents."""
    
    def __init__(self, prompt_loader):
        settings = get_settings()
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.prompt_loader = prompt_loader
        self.model = "claude-sonnet-4-20250514"
    
    async def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096
    ) -> str:
        """Make a call to Claude."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.content[0].text
    
    async def call_llm_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096
    ) -> Dict:
        """Make a call expecting JSON response."""
        response = await self.call_llm(
            system_prompt=system_prompt + "\n\nRespond ONLY with valid JSON.",
            user_prompt=user_prompt,
            max_tokens=max_tokens
        )
        
        # Parse JSON from response
        import json
        # Handle markdown code blocks
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        return json.loads(response.strip())
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the agent's task."""
        pass
```

### `services/creative/agents/analyst.py`

```python
"""
Analyst Agent - Extracts brand DNA from business data.
"""
from typing import Dict
from .base import BaseAgent

class AnalystAgent(BaseAgent):
    """
    Analyzes GMB data to extract:
    - Review highlights (the "hook" for emails)
    - Brand archetype
    - Key selling points
    - Tone of voice
    """
    
    AGENT_NAME = "analyst"
    
    async def analyze(self, business: Dict) -> Dict:
        """
        Analyze a business and extract brand DNA.
        
        Args:
            business: Dict with name, category, reviews, etc.
            
        Returns:
            Analysis dict with extracted data
        """
        # Load dynamic prompt sections from database
        sections = await self.prompt_loader.load_sections(self.AGENT_NAME)
        
        system_prompt = self._build_system_prompt(sections)
        user_prompt = self._build_user_prompt(business)
        
        result = await self.call_llm_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return result
    
    def _build_system_prompt(self, sections: Dict) -> str:
        """Construct the system prompt with dynamic sections."""
        return f"""You are a Creative Director and Sales Strategist.

Your task is to analyze a business and extract key insights for:
1. A personalized sales email
2. A custom website design

{sections.get('analysis_guidelines', '')}

OUTPUT FORMAT:
{{
    "brand_archetype": "The Sage | The Hero | The Caregiver | etc.",
    "review_highlight": "A specific thing customers rave about",
    "key_selling_points": ["point1", "point2", "point3"],
    "tone_of_voice": "Description of how they should sound",
    "target_emotion": "What feeling the website should evoke",
    "suggested_headline": "A powerful H1 for the hero section"
}}"""
    
    def _build_user_prompt(self, business: Dict) -> str:
        """Build the user prompt with business data."""
        reviews_text = ""
        if business.get("reviews_data"):
            reviews_text = "\n".join([
                f"- {r.get('text', '')[:200]}"
                for r in business["reviews_data"][:10]
            ])
        
        return f"""Analyze this business:

BUSINESS NAME: {business.get('name', 'Unknown')}
CATEGORY: {business.get('category', 'Unknown')}
RATING: {business.get('rating', 'N/A')} stars ({business.get('review_count', 0)} reviews)
LOCATION: {business.get('city', '')}, {business.get('state', '')}

SAMPLE REVIEWS:
{reviews_text or 'No reviews available'}

Extract the brand DNA."""
```

### `services/creative/agents/director.py`

```python
"""
Art Director Agent - Creates detailed design briefs.
"""
from typing import Dict
from .base import BaseAgent

class ArtDirectorAgent(BaseAgent):
    """
    Creates a technical design brief including:
    - Typography choices
    - Color palette
    - Layout structure
    - Loader design
    - Hero section concept
    - Micro-interactions
    - Background treatments
    """
    
    AGENT_NAME = "director"
    
    async def create_brief(
        self,
        business: Dict,
        creative_dna: Dict
    ) -> Dict:
        """
        Create a detailed design brief.
        
        Args:
            business: Business data
            creative_dna: Output from Analyst + Concept agents
            
        Returns:
            Design brief dict
        """
        sections = await self.prompt_loader.load_sections(self.AGENT_NAME)
        
        system_prompt = self._build_system_prompt(sections)
        user_prompt = self._build_user_prompt(business, creative_dna)
        
        result = await self.call_llm_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=4096
        )
        
        return result
    
    def _build_system_prompt(self, sections: Dict) -> str:
        """Build system prompt with configurable sections."""
        
        # These sections are editable from the admin UI
        vibe_list = sections.get('vibe_list', self._default_vibe_list())
        typography_rules = sections.get('typography_rules', self._default_typography())
        banned_patterns = sections.get('banned_patterns', self._default_banned())
        
        return f"""You are a Senior Frontend Architect known for Awwwards-winning designs.

ROLE: Create a technical design brief for a landing page. Do NOT write code.
Be bold. Be distinctive. Avoid generic "AI slop" aesthetics.

{sections.get('frontend_aesthetics', '')}

AVAILABLE VIBES (choose one or blend):
{vibe_list}

TYPOGRAPHY RULES:
{typography_rules}

BANNED PATTERNS (never use these):
{banned_patterns}

OUTPUT FORMAT:
{{
    "vibe": "The selected design vibe",
    "typography": {{
        "heading_font": "Google Font name",
        "body_font": "Google Font name",
        "font_reasoning": "Why these fonts match the brand"
    }},
    "colors": {{
        "primary": "#hex",
        "secondary": "#hex",
        "accent": "#hex",
        "background": "#hex",
        "text": "#hex",
        "color_reasoning": "Why this palette"
    }},
    "loader": {{
        "type": "Description of loader animation",
        "duration_ms": 2500
    }},
    "hero_section": {{
        "layout": "Description of hero layout",
        "headline_treatment": "How the headline should be styled",
        "background_treatment": "Gradient, pattern, image, etc."
    }},
    "cursor": {{
        "type": "default | custom | spotlight | grow",
        "description": "If custom, describe the interaction"
    }},
    "micro_interactions": [
        "Description of interaction 1",
        "Description of interaction 2"
    ],
    "overall_atmosphere": "One paragraph describing the feel"
}}"""
    
    def _default_vibe_list(self) -> str:
        return """- Swiss International: Grid systems, clean typography, huge whitespace
- Neo-Brutalism: Hard outlines, raw HTML feel, high contrast
- Glassmorphism: Blur effects, frosted glass, soft gradients
- Dark Luxury: Gold/silver on black, serif fonts, slow fades
- Industrial: Monospace fonts, technical lines, blueprint aesthetics
- Retro-Futurism: Neon colors, CRT effects, 80s nostalgia
- Organic/Natural: Earth tones, flowing shapes, botanical elements
- Cyber-Medical: Clinical whites with neon accents, precision"""
    
    def _default_typography(self) -> str:
        return """BANNED FONTS: Roboto, Open Sans, Lato, Montserrat, Poppins, Inter, Arial
PREFERRED: Syne, Clash Display, Cabinet Grotesk, Outfit, Plus Jakarta Sans, 
           DM Serif Display, Fraunces, Playfair Display, Space Mono"""
    
    def _default_banned(self) -> str:
        return """- Purple gradients on white backgrounds
- Generic blue (#3B82F6) as primary
- Centered text-over-stock-image heroes
- Cookie-cutter card layouts
- Floating abstract shapes with no purpose"""
    
    def _build_user_prompt(self, business: Dict, creative_dna: Dict) -> str:
        return f"""Create a design brief for:

BUSINESS: {business.get('name')}
CATEGORY: {business.get('category')}
LOCATION: {business.get('city')}, {business.get('state')}

CREATIVE DNA:
- Archetype: {creative_dna.get('brand_archetype', 'Unknown')}
- Angle: {creative_dna.get('angle', 'Unknown')}
- Tone: {creative_dna.get('tone_of_voice', 'Professional')}
- Target Emotion: {creative_dna.get('target_emotion', 'Trust')}
- Suggested Headline: {creative_dna.get('suggested_headline', '')}

Design a website that will STOP THE SCROLL and make this business look world-class."""
```

### `services/creative/prompts/loader.py`

```python
"""
Dynamic prompt loader - fetches prompts from database.
Enables editing prompts via admin UI without code changes.
"""
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ....models.prompt_settings import PromptSettings

class PromptLoader:
    """
    Loads prompt sections from the database.
    Falls back to defaults if not found.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache: Dict[str, Dict] = {}
    
    async def load_sections(
        self,
        agent_name: str,
        use_cache: bool = True
    ) -> Dict[str, str]:
        """
        Load all prompt sections for an agent.
        
        Args:
            agent_name: analyst, concept, director, architect
            use_cache: Whether to use cached values
            
        Returns:
            Dict mapping section_name to content
        """
        cache_key = f"agent:{agent_name}"
        
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        query = (
            select(PromptSettings)
            .where(PromptSettings.agent_name == agent_name)
            .where(PromptSettings.is_active == True)
        )
        
        result = await self.db.execute(query)
        rows = result.scalars().all()
        
        sections = {}
        for row in rows:
            sections[row.section_name] = row.content
        
        if use_cache:
            self._cache[cache_key] = sections
        
        return sections
    
    async def load_section(
        self,
        agent_name: str,
        section_name: str,
        default: str = ""
    ) -> str:
        """Load a specific section."""
        sections = await self.load_sections(agent_name)
        return sections.get(section_name, default)
    
    def clear_cache(self, agent_name: Optional[str] = None):
        """Clear the cache for an agent or all agents."""
        if agent_name:
            cache_key = f"agent:{agent_name}"
            self._cache.pop(cache_key, None)
        else:
            self._cache.clear()
```

---

## 📧 Pitcher Module (Outreach)

### `services/pitcher/email_composer.py`

```python
"""
Personalized email composition using AI.
"""
from typing import Dict
from ..creative.agents.base import BaseAgent

class EmailComposer(BaseAgent):
    """Composes personalized cold emails."""
    
    AGENT_NAME = "email_composer"
    
    async def compose(
        self,
        business: Dict,
        site_url: str,
        review_highlight: str
    ) -> Dict:
        """
        Compose a personalized email.
        
        Returns:
            {"subject": "...", "body": "...", "preview_text": "..."}
        """
        sections = await self.prompt_loader.load_sections(self.AGENT_NAME)
        
        template = sections.get('email_template', self._default_template())
        
        # Simple template substitution (not AI for efficiency)
        email_body = template.format(
            business_name=business.get('name', 'your business'),
            review_highlight=review_highlight,
            site_url=site_url,
            sender_name="Hugo"
        )
        
        # AI-generated subject line for better open rates
        subject = await self._generate_subject(business, review_highlight)
        
        return {
            "subject": subject,
            "body": email_body,
            "preview_text": f"I built a website for {business.get('name')}..."
        }
    
    async def _generate_subject(
        self,
        business: Dict,
        review_highlight: str
    ) -> str:
        """Generate a compelling subject line."""
        response = await self.call_llm(
            system_prompt="""Generate an email subject line that:
1. Looks like it's from a customer, not a salesperson
2. References something specific about the business
3. Is under 50 characters
4. Creates curiosity

Output ONLY the subject line, nothing else.""",
            user_prompt=f"""Business: {business.get('name')}
Category: {business.get('category')}
Review highlight: {review_highlight}

Generate a subject line:""",
            max_tokens=100
        )
        return response.strip().strip('"')
    
    def _default_template(self) -> str:
        return """Hi there,

I was checking {business_name} on Google Maps and the reviews are incredible. It looks like {review_highlight}.

I noticed you don't have a website to showcase that reputation. You're leaving money on the table.

My name is {sender_name}. I took the liberty of building a concept site for you already. I used your brand style and focused on the reviews.

**You can see it here:** {site_url}

If you like it, you can claim it right now for **$500** (one-time) + **$99/mo** for hosting. I can transfer it to your own domain immediately.

Best,
{sender_name}"""
```

### `services/pitcher/screenshot.py`

```python
"""
Screenshot generation using Playwright.
"""
from playwright.async_api import async_playwright
from pathlib import Path
import asyncio

class ScreenshotService:
    """Generates screenshots of generated websites."""
    
    async def capture(
        self,
        html_path: str,
        output_dir: str,
        subdomain: str
    ) -> Dict[str, str]:
        """
        Capture desktop and mobile screenshots.
        
        Returns:
            {"desktop": "path/to/desktop.png", "mobile": "path/to/mobile.png"}
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            
            # Desktop screenshot (1440x900)
            desktop_path = await self._capture_viewport(
                browser=browser,
                html_path=html_path,
                output_path=output_path / f"{subdomain}_desktop.png",
                width=1440,
                height=900
            )
            
            # Mobile screenshot (390x844 - iPhone 14)
            mobile_path = await self._capture_viewport(
                browser=browser,
                html_path=html_path,
                output_path=output_path / f"{subdomain}_mobile.png",
                width=390,
                height=844
            )
            
            await browser.close()
        
        return {
            "desktop": str(desktop_path),
            "mobile": str(mobile_path)
        }
    
    async def _capture_viewport(
        self,
        browser,
        html_path: str,
        output_path: Path,
        width: int,
        height: int
    ) -> Path:
        """Capture a single viewport."""
        page = await browser.new_page(
            viewport={"width": width, "height": height}
        )
        
        # Load the HTML file
        await page.goto(f"file://{html_path}")
        
        # Wait for animations to complete
        await asyncio.sleep(3)
        
        # Take screenshot
        await page.screenshot(path=str(output_path), full_page=False)
        await page.close()
        
        return output_path
```

---

## 💳 Payments Module (Recurrente)

See dedicated document: [BLUEPRINT_05_PAYMENTS_RECURRENTE.md](./BLUEPRINT_05_PAYMENTS_RECURRENTE.md)

---

## 📡 API Routes

### `api/v1/settings.py`

```python
"""
Prompt settings management API.
Allows editing prompts via admin dashboard.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ...core.database import get_db
from ...models.prompt_settings import PromptSettings
from ..schemas.settings import (
    PromptSettingRead,
    PromptSettingCreate,
    PromptSettingUpdate
)

router = APIRouter(prefix="/settings/prompts", tags=["settings"])

@router.get("/agents")
async def list_agents() -> List[str]:
    """List all agent names."""
    return ["analyst", "concept", "director", "architect", "email_composer"]

@router.get("/agents/{agent_name}")
async def get_agent_sections(
    agent_name: str,
    db: AsyncSession = Depends(get_db)
) -> List[PromptSettingRead]:
    """Get all prompt sections for an agent."""
    query = select(PromptSettings).where(
        PromptSettings.agent_name == agent_name
    ).order_by(PromptSettings.section_name)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.put("/agents/{agent_name}/{section_name}")
async def update_section(
    agent_name: str,
    section_name: str,
    data: PromptSettingUpdate,
    db: AsyncSession = Depends(get_db)
) -> PromptSettingRead:
    """
    Update a prompt section.
    Creates a new version if content changed.
    """
    # Find existing
    query = select(PromptSettings).where(
        PromptSettings.agent_name == agent_name,
        PromptSettings.section_name == section_name,
        PromptSettings.is_active == True
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        # Deactivate old version
        existing.is_active = False
        
        # Create new version
        new_version = PromptSettings(
            agent_name=agent_name,
            section_name=section_name,
            content=data.content,
            description=data.description or existing.description,
            version=existing.version + 1,
            is_active=True
        )
        db.add(new_version)
    else:
        # Create first version
        new_version = PromptSettings(
            agent_name=agent_name,
            section_name=section_name,
            content=data.content,
            description=data.description,
            version=1,
            is_active=True
        )
        db.add(new_version)
    
    await db.commit()
    await db.refresh(new_version)
    
    # Clear cache
    from ...services.creative.prompts.loader import PromptLoader
    # (In practice, use dependency injection for the loader)
    
    return new_version
```

---

## 🔄 Celery Tasks

### `tasks/creative_tasks.py`

```python
"""
Async tasks for website generation.
"""
from celery import shared_task
from .celery_app import celery_app
from ..core.database import AsyncSessionLocal
from ..services.creative.orchestrator import CreativePipeline
from ..services.pitcher.screenshot import ScreenshotService
from ..models.business import Business
from ..models.site import GeneratedSite

@celery_app.task(bind=True, max_retries=3)
async def generate_site_for_business(self, business_id: str):
    """
    Generate a website for a business.
    
    This is the main generation task that:
    1. Runs the creative pipeline
    2. Saves the generated site
    3. Takes screenshots
    4. Updates business status
    """
    async with AsyncSessionLocal() as db:
        # Load business
        business = await db.get(Business, business_id)
        if not business:
            return {"error": "Business not found"}
        
        # Update status
        business.website_status = "generating"
        await db.commit()
        
        try:
            # Run pipeline
            pipeline = CreativePipeline(db)
            result = await pipeline.generate(business.to_dict())
            
            if not result.success:
                business.website_status = "failed"
                await db.commit()
                return {"error": result.error}
            
            # Create site record
            site = GeneratedSite(
                business_id=business.id,
                subdomain=business.slug,
                html_content=result.html_content,
                css_content=result.css_content,
                js_content=result.js_content,
                creative_dna=result.creative_dna,
                design_brief=result.design_brief,
                builder_prompt=result.builder_prompt,
                status="draft"
            )
            db.add(site)
            
            # Update business
            business.website_status = "generated"
            business.creative_dna = result.creative_dna
            
            await db.commit()
            await db.refresh(site)
            
            # Trigger screenshot task
            take_screenshots.delay(str(site.id))
            
            return {
                "success": True,
                "site_id": str(site.id),
                "subdomain": site.subdomain
            }
            
        except Exception as e:
            business.website_status = "failed"
            await db.commit()
            raise self.retry(exc=e)

@celery_app.task
async def take_screenshots(site_id: str):
    """Take screenshots of a generated site."""
    async with AsyncSessionLocal() as db:
        site = await db.get(GeneratedSite, site_id)
        if not site:
            return
        
        # Write HTML to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.html',
            delete=False
        ) as f:
            f.write(site.html_content)
            html_path = f.name
        
        # Take screenshots
        service = ScreenshotService()
        screenshots = await service.capture(
            html_path=html_path,
            output_dir="/var/www/screenshots",
            subdomain=site.subdomain
        )
        
        # Update site record
        site.screenshot_desktop_url = screenshots["desktop"]
        site.screenshot_mobile_url = screenshots["mobile"]
        site.status = "preview"
        
        await db.commit()
```
