"""
Business service for database operations.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from datetime import datetime
from slugify import slugify
import logging

from models.business import Business
from core.exceptions import DatabaseException, ValidationException

logger = logging.getLogger(__name__)


class BusinessService:
    """Service for business/lead management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_business(
        self,
        business_data: Dict[str, Any],
        coverage_grid_id: Optional[UUID] = None
    ) -> Business:
        """
        Create a new business record.
        
        Args:
            business_data: Dictionary with business fields
            coverage_grid_id: Associated coverage grid ID
            
        Returns:
            Created Business instance
            
        Raises:
            ValidationException: If data is invalid
            DatabaseException: If database operation fails
        """
        try:
            # Generate slug from name
            slug = self._generate_unique_slug(business_data.get("name", ""))
            
            business = Business(
                **business_data,
                slug=slug,
                coverage_grid_id=coverage_grid_id,
                scraped_at=datetime.utcnow()
            )
            
            self.db.add(business)
            await self.db.flush()
            await self.db.refresh(business)
            
            logger.info(f"Created business: {business.name} ({business.id})")
            return business
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error creating business: {str(e)}")
            raise DatabaseException(f"Business already exists or constraint violated")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating business: {str(e)}")
            raise DatabaseException(f"Failed to create business: {str(e)}")
    
    async def get_business(self, business_id: UUID) -> Optional[Business]:
        """Get business by ID."""
        result = await self.db.execute(
            select(Business).where(Business.id == business_id)
        )
        return result.scalar_one_or_none()
    
    async def get_business_by_gmb_id(self, gmb_id: str) -> Optional[Business]:
        """Get business by Google My Business ID."""
        result = await self.db.execute(
            select(Business).where(Business.gmb_id == gmb_id)
        )
        return result.scalar_one_or_none()
    
    async def get_business_by_slug(self, slug: str) -> Optional[Business]:
        """Get business by slug."""
        result = await self.db.execute(
            select(Business).where(Business.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def create_or_update_business(
        self,
        data: Dict[str, Any],
        source: str = "outscraper_gmaps",
        discovery_city: Optional[str] = None,
        discovery_state: Optional[str] = None,
        discovery_zone_id: Optional[str] = None,
        discovery_zone_lat: Optional[float] = None,
        discovery_zone_lon: Optional[float] = None,
        lead_score: Optional[float] = None,
        qualification_reasons: Optional[List[str]] = None
    ) -> Optional[Business]:
        """
        Create or update a business record (idempotent).
        
        Looks up by gmb_id first, creates if not found, updates if found.
        
        Args:
            data: Business data dictionary
            source: Data source identifier
            discovery_city: City where business was discovered
            discovery_state: State where business was discovered
            discovery_zone_id: Zone ID where business was discovered
            discovery_zone_lat: Zone latitude
            discovery_zone_lon: Zone longitude
            lead_score: Qualification score
            qualification_reasons: List of qualification reason strings
            
        Returns:
            Business instance or None if creation failed
        """
        try:
            # Extract gmb_id for lookup
            gmb_id = data.get("gmb_id") or data.get("cid")
            
            # Try to find existing business
            existing = None
            if gmb_id:
                existing = await self.get_business_by_gmb_id(str(gmb_id))
            
            # Build business data with discovery metadata
            business_data = {
                **data,
                "source": source,
                "discovery_city": discovery_city,
                "discovery_state": discovery_state,
                "discovery_zone_id": discovery_zone_id,
                "discovery_zone_lat": discovery_zone_lat,
                "discovery_zone_lon": discovery_zone_lon,
                "lead_score": lead_score,
                "qualification_reasons": qualification_reasons
            }
            
            # Clean None values
            business_data = {k: v for k, v in business_data.items() if v is not None}
            
            if existing:
                # Update existing business with new data
                logger.info(f"Updating existing business: {existing.name} ({existing.id})")
                updated = await self.update_business(existing.id, business_data)
                if updated:
                    updated._is_new = False
                return updated
            else:
                # Create new business
                business = await self.create_business(business_data)
                if business:
                    business._is_new = True
                return business
                
        except Exception as e:
            logger.error(f"Error in create_or_update_business: {str(e)}")
            return None
    
    async def list_businesses(
        self,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> tuple[List[Business], int]:
        """
        List businesses with pagination and filters.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters (e.g., {"website_status": "none", "rating__gte": 4.0})
            
        Returns:
            Tuple of (businesses list, total count)
        """
        # Build query
        query = select(Business)
        count_query = select(func.count(Business.id))
        
        # Apply filters
        if filters:
            conditions = self._build_filter_conditions(filters)
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
        
        # Add ordering
        query = query.order_by(Business.created_at.desc())
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        businesses = result.scalars().all()
        
        return list(businesses), total
    
    async def update_business(
        self,
        business_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[Business]:
        """Update business fields."""
        try:
            updates["updated_at"] = datetime.utcnow()
            
            await self.db.execute(
                update(Business)
                .where(Business.id == business_id)
                .values(**updates)
            )
            await self.db.flush()
            
            # Fetch updated business
            return await self.get_business(business_id)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating business: {str(e)}")
            raise DatabaseException(f"Failed to update business: {str(e)}")
    
    async def delete_business(self, business_id: UUID) -> bool:
        """Delete business by ID."""
        try:
            result = await self.db.execute(
                delete(Business).where(Business.id == business_id)
            )
            await self.db.flush()
            return result.rowcount > 0
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting business: {str(e)}")
            raise DatabaseException(f"Failed to delete business: {str(e)}")
    
    async def bulk_create_businesses(
        self,
        businesses_data: List[Dict[str, Any]],
        coverage_grid_id: Optional[UUID] = None
    ) -> List[Business]:
        """
        Bulk create businesses (optimized for scraping).
        Skips duplicates based on gmb_id.
        
        Args:
            businesses_data: List of business dictionaries
            coverage_grid_id: Associated coverage grid ID
            
        Returns:
            List of created Business instances
        """
        created = []
        skipped = 0
        
        for business_data in businesses_data:
            try:
                # Check if already exists by gmb_id
                gmb_id = business_data.get("gmb_id")
                if gmb_id:
                    existing = await self.get_business_by_gmb_id(gmb_id)
                    if existing:
                        logger.debug(f"Skipping duplicate business: {gmb_id}")
                        skipped += 1
                        continue
                
                # Create business
                business = await self.create_business(
                    business_data,
                    coverage_grid_id=coverage_grid_id
                )
                created.append(business)
                
            except Exception as e:
                logger.warning(f"Failed to create business: {str(e)}")
                continue
        
        logger.info(f"Bulk created {len(created)} businesses, skipped {skipped} duplicates")
        return created
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get business statistics."""
        # Total leads
        total_result = await self.db.execute(select(func.count(Business.id)))
        total = total_result.scalar()
        
        # With email
        with_email_result = await self.db.execute(
            select(func.count(Business.id)).where(Business.email.isnot(None))
        )
        with_email = with_email_result.scalar()
        
        # Without website
        no_website_result = await self.db.execute(
            select(func.count(Business.id)).where(
                or_(
                    Business.website_url.is_(None),
                    Business.website_url == ""
                )
            )
        )
        no_website = no_website_result.scalar()
        
        # High rating (4.0+)
        high_rating_result = await self.db.execute(
            select(func.count(Business.id)).where(Business.rating >= 4.0)
        )
        high_rating = high_rating_result.scalar()
        
        # Qualified (score > 0)
        qualified_result = await self.db.execute(
            select(func.count(Business.id)).where(Business.qualification_score > 0)
        )
        qualified = qualified_result.scalar()
        
        # By status
        by_status = {}
        status_result = await self.db.execute(
            select(Business.website_status, func.count(Business.id))
            .group_by(Business.website_status)
        )
        for status, count in status_result:
            by_status[status] = count
        
        # By category (top 10)
        by_category = {}
        category_result = await self.db.execute(
            select(Business.category, func.count(Business.id))
            .where(Business.category.isnot(None))
            .group_by(Business.category)
            .order_by(func.count(Business.id).desc())
            .limit(10)
        )
        for category, count in category_result:
            by_category[category] = count
        
        return {
            "total_leads": total,
            "qualified_leads": qualified,
            "with_email": with_email,
            "without_website": no_website,
            "high_rating": high_rating,
            "by_status": by_status,
            "by_category": by_category
        }
    
    def _generate_unique_slug(self, name: str) -> str:
        """Generate URL-safe slug from business name."""
        base_slug = slugify(name, max_length=200)
        if not base_slug:
            base_slug = "business"
        
        # Add timestamp suffix for uniqueness
        import time
        timestamp = int(time.time() * 1000)  # milliseconds
        return f"{base_slug}-{timestamp}"
    
    def _build_filter_conditions(self, filters: Dict[str, Any]) -> List:
        """Build SQLAlchemy filter conditions from dict."""
        conditions = []
        
        for key, value in filters.items():
            # Handle comparison operators in key (e.g., "rating__gte")
            if "__" in key:
                field_name, operator = key.split("__", 1)
                field = getattr(Business, field_name, None)
                if field is None:
                    continue
                
                if operator == "gte":
                    conditions.append(field >= value)
                elif operator == "lte":
                    conditions.append(field <= value)
                elif operator == "gt":
                    conditions.append(field > value)
                elif operator == "lt":
                    conditions.append(field < value)
                elif operator == "ne":
                    conditions.append(field != value)
                elif operator == "in":
                    conditions.append(field.in_(value))
                elif operator == "like":
                    conditions.append(field.like(f"%{value}%"))
            else:
                # Simple equality
                field = getattr(Business, key, None)
                if field is not None:
                    conditions.append(field == value)
        
        return conditions
