"""
Analyst Agent - extracts insights from business data and reviews.
Identifies brand archetype, emotional triggers, and key differentiators.
"""
from typing import Dict, Any, List, Optional
import logging

from services.creative.agents.base import BaseAgent
from services.creative.prompts.builder import PromptBuilder

logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent):
    """
    Analyst Agent: Analyzes business data to extract strategic insights.
    
    Input: Business data (name, category, rating, reviews, photos)
    Output: Brand archetype, emotional triggers, differentiators, sentiment
    """
    
    def __init__(self, prompt_builder: PromptBuilder, model: str = "claude-sonnet-4-5"):
        super().__init__(
            agent_name="analyst",
            model=model,
            temperature=0.5,  # Lower temp for more analytical output
            max_tokens=64000  # Max for Claude Sonnet 4.5
        )
        self.prompt_builder = prompt_builder
    
    async def analyze(
        self,
        business_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze business data and extract insights.
        
        Args:
            business_data: Dictionary containing:
                - name: Business name
                - category: Business category
                - location: City, State
                - rating: Average rating (0-5)
                - review_count: Number of reviews
                - reviews_data: List of review dicts with 'text' and 'rating'
                - photos_urls: List of photo URLs (optional)
                
        Returns:
            Dictionary with analysis:
                - review_highlight: Best customer quote (1-2 sentences)
                - brand_archetype: Brand archetype (Hero, Creator, etc.)
                - emotional_triggers: List of emotional triggers
                - key_differentiators: List of unique selling points
                - customer_sentiment: Overall sentiment
                - tone_descriptors: List of tone words
                - content_themes: Main themes to emphasize
        """
        logger.info(f"Analyzing business: {business_data.get('name')}")
        
        # Prepare review text
        review_texts = self._format_reviews(
            business_data.get("reviews_data", [])
        )
        
        # Build prompts
        system_prompt, user_prompt = await self.prompt_builder.build_prompts(
            agent_name="analyst",
            data={
                "name": business_data.get("name", "Unknown Business"),
                "category": business_data.get("category", "Business"),
                "location": f"{business_data.get('city', '')}, {business_data.get('state', '')}",
                "rating": business_data.get("rating", 0),
                "review_count": business_data.get("review_count", 0),
                "reviews": review_texts,
                "has_photos": len(business_data.get("photos_urls", [])) > 0,
                "photo_count": len(business_data.get("photos_urls", []))
            }
        )
        
        # Generate analysis
        try:
            result = await self.generate_json(system_prompt, user_prompt)
            
            # Validate and enhance result
            analysis = self._validate_analysis(result, business_data)
            
            logger.info(
                f"Analysis complete: {analysis.get('brand_archetype')} archetype"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            # Return fallback analysis
            return self._create_fallback_analysis(business_data)
    
    def _format_reviews(self, reviews_data: List[Dict[str, Any]]) -> str:
        """Format reviews for prompt."""
        if not reviews_data:
            return "No reviews available."
        
        formatted = []
        for i, review in enumerate(reviews_data[:20], 1):  # Max 20 reviews
            text = review.get("text", "").strip()
            rating = review.get("rating")
            if text:
                formatted.append(
                    f"Review {i} ({rating}★): {text}"
                )
        
        return "\n\n".join(formatted) if formatted else "No reviews available."
    
    def _validate_analysis(
        self,
        result: Dict[str, Any],
        business_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and enhance analysis result.
        Ensures all required fields are present.
        """
        # Default values
        validated = {
            "review_highlight": result.get(
                "review_highlight",
                "Customers love this business."
            ),
            "brand_archetype": result.get(
                "brand_archetype",
                "The Everyman"
            ),
            "emotional_triggers": result.get(
                "emotional_triggers",
                ["trust", "quality"]
            ),
            "key_differentiators": result.get(
                "key_differentiators",
                ["experienced", "reliable"]
            ),
            "customer_sentiment": result.get(
                "customer_sentiment",
                "positive"
            ),
            "tone_descriptors": result.get(
                "tone_descriptors",
                ["professional", "friendly"]
            ),
            "content_themes": result.get(
                "content_themes",
                ["expertise", "customer service"]
            )
        }
        
        # Ensure lists are actually lists
        for key in ["emotional_triggers", "key_differentiators", "tone_descriptors", "content_themes"]:
            if not isinstance(validated[key], list):
                validated[key] = [validated[key]]
        
        # Add metadata
        validated["_metadata"] = {
            "business_name": business_data.get("name"),
            "category": business_data.get("category"),
            "rating": business_data.get("rating"),
            "review_count": business_data.get("review_count")
        }
        
        return validated
    
    def _create_fallback_analysis(
        self,
        business_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create basic analysis when AI fails."""
        category = business_data.get("category", "business")
        name = business_data.get("name", "this business")
        rating = business_data.get("rating") or 0
        
        return {
            "review_highlight": f"Customers highly recommend {name} for quality {category} services.",
            "brand_archetype": "The Everyman",
            "emotional_triggers": ["trust", "reliability", "quality"],
            "key_differentiators": ["experienced", "customer-focused", "reliable"],
            "customer_sentiment": "positive" if rating >= 4.0 else "mixed",
            "tone_descriptors": ["professional", "approachable", "trustworthy"],
            "content_themes": ["expertise", "customer satisfaction", "quality service"],
            "_metadata": {
                "business_name": name,
                "category": category,
                "rating": rating,
                "review_count": business_data.get("review_count", 0),
                "fallback": True
            }
        }


# Brand archetypes reference for documentation
BRAND_ARCHETYPES = {
    "The Hero": "Brave, bold, confident. Overcomes challenges.",
    "The Creator": "Innovative, artistic, imaginative. Creates value.",
    "The Sage": "Wise, expert, trusted advisor. Shares knowledge.",
    "The Caregiver": "Nurturing, compassionate, supportive. Helps others.",
    "The Explorer": "Adventurous, independent, pioneering. Seeks discovery.",
    "The Rebel": "Revolutionary, disruptive, bold. Breaks rules.",
    "The Magician": "Transformative, visionary, charismatic. Makes dreams real.",
    "The Lover": "Passionate, intimate, sensual. Creates connection.",
    "The Jester": "Playful, humorous, lighthearted. Brings joy.",
    "The Everyman": "Relatable, down-to-earth, authentic. Builds belonging.",
    "The Ruler": "Authoritative, organized, successful. Takes control.",
    "The Innocent": "Optimistic, pure, simple. Spreads happiness."
}
