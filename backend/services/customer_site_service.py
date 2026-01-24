"""
Customer Site Ownership Service

Provides helper methods for managing customer-site relationships
in the multi-site ownership system.

Author: WebMagic Team
Date: January 24, 2026
"""
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from models.site_models import CustomerUser, Site, CustomerSiteOwnership
from core.exceptions import NotFoundError, ValidationError, ForbiddenError

logger = logging.getLogger(__name__)


class CustomerSiteService:
    """Service for managing customer-site ownership relationships."""
    
    @staticmethod
    async def add_site_to_customer(
        db: AsyncSession,
        customer_user_id: UUID,
        site_id: UUID,
        is_primary: bool = False,
        role: str = "owner"
    ) -> CustomerSiteOwnership:
        """
        Add a site to a customer's ownership.
        
        Args:
            db: Database session
            customer_user_id: Customer user ID
            site_id: Site ID
            is_primary: Whether this should be the primary site
            role: Ownership role (owner, collaborator)
            
        Returns:
            CustomerSiteOwnership instance
            
        Raises:
            NotFoundError: If customer or site doesn't exist
            ValidationError: If ownership already exists
        """
        # Verify customer exists
        customer_result = await db.execute(
            select(CustomerUser).where(CustomerUser.id == customer_user_id)
        )
        customer = customer_result.scalar_one_or_none()
        if not customer:
            raise NotFoundError(f"Customer not found: {customer_user_id}")
        
        # Verify site exists
        site_result = await db.execute(
            select(Site).where(Site.id == site_id)
        )
        site = site_result.scalar_one_or_none()
        if not site:
            raise NotFoundError(f"Site not found: {site_id}")
        
        # Check if ownership already exists
        existing = await db.execute(
            select(CustomerSiteOwnership).where(
                and_(
                    CustomerSiteOwnership.customer_user_id == customer_user_id,
                    CustomerSiteOwnership.site_id == site_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationError("Customer already owns this site")
        
        # Create ownership
        ownership = CustomerSiteOwnership(
            customer_user_id=customer_user_id,
            site_id=site_id,
            role=role,
            is_primary=is_primary,
            acquired_at=datetime.utcnow()
        )
        db.add(ownership)
        
        # If marking as primary, update customer's primary_site_id
        if is_primary:
            # Unmark any other primary sites
            await db.execute(
                select(CustomerSiteOwnership).where(
                    and_(
                        CustomerSiteOwnership.customer_user_id == customer_user_id,
                        CustomerSiteOwnership.is_primary == True,
                        CustomerSiteOwnership.site_id != site_id
                    )
                )
            )
            # Set new primary
            customer.primary_site_id = site_id
        
        await db.commit()
        await db.refresh(ownership)
        
        logger.info(
            f"Added site {site.slug} to customer {customer.email} "
            f"(primary={is_primary}, role={role})"
        )
        
        return ownership
    
    @staticmethod
    async def remove_site_from_customer(
        db: AsyncSession,
        customer_user_id: UUID,
        site_id: UUID
    ) -> bool:
        """
        Remove a site from a customer's ownership.
        
        Args:
            db: Database session
            customer_user_id: Customer user ID
            site_id: Site ID
            
        Returns:
            True if removed, False if not found
        """
        result = await db.execute(
            select(CustomerSiteOwnership).where(
                and_(
                    CustomerSiteOwnership.customer_user_id == customer_user_id,
                    CustomerSiteOwnership.site_id == site_id
                )
            )
        )
        ownership = result.scalar_one_or_none()
        
        if not ownership:
            return False
        
        was_primary = ownership.is_primary
        
        await db.delete(ownership)
        await db.commit()
        
        # If this was primary, update customer's primary_site_id
        if was_primary:
            customer_result = await db.execute(
                select(CustomerUser).where(CustomerUser.id == customer_user_id)
            )
            customer = customer_result.scalar_one_or_none()
            if customer:
                # Get another site to make primary (if any)
                other_ownership = await db.execute(
                    select(CustomerSiteOwnership)
                    .where(CustomerSiteOwnership.customer_user_id == customer_user_id)
                    .limit(1)
                )
                other = other_ownership.scalar_one_or_none()
                if other:
                    other.is_primary = True
                    customer.primary_site_id = other.site_id
                else:
                    customer.primary_site_id = None
                
                await db.commit()
        
        logger.info(f"Removed site {site_id} from customer {customer_user_id}")
        return True
    
    @staticmethod
    async def set_primary_site(
        db: AsyncSession,
        customer_user_id: UUID,
        site_id: UUID
    ) -> CustomerSiteOwnership:
        """
        Set a site as the customer's primary site.
        
        Args:
            db: Database session
            customer_user_id: Customer user ID
            site_id: Site ID to make primary
            
        Returns:
            Updated CustomerSiteOwnership instance
            
        Raises:
            NotFoundError: If ownership doesn't exist
        """
        # Verify ownership exists
        ownership_result = await db.execute(
            select(CustomerSiteOwnership).where(
                and_(
                    CustomerSiteOwnership.customer_user_id == customer_user_id,
                    CustomerSiteOwnership.site_id == site_id
                )
            )
        )
        ownership = ownership_result.scalar_one_or_none()
        
        if not ownership:
            raise NotFoundError("Customer doesn't own this site")
        
        # Unmark all other sites as primary
        await db.execute(
            select(CustomerSiteOwnership)
            .where(
                and_(
                    CustomerSiteOwnership.customer_user_id == customer_user_id,
                    CustomerSiteOwnership.is_primary == True
                )
            )
        )
        # Update in-memory objects
        all_ownerships = await db.execute(
            select(CustomerSiteOwnership).where(
                CustomerSiteOwnership.customer_user_id == customer_user_id
            )
        )
        for own in all_ownerships.scalars():
            own.is_primary = (own.site_id == site_id)
        
        # Update customer's primary_site_id
        customer_result = await db.execute(
            select(CustomerUser).where(CustomerUser.id == customer_user_id)
        )
        customer = customer_result.scalar_one_or_none()
        if customer:
            customer.primary_site_id = site_id
        
        await db.commit()
        await db.refresh(ownership)
        
        logger.info(f"Set site {site_id} as primary for customer {customer_user_id}")
        return ownership
    
    @staticmethod
    async def get_customer_sites(
        db: AsyncSession,
        customer_user_id: UUID,
        include_site_details: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all sites owned by a customer.
        
        Args:
            db: Database session
            customer_user_id: Customer user ID
            include_site_details: Whether to include full site details
            
        Returns:
            List of site dictionaries
        """
        query = select(CustomerSiteOwnership).where(
            CustomerSiteOwnership.customer_user_id == customer_user_id
        ).order_by(
            CustomerSiteOwnership.is_primary.desc(),
            CustomerSiteOwnership.acquired_at.desc()
        )
        
        if include_site_details:
            query = query.options(selectinload(CustomerSiteOwnership.site))
        
        result = await db.execute(query)
        ownerships = result.scalars().all()
        
        sites = []
        for ownership in ownerships:
            site_data = {
                "ownership_id": str(ownership.id),
                "site_id": str(ownership.site_id),
                "is_primary": ownership.is_primary,
                "role": ownership.role,
                "acquired_at": ownership.acquired_at.isoformat() if ownership.acquired_at else None
            }
            
            if include_site_details and ownership.site:
                site = ownership.site
                site_data.update({
                    "slug": site.slug,
                    "site_title": site.site_title,
                    "site_url": f"https://sites.lavish.solutions/{site.slug}",  # TODO: Use site_service
                    "status": site.status,
                    "subscription_status": site.subscription_status,
                    "purchased_at": site.purchased_at.isoformat() if site.purchased_at else None,
                    "next_billing_date": site.next_billing_date.isoformat() if site.next_billing_date else None,
                    "custom_domain": site.custom_domain
                })
            
            sites.append(site_data)
        
        return sites
    
    @staticmethod
    async def verify_site_ownership(
        db: AsyncSession,
        customer_user_id: UUID,
        site_id: UUID
    ) -> bool:
        """
        Verify that a customer owns a specific site.
        
        Args:
            db: Database session
            customer_user_id: Customer user ID
            site_id: Site ID
            
        Returns:
            True if customer owns the site, False otherwise
        """
        result = await db.execute(
            select(CustomerSiteOwnership).where(
                and_(
                    CustomerSiteOwnership.customer_user_id == customer_user_id,
                    CustomerSiteOwnership.site_id == site_id
                )
            )
        )
        ownership = result.scalar_one_or_none()
        return ownership is not None
    
    @staticmethod
    async def get_site_owners(
        db: AsyncSession,
        site_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get all customers who own a specific site.
        
        Args:
            db: Database session
            site_id: Site ID
            
        Returns:
            List of owner dictionaries
        """
        result = await db.execute(
            select(CustomerSiteOwnership)
            .where(CustomerSiteOwnership.site_id == site_id)
            .options(selectinload(CustomerSiteOwnership.customer_user))
            .order_by(CustomerSiteOwnership.is_primary.desc())
        )
        ownerships = result.scalars().all()
        
        owners = []
        for ownership in ownerships:
            if ownership.customer_user:
                owners.append({
                    "customer_id": str(ownership.customer_user_id),
                    "email": ownership.customer_user.email,
                    "full_name": ownership.customer_user.full_name,
                    "is_primary": ownership.is_primary,
                    "role": ownership.role,
                    "acquired_at": ownership.acquired_at.isoformat() if ownership.acquired_at else None
                })
        
        return owners


# Singleton instance
def get_customer_site_service() -> CustomerSiteService:
    """Get CustomerSiteService instance."""
    return CustomerSiteService()
