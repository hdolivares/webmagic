"""
Application configuration management.
Loads settings from environment variables with secure defaults.
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # App Info
    APP_NAME: str = "WebMagic"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    # API Keys
    OUTSCRAPER_API_KEY: str
    ANTHROPIC_API_KEY: str
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    TELNYX_API_KEY: Optional[str] = None
    TELNYX_PUBLIC_KEY: Optional[str] = None
    
    # JWT / Auth
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Frontend URL
    FRONTEND_URL: str = "https://web.lavish.solutions"
    
    # Site Serving
    SITES_DOMAIN: str = "sites.lavish.solutions"
    
    # Stripe Webhooks
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Telnyx Webhooks
    TELNYX_WEBHOOK_SECRET: Optional[str] = None
    
    # SMS Configuration
    TELNYX_MESSAGING_PROFILE_ID: Optional[str] = None
    TELNYX_FROM_NUMBER: Optional[str] = None
    
    # Website Validation (NEW)
    ENABLE_AUTO_VALIDATION: bool = True  # Auto-validate websites after scraping
    VALIDATION_BATCH_SIZE: int = 10  # Max businesses to validate per batch
    VALIDATION_CAPTURE_SCREENSHOTS: bool = False  # Disable screenshots for performance
    VALIDATION_TIMEOUT_MS: int = 30000  # 30 seconds per website
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
