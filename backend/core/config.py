"""
Application configuration management.
Loads settings from environment variables with secure defaults.
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


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
    LABSMOBILE_WEBHOOK_TOKEN: Optional[str] = None  # Shared secret appended to callback URLs
    GEMINI_API_KEY: Optional[str] = None
    BREVO_API_KEY: Optional[str] = None
    SCRAPINGDOG_API_KEY: Optional[str] = None  # For Google search verification
    
    # Payment Providers (Recurrente - Legacy)
    RECURRENTE_PUBLIC_KEY: Optional[str] = None
    RECURRENTE_SECRET_KEY: Optional[str] = None
    RECURRENTE_WEBHOOK_SECRET: Optional[str] = None
    RECURRENTE_BASE_URL: str = "https://app.recurrente.com"
    
    # JWT / Auth
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # API Versioning
    API_VERSION: str = "v1"
    
    # Frontend URL (admin dashboard + customer portal)
    FRONTEND_URL: str = "http://localhost:3000"
    
    # API URL (for generated site claim buttons and webhook callbacks)
    API_URL: str = "http://localhost:8000"

    # Extra comma-separated origins allowed by CORS (FRONTEND_URL and SITES_BASE_URL are always allowed)
    CORS_ORIGINS: str = ""
    
    # Site Serving
    SITES_DOMAIN: str = "localhost:8000"
    SITES_BASE_URL: str = "http://localhost:8000"
    SITES_BASE_PATH: str = "/var/www/sites"
    SITES_USE_PATH_ROUTING: bool = True  # Use path-based URLs (/slug) instead of subdomains (slug.domain)
    
    # Email Configuration
    EMAIL_PROVIDER: str = "brevo"
    EMAIL_FROM: str = "hello@example.com"
    EMAIL_FROM_NAME: str = "WebMagic"
    SUPPORT_ADMIN_EMAIL: str = "admin@example.com"

    # Public IP of the server customers point their custom-domain A records at
    SERVER_IP: Optional[str] = None
    
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
    
    # Activity filtering — gates site generation on review/social recency
    ENABLE_FACEBOOK_ACTIVITY_CHECK: bool = True
    # When True, scrapes the Facebook page URL (if present) via ScrapingDog GWS
    # to capture last_facebook_post_date.  Costs 5 ScrapingDog credits per business.
    # Set to False to disable without a code deploy.

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

    # Bandwidth monitoring (vnstat snapshot)
    # Path to JSON file written by cron: vnstat -i eth0 --json > VNSTAT_SNAPSHOT_PATH
    VNSTAT_SNAPSHOT_PATH: str = "/var/log/webmagic/vnstat_snapshot.json"
    # Consider snapshot stale after this many seconds (default 1 hour)
    VNSTAT_STALE_SECONDS: int = 3600

    @field_validator("SECRET_KEY")
    @classmethod
    def _secret_key_must_be_strong(cls, value: str) -> str:
        if len(value) < 32 or "your-secret-key" in value or "change" in value.lower():
            raise ValueError(
                "SECRET_KEY must be a random value of at least 32 characters "
                "(generate one with: openssl rand -hex 32)"
            )
        return value

    @property
    def cors_origins(self) -> List[str]:
        origins = {self.FRONTEND_URL.rstrip("/"), self.SITES_BASE_URL.rstrip("/")}
        origins.update(o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip())
        if self.DEBUG:
            origins.update({"http://localhost:3000", "http://localhost:5173"})
        return sorted(origins)

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow",  # Allow extra fields from .env
    )


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
