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
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    # API Keys
    OUTSCRAPER_API_KEY: str
    ANTHROPIC_API_KEY: str
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    TELNYX_API_KEY: Optional[str] = None
    TELNYX_PUBLIC_KEY: Optional[str] = None

    # LabsMobile SMS
    LABSMOBILE_USERNAME: Optional[str] = None
    LABSMOBILE_TOKEN: Optional[str] = None
    LABSMOBILE_PHONE_NUMBER: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    BREVO_API_KEY: Optional[str] = None
    SCRAPINGDOG_API_KEY: Optional[str] = None  # For Google search verification
    
    # Payment Providers (Recurrente - Legacy)
    RECURRENTE_PUBLIC_KEY: Optional[str] = None
    RECURRENTE_SECRET_KEY: Optional[str] = None
    RECURRENTE_WEBHOOK_SECRET: Optional[str] = None
    RECURRENTE_BASE_URL: Optional[str] = None
    
    # JWT / Auth
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # API Versioning
    API_VERSION: str = "v1"
    
    # Frontend URL
    FRONTEND_URL: str = "https://web.lavish.solutions"
    
    # API URL (for generated site claim buttons)
    API_URL: str = "https://web.lavish.solutions"
    
    # Site Serving
    SITES_DOMAIN: str = "sites.lavish.solutions"
    SITES_BASE_URL: str = "https://sites.lavish.solutions"
    SITES_BASE_PATH: str = "/var/www/sites"
    SITES_USE_PATH_ROUTING: bool = True  # Use path-based URLs (/slug) instead of subdomains (slug.domain)
    
    # Email Configuration
    EMAIL_PROVIDER: str = "brevo"
    EMAIL_FROM: str = "hello@lavish.solutions"
    EMAIL_FROM_NAME: str = "WebMagic"
    SUPPORT_ADMIN_EMAIL: str = "admin@lavish.solutions"
    
    # Stripe Webhooks
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Telnyx Configuration
    TELNYX_WEBHOOK_SECRET: Optional[str] = None
    TELNYX_MESSAGING_PROFILE_ID: Optional[str] = None
    TELNYX_FROM_NUMBER: Optional[str] = None
    TELNYX_PHONE_NUMBER: Optional[str] = None
    
    # SMS Configuration
    SMS_PROVIDER: str = "labsmobile"
    SMS_DAILY_BUDGET: str = "10.00"
    SMS_MAX_COST_PER_MESSAGE: str = "0.05"
    SMS_ENABLE_COST_ALERTS: str = "true"
    SMS_ENFORCE_BUSINESS_HOURS: str = "true"
    SMS_DEFAULT_TIMEZONE: str = "America/Chicago"
    
    # Website Validation (NEW)
    ENABLE_AUTO_VALIDATION: bool = True  # Auto-validate websites after scraping
    VALIDATION_BATCH_SIZE: int = 10  # Max businesses to validate per batch
    VALIDATION_CAPTURE_SCREENSHOTS: bool = False  # Disable screenshots for performance
    VALIDATION_TIMEOUT_MS: int = 30000  # 30 seconds per website
    
    # LLM Configuration for Website Validation
    LLM_MODEL: str = "claude-3-haiku-20240307"  # Fallback validation model (overridden by database settings)

    # Abandoned cart recovery
    ABANDONED_CART_WINDOW_MINUTES: int = 15  # Treat checkout as abandoned after this many minutes
    ABANDONED_CART_COUPON_VALIDITY_HOURS: int = 24  # Recurrente coupon expiry for recovery emails

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from .env


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
