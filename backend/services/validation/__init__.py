"""
Website validation services.
Provides URL prescreening, Playwright validation, and LLM-powered validation.
"""

# Lazy imports to avoid requiring all dependencies upfront
# Import specific modules as needed

__all__ = [
    "PlaywrightValidationService",
    "ContentAnalyzer",
    "URLPrescreener",
    "LLMWebsiteValidator",
    "ValidationOrchestrator",
]


def __getattr__(name):
    """Lazy import to avoid requiring Playwright/LLM dependencies until needed."""
    if name == "PlaywrightValidationService":
        from .playwright_service import PlaywrightValidationService
        return PlaywrightValidationService
    elif name == "ContentAnalyzer":
        from .content_analyzer import ContentAnalyzer
        return ContentAnalyzer
    elif name == "URLPrescreener":
        from .url_prescreener import URLPrescreener
        return URLPrescreener
    elif name == "LLMWebsiteValidator":
        from .llm_validator import LLMWebsiteValidator
        return LLMWebsiteValidator
    elif name == "ValidationOrchestrator":
        from .validation_orchestrator import ValidationOrchestrator
        return ValidationOrchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

