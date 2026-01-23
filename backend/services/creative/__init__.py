"""
Creative Engine: AI-powered website generation system.
Multi-agent pipeline for personalized website creation.

Components:
- Agents: Analyst, Concept, Director, Architect
- Services: Orchestrator, SiteService, CategoryKnowledge, IndustryStyle
- Prompts: Builder, Loader

Usage:
    from services.creative.orchestrator import CreativeOrchestrator
    from services.creative.site_service import SiteService
    from services.creative.category_knowledge import CategoryKnowledgeService
    from services.creative.industry_style_service import IndustryStyleService
"""

# Lazy imports to avoid circular dependencies and allow standalone testing
__all__ = [
    "CreativeOrchestrator",
    "SiteService", 
    "CategoryKnowledgeService",
    "IndustryStyleService",
]


def __getattr__(name: str):
    """Lazy import of module components."""
    if name == "CreativeOrchestrator":
        from services.creative.orchestrator import CreativeOrchestrator
        return CreativeOrchestrator
    elif name == "SiteService":
        from services.creative.site_service import SiteService
        return SiteService
    elif name == "CategoryKnowledgeService":
        from services.creative.category_knowledge import CategoryKnowledgeService
        return CategoryKnowledgeService
    elif name == "IndustryStyleService":
        from services.creative.industry_style_service import IndustryStyleService
        return IndustryStyleService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
