"""
System Settings Service - Manages runtime configuration.
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.system_settings import SystemSetting
import logging
import json

logger = logging.getLogger(__name__)


# Available AI models and providers
AI_PROVIDERS = {
    "anthropic": {
        "name": "Anthropic (Claude)",
        "models": [
            {"id": "claude-3-5-sonnet-20240620", "name": "Claude 3.5 Sonnet", "recommended": True},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus (Most Capable)"},
            {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku (Fastest)"},
        ],
        "requires_key": "ANTHROPIC_API_KEY"
    },
    "google": {
        "name": "Google (Gemini)",
        "models": [
            {"id": "gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash (Experimental)", "recommended": True},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
            {"id": "gemini-1.0-pro", "name": "Gemini 1.0 Pro"},
        ],
        "requires_key": "GEMINI_API_KEY"
    },
    "openai": {
        "name": "OpenAI (GPT)",
        "models": [
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "gpt-4", "name": "GPT-4"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
        ],
        "requires_key": "OPENAI_API_KEY"
    }
}

IMAGE_PROVIDERS = {
    "google": {
        "name": "Google (Imagen / Nano Banana)",
        "models": [
            {"id": "imagen-3.0-generate-001", "name": "Imagen 3.0", "recommended": True},
            {"id": "imagegeneration@006", "name": "Imagen 2.0"},
        ],
        "requires_key": "GEMINI_API_KEY"
    },
    "openai": {
        "name": "OpenAI (DALL-E)",
        "models": [
            {"id": "dall-e-3", "name": "DALL-E 3", "recommended": True},
            {"id": "dall-e-2", "name": "DALL-E 2"},
        ],
        "requires_key": "OPENAI_API_KEY"
    }
}


class SystemSettingsService:
    """Service for managing system-wide settings."""
    
    @staticmethod
    async def get_setting(db: AsyncSession, key: str, default: Any = None) -> Any:
        """Get a setting value with type conversion."""
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            return setting.get_typed_value()
        return default
    
    @staticmethod
    async def get_settings_by_category(db: AsyncSession, category: str) -> Dict[str, Any]:
        """Get all settings for a category."""
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.category == category)
        )
        settings = result.scalars().all()
        
        return {
            setting.key: setting.get_typed_value() 
            for setting in settings
        }
    
    @staticmethod
    async def set_setting(
        db: AsyncSession, 
        key: str, 
        value: Any,
        value_type: str = "string",
        category: str = "general",
        label: str = "",
        description: str = "",
        is_secret: bool = False
    ) -> SystemSetting:
        """Set or update a setting."""
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        
        # Convert value to string for storage
        if value_type == "json":
            value_str = json.dumps(value)
        elif value is not None:
            value_str = str(value)
        else:
            value_str = None
        
        if setting:
            setting.value = value_str
            setting.value_type = value_type
        else:
            setting = SystemSetting(
                key=key,
                value=value_str,
                value_type=value_type,
                category=category,
                label=label or key,
                description=description,
                is_secret=is_secret
            )
            db.add(setting)
        
        await db.commit()
        await db.refresh(setting)
        return setting
    
    @staticmethod
    async def get_ai_config(db: AsyncSession) -> Dict[str, Any]:
        """Get current AI configuration."""
        llm_provider = await SystemSettingsService.get_setting(db, "llm_provider", "anthropic")
        llm_model = await SystemSettingsService.get_setting(db, "llm_model", "claude-3-5-sonnet-20240620")
        image_provider = await SystemSettingsService.get_setting(db, "image_provider", "google")
        image_model = await SystemSettingsService.get_setting(db, "image_model", "imagen-3.0-generate-001")
        
        return {
            "llm": {
                "provider": llm_provider,
                "model": llm_model,
                "provider_info": AI_PROVIDERS.get(llm_provider, {})
            },
            "image": {
                "provider": image_provider,
                "model": image_model,
                "provider_info": IMAGE_PROVIDERS.get(image_provider, {})
            }
        }
    
    @staticmethod
    async def get_available_providers() -> Dict[str, Any]:
        """Get list of available AI providers and their models."""
        return {
            "llm": AI_PROVIDERS,
            "image": IMAGE_PROVIDERS
        }
    
    @staticmethod
    async def seed_ai_defaults(db: AsyncSession):
        """Seed default AI configuration settings."""
        defaults = [
            {
                "key": "llm_provider",
                "value": "anthropic",
                "value_type": "string",
                "category": "ai",
                "label": "LLM Provider",
                "description": "Primary AI provider for text generation (agents)",
                "options": [
                    {"value": "anthropic", "label": "Anthropic (Claude)"},
                    {"value": "google", "label": "Google (Gemini)"},
                    {"value": "openai", "label": "OpenAI (GPT)"}
                ]
            },
            {
                "key": "llm_model",
                "value": "claude-3-5-sonnet-20240620",
                "value_type": "string",
                "category": "ai",
                "label": "LLM Model",
                "description": "Specific model to use for agents (Analyst, Concept, Art Director, Architect)",
                "options": []  # Populated dynamically based on provider
            },
            {
                "key": "image_provider",
                "value": "google",
                "value_type": "string",
                "category": "ai",
                "label": "Image Generation Provider",
                "description": "Provider for AI image generation",
                "options": [
                    {"value": "google", "label": "Google (Imagen)"},
                    {"value": "openai", "label": "OpenAI (DALL-E)"}
                ]
            },
            {
                "key": "image_model",
                "value": "imagen-3.0-generate-001",
                "value_type": "string",
                "category": "ai",
                "label": "Image Generation Model",
                "description": "Specific image generation model",
                "options": []  # Populated dynamically based on provider
            }
        ]
        
        for setting_data in defaults:
            options_json = json.dumps(setting_data["options"]) if setting_data["options"] else None
            
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key == setting_data["key"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                setting = SystemSetting(
                    key=setting_data["key"],
                    value=setting_data["value"],
                    value_type=setting_data["value_type"],
                    category=setting_data["category"],
                    label=setting_data["label"],
                    description=setting_data["description"],
                    options=setting_data["options"] if setting_data["options"] else None
                )
                db.add(setting)
                logger.info(f"Created setting: {setting_data['key']}")
        
        await db.commit()
        logger.info("AI defaults seeded successfully")
