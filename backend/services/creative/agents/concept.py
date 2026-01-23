"""
Concept Agent - generates brand personality and Creative DNA.
Takes analyst insights and creates cohesive brand concepts.
"""
from typing import Dict, Any, List
import logging

from services.creative.agents.base import BaseAgent
from services.creative.prompts.builder import PromptBuilder

logger = logging.getLogger(__name__)


class ConceptAgent(BaseAgent):
    """
    Concept Agent: Creates brand personality and "Creative DNA".
    
    Input: Analyst output + business data
    Output: 3 brand concepts + selected concept + Creative DNA
    """
    
    def __init__(self, prompt_builder: PromptBuilder, model: str = "claude-sonnet-4-5"):
        super().__init__(
            agent_name="concept",
            model=model,
            temperature=0.8,  # Higher temp for more creative concepts
            max_tokens=64000  # Max for Claude Sonnet 4.5
        )
        self.prompt_builder = prompt_builder
    
    async def generate_concepts(
        self,
        business_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate brand concepts and Creative DNA.
        
        Args:
            business_data: Original business data
            analysis: Output from Analyst agent
                
        Returns:
            Dictionary with:
                - concepts: List of 3 brand concept dicts
                - selected_concept_index: Index of best concept (0-2)
                - selected_concept: The chosen concept
                - creative_dna: Complete Creative DNA blueprint
        """
        logger.info(f"Generating concepts for: {business_data.get('name')}")
        
        # Build prompts
        system_prompt, user_prompt = await self.prompt_builder.build_prompts(
            agent_name="concept",
            data={
                "name": business_data.get("name"),
                "category": business_data.get("category"),
                "location": f"{business_data.get('city', '')}, {business_data.get('state', '')}",
                "brand_archetype": analysis.get("brand_archetype"),
                "emotional_triggers": ", ".join(analysis.get("emotional_triggers", [])),
                "differentiators": ", ".join(analysis.get("key_differentiators", [])),
                "tone": ", ".join(analysis.get("tone_descriptors", [])),
                "themes": ", ".join(analysis.get("content_themes", [])),
                "sentiment": analysis.get("customer_sentiment"),
                "review_highlight": analysis.get("review_highlight")
            }
        )
        
        # Generate concepts
        try:
            result = await self.generate_json(system_prompt, user_prompt)
            
            # Validate and enhance
            concepts_data = self._validate_concepts(result, business_data, analysis)
            
            logger.info(
                f"Generated {len(concepts_data['concepts'])} concepts, "
                f"selected: {concepts_data['selected_concept']['name']}"
            )
            
            return concepts_data
            
        except Exception as e:
            logger.error(f"Concept generation failed: {str(e)}")
            return self._create_fallback_concept(business_data, analysis)
    
    def _validate_concepts(
        self,
        result: Dict[str, Any],
        business_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and enhance concepts result."""
        # Get concepts
        concepts = result.get("concepts", [])
        if len(concepts) < 3:
            # Generate fallback if not enough concepts
            return self._create_fallback_concept(business_data, analysis)
        
        # Get selection
        selected_index = result.get("selected_concept_index", 0)
        if selected_index < 0 or selected_index >= len(concepts):
            selected_index = 0
        
        selected_concept = concepts[selected_index]
        
        # Build Creative DNA
        creative_dna = result.get("creative_dna", {})
        if not creative_dna:
            creative_dna = self._build_creative_dna(
                selected_concept,
                business_data,
                analysis
            )
        
        return {
            "concepts": concepts,
            "selected_concept_index": selected_index,
            "selected_concept": selected_concept,
            "creative_dna": creative_dna,
            "_metadata": {
                "business_name": business_data.get("name"),
                "concept_name": selected_concept.get("name"),
                "archetype": analysis.get("brand_archetype")
            }
        }
    
    def _build_creative_dna(
        self,
        concept: Dict[str, Any],
        business_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build Creative DNA from selected concept."""
        return {
            "concept_name": concept.get("name", "Brand Concept"),
            "personality_traits": concept.get("personality_traits", [
                analysis.get("brand_archetype", "professional").lower()
            ]),
            "communication_style": concept.get("communication_style", "conversational"),
            "tone_of_voice": concept.get("tone_of_voice", "friendly and professional"),
            "brand_story": concept.get("brand_story", ""),
            "value_proposition": concept.get("value_proposition", ""),
            "differentiation_angle": concept.get("differentiation_angle", ""),
            "emotional_core": analysis.get("emotional_triggers", [])[0] if analysis.get("emotional_triggers") else "trust",
            "target_emotion": concept.get("target_emotion", "confidence"),
            "content_pillars": analysis.get("content_themes", []),
            "keywords": concept.get("keywords", []),
            "avoid": concept.get("avoid", ["generic claims", "corporate jargon"])
        }
    
    def _create_fallback_concept(
        self,
        business_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create fallback concepts when AI fails."""
        name = business_data.get("name", "Business")
        category = business_data.get("category", "business")
        archetype = analysis.get("brand_archetype", "The Everyman")
        
        # Create 3 simple concepts
        concepts = [
            {
                "name": "Trusted Professional",
                "personality": f"Reliable, experienced {category} expert",
                "tone": "professional, approachable, trustworthy",
                "differentiation_angle": "Years of experience and customer satisfaction",
                "brand_story": f"{name} has built a reputation for quality {category} services.",
                "personality_traits": ["professional", "reliable", "experienced"],
                "communication_style": "clear and straightforward",
                "tone_of_voice": "confident yet approachable",
                "value_proposition": f"Quality {category} services you can trust",
                "target_emotion": "confidence",
                "keywords": ["quality", "experience", "trusted"]
            },
            {
                "name": "Customer Champion",
                "personality": "Customer-focused, caring, dedicated",
                "tone": "warm, personal, attentive",
                "differentiation_angle": "Exceptional customer service",
                "brand_story": f"At {name}, your satisfaction is our top priority.",
                "personality_traits": ["caring", "attentive", "dedicated"],
                "communication_style": "personal and warm",
                "tone_of_voice": "friendly and supportive",
                "value_proposition": "Service that puts you first",
                "target_emotion": "trust",
                "keywords": ["care", "service", "satisfaction"]
            },
            {
                "name": "Local Expert",
                "personality": "Community-rooted, knowledgeable, authentic",
                "tone": "local, genuine, experienced",
                "differentiation_angle": "Deep local knowledge and community connections",
                "brand_story": f"{name} is proud to serve the local community with authentic {category} expertise.",
                "personality_traits": ["local", "authentic", "knowledgeable"],
                "communication_style": "down-to-earth",
                "tone_of_voice": "genuine and relatable",
                "value_proposition": "Your trusted local {category} expert",
                "target_emotion": "belonging",
                "keywords": ["local", "community", "authentic"]
            }
        ]
        
        # Select based on archetype
        selected_index = 0  # Default to first
        
        # Build Creative DNA
        selected_concept = concepts[selected_index]
        creative_dna = self._build_creative_dna(
            selected_concept,
            business_data,
            analysis
        )
        
        return {
            "concepts": concepts,
            "selected_concept_index": selected_index,
            "selected_concept": selected_concept,
            "creative_dna": creative_dna,
            "_metadata": {
                "business_name": name,
                "concept_name": selected_concept["name"],
                "archetype": archetype,
                "fallback": True
            }
        }
