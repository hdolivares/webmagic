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
    
    # Email
    EMAIL_PROVIDER: str = "ses"  # ses or sendgrid
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    SENDGRID_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "hugo@webmagic.com"
    
    # Recurrente
    RECURRENTE_PUBLIC_KEY: str
    RECURRENTE_SECRET_KEY: str
    RECURRENTE_WEBHOOK_SECRET: str = ""
    RECURRENTE_BASE_URL: str = "https://app.recurrente.com"
    
    # Site Hosting
    SITES_DOMAIN: str = "sites.webmagic.com"
    SITES_BASE_PATH: str = "/var/www/sites"
    
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
