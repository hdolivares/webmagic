"""
SQLAlchemy models for WebMagic.
"""
from models.base import BaseModel
from models.user import AdminUser
from models.business import Business

__all__ = [
    "BaseModel",
    "AdminUser",
    "Business",
]
