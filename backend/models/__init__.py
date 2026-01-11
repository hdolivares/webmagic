"""
SQLAlchemy models for WebMagic.
"""
from models.base import BaseModel
from models.user import AdminUser
from models.business import Business
from models.coverage import CoverageGrid
from models.prompt import PromptTemplate, PromptSetting
from models.site import GeneratedSite

__all__ = [
    "BaseModel",
    "AdminUser",
    "Business",
    "CoverageGrid",
    "PromptTemplate",
    "PromptSetting",
    "GeneratedSite",
]
