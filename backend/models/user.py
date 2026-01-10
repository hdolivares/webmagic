"""
Admin user model for dashboard access.
"""
from sqlalchemy import Column, String, Boolean, DateTime
from models.base import BaseModel


class AdminUser(BaseModel):
    """Admin user model for dashboard authentication."""
    
    __tablename__ = "admin_users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(30), default="viewer", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<AdminUser {self.email}>"
