"""
System Settings API - Configure AI models, providers, and other system settings.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from api.deps import get_db, get_current_user
from core.config import get_settings
from models.user import AdminUser
from services.system_settings_service import SystemSettingsService, MESSAGING_DEFAULT_TEMPLATES
from services.bandwidth_snapshot import get_bandwidth_snapshot

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
        elif request.key.startswith("shortener_"):
            category = "shortener"
        elif request.key.startswith("autopilot_"):
            category = "autopilot"
        
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


# ── Autopilot Settings ───────────────────────────────────────────────────────

class AutopilotSettingsResponse(BaseModel):
    enabled: bool
    target_businesses: int


class AutopilotSettingsUpdate(BaseModel):
    enabled: bool
    target_businesses: int = Field(default=30, ge=1, le=500)


@router.get("/autopilot", response_model=AutopilotSettingsResponse)
async def get_autopilot_settings(
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current autopilot mode configuration."""
    try:
        settings = await SystemSettingsService.get_autopilot_settings(db)
        return AutopilotSettingsResponse(**settings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/autopilot", response_model=AutopilotSettingsResponse)
async def update_autopilot_settings(
    request: AutopilotSettingsUpdate,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable / disable autopilot and set the target business count."""
    try:
        saved = await SystemSettingsService.set_autopilot_settings(
            db=db,
            enabled=request.enabled,
            target_businesses=request.target_businesses,
        )
        return AutopilotSettingsResponse(**saved)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Notification Settings ─────────────────────────────────────────────────────

from core.config import get_settings as get_app_settings
from pydantic import EmailStr

class NotificationSettingsResponse(BaseModel):
    support_admin_email: str
    config_default: str  # The .env fallback value, shown as placeholder


class NotificationSettingsUpdate(BaseModel):
    support_admin_email: str


@router.get("/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notification settings (support email address, etc.)."""
    app_settings = get_app_settings()
    db_value = await SystemSettingsService.get_setting(db, "support_admin_email")
    return NotificationSettingsResponse(
        support_admin_email=db_value or app_settings.SUPPORT_ADMIN_EMAIL,
        config_default=app_settings.SUPPORT_ADMIN_EMAIL,
    )


@router.put("/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    request: NotificationSettingsUpdate,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save notification settings to the database."""
    app_settings = get_app_settings()
    await SystemSettingsService.set_setting(
        db=db,
        key="support_admin_email",
        value=request.support_admin_email,
        value_type="string",
        category="notifications",
        label="Support Notification Email",
        description="Admin email address that receives new ticket and customer reply alerts.",
    )
    return NotificationSettingsResponse(
        support_admin_email=request.support_admin_email,
        config_default=app_settings.SUPPORT_ADMIN_EMAIL,
    )


# ── Bandwidth monitoring (vnstat snapshot) ─────────────────────────────────────

class DailyTraffic(BaseModel):
    """Traffic totals for a single day."""
    date: str
    rx_bytes: int = 0
    tx_bytes: int = 0


class TrafficTotals(BaseModel):
    """Received and transmitted byte totals."""
    rx_bytes: int = 0
    tx_bytes: int = 0


class BandwidthResponse(BaseModel):
    """
    Bandwidth snapshot for the admin UI.
    When available is False, reason indicates why (file_missing, file_too_old, parse_error).
    Optional fields are null when monitoring is not available.
    """
    available: bool
    reason: Optional[str] = None
    updated_at: Optional[str] = None
    interface: Optional[str] = None
    daily: Optional[List[DailyTraffic]] = None
    monthly: Optional[TrafficTotals] = None
    total: Optional[TrafficTotals] = None


@router.get("/bandwidth", response_model=BandwidthResponse)
async def get_bandwidth(
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Get bandwidth (in/out) from vnstat snapshot file for the admin UI.
    Read-only; requires admin auth. Snapshot is written by cron (e.g. vnstat -i eth0 --json).
    When available is False, the UI can show a message based on reason (file_missing, file_too_old, parse_error).
    """
    settings = get_settings()
    path = Path(settings.VNSTAT_SNAPSHOT_PATH)
    stale_seconds = settings.VNSTAT_STALE_SECONDS
    raw = get_bandwidth_snapshot(path, stale_seconds)
    # Map to response model
    if not raw.get("available"):
        return BandwidthResponse(
            available=False,
            reason=raw.get("reason"),
        )
    return BandwidthResponse(
        available=True,
        updated_at=raw.get("updated_at"),
        interface=raw.get("interface"),
        daily=[DailyTraffic(**d) for d in (raw.get("daily") or [])],
        monthly=TrafficTotals(**(raw["monthly"] or {})) if raw.get("monthly") else None,
        total=TrafficTotals(**(raw["total"] or {})) if raw.get("total") else None,
    )
