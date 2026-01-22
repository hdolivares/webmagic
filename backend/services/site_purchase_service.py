"""
Site Purchase Service

Handles the complete site purchase flow:
1. Create checkout session ($495 one-time)
2. Process payment webhook
3. Create customer user account
4. Associate site with customer
5. Send welcome email

Updated: January 22, 2026
- Integrated CRM services to ensure business records always exist
- Automated contact_status and website_status updates on purchase

Author: WebMagic Team
Date: January 21, 2026
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.site_models import Site, CustomerUser, SiteVersion
from services.payments.recurrente_client import RecurrenteClient
from services.customer_auth_service import CustomerAuthService
from services.site_service import get_site_service
from services.crm import LeadService, BusinessLifecycleService
from core.config import get_settings
from core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)
settings = get_settings()


class SitePurchaseService:
    """Service for handling site purchases."""
    
    def __init__(self):
        """Initialize service with Recurrente client."""
        self.recurrente = RecurrenteClient()
        self.site_service = get_site_service()
    
    async def create_purchase_checkout(
        self,
        db: AsyncSession,
        slug: str,
        customer_email: str,
        customer_name: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Recurrente checkout session for site purchase.
        
        Args:
            db: Database session
            slug: Site slug
            customer_email: Customer email
            customer_name: Optional customer name
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled
        
        Returns:
            Dictionary with checkout_id and checkout_url
        
        Raises:
            NotFoundError: If site doesn't exist
            ValidationError: If site is not in preview status
        """
        # Get site
        result = await db.execute(
            select(Site).where(Site.slug == slug)
        )
        site = result.scalar_one_or_none()
        
        if not site:
            raise NotFoundError(f"Site not found: {slug}")
        
        if site.status != "preview":
            raise ValidationError(f"Site is not available for purchase (status: {site.status})")
        
        # Create checkout with Recurrente
        site_url = self.site_service.generate_site_url(slug)
        checkout = await self.recurrente.create_checkout(
            description=f"Website Purchase - {site.site_title or slug}",
            price_cents=int(site.purchase_amount * 100),  # Convert to cents
            currency="USD",
            recurrence_type="once",
            success_url=success_url or f"{settings.SITES_BASE_URL}/purchase-success",
            cancel_url=cancel_url or f"{settings.SITES_BASE_URL}/purchase-cancelled",
            user_email=customer_email,
            user_name=customer_name,
            metadata={
                "site_id": str(site.id),
                "site_slug": slug,
                "site_url": site_url,
                "purchase_type": "website"
            }
        )
        
        logger.info(f"Created purchase checkout for site {slug}: {checkout['id']}")
        
        return {
            "checkout_id": checkout["id"],
            "checkout_url": checkout["checkout_url"],
            "site_slug": slug,
            "site_title": site.site_title,
            "amount": float(site.purchase_amount),
            "currency": "USD"
        }
    
    async def process_purchase_payment(
        self,
        db: AsyncSession,
        checkout_id: str,
        payment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a successful purchase payment (called from webhook).
        
        This method:
        1. Verifies site exists and is in preview
        2. Creates customer user account
        3. Updates site status to 'owned'
        4. Records purchase transaction
        5. Creates initial site version
        
        Args:
            db: Database session
            checkout_id: Recurrente checkout ID
            payment_data: Payment data from webhook
        
        Returns:
            Dictionary with purchase details
        
        Raises:
            NotFoundError: If site doesn't exist
            ValidationError: If site is not in preview status
        """
        # Extract data from payment
        metadata = payment_data.get("metadata", {})
        site_id_str = metadata.get("site_id")
        customer_email = payment_data.get("user_email")
        customer_name = payment_data.get("user_name")
        transaction_id = payment_data.get("id")
        
        if not site_id_str:
            raise ValidationError("Missing site_id in payment metadata")
        
        site_id = UUID(site_id_str)
        
        # Get site
        result = await db.execute(
            select(Site).where(Site.id == site_id)
        )
        site = result.scalar_one_or_none()
        
        if not site:
            raise NotFoundError(f"Site not found: {site_id}")
        
        if site.status != "preview":
            logger.warning(f"Attempted purchase of non-preview site: {site.slug} ({site.status})")
            raise ValidationError(f"Site is not available for purchase (status: {site.status})")
        
        # Create or get customer user
        customer_user = await CustomerAuthService.get_customer_by_email(db, customer_email)
        
        if not customer_user:
            # Generate a temporary password (customer will set their own via email)
            import secrets
            temp_password = secrets.token_urlsafe(16)
            
            customer_user = await CustomerAuthService.create_customer_user(
                db=db,
                email=customer_email,
                password=temp_password,
                full_name=customer_name,
                site_id=site.id
            )
            logger.info(f"Created new customer user: {customer_email}")
        else:
            # Update existing user's site
            customer_user.site_id = site.id
            await db.commit()
            await db.refresh(customer_user)
            logger.info(f"Associated site with existing customer: {customer_email}")
        
        # Update site status
        site.status = "owned"
        site.purchased_at = datetime.utcnow()
        site.purchase_transaction_id = transaction_id
        site.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(site)
        
        # CRM Integration: Update business lifecycle status
        if site.business_id:
            lifecycle_service = BusinessLifecycleService(db)
            await lifecycle_service.mark_website_sold(site.business_id)
            await db.commit()
            logger.info(
                f"Updated business {site.business_id}: "
                f"website_status=sold, contact_status=purchased"
            )
        else:
            logger.warning(
                f"Site {site.slug} purchased but has no business_id! "
                f"This should not happen after Phase 1 implementation."
            )
        
        logger.info(f"Site purchased: {site.slug} by {customer_email}")
        
        return {
            "site_id": str(site.id),
            "site_slug": site.slug,
            "site_url": self.site_service.generate_site_url(site.slug),
            "customer_id": str(customer_user.id),
            "customer_email": customer_user.email,
            "purchase_amount": float(site.purchase_amount),
            "transaction_id": transaction_id,
            "purchased_at": site.purchased_at.isoformat()
        }
    
    async def activate_subscription(
        self,
        db: AsyncSession,
        site_id: UUID,
        subscription_data: Dict[str, Any]
    ) -> Site:
        """
        Activate monthly subscription for a site (Phase 3).
        
        Args:
            db: Database session
            site_id: Site ID
            subscription_data: Subscription data from Recurrente
        
        Returns:
            Updated Site instance
        
        Raises:
            NotFoundError: If site doesn't exist
            ValidationError: If site is not owned
        """
        result = await db.execute(
            select(Site).where(Site.id == site_id)
        )
        site = result.scalar_one_or_none()
        
        if not site:
            raise NotFoundError(f"Site not found: {site_id}")
        
        if site.status != "owned":
            raise ValidationError(f"Site must be owned to activate subscription (status: {site.status})")
        
        # Update site with subscription info
        site.status = "active"
        site.subscription_status = "active"
        site.subscription_id = subscription_data.get("id")
        site.subscription_started_at = datetime.utcnow()
        site.next_billing_date = subscription_data.get("next_billing_date")
        site.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(site)
        
        logger.info(f"Subscription activated for site: {site.slug}")
        return site
    
    async def get_site_by_slug(
        self,
        db: AsyncSession,
        slug: str
    ) -> Optional[Site]:
        """
        Get site by slug.
        
        Args:
            db: Database session
            slug: Site slug
        
        Returns:
            Site instance or None
        """
        result = await db.execute(
            select(Site).where(Site.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def get_site_by_id(
        self,
        db: AsyncSession,
        site_id: UUID
    ) -> Optional[Site]:
        """
        Get site by ID.
        
        Args:
            db: Database session
            site_id: Site ID
        
        Returns:
            Site instance or None
        """
        result = await db.execute(
            select(Site).where(Site.id == site_id)
        )
        return result.scalar_one_or_none()
    
    async def create_site_record(
        self,
        db: AsyncSession,
        slug: str,
        site_title: Optional[str] = None,
        site_description: Optional[str] = None,
        business_id: Optional[UUID] = None,
        business_data: Optional[Dict[str, Any]] = None,
        html_content: Optional[str] = None
    ) -> Site:
        """
        Create a new site record with proper CRM integration.
        
        IMPORTANT: This method ensures every site has a business record.
        If business_id is not provided, it will create/get a business using business_data.
        
        Args:
            db: Database session
            slug: Site slug
            site_title: Site title
            site_description: Site description
            business_id: Associated business ID (optional if business_data provided)
            business_data: Business info for creating record (optional if business_id provided)
            html_content: Initial HTML content
        
        Returns:
            Created Site instance
        
        Raises:
            ValidationError: If slug already exists or business info is invalid
        
        Example:
            >>> # With existing business
            >>> site = await service.create_site_record(
            ...     db, "plumbing-pros", business_id=business.id
            ... )
            
            >>> # Without existing business (creates one)
            >>> site = await service.create_site_record(
            ...     db, "plumbing-pros",
            ...     site_title="LA Plumbing Pros",
            ...     business_data={
            ...         "name": "LA Plumbing Pros",
            ...         "phone": "(310) 123-4567",
            ...         "city": "Los Angeles",
            ...         "state": "CA"
            ...     }
            ... )
        """
        # Check if slug exists
        existing = await self.get_site_by_slug(db, slug)
        if existing:
            raise ValidationError(f"Site with slug already exists: {slug}")
        
        # PHASE 1 FIX: Ensure business record exists
        if not business_id:
            if not business_data:
                # Extract business data from site info
                business_data = {
                    "name": site_title or slug.replace("-", " ").title(),
                    "slug": slug
                }
                logger.warning(
                    f"Creating site '{slug}' without explicit business data. "
                    f"Generating minimal business record."
                )
            
            # Get or create business record
            lead_service = LeadService(db)
            business, created = await lead_service.get_or_create_business(business_data)
            business_id = business.id
            
            if created:
                logger.info(
                    f"Created new business record for site '{slug}': "
                    f"{business.name} ({business_id})"
                )
            else:
                logger.info(
                    f"Using existing business for site '{slug}': "
                    f"{business.name} ({business_id})"
                )
        
        # Create site with guaranteed business_id
        site = Site(
            slug=slug,
            site_title=site_title,
            site_description=site_description,
            business_id=business_id,
            status="preview"  # New sites start as preview
        )
        
        db.add(site)
        await db.commit()
        await db.refresh(site)
        
        logger.info(
            f"Created site '{slug}' (ID: {site.id}, Business: {business_id})"
        )
        
        # Create initial version if HTML provided
        if html_content:
            version = SiteVersion(
                site_id=site.id,
                version_number=1,
                html_content=html_content,
                change_description="Initial site generation",
                change_type="initial",
                created_by_type="admin",
                is_current=True
            )
            db.add(version)
            await db.commit()
            await db.refresh(version)
            
            # Update site's current_version_id
            site.current_version_id = version.id
            await db.commit()
            await db.refresh(site)
            
            logger.info(f"Created initial version for site: {slug}")
        
        logger.info(f"Created site record: {slug}")
        return site
    
    async def get_purchase_statistics(
        self,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get purchase statistics (for admin dashboard).
        
        Args:
            db: Database session
        
        Returns:
            Dictionary with statistics
        """
        from sqlalchemy import func
        
        # Total sites by status
        result = await db.execute(
            select(
                Site.status,
                func.count(Site.id).label("count")
            ).group_by(Site.status)
        )
        status_counts = {row.status: row.count for row in result}
        
        # Total revenue
        result = await db.execute(
            select(func.sum(Site.purchase_amount))
            .where(Site.purchased_at.isnot(None))
        )
        total_revenue = result.scalar() or Decimal(0)
        
        # Recent purchases
        result = await db.execute(
            select(Site)
            .where(Site.purchased_at.isnot(None))
            .order_by(Site.purchased_at.desc())
            .limit(10)
        )
        recent_purchases = result.scalars().all()
        
        return {
            "status_counts": status_counts,
            "total_preview": status_counts.get("preview", 0),
            "total_owned": status_counts.get("owned", 0),
            "total_active": status_counts.get("active", 0),
            "total_revenue": float(total_revenue),
            "recent_purchases": [
                {
                    "slug": site.slug,
                    "title": site.site_title,
                    "purchased_at": site.purchased_at.isoformat() if site.purchased_at else None,
                    "amount": float(site.purchase_amount)
                }
                for site in recent_purchases
            ]
        }


# Singleton instance
_site_purchase_service = None


def get_site_purchase_service() -> SitePurchaseService:
    """
    Get singleton instance of SitePurchaseService.
    
    Returns:
        SitePurchaseService instance
    """
    global _site_purchase_service
    if _site_purchase_service is None:
        _site_purchase_service = SitePurchaseService()
    return _site_purchase_service
