"""
Orchestrator - chains all creative agents together.
Manages the complete website generation pipeline.
"""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import time
from datetime import datetime

from services.creative.agents.analyst import AnalystAgent
from services.creative.agents.concept import ConceptAgent
from services.creative.agents.director import ArtDirectorAgent
from services.creative.agents.architect_v2 import ArchitectAgentV2
from services.creative.prompts.loader import PromptLoader
from services.creative.prompts.builder import PromptBuilder
from services.system_settings_service import SystemSettingsService
from core.exceptions import GenerationException

logger = logging.getLogger(__name__)


class CreativeOrchestrator:
    """
    Orchestrates the complete website generation pipeline.
    Chains Analyst → Concept → Art Director → Architect.
    """
    
    def __init__(self, db: AsyncSession, model_override: Optional[str] = None):
        """
        Initialize orchestrator with all agents.
        
        Args:
            db: Database session for prompt loading
            model_override: Optional model name to override system settings
        """
        self.db = db
        self.model_override = model_override
        
        # Initialize prompt system
        self.prompt_loader = PromptLoader(db)
        self.prompt_builder = PromptBuilder(self.prompt_loader)
        
        # Agents will be initialized with dynamic model in generate_website
        self.analyst = None
        self.concept = None
        self.director = None
        self.architect = None
        
        logger.info("Creative Orchestrator initialized")
    
    async def generate_website(
        self,
        business_data: Dict[str, Any],
        save_intermediate: bool = True,
        subdomain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete website through multi-agent pipeline.
        
        Workflow:
        1. Analyst: Extract insights from reviews
        2. Concept: Generate brand personality
        3. Art Director: Create design brief
        4. Architect: Generate HTML/CSS/JS
        
        Args:
            business_data: Business information
            save_intermediate: Whether to save intermediate outputs
            
        Returns:
            Dictionary with all outputs and final website code
            
        Raises:
            GenerationException: If any stage fails critically
        """
        business_name = business_data.get("name", "Unknown")
        logger.info(f"Starting website generation for: {business_name}")
        
        # Load AI model configuration from system settings
        try:
            if self.model_override:
                model = self.model_override
                logger.info(f"Using model override: {model}")
            else:
                ai_config = await SystemSettingsService.get_ai_config(self.db)
                model = ai_config["llm"]["model"]
                provider = ai_config["llm"]["provider"]
                logger.info(f"Using configured model: {provider}/{model}")
        except Exception as e:
            # Fallback to default if settings not found
            model = "claude-sonnet-4-5"
            logger.warning(f"Failed to load model config, using default: {model}. Error: {e}")
        
        # Initialize agents with dynamic model
        self.analyst = AnalystAgent(self.prompt_builder, model=model)
        self.concept = ConceptAgent(self.prompt_builder, model=model)
        self.director = ArtDirectorAgent(self.prompt_builder, model=model)
        self.architect = ArchitectAgentV2(self.prompt_builder, model=model)
        
        start_time = time.time()
        results = {
            "business_id": business_data.get("id"),
            "business_name": business_name,
            "started_at": datetime.utcnow().isoformat(),
            "status": "in_progress",
            "ai_model": model
        }
        
        try:
            # Stage 1: Analyst
            logger.info(f"[{business_name}] Stage 1/4: Analyzing business...")
            stage_start = time.time()
            
            analysis = await self.analyst.analyze(business_data)
            results["analysis"] = analysis
            results["stage_1_duration_ms"] = (time.time() - stage_start) * 1000
            
            logger.info(
                f"[{business_name}] Analysis complete in {results['stage_1_duration_ms']:.0f}ms: "
                f"{analysis.get('brand_archetype')}"
            )
            
            # Stage 2: Concept
            logger.info(f"[{business_name}] Stage 2/4: Generating brand concepts...")
            stage_start = time.time()
            
            concepts = await self.concept.generate_concepts(business_data, analysis)
            results["concepts"] = concepts
            results["creative_dna"] = concepts.get("creative_dna")
            results["stage_2_duration_ms"] = (time.time() - stage_start) * 1000
            
            logger.info(
                f"[{business_name}] Concepts complete in {results['stage_2_duration_ms']:.0f}ms: "
                f"{concepts.get('selected_concept', {}).get('name')}"
            )
            
            # Stage 3: Art Director
            logger.info(f"[{business_name}] Stage 3/4: Creating design brief...")
            stage_start = time.time()
            
            design_brief = await self.director.create_brief(
                business_data,
                concepts.get("creative_dna", {})
            )
            results["design_brief"] = design_brief
            results["stage_3_duration_ms"] = (time.time() - stage_start) * 1000
            
            logger.info(
                f"[{business_name}] Design brief complete in {results['stage_3_duration_ms']:.0f}ms: "
                f"{design_brief.get('vibe')} vibe"
            )
            
            # Stage 4: Architect
            logger.info(f"[{business_name}] Stage 4/4: Generating website code...")
            stage_start = time.time()
            
            website = await self.architect.generate_website(
                business_data,
                concepts.get("creative_dna", {}),
                design_brief,
                subdomain=subdomain,
            )
            results["website"] = website
            results["stage_4_duration_ms"] = (time.time() - stage_start) * 1000
            
            logger.info(
                f"[{business_name}] Website code complete in {results['stage_4_duration_ms']:.0f}ms: "
                f"{len(website.get('html', ''))} chars"
            )
            
            # Calculate total duration
            total_duration = time.time() - start_time
            results["total_duration_ms"] = total_duration * 1000
            results["completed_at"] = datetime.utcnow().isoformat()
            results["status"] = "completed"
            
            logger.info(
                f"[{business_name}] ✅ Complete generation pipeline finished in {total_duration:.1f}s"
            )
            
            return results
            
        except Exception as e:
            # Log error and update results
            logger.error(
                f"[{business_name}] ❌ Generation failed: {str(e)}",
                exc_info=True
            )
            
            results["status"] = "failed"
            results["error"] = str(e)
            results["failed_at"] = datetime.utcnow().isoformat()
            
            raise GenerationException(
                f"Website generation failed for {business_name}: {str(e)}"
            )
    
    async def regenerate_stage(
        self,
        business_data: Dict[str, Any],
        stage: str,
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Regenerate a specific stage (for iteration).
        
        Args:
            business_data: Business information
            stage: Stage to regenerate ("analysis", "concepts", "design", "code")
            previous_results: Previous generation results
            
        Returns:
            Updated results with regenerated stage
        """
        logger.info(f"Regenerating stage: {stage}")
        
        if stage == "analysis":
            analysis = await self.analyst.analyze(business_data)
            return {"analysis": analysis}
        
        elif stage == "concepts":
            analysis = previous_results.get("analysis", {})
            concepts = await self.concept.generate_concepts(business_data, analysis)
            return {"concepts": concepts, "creative_dna": concepts.get("creative_dna")}
        
        elif stage == "design":
            creative_dna = previous_results.get("creative_dna", {})
            design_brief = await self.director.create_brief(business_data, creative_dna)
            return {"design_brief": design_brief}
        
        elif stage == "code":
            creative_dna = previous_results.get("creative_dna", {})
            design_brief = previous_results.get("design_brief", {})
            website = await self.architect.generate_website(
                business_data,
                creative_dna,
                design_brief,
            )
            return {"website": website}
        
        else:
            raise ValueError(f"Unknown stage: {stage}")
    
    def get_generation_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get human-readable summary of generation results.
        
        Args:
            results: Complete generation results
            
        Returns:
            Summary dictionary
        """
        if results.get("status") != "completed":
            return {
                "status": results.get("status"),
                "error": results.get("error"),
                "message": "Generation incomplete or failed"
            }
        
        return {
            "status": "completed",
            "business_name": results.get("business_name"),
            "total_duration_seconds": results.get("total_duration_ms", 0) / 1000,
            "brand_archetype": results.get("analysis", {}).get("brand_archetype"),
            "concept_name": results.get("concepts", {}).get("selected_concept", {}).get("name"),
            "design_vibe": results.get("design_brief", {}).get("vibe"),
            "primary_font": results.get("design_brief", {}).get("typography", {}).get("display"),
            "html_size": len(results.get("website", {}).get("html", "")),
            "css_size": len(results.get("website", {}).get("css", "")),
            "js_size": len(results.get("website", {}).get("js", "")),
            "assets_count": len(results.get("website", {}).get("assets_needed", [])),
            "stage_durations": {
                "analysis_ms": results.get("stage_1_duration_ms"),
                "concepts_ms": results.get("stage_2_duration_ms"),
                "design_ms": results.get("stage_3_duration_ms"),
                "code_ms": results.get("stage_4_duration_ms")
            }
        }
