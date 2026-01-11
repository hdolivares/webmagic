"""
Prompt management models.
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from models.base import BaseModel


class PromptTemplate(BaseModel):
    """
    Master prompt template for each agent.
    Rarely changed - contains the core agent instructions.
    """
    
    __tablename__ = "prompt_templates"
    
    agent_name = Column(String(50), unique=True, nullable=False, index=True)
    system_prompt = Column(Text, nullable=False)
    output_format = Column(Text, nullable=True)
    placeholder_sections = Column(JSONB, default=[], nullable=True)
    
    def __repr__(self):
        return f"<PromptTemplate {self.agent_name}>"


class PromptSetting(BaseModel):
    """
    Dynamic prompt settings - editable via UI.
    These get injected into the master template.
    """
    
    __tablename__ = "prompt_settings"
    
    agent_name = Column(String(50), nullable=False, index=True)
    section_name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    variant = Column(String(50), nullable=True)
    weight = Column(Integer, default=100, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    def __repr__(self):
        return f"<PromptSetting {self.agent_name}.{self.section_name} v{self.version}>"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.usage_count == 0:
            return 0.0
        return (self.success_count / self.usage_count) * 100
