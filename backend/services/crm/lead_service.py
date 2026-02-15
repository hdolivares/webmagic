"""
Lead Service

Handles business/lead creation and ensures proper tracking in the CRM system.
Every site generation must have an associated business record.

Best Practices:
- Single Responsibility: Only handles business record management
- DRY: Reusable methods for getting or creating businesses
- Type Safety: Full type hints
- Error Handling: Graceful fallbacks with logging

Author: WebMagic Team  
Date: January 22, 2026
"""
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime
from slugify import slugify
import logging

from models.business import Business
from core.exceptions import ValidationException, DatabaseException

logger = logging.getLogger(__name__)


class LeadService:
    """
    Service for managing business leads in the CRM system.
    
    Responsibilities:
    - Create business records with proper defaults
    - Get or create businesses (idempotent operations)
    - Validate business data before creation
    - Calculate qualification scores
    """
    
    # CRM Status Constants
    CONTACT_STATUS_PENDING = "pending"
    CONTACT_STATUS_EMAILED = "emailed"
    CONTACT_STATUS_OPENED = "opened"
    CONTACT_STATUS_CLICKED = "clicked"
    CONTACT_STATUS_REPLIED = "replied"
    CONTACT_STATUS_PURCHASED = "purchased"
    CONTACT_STATUS_UNSUBSCRIBED = "unsubscribed"
    
    WEBSITE_STATUS_NONE = "none"
    WEBSITE_STATUS_GENERATING = "generating"
    WEBSITE_STATUS_GENERATED = "generated"
    WEBSITE_STATUS_DEPLOYED = "deployed"
    WEBSITE_STATUS_SOLD = "sold"
    WEBSITE_STATUS_ARCHIVED = "archived"
    
    def __init__(self, db: AsyncSession):
        """
        Initialize lead service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def get_or_create_business(
        self,
        business_data: Dict[str, Any],
        coverage_grid_id: Optional[UUID] = None
    ) -> Tuple[Business, bool]:
        """
        Get existing business or create new one (idempotent).
        
        This is the PRIMARY method for ensuring business records exist
        before any site generation or campaign activity.
        
        Lookup Priority:
        1. By business_id (if provided)
        2. By gmb_id (Google My Business ID)
        3. By slug (if provided)
        4. Create new business
        
        Args:
            business_data: Dictionary with business fields:
                - id (optional): Business UUID
                - gmb_id (optional): GMB identifier
                - name (required): Business name
                - category (optional): Industry category
                - email (optional): Contact email
                - phone (optional): Contact phone
                - city, state, country (optional): Location
                - rating, review_count (optional): Ratings
            coverage_grid_id: Associated coverage grid ID
        
        Returns:
            Tuple of (Business instance, created_flag)
            - created_flag is True if new business was created
        
        Raises:
            ValidationException: If required fields are missing
            DatabaseException: If database operation fails
        
        Example:
            >>> business, created = await lead_service.get_or_create_business({
            ...     "name": "LA Plumbing Pros",
            ...     "category": "Plumber",
            ...     "phone": "(310) 861-9785",
            ...     "city": "Los Angeles",
            ...     "state": "CA"
            ... })
            >>> if created:
            ...     logger.info(f"Created new business: {business.name}")
        """
        try:
            # Validate required fields
            if not business_data.get("name"):
                raise ValidationException("Business name is required")
            
            # Try to find existing business
            existing_business = await self._find_existing_business(business_data)
            
            if existing_business:
                logger.info(
                    f"Found existing business: {existing_business.name} "
                    f"(ID: {existing_business.id})"
                )
                return existing_business, False
            
            # Create new business
            business = await self._create_business_record(
                business_data,
                coverage_grid_id
            )
            
            logger.info(
                f"Created new business: {business.name} "
                f"(ID: {business.id}, Status: {business.contact_status})"
            )
            
            return business, True
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error in get_or_create_business: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to get or create business: {str(e)}")
    
    async def _find_existing_business(
        self,
        business_data: Dict[str, Any]
    ) -> Optional[Business]:
        """
        Find existing business by various identifiers.
        
        Args:
            business_data: Business data dictionary
        
        Returns:
            Business instance if found, None otherwise
        """
        # Try by business_id first
        business_id = business_data.get("id")
        if business_id:
            try:
                result = await self.db.execute(
                    select(Business).where(Business.id == UUID(str(business_id)))
                )
                business = result.scalar_one_or_none()
                if business:
                    return business
            except Exception as e:
                logger.debug(f"Business ID lookup failed: {e}")
        
        # Try by gmb_id
        gmb_id = business_data.get("gmb_id")
        if gmb_id:
            result = await self.db.execute(
                select(Business).where(Business.gmb_id == gmb_id)
            )
            business = result.scalar_one_or_none()
            if business:
                return business
        
        # Try by slug (if provided)
        slug = business_data.get("slug")
        if slug:
            result = await self.db.execute(
                select(Business).where(Business.slug == slug)
            )
            business = result.scalar_one_or_none()
            if business:
                return business
        
        return None
    
    async def _create_business_record(
        self,
        business_data: Dict[str, Any],
        coverage_grid_id: Optional[UUID] = None
    ) -> Business:
        """
        Create a new business record with proper defaults.
        
        Args:
            business_data: Business data dictionary
            coverage_grid_id: Associated coverage grid ID
        
        Returns:
            Created Business instance
        
        Raises:
            DatabaseException: If creation fails
        """
        try:
            # Generate unique slug from name and location
            slug = self._generate_unique_slug(
                business_data.get("name", ""),
                business_data.get("city", ""),
                business_data.get("state", "")
            )
            
            # Calculate qualification score
            qualification_score = self._calculate_qualification_score(business_data)
            
            # Prepare business data with CRM defaults
            from core.validation_enums import URLSource
            
            website_url = business_data.get("website_url")
            
            # Initialize V2 validation metadata
            website_metadata = {
                "source": URLSource.OUTSCRAPER.value if website_url else URLSource.NONE.value,
                "source_timestamp": datetime.utcnow().isoformat(),
                "validation_history": [],
                "discovery_attempts": {},
                "notes": None
            }
            
            business_fields = {
                "name": business_data.get("name"),
                "slug": slug,
                "gmb_id": business_data.get("gmb_id"),
                "gmb_place_id": business_data.get("gmb_place_id"),
                "email": business_data.get("email"),
                "phone": business_data.get("phone"),
                "website_url": website_url,
                "website_metadata": website_metadata,  # V2 metadata initialization
                "website_validation_status": "pending" if website_url else None,
                "address": business_data.get("address"),
                "city": business_data.get("city"),
                "state": business_data.get("state"),
                "zip_code": business_data.get("zip_code"),
                "country": business_data.get("country", "US"),
                "latitude": business_data.get("latitude"),
                "longitude": business_data.get("longitude"),
                "category": business_data.get("category"),
                "subcategory": business_data.get("subcategory"),
                "rating": business_data.get("rating"),
                "review_count": business_data.get("review_count", 0),
                "reviews_summary": business_data.get("reviews_summary"),
                "review_highlight": business_data.get("review_highlight"),
                "brand_archetype": business_data.get("brand_archetype"),
                "photos_urls": business_data.get("photos_urls", []),
                "logo_url": business_data.get("logo_url"),
                # CRM fields
                "website_status": self.WEBSITE_STATUS_NONE,
                "contact_status": self.CONTACT_STATUS_PENDING,
                "qualification_score": qualification_score,
                "coverage_grid_id": coverage_grid_id,
                "scraped_at": datetime.utcnow(),
            }
            
            # Create business
            business = Business(**business_fields)
            self.db.add(business)
            await self.db.flush()
            await self.db.refresh(business)
            
            return business
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating business record: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to create business: {str(e)}")
    
    def _generate_unique_slug(self, name: str, city: str = "", state: str = "") -> str:
        """
        Generate clean, human-readable slug: business-name-region
        
        Examples:
            - "Body Care Chiropractic" in "Los Angeles" -> "bodycare-la"
            - "Elite Auto Repair" in "San Francisco" -> "elite-auto-sf"
            - "ABC Company LLC" in "New York" -> "abc-ny"
        
        Args:
            name: Business name
            city: City name (optional)
            state: State name (optional)
            
        Returns:
            URL-safe slug like "business-name-region"
        """
        # Import the helper methods from business_service
        # (reusing same logic for consistency)
        from services.hunter.business_service import BusinessService
        
        # Create temporary instance to access helper methods
        helper = BusinessService(self.db)
        
        # Use the same slug generation logic
        return helper._generate_unique_slug(name, city, state)
    
    def _calculate_qualification_score(self, business_data: Dict[str, Any]) -> int:
        """
        Calculate lead qualification score (0-100).
        
        Scoring Factors:
        - Has email: +30 points
        - Has phone: +10 points
        - Has rating 4.0+: +20 points
        - Has 10+ reviews: +15 points
        - Has photos: +10 points
        - Has website: -15 points (less likely to need us)
        - High review count (50+): +15 points
        
        Args:
            business_data: Business data dictionary
        
        Returns:
            Score from 0-100
        """
        score = 0
        
        # Email is critical for outreach
        if business_data.get("email"):
            score += 30
        
        # Phone allows SMS campaigns
        if business_data.get("phone"):
            score += 10
        
        # High rating indicates quality business
        rating = business_data.get("rating")
        if rating and rating >= 4.0:
            score += 20
        
        # Review count indicates established business
        review_count = business_data.get("review_count", 0)
        if review_count >= 10:
            score += 15
        if review_count >= 50:
            score += 15
        
        # Photos indicate active GMB profile
        photos = business_data.get("photos_urls", [])
        if photos and len(photos) > 0:
            score += 10
        
        # Already has website (less likely to buy)
        if business_data.get("website_url"):
            score -= 15
        
        # Ensure score is within bounds
        return max(0, min(100, score))
    
    async def get_business_by_id(self, business_id: UUID) -> Optional[Business]:
        """
        Get business by ID.
        
        Args:
            business_id: Business UUID
        
        Returns:
            Business instance or None
        """
        result = await self.db.execute(
            select(Business).where(Business.id == business_id)
        )
        return result.scalar_one_or_none()
    
    async def get_business_by_slug(self, slug: str) -> Optional[Business]:
        """
        Get business by slug.
        
        Args:
            slug: Business slug
        
        Returns:
            Business instance or None
        """
        result = await self.db.execute(
            select(Business).where(Business.slug == slug)
        )
        return result.scalar_one_or_none()

