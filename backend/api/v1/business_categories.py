"""
Business Categories API
Returns the list of business categories for frontend dropdowns
"""
from fastapi import APIRouter
from typing import List, Dict, Any

from scripts.business_categories import BUSINESS_CATEGORIES

router = APIRouter(prefix="/business-categories", tags=["business-categories"])


@router.get("/", response_model=List[Dict[str, Any]])
async def get_business_categories():
    """
    Get all business categories.
    
    Returns list of categories with their search terms and metadata.
    """
    categories = []
    
    for category_tuple in BUSINESS_CATEGORIES:
        display_name, search_term, profitability, avg_deal = category_tuple
        
        categories.append({
            "display_name": display_name,
            "search_term": search_term,
            "profitability_score": profitability,
            "avg_deal_value": avg_deal
        })
    
    return categories


@router.get("/search-terms", response_model=List[str])
async def get_category_search_terms():
    """
    Get just the search terms (for simple dropdowns).
    
    Returns list of search terms only.
    """
    return [category[1] for category in BUSINESS_CATEGORIES]


@router.get("/grouped", response_model=Dict[str, List[Dict[str, Any]]])
async def get_categories_grouped():
    """
    Get categories grouped by industry vertical.
    
    This would require updating business_categories.py to include grouping metadata.
    For now, returns all categories under "All Categories".
    """
    categories = []
    
    for category_tuple in BUSINESS_CATEGORIES:
        display_name, search_term, profitability, avg_deal = category_tuple
        
        categories.append({
            "display_name": display_name,
            "search_term": search_term,
            "profitability_score": profitability,
            "avg_deal_value": avg_deal
        })
    
    return {
        "All Categories": categories
    }

