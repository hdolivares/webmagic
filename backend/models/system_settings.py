"""
System-wide settings that can be configured via admin UI.
"""
from sqlalchemy import Column, String, Text, Boolean, Float
from sqlalchemy.dialects.postgresql import JSONB
from models.base import BaseModel


class SystemSetting(BaseModel):
    """
    System-wide configuration settings.
    Allows runtime configuration without code changes.
    """
    
    __tablename__ = "system_settings"
    
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), nullable=False, default="string")  # string, int, float, bool, json
    category = Column(String(50), nullable=False, index=True)  # llm, image, email, payment, etc.
    label = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    options = Column(JSONB, nullable=True)  # For dropdown/select options
    is_secret = Column(Boolean, default=False, nullable=False)  # Hide value in UI
    is_required = Column(Boolean, default=False, nullable=False)
    default_value = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<SystemSetting {self.key}={self.value}>"
    
    def get_typed_value(self):
        """Return value with correct type."""
        if self.value is None:
            return None
        
        if self.value_type == "int":
            return int(self.value)
        elif self.value_type == "float":
            return float(self.value)
        elif self.value_type == "bool":
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == "json":
            import json
            return json.loads(self.value)
        else:
            return self.value
