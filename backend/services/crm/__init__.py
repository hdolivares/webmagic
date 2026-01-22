"""
CRM Services Package

Handles lead lifecycle management, business tracking, and sales funnel operations.

Author: WebMagic Team
Date: January 22, 2026
"""

from services.crm.lead_service import LeadService
from services.crm.lifecycle_service import BusinessLifecycleService

__all__ = [
    "LeadService",
    "BusinessLifecycleService"
]

