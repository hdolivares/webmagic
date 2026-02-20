"""
Site service for generated sites database operations.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from uuid import UUID
from datetime import datetime
from slugify import slugify
import logging

from models.site import GeneratedSite
from models.business import Business
from core.exceptions import DatabaseException

logger = logging.getLogger(__name__)


class SiteService:
    """Service for generated site management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_site(
        self,
        business_id: UUID,
        html_content: str,
        subdomain: str,
        css_content: Optional[str] = None,
        js_content: Optional[str] = None,
        design_brief: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> GeneratedSite:
        """
        Create a new generated site.
        
        Args:
            business_id: Associated business ID
            html_content: HTML code
            subdomain: Subdomain for the site
            css_content: CSS code
            js_content: JavaScript code
            design_brief: Design brief JSON
            **kwargs: Additional fields
            
        Returns:
            Created GeneratedSite instance
        """
        try:
            site = GeneratedSite(
                business_id=business_id,
                subdomain=subdomain,
                html_content=html_content,
                css_content=css_content,
                js_content=js_content,
                design_brief=design_brief,
                **kwargs
            )
            
            self.db.add(site)
            await self.db.flush()
            await self.db.refresh(site)
            
            logger.info(f"Created site: {subdomain} for business {business_id}")
            return site
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating site: {str(e)}")
            raise DatabaseException(f"Failed to create site: {str(e)}")
    
    async def get_site(self, site_id: UUID) -> Optional[GeneratedSite]:
        """Get site by ID (includes business relationship)."""
        from sqlalchemy.orm import joinedload
        result = await self.db.execute(
            select(GeneratedSite)
            .options(joinedload(GeneratedSite.business))
            .where(GeneratedSite.id == site_id)
        )
        return result.scalar_one_or_none()
    
    async def get_site_by_subdomain(self, subdomain: str) -> Optional[GeneratedSite]:
        """Get site by subdomain."""
        result = await self.db.execute(
            select(GeneratedSite).where(GeneratedSite.subdomain == subdomain)
        )
        return result.scalar_one_or_none()
    
    async def get_sites_by_business(
        self,
        business_id: UUID,
        status: Optional[str] = None
    ) -> List[GeneratedSite]:
        """Get all sites for a business."""
        query = select(GeneratedSite).where(
            GeneratedSite.business_id == business_id
        )
        
        if status:
            query = query.where(GeneratedSite.status == status)
        
        query = query.order_by(GeneratedSite.version.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def list_sites(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None
    ) -> tuple[List[GeneratedSite], int]:
        """List sites with pagination. Includes business relationship."""
        from sqlalchemy.orm import joinedload
        
        query = select(GeneratedSite).options(joinedload(GeneratedSite.business))
        count_query = select(func.count(GeneratedSite.id))
        
        if status:
            query = query.where(GeneratedSite.status == status)
            count_query = count_query.where(GeneratedSite.status == status)
        
        query = query.order_by(GeneratedSite.created_at.desc())
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        sites = result.scalars().all()
        
        return list(sites), total
    
    async def update_site(
        self,
        site_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[GeneratedSite]:
        """Update site fields."""
        try:
            updates["updated_at"] = datetime.utcnow()
            
            await self.db.execute(
                update(GeneratedSite)
                .where(GeneratedSite.id == site_id)
                .values(**updates)
            )
            await self.db.flush()
            
            return await self.get_site(site_id)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating site: {str(e)}")
            raise DatabaseException(f"Failed to update site: {str(e)}")
    
    async def generate_subdomain(self, business_name: str) -> str:
        """
        Generate unique subdomain from business name.
        
        Args:
            business_name: Business name
            
        Returns:
            Unique subdomain
        """
        base_slug = slugify(business_name, max_length=50)
        if not base_slug:
            base_slug = "site"
        
        # Check if subdomain exists
        existing = await self.get_site_by_subdomain(base_slug)
        if not existing:
            return base_slug
        
        # Add number suffix
        counter = 1
        while True:
            subdomain = f"{base_slug}-{counter}"
            existing = await self.get_site_by_subdomain(subdomain)
            if not existing:
                return subdomain
            counter += 1
            
            if counter > 100:
                # Fallback to timestamp
                import time
                return f"{base_slug}-{int(time.time())}"
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get site statistics."""
        # Total sites
        total_result = await self.db.execute(
            select(func.count(GeneratedSite.id))
        )
        total = total_result.scalar()
        
        # By status
        by_status = {}
        status_result = await self.db.execute(
            select(GeneratedSite.status, func.count(GeneratedSite.id))
            .group_by(GeneratedSite.status)
        )
        for status, count in status_result:
            by_status[status] = count
        
        # Live sites
        total_live = by_status.get("live", 0)
        
        # Sold sites
        sold_result = await self.db.execute(
            select(func.count(GeneratedSite.id))
            .where(GeneratedSite.sold_at.isnot(None))
        )
        total_sold = sold_result.scalar()
        
        # Average lighthouse score
        lighthouse_result = await self.db.execute(
            select(func.avg(GeneratedSite.lighthouse_score))
            .where(GeneratedSite.lighthouse_score.isnot(None))
        )
        avg_lighthouse = lighthouse_result.scalar()
        
        # Average load time
        load_time_result = await self.db.execute(
            select(func.avg(GeneratedSite.load_time_ms))
            .where(GeneratedSite.load_time_ms.isnot(None))
        )
        avg_load_time = load_time_result.scalar()
        
        return {
            "total_sites": total,
            "by_status": by_status,
            "avg_lighthouse_score": float(avg_lighthouse) if avg_lighthouse else None,
            "avg_load_time_ms": float(avg_load_time) if avg_load_time else None,
            "total_live": total_live,
            "total_sold": total_sold
        }
