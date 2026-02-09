"""
Website discovery services.

Provides intelligent website discovery using:
- Google Search (ScrapingDog API)
- LLM-powered analysis and cross-referencing
- Business data validation
"""
from services.discovery.llm_discovery_service import LLMDiscoveryService

__all__ = ["LLMDiscoveryService"]
