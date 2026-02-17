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
    CustomerSiteOwnership,
    SiteVersion,
    EditRequest,
    DomainVerificationRecord
)
from models.support_ticket import (
    SupportTicket,
    TicketMessage,
    TicketTemplate
)
from models.sms_opt_out import SMSOptOut
from models.sms_message import SMSMessage
from models.activity_log import ActivityLog
from models.analytics_snapshot import AnalyticsSnapshot
from models.geo_strategy import GeoStrategy
from models.draft_campaign import DraftCampaign
from models.system_settings import SystemSetting
from models.website_validation import WebsiteValidation
from models.business_filter_preset import BusinessFilterPreset
from models.scrape_session import ScrapeSession
# from models.short_link import ShortLink  # TEMP: Disabled due to SQLAlchemy metadata conflict

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
    "CustomerSiteOwnership",
    "SiteVersion",
    "EditRequest",
    "DomainVerificationRecord",
    # Phase 6 models
    "SupportTicket",
    "TicketMessage",
    "TicketTemplate",
    # SMS models
    "SMSOptOut",
    "SMSMessage",
    # Analytics & Audit models
    "ActivityLog",
    "AnalyticsSnapshot",
    # Geo-scraping models
    "GeoStrategy",
    "DraftCampaign",
    # System models
    "SystemSetting",
    # Website validation & filtering models
    "WebsiteValidation",
    "BusinessFilterPreset",
    # Phase 2: Async scraping models
    "ScrapeSession",
    # URL Shortener
    # "ShortLink",  # TEMP: Disabled
]
