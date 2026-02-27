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
            # Generate slug from name and location
            slug = self._generate_unique_slug(
                business_data.get("name", ""),
                business_data.get("city", ""),
                business_data.get("state", "")
            )
            
            # Use a savepoint so a constraint violation here only rolls back this
            # insert — not the entire outer transaction (e.g., the flushed coverage row).
            async with self.db.begin_nested():
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
            logger.error(f"Integrity error creating business: {str(e)}")
            raise DatabaseException(f"Business already exists or constraint violated")
        except Exception as e:
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
        coverage_grid_id: Optional[UUID] = None,
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
            source: Data source identifier (not stored in Business model)
            coverage_grid_id: Coverage grid ID to link business to (stored)
            discovery_city: City where business was discovered (not stored)
            discovery_state: State where business was discovered (not stored)
            discovery_zone_id: Zone ID where business was discovered (not stored)
            discovery_zone_lat: Zone latitude (not stored)
            discovery_zone_lon: Zone longitude (not stored)
            lead_score: Qualification score
            qualification_reasons: List of qualification reason strings (not stored)
            
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
            
            # Only pass fields that exist in the Business model
            # NOTE: coverage_grid_id is handled separately as a parameter
            valid_fields = {
                "gmb_id", "gmb_place_id", "name", "slug",
                "email", "phone", "website_url",
                "address", "city", "state", "zip_code", "country", "latitude", "longitude",
                "category", "subcategory", "rating", "review_count",
                "reviews_summary", "review_highlight", "brand_archetype",
                "photos_urls", "logo_url",
                "website_status", "contact_status", "qualification_score",
                "website_validation_status", "website_validated_at",  # NEW: Website validation fields
                "creative_dna", "scraped_at",
                "raw_data"  # NEW: Store full Outscraper response for reprocessing
            }
            
            # Filter business data to only valid fields
            # IMPORTANT: raw_data should ALWAYS be saved, even if it's a dict (don't check None)
            business_data = {}
            for k, v in data.items():
                if k not in valid_fields:
                    continue
                # Always save raw_data regardless of value
                if k == "raw_data":
                    business_data[k] = v
                    logger.info(f"Saving raw_data: {type(v)}, keys: {list(v.keys()) if isinstance(v, dict) else 'N/A'}")
                # For other fields, skip if None
                elif v is not None:
                    business_data[k] = v
            
            # Add qualification score if provided
            if lead_score is not None:
                business_data["qualification_score"] = int(lead_score)
            
            if existing:
                # Update existing business with new data
                logger.info(f"Updating existing business: {existing.name} ({existing.id})")
                updated = await self.update_business(existing.id, business_data)
                if updated:
                    updated._is_new = False
                return updated
            else:
                # Create new business with coverage_grid_id link
                business = await self.create_business(
                    business_data, 
                    coverage_grid_id=coverage_grid_id
                )
                if business:
                    business._is_new = True
                return business
                
        except Exception as e:
            logger.error(f"Error in create_or_update_business: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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
            
            # Use a savepoint so an update failure doesn't corrupt the outer transaction.
            async with self.db.begin_nested():
                await self.db.execute(
                    update(Business)
                    .where(Business.id == business_id)
                    .values(**updates)
                )
                await self.db.flush()
            
            # Fetch updated business
            return await self.get_business(business_id)
            
        except Exception as e:
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
        # Clean and shorten business name
        name_slug = self._create_business_name_slug(name)
        
        # Create region code from city
        region_code = self._create_region_code(city, state)
        
        # Combine: business-name-region
        if region_code:
            base_slug = f"{name_slug}-{region_code}"
        else:
            base_slug = name_slug
        
        # Ensure it's not too long (max 50 chars for safety)
        if len(base_slug) > 50:
            # Truncate business name part to fit
            max_name_length = 50 - len(region_code) - 1  # -1 for hyphen
            name_slug = name_slug[:max_name_length].rstrip('-')
            base_slug = f"{name_slug}-{region_code}" if region_code else name_slug
        
        return base_slug
    
    def _create_business_name_slug(self, name: str) -> str:
        """
        Create clean, shortened business name slug.
        
        Rules:
        - Remove common business suffixes (LLC, Inc, Co, Corp, etc.)
        - Remove special characters
        - Abbreviate if too long
        - Max ~20 chars
        
        Examples:
            "Body Care Chiropractic LLC" -> "bodycare-chiro"
            "Elite Auto Repair & Detailing Inc" -> "elite-auto"
            "ABC Company" -> "abc"
        """
        # Remove common business entity suffixes
        suffixes_to_remove = [
            'llc', 'inc', 'incorporated', 'corp', 'corporation',
            'co', 'company', 'ltd', 'limited', 'pllc', 'pc',
            '&', 'and', 'the'
        ]
        
        # Convert to lowercase and split into words
        name_lower = name.lower()
        for suffix in suffixes_to_remove:
            # Remove suffix with word boundaries
            name_lower = name_lower.replace(f' {suffix} ', ' ')
            name_lower = name_lower.replace(f' {suffix}', '')
            name_lower = name_lower.replace(f'{suffix} ', '')
        
        # Slugify (handles special chars, extra spaces, etc.)
        slug = slugify(name_lower, max_length=100)
        
        if not slug:
            return "business"
        
        # If still too long (>20 chars), intelligently shorten
        if len(slug) > 20:
            words = slug.split('-')
            
            # Try to keep first word + abbreviated rest
            if len(words) > 1:
                # Keep first word, abbreviate others
                first_word = words[0]
                
                # Common abbreviations for business types
                abbreviations = {
                    'chiropractic': 'chiro',
                    'chiropractor': 'chiro',
                    'veterinary': 'vet',
                    'veterinarian': 'vet',
                    'restaurant': 'rest',
                    'pharmacy': 'pharm',
                    'automobile': 'auto',
                    'accounting': 'acct',
                    'dentistry': 'dental',
                    'dental': 'dental',
                    'medical': 'med',
                    'clinic': 'clinic',
                    'hospital': 'hosp',
                    'plumbing': 'plumb',
                    'electrical': 'elec',
                    'painting': 'paint',
                    'cleaning': 'clean',
                    'landscaping': 'landscape',
                    'construction': 'const',
                    'consulting': 'consult',
                    'services': 'svc',
                    'service': 'svc',
                    'repair': 'repair',
                    'rehab': 'rehab',
                    'rehabilitation': 'rehab'
                }
                
                # Abbreviate remaining words
                abbreviated = [first_word]
                for word in words[1:3]:  # Max 2 additional words
                    abbreviated.append(abbreviations.get(word, word[:4]))
                
                slug = '-'.join(abbreviated)
            
            # Final truncate if still too long
            slug = slug[:20].rstrip('-')
        
        return slug
    
    def _create_region_code(self, city: str, state: str) -> str:
        """
        Create short region code from city/state.
        
        Examples:
            "Los Angeles", "California" -> "la"
            "San Francisco", "California" -> "sf"
            "New York", "New York" -> "ny"
            "Las Vegas", "Nevada" -> "lv"
        
        Returns:
            2-4 char region code
        """
        if not city:
            # Fallback to state code if available
            if state:
                # Try to get state abbreviation
                state_abbrev = self._get_state_abbreviation(state)
                return state_abbrev.lower() if state_abbrev else ""
            return ""
        
        city_lower = city.lower().strip()
        
        # Common city abbreviations
        city_codes = {
            'los angeles': 'la',
            'san francisco': 'sf',
            'san diego': 'sd',
            'san jose': 'sj',
            'new york': 'ny',
            'las vegas': 'lv',
            'washington': 'dc',
            'philadelphia': 'phl',
            'phoenix': 'phx',
            'chicago': 'chi',
            'houston': 'hou',
            'dallas': 'dal',
            'austin': 'atx',
            'seattle': 'sea',
            'denver': 'den',
            'boston': 'bos',
            'miami': 'mia',
            'atlanta': 'atl',
            'portland': 'pdx',
            'sacramento': 'sac',
            'santa barbara': 'sb',
            'santa monica': 'sm',
            'long beach': 'lb',
            'palm springs': 'ps',
        }
        
        # Check if we have a known abbreviation
        if city_lower in city_codes:
            return city_codes[city_lower]
        
        # Otherwise, create abbreviation from first letters of each word
        words = city_lower.split()
        if len(words) >= 2:
            # Multi-word city: take first letter of each word (max 3)
            return ''.join([w[0] for w in words[:3]])
        elif len(words) == 1:
            # Single word: take first 2-3 chars
            return city_lower[:3]
        
        return ""
    
    def _get_state_abbreviation(self, state: str) -> str:
        """Get 2-letter state code from full state name."""
        state_map = {
            'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
            'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
            'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
            'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
            'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
            'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
            'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
            'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
            'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
            'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
            'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
            'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
            'wisconsin': 'WI', 'wyoming': 'WY'
        }
        
        state_lower = state.lower().strip()
        return state_map.get(state_lower, state[:2].upper())
    
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
