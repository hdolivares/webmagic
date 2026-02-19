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
            {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5 (Latest)", "recommended": True},
            {"id": "claude-3-5-sonnet-20240620", "name": "Claude 3.5 Sonnet (June 2024)"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus"},
            {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet"},
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

# Default SMS message templates (Research-backed for 40-50% response rates)
# Updated: 2026-02-15 based on cold SMS best practices research
MESSAGING_TEMPLATE_KEYS = (
    "messaging_sms_template_friendly",
    "messaging_sms_template_professional", 
    "messaging_sms_template_urgent",
    "messaging_sms_template_value_first",
    "messaging_sms_template_local_community"
)

MESSAGING_DEFAULT_TEMPLATES = {
    # RECOMMENDED: Friendly — leads with review compliment (highest reply rate)
    # Research: compliment + gap + soft question = 28-45% reply rate
    "messaging_sms_template_friendly": (
        "Hi {{business_name}}! Saw your {{rating}} Google reviews — nice work. "
        "No website yet, so I built one: {{site_url}}. "
        "Want to personalize it? Reply STOP to opt out."
    ),

    # Professional — polite and personal, suitable for formal service businesses
    "messaging_sms_template_professional": (
        "Hi {{business_name}}, I came across your {{rating}} Google rating and noticed "
        "you don't have a website yet. I built a preview for your {{category}} business: "
        "{{site_url}}. Would you like it customized? Reply STOP to opt out."
    ),

    # Value-First — ultra-short, lowest cost (1 segment guaranteed)
    "messaging_sms_template_value_first": (
        "Hi {{business_name}} — {{rating}} stars on Google, no website yet. "
        "I made one for you: {{site_url}}. Want it? Reply STOP to opt out."
    ),

    # Local Community — mentions city for hyper-local feel
    "messaging_sms_template_local_community": (
        "Hi {{business_name}}! Noticed your great reputation in {{city}} but no website. "
        "I built a free preview: {{site_url}}. Want to customize it? Reply STOP to opt out."
    ),

    # Urgent — direct and confident, for emergency/on-demand services
    "messaging_sms_template_urgent": (
        "{{business_name}} — {{rating}} stars but no website. "
        "I built one for your {{category}} business: {{site_url}}. "
        "Interested? Reply STOP to opt out."
    ),
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
        llm_model = await SystemSettingsService.get_setting(db, "llm_model", "claude-sonnet-4-5")
        validation_provider = await SystemSettingsService.get_setting(db, "validation_provider", "anthropic")
        validation_model = await SystemSettingsService.get_setting(db, "validation_model", "claude-3-haiku-20240307")
        image_provider = await SystemSettingsService.get_setting(db, "image_provider", "google")
        image_model = await SystemSettingsService.get_setting(db, "image_model", "imagen-3.0-generate-001")
        
        return {
            "llm": {
                "provider": llm_provider,
                "model": llm_model,
                "provider_info": AI_PROVIDERS.get(llm_provider, {})
            },
            "validation": {
                "provider": validation_provider,
                "model": validation_model,
                "provider_info": AI_PROVIDERS.get(validation_provider, {})
            },
            "image": {
                "provider": image_provider,
                "model": image_model,
                "provider_info": IMAGE_PROVIDERS.get(image_provider, {})
            }
        }
    
    @staticmethod
    async def get_messaging_templates(db: AsyncSession) -> Dict[str, Optional[str]]:
        """Get SMS message templates for each tone. Returns None for keys not set (so SMS generator uses AI)."""
        result = {}
        for key in MESSAGING_TEMPLATE_KEYS:
            result[key] = await SystemSettingsService.get_setting(db, key, default=None)
        return result

    @staticmethod
    def get_messaging_default_templates() -> Dict[str, str]:
        """Return default template text for Settings UI when user has not saved yet."""
        return dict(MESSAGING_DEFAULT_TEMPLATES)

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
                "label": "Website Generation Provider",
                "description": "AI provider for website generation (agents: Analyst, Concept, Art Director, Architect)",
                "options": [
                    {"value": "anthropic", "label": "Anthropic (Claude)"},
                    {"value": "google", "label": "Google (Gemini)"},
                    {"value": "openai", "label": "OpenAI (GPT)"}
                ]
            },
            {
                "key": "llm_model",
                "value": "claude-sonnet-4-5",
                "value_type": "string",
                "category": "ai",
                "label": "Website Generation Model",
                "description": "Model for generating websites (Analyst, Concept, Art Director, Architect)",
                "options": []  # Populated dynamically based on provider
            },
            {
                "key": "validation_provider",
                "value": "anthropic",
                "value_type": "string",
                "category": "ai",
                "label": "Website Validation Provider",
                "description": "AI provider for website validation (fast, cheap verification tasks)",
                "options": [
                    {"value": "anthropic", "label": "Anthropic (Claude)"},
                    {"value": "google", "label": "Google (Gemini)"},
                    {"value": "openai", "label": "OpenAI (GPT)"}
                ]
            },
            {
                "key": "validation_model",
                "value": "claude-3-haiku-20240307",
                "value_type": "string",
                "category": "ai",
                "label": "Website Validation Model",
                "description": "Model for validating websites (fast, cost-effective verification)",
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
