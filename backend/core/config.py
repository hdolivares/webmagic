"""
Application configuration using Pydantic Settings.
Loads from environment variables with validation.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "WebMagic"
    DEBUG: bool = False
    API_VERSION: str = "v1"
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_URL_POOL: Optional[str] = None  # Supabase pooler URL (optional)
    DIRECT_URL: Optional[str] = None  # Supabase direct connection (optional)
    
    # Supabase (optional - for client SDK if needed)
    SUPABASE_PROJECT_URL: Optional[str] = None
    SUPABASE_API_KEY: Optional[str] = None
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # External APIs
    ANTHROPIC_API_KEY: str
    OUTSCRAPER_API_KEY: str
    GEMINI_API_KEY: Optional[str] = None  # For image generation (Nano Banana)
    
    # Email
    EMAIL_PROVIDER: str = "brevo"  # ses, sendgrid, smtp, or brevo
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    SENDGRID_API_KEY: Optional[str] = None
    BREVO_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "hugo@webmagic.com"
    EMAIL_FROM_NAME: str = "WebMagic"
    FRONTEND_URL: str = "https://app.lavish.solutions"  # Frontend URL for email links
    
    # SMS / Twilio
    SMS_PROVIDER: str = "twilio"  # Currently only twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None  # Your Twilio number (e.g., +12345678900)
    SMS_COST_PER_SEGMENT: float = 0.0079  # Twilio US SMS cost
    MAX_SMS_DAILY_BUDGET: float = 50.00  # Maximum daily SMS spend in USD
    DEFAULT_CAMPAIGN_CHANNEL: str = "auto"  # auto, email, sms, both
    API_URL: str = "https://api.lavish.solutions"  # For Twilio webhooks
    
    # SMTP (development/fallback)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    
    # Recurrente
    RECURRENTE_PUBLIC_KEY: str
    RECURRENTE_SECRET_KEY: str
    RECURRENTE_WEBHOOK_SECRET: str = ""
    RECURRENTE_BASE_URL: str = "https://app.recurrente.com"
    RECURRENTE_SUBSCRIPTION_PLAN_ID: str = "default_plan"  # Monthly subscription plan ID
    
    # Site Hosting
    SITES_DOMAIN: str = "sites.lavish.solutions"  # Domain for path-based hosting
    SITES_BASE_PATH: str = "/var/www/sites"  # File system path for site files
    SITES_BASE_URL: str = "https://sites.lavish.solutions"  # Base URL for customer sites
    SITES_USE_PATH_ROUTING: bool = True  # True = path-based, False = subdomain-based
    
    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()
