"""
SQLAlchemy models for WebMagic.
"""
from models.base import BaseModel
from models.user import AdminUser
from models.business import Business
from models.coverage import CoverageGrid
from models.prompt import PromptTemplate, PromptSetting
from models.site import GeneratedSite
from models.campaign import Campaign
from models.customer import Customer, Subscription, Payment
from models.site_models import (
    Site,
    CustomerUser,
    SiteVersion,
    EditRequest,
    DomainVerificationRecord
)
from models.support_ticket import (
    SupportTicket,
    TicketMessage,
    TicketTemplate
)

__all__ = [
    "BaseModel",
    "AdminUser",
    "Business",
    "CoverageGrid",
    "PromptTemplate",
    "PromptSetting",
    "GeneratedSite",
    "Campaign",
    "Customer",
    "Subscription",
    "Payment",
    # Phase 2 models
    "Site",
    "CustomerUser",
    "SiteVersion",
    "EditRequest",
    "DomainVerificationRecord",
    # Phase 6 models
    "SupportTicket",
    "TicketMessage",
    "TicketTemplate",
]
