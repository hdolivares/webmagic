"""
Business Filter Service.

Provides powerful, flexible filtering of businesses with support for:
- Website status filtering (none, valid, invalid, generating, generated)
- Geographic filtering (country, state, city)
- Category/industry filtering
- Rating and review filtering
- Lead score filtering
- Custom field filtering with AND/OR logic
- Saved filter presets

Best Practices:
- Type-safe filter definitions
- SQL injection prevention via SQLAlchemy
- Efficient query building
- Composable filter logic
"""
import logging
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, case
from sqlalchemy.orm import selectinload

from models.business import Business
from models.coverage import CoverageGrid
from models.business_filter_preset import BusinessFilterPreset
from models.user import AdminUser

logger = logging.getLogger(__name__)


class FilterOperator:
    """Filter operator constants for type safety."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class FilterField:
    """Available filter fields for type safety."""
    # Identity fields
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    
    # Location fields
    COUNTRY = "country"
    STATE = "state"
    CITY = "city"
    ZIP_CODE = "zip_code"
    
    # Business fields
    CATEGORY = "category"
    INDUSTRY = "industry"
    RATING = "rating"
    REVIEW_COUNT = "review_count"
    
    # Website fields
    WEBSITE_STATUS = "website_status"
    WEBSITE_VALIDATION_STATUS = "website_validation_status"
    HAS_WEBSITE = "has_website"
    
    # Lead fields
    LEAD_SCORE = "qualification_score"
    STATUS = "status"
    
    # Generation fields
    GENERATION_STATUS = "generation_status"
    GENERATION_ATTEMPTS = "generation_attempts"
    
    # Timestamps
    SCRAPED_AT = "scraped_at"
    UPDATED_AT = "updated_at"


class BusinessFilterService:
    """
    Service for filtering businesses with advanced query building.
    
    Supports:
    - Complex AND/OR filter combinations
    - Saved filter presets
    - Efficient pagination
    - Count-only queries for statistics
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize business filter service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def _build_filter_condition(self, field: str, operator: str, value: Any):
        """
        Build a single filter condition.
        
        Args:
            field: Field name to filter on
            operator: Comparison operator
            value: Value to compare against
            
        Returns:
            SQLAlchemy filter condition
            
        Raises:
            ValueError: If field or operator is invalid
        """
        # Get the model column
        if not hasattr(Business, field):
            raise ValueError(f"Invalid filter field: {field}")
        
        column = getattr(Business, field)
        
        # Build condition based on operator
        if operator == FilterOperator.EQUALS:
            return column == value
        elif operator == FilterOperator.NOT_EQUALS:
            return column != value
        elif operator == FilterOperator.GREATER_THAN:
            return column > value
        elif operator == FilterOperator.GREATER_THAN_OR_EQUAL:
            return column >= value
        elif operator == FilterOperator.LESS_THAN:
            return column < value
        elif operator == FilterOperator.LESS_THAN_OR_EQUAL:
            return column <= value
        elif operator == FilterOperator.IN:
            if not isinstance(value, (list, tuple)):
                value = [value]
            return column.in_(value)
        elif operator == FilterOperator.NOT_IN:
            if not isinstance(value, (list, tuple)):
                value = [value]
            return column.not_in(value)
        elif operator == FilterOperator.CONTAINS:
            return column.ilike(f"%{value}%")
        elif operator == FilterOperator.STARTS_WITH:
            return column.ilike(f"{value}%")
        elif operator == FilterOperator.ENDS_WITH:
            return column.ilike(f"%{value}")
        elif operator == FilterOperator.IS_NULL:
            return column.is_(None)
        elif operator == FilterOperator.IS_NOT_NULL:
            return column.isnot(None)
        else:
            raise ValueError(f"Invalid filter operator: {operator}")
    
    def _build_query_filters(self, filters: Dict[str, Any], logic: str = "AND"):
        """
        Build complex filter conditions from filter dict.
        
        Args:
            filters: Dictionary of filters
                {
                    "field": "value",  # Simple equality
                    "field": {"operator": "gt", "value": 5},  # With operator
                    "AND": [...],  # Nested AND conditions
                    "OR": [...]  # Nested OR conditions
                }
            logic: Logic operator for combining filters (AND/OR)
            
        Returns:
            SQLAlchemy filter condition
        """
        conditions = []
        
        for key, value in filters.items():
            # Handle nested AND/OR logic
            if key.upper() == "AND":
                if isinstance(value, list):
                    nested = [self._build_query_filters(f, "AND") for f in value]
                    conditions.append(and_(*nested))
            elif key.upper() == "OR":
                if isinstance(value, list):
                    nested = [self._build_query_filters(f, "OR") for f in value]
                    conditions.append(or_(*nested))
            # Handle regular field filters
            else:
                if isinstance(value, dict) and "operator" in value:
                    # Complex filter with operator
                    operator = value["operator"]
                    filter_value = value["value"]
                    conditions.append(
                        self._build_filter_condition(key, operator, filter_value)
                    )
                else:
                    # Simple equality filter
                    conditions.append(
                        self._build_filter_condition(key, FilterOperator.EQUALS, value)
                    )
        
        # Combine conditions with specified logic
        if not conditions:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        elif logic.upper() == "OR":
            return or_(*conditions)
        else:
            return and_(*conditions)
    
    async def filter_businesses(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "scraped_at",
        sort_desc: bool = True,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Filter businesses with advanced query building.
        
        Args:
            filters: Dictionary of filters (supports AND/OR logic)
            sort_by: Field to sort by
            sort_desc: Sort descending if True
            skip: Number of records to skip (pagination)
            limit: Maximum records to return
            
        Returns:
            Dict with businesses and metadata:
            {
                "businesses": [...],
                "total": 100,
                "page": 1,
                "pages": 2,
                "filters_applied": {...}
            }
        """
        # Start with base query
        query = select(Business)
        count_query = select(func.count()).select_from(Business)
        
        # Apply filters if provided
        if filters:
            filter_condition = self._build_query_filters(filters)
            if filter_condition is not None:
                query = query.where(filter_condition)
                count_query = count_query.where(filter_condition)
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply sorting
        if hasattr(Business, sort_by):
            sort_column = getattr(Business, sort_by)
            if sort_desc:
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await self.db.execute(query)
        businesses = result.scalars().all()
        
        # Calculate pagination metadata
        pages = (total + limit - 1) // limit if limit > 0 else 1
        page = (skip // limit) + 1 if limit > 0 else 1
        
        return {
            "businesses": [self._business_to_dict(b) for b in businesses],
            "total": total,
            "page": page,
            "pages": pages,
            "limit": limit,
            "filters_applied": filters or {}
        }
    
    async def count_by_website_status(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, int]:
        """
        Get count of businesses by website status.
        
        Args:
            filters: Optional additional filters to apply
            
        Returns:
            Dict with counts by website status
        """
        query = select(
            Business.website_validation_status,
            func.count().label("count")
        ).group_by(Business.website_validation_status)
        
        # Apply filters if provided
        if filters:
            filter_condition = self._build_query_filters(filters)
            if filter_condition is not None:
                query = query.where(filter_condition)
        
        result = await self.db.execute(query)
        counts = {row.website_validation_status or "unknown": row.count for row in result}
        
        return counts
    
    async def save_filter_preset(
        self,
        user_id: UUID,
        name: str,
        filters: Dict[str, Any],
        is_public: bool = False
    ) -> BusinessFilterPreset:
        """
        Save a filter preset for reuse.
        
        Args:
            user_id: ID of user creating preset
            name: Name for the preset
            filters: Filter configuration
            is_public: If true, preset is available to all users
            
        Returns:
            Created BusinessFilterPreset
        """
        preset = BusinessFilterPreset(
            user_id=user_id,
            name=name,
            filters=filters,
            is_public=is_public
        )
        
        self.db.add(preset)
        await self.db.commit()
        await self.db.refresh(preset)
        
        logger.info(f"Filter preset '{name}' created by user {user_id}")
        
        return preset
    
    async def get_user_presets(
        self,
        user_id: UUID,
        include_public: bool = True
    ) -> List[BusinessFilterPreset]:
        """
        Get all filter presets for a user.
        
        Args:
            user_id: User ID
            include_public: If true, include public presets from other users
            
        Returns:
            List of BusinessFilterPreset objects
        """
        query = select(BusinessFilterPreset)
        
        if include_public:
            query = query.where(
                or_(
                    BusinessFilterPreset.user_id == user_id,
                    BusinessFilterPreset.is_public == 1
                )
            )
        else:
            query = query.where(BusinessFilterPreset.user_id == user_id)
        
        query = query.order_by(BusinessFilterPreset.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def delete_preset(self, preset_id: UUID, user_id: UUID) -> bool:
        """
        Delete a filter preset.
        
        Args:
            preset_id: Preset ID to delete
            user_id: User ID (must own the preset)
            
        Returns:
            True if deleted, False if not found or unauthorized
        """
        result = await self.db.execute(
            select(BusinessFilterPreset).where(
                and_(
                    BusinessFilterPreset.id == preset_id,
                    BusinessFilterPreset.user_id == user_id
                )
            )
        )
        preset = result.scalar_one_or_none()
        
        if not preset:
            return False
        
        await self.db.delete(preset)
        await self.db.commit()
        
        logger.info(f"Filter preset {preset_id} deleted by user {user_id}")
        
        return True
    
    def _business_to_dict(self, business: Business) -> Dict[str, Any]:
        """
        Convert Business model to dictionary.
        
        Args:
            business: Business model instance
            
        Returns:
            Dictionary representation
        """
        return {
            "id": str(business.id),
            "name": business.name,
            "email": business.email,
            "phone": business.phone,
            "website_url": business.website_url,
            "city": business.city,
            "state": business.state,
            "country": business.country,
            "zip_code": business.zip_code,
            "category": business.category,
            "rating": float(business.rating) if business.rating else None,
            "review_count": business.review_count,
            "website_status": business.website_status,
            "website_validation_status": business.website_validation_status,
            "qualification_score": float(business.qualification_score) if business.qualification_score else None,
            "status": business.status,
            "generation_queued_at": business.generation_queued_at.isoformat() if business.generation_queued_at else None,
            "generation_attempts": business.generation_attempts,
            "scraped_at": business.scraped_at.isoformat() if business.scraped_at else None,
            "updated_at": business.updated_at.isoformat() if business.updated_at else None
        }


# Quick filter presets (commonly used filters)
QUICK_FILTERS = {
    "no_website": {
        "name": "Businesses Without Website",
        "filters": {
            "OR": [
                {"website_url": {"operator": FilterOperator.IS_NULL, "value": None}},
                {"website_validation_status": {"operator": FilterOperator.IN, "value": ["missing", "invalid"]}}
            ]
        }
    },
    "valid_website": {
        "name": "Businesses With Valid Website",
        "filters": {
            "website_validation_status": {"operator": FilterOperator.EQUALS, "value": "valid"}
        }
    },
    "high_rated": {
        "name": "High Rated (4.0+)",
        "filters": {
            "rating": {"operator": FilterOperator.GREATER_THAN_OR_EQUAL, "value": 4.0}
        }
    },
    "needs_generation": {
        "name": "Needs Website Generation",
        "filters": {
            "AND": [
                {
                    "OR": [
                        {"website_url": {"operator": FilterOperator.IS_NULL, "value": None}},
                        {"website_validation_status": {"operator": FilterOperator.IN, "value": ["missing", "invalid"]}}
                    ]
                },
                {"generation_queued_at": {"operator": FilterOperator.IS_NULL, "value": None}}
            ]
        }
    },
    "generation_in_progress": {
        "name": "Website Generation In Progress",
        "filters": {
            "AND": [
                {"generation_queued_at": {"operator": FilterOperator.IS_NOT_NULL, "value": None}},
                {"generation_completed_at": {"operator": FilterOperator.IS_NULL, "value": None}}
            ]
        }
    }
}

