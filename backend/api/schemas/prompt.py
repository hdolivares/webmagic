"""
Prompt Settings schemas for API validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class PromptSettingResponse(BaseModel):
    """Prompt setting response schema."""
    id: UUID
    agent_name: str
    section_name: str
    content: str
    description: Optional[str]
    version: int
    is_active: bool
    usage_count: int
    success_count: int
    success_rate: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PromptSettingCreate(BaseModel):
    """Create new prompt setting."""
    agent_name: str = Field(..., min_length=1, max_length=50)
    section_name: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)
    description: Optional[str] = None
    variant: Optional[str] = None


class PromptSettingUpdate(BaseModel):
    """Update prompt setting."""
    content: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PromptSettingsList(BaseModel):
    """List of prompt settings."""
    settings: List[PromptSettingResponse]
    total: int


class PromptTemplateResponse(BaseModel):
    """Prompt template response."""
    id: UUID
    agent_name: str
    system_prompt: str
    output_format: Optional[str]
    placeholder_sections: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
