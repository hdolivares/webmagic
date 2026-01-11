"""
Prompt Settings API endpoints - manage AI agent prompts.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional
from uuid import UUID

from core.database import get_db
from api.deps import get_current_user
from api.schemas.prompt import (
    PromptSettingResponse,
    PromptSettingCreate,
    PromptSettingUpdate,
    PromptSettingsList,
    PromptTemplateResponse
)
from models.prompt import PromptSetting, PromptTemplate
from models.user import AdminUser

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/prompts", response_model=PromptSettingsList)
async def list_prompt_settings(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    active_only: bool = Query(True, description="Only show active settings"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """List all prompt settings."""
    query = select(PromptSetting)
    
    if agent_name:
        query = query.where(PromptSetting.agent_name == agent_name)
    
    if active_only:
        query = query.where(PromptSetting.is_active == True)
    
    query = query.order_by(
        PromptSetting.agent_name,
        PromptSetting.section_name,
        PromptSetting.version.desc()
    )
    
    result = await db.execute(query)
    settings = result.scalars().all()
    
    return PromptSettingsList(
        settings=[PromptSettingResponse.model_validate(s) for s in settings],
        total=len(settings)
    )


@router.get("/prompts/{setting_id}", response_model=PromptSettingResponse)
async def get_prompt_setting(
    setting_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get a specific prompt setting."""
    result = await db.execute(
        select(PromptSetting).where(PromptSetting.id == setting_id)
    )
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Prompt setting not found")
    
    return PromptSettingResponse.model_validate(setting)


@router.post("/prompts", response_model=PromptSettingResponse, status_code=201)
async def create_prompt_setting(
    setting_data: PromptSettingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Create a new prompt setting."""
    # Get latest version for this section
    result = await db.execute(
        select(PromptSetting.version)
        .where(
            PromptSetting.agent_name == setting_data.agent_name,
            PromptSetting.section_name == setting_data.section_name
        )
        .order_by(PromptSetting.version.desc())
        .limit(1)
    )
    latest_version = result.scalar()
    next_version = (latest_version or 0) + 1
    
    # Create new setting
    setting = PromptSetting(
        **setting_data.model_dump(),
        version=next_version,
        created_by=current_user.id
    )
    
    db.add(setting)
    await db.commit()
    await db.refresh(setting)
    
    return PromptSettingResponse.model_validate(setting)


@router.patch("/prompts/{setting_id}", response_model=PromptSettingResponse)
async def update_prompt_setting(
    setting_id: UUID,
    updates: PromptSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Update a prompt setting."""
    # Get existing setting
    result = await db.execute(
        select(PromptSetting).where(PromptSetting.id == setting_id)
    )
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Prompt setting not found")
    
    # Apply updates
    update_dict = updates.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    from datetime import datetime
    update_dict["updated_at"] = datetime.utcnow()
    
    await db.execute(
        update(PromptSetting)
        .where(PromptSetting.id == setting_id)
        .values(**update_dict)
    )
    await db.commit()
    
    # Refresh
    await db.refresh(setting)
    
    return PromptSettingResponse.model_validate(setting)


@router.get("/templates", response_model=list[PromptTemplateResponse])
async def list_prompt_templates(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """List all prompt templates."""
    result = await db.execute(
        select(PromptTemplate).order_by(PromptTemplate.agent_name)
    )
    templates = result.scalars().all()
    
    return [PromptTemplateResponse.model_validate(t) for t in templates]


@router.get("/templates/{agent_name}", response_model=PromptTemplateResponse)
async def get_prompt_template(
    agent_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get prompt template for a specific agent."""
    result = await db.execute(
        select(PromptTemplate).where(PromptTemplate.agent_name == agent_name)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return PromptTemplateResponse.model_validate(template)


@router.get("/templates/{template_id}/settings", response_model=list[PromptSettingResponse])
async def get_template_settings(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get all prompt settings for a specific template."""
    # First get the template to get the agent_name
    template_result = await db.execute(
        select(PromptTemplate).where(PromptTemplate.id == template_id)
    )
    template = template_result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Get settings for this template
    result = await db.execute(
        select(PromptSetting)
        .where(PromptSetting.template_id == template_id)
        .where(PromptSetting.is_active == True)
        .order_by(PromptSetting.section_name, PromptSetting.version.desc())
    )
    settings = result.scalars().all()
    
    return [PromptSettingResponse.model_validate(s) for s in settings]


@router.patch("/settings/{setting_id}", response_model=PromptSettingResponse)
async def update_setting_by_id(
    setting_id: UUID,
    updates: PromptSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Update a specific prompt setting (alternative endpoint)."""
    return await update_prompt_setting(setting_id, updates, db, current_user)
