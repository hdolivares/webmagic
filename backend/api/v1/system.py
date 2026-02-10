"""
System Settings API - Configure AI models, providers, and other system settings.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
from pydantic import BaseModel

from api.deps import get_db, get_current_user
from models.user import AdminUser
from services.system_settings_service import SystemSettingsService, MESSAGING_DEFAULT_TEMPLATES

router = APIRouter(prefix="/system", tags=["System Settings"])


class AIConfigResponse(BaseModel):
    """Current AI configuration."""
    llm: Dict[str, Any]
    image: Dict[str, Any]


class ProvidersResponse(BaseModel):
    """Available AI providers."""
    llm: Dict[str, Any]
    image: Dict[str, Any]


class UpdateSettingRequest(BaseModel):
    """Update a setting value."""
    key: str
    value: str


@router.get("/ai-config", response_model=AIConfigResponse)
async def get_ai_config(
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current AI configuration (LLM and Image models).
    """
    try:
        config = await SystemSettingsService.get_ai_config(db)
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get AI config: {str(e)}")


@router.get("/ai-providers", response_model=ProvidersResponse)
async def get_ai_providers(
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get list of available AI providers and their models.
    """
    try:
        providers = await SystemSettingsService.get_available_providers()
        return providers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get providers: {str(e)}")


@router.post("/settings")
async def update_setting(
    request: UpdateSettingRequest,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a system setting.
    """
    try:
        # Determine category and type based on key
        category = "general"
        value_type = "string"
        
        if request.key.startswith("llm_") or request.key.startswith("image_"):
            category = "ai"
        elif request.key.startswith("messaging_"):
            category = "messaging"
        
        setting = await SystemSettingsService.set_setting(
            db=db,
            key=request.key,
            value=request.value,
            value_type=value_type,
            category=category,
            label=request.key.replace("_", " ").title()
        )
        
        return {
            "success": True,
            "message": f"Setting '{request.key}' updated successfully",
            "setting": {
                "key": setting.key,
                "value": setting.value,
                "category": setting.category
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update setting: {str(e)}")


@router.get("/messaging-templates")
async def get_messaging_templates(
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get SMS message templates for Friendly, Professional, and Urgent tones.
    Used by Settings > Messaging and by campaign preview/generation.
    """
    try:
        raw = await SystemSettingsService.get_messaging_templates(db)
        return {
            "friendly": raw.get("messaging_sms_template_friendly") or "",
            "professional": raw.get("messaging_sms_template_professional") or "",
            "urgent": raw.get("messaging_sms_template_urgent") or "",
            "defaults": {
                "friendly": MESSAGING_DEFAULT_TEMPLATES.get("messaging_sms_template_friendly", ""),
                "professional": MESSAGING_DEFAULT_TEMPLATES.get("messaging_sms_template_professional", ""),
                "urgent": MESSAGING_DEFAULT_TEMPLATES.get("messaging_sms_template_urgent", ""),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/{category}")
async def get_settings_by_category(
    category: str,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all settings for a specific category.
    """
    try:
        settings = await SystemSettingsService.get_settings_by_category(db, category)
        return {
            "category": category,
            "settings": settings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")
