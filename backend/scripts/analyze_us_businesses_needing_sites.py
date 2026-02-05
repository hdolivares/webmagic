"""
Analyze US businesses to generate accurate list of those needing sites.

This script:
1. Queries all US businesses
2. Checks website validation status
3. Filters by target regions (if specified)
4. Generates prioritized list based on:
   - Rating (higher is better)
   - Review count (more reviews = more established)
   - Location (target cities/states)
   - Category (target categories)

Usage:
    python -m scripts.analyze_us_businesses_needing_sites
    python -m scripts.analyze_us_businesses_needing_sites --export-csv
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any
import argparse
import logging
import csv
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_, or_, func
from core.database import AsyncSessionLocal
from models.business import Business

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Target regions (can be customized)
TARGET_STATES = {
    "TX", "FL", "CA", "NY", "IL", "PA", "OH", "GA", "NC", "MI"
}

TARGET_CITIES = {
    "Houston", "Dallas", "Austin", "San Antonio",  # TX
    "Miami", "Tampa", "Orlando", "Jacksonville",  # FL
    "Los Angeles", "San Diego", "San Jose", "San Francisco",  # CA
    "New York", "Brooklyn", "Queens",  # NY
    "Chicago",  # IL
    "Philadelphia",  # PA
    "Columbus", "Cleveland",  # OH
    "Atlanta",  # GA
    "Charlotte", "Raleigh",  # NC
    "Detroit",  # MI
}

# Target categories (high-value service businesses)
TARGET_CATEGORIES = {
    "plumber", "plumbing", "hvac", "electrician", "contractor",
    "roofing", "landscaping", "pest control", "locksmith",
    "garage door", "flooring", "painting", "remodeling",
    "handyman", "cleaning", "carpet cleaning", "window cleaning",
    "tree service", "lawn care", "pool service", "appliance repair"
}


async def analyze_businesses(
    export_csv: bool = False,
    min_rating: float = 3.5,
    min_reviews: int = 5
):
    """
    Analyze US businesses and generate prioritized list.
    
    Args:
        export_csv: Export results to CSV file
        min_rating: Minimum rating threshold
        min_reviews: Minimum review count threshold
    """
    logger.info("="*80)
    logger.info("ANALYZE US BUSINESSES NEEDING SITES")
    logger.info("="*80)
    logger.info(f"Minimum rating: {min_rating}")
    logger.info(f"Minimum reviews: {min_reviews}")
    logger.info(f"Target states: {', '.join(sorted(TARGET_STATES))}")
    logger.info("")
    
    async with AsyncSessionLocal() as db:
        # Query 1: All US businesses without websites
        logger.info("📊 Querying database...")
        
        query = select(Business).where(
            and_(
                Business.country == "US",
                or_(
                    Business.website_url.is_(None),
                    Business.website_url == "",
                    Business.website_validation_status.in_(["invalid", "missing"])
                )
            )
        )
        
        result = await db.execute(query)
        all_businesses = result.scalars().all()
        
        logger.info(f"Found {len(all_businesses)} US businesses without valid websites")
        logger.info("")
        
        # Filter and score businesses
        scored_businesses = []
        
        for business in all_businesses:
            # Calculate score
            score = 0
            reasons = []
            
            # Rating score (0-50 points)
            if business.rating:
                rating_score = (business.rating / 5.0) * 50
                score += rating_score
                reasons.append(f"Rating: {business.rating}/5.0")
            
            # Review count score (0-30 points, capped at 50 reviews)
            if business.review_count:
                review_score = min(business.review_count / 50.0, 1.0) * 30
                score += review_score
                reasons.append(f"Reviews: {business.review_count}")
            
            # Location score (0-20 points)
            location_score = 0
            if business.state in TARGET_STATES:
                location_score += 10
                reasons.append(f"Target state: {business.state}")
            if business.city in TARGET_CITIES:
                location_score += 10
                reasons.append(f"Target city: {business.city}")
            score += location_score
            
            # Category score (0-10 points)
            category_lower = (business.category or "").lower()
            if any(target in category_lower for target in TARGET_CATEGORIES):
                score += 10
                reasons.append(f"Target category: {business.category}")
            
            # Apply minimum thresholds
            if business.rating and business.rating < min_rating:
                continue
            if business.review_count and business.review_count < min_reviews:
                continue
            
            scored_businesses.append({
                "business": business,
                "score": score,
                "reasons": reasons
            })
        
        # Sort by score (highest first)
        scored_businesses.sort(key=lambda x: x["score"], reverse=True)
        
        logger.info(f"✅ Filtered to {len(scored_businesses)} qualified businesses")
        logger.info("")
        
        # Statistics
        logger.info("="*80)
        logger.info("STATISTICS")
        logger.info("="*80)
        
        # By state
        state_counts = {}
        for item in scored_businesses:
            state = item["business"].state or "Unknown"
            state_counts[state] = state_counts.get(state, 0) + 1
        
        logger.info("By State:")
        for state, count in sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {state}: {count}")
        logger.info("")
        
        # By category
        category_counts = {}
        for item in scored_businesses:
            category = item["business"].category or "Unknown"
            category_counts[category] = category_counts.get(category, 0) + 1
        
        logger.info("By Category:")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {category}: {count}")
        logger.info("")
        
        # Score distribution
        score_ranges = {
            "80-100": 0,
            "60-79": 0,
            "40-59": 0,
            "20-39": 0,
            "0-19": 0
        }
        for item in scored_businesses:
            score = item["score"]
            if score >= 80:
                score_ranges["80-100"] += 1
            elif score >= 60:
                score_ranges["60-79"] += 1
            elif score >= 40:
                score_ranges["40-59"] += 1
            elif score >= 20:
                score_ranges["20-39"] += 1
            else:
                score_ranges["0-19"] += 1
        
        logger.info("Score Distribution:")
        for range_name, count in score_ranges.items():
            logger.info(f"  {range_name}: {count}")
        logger.info("")
        
        # Top 20 businesses
        logger.info("="*80)
        logger.info("TOP 20 BUSINESSES (Highest Priority)")
        logger.info("="*80)
        
        for idx, item in enumerate(scored_businesses[:20], 1):
            business = item["business"]
            score = item["score"]
            reasons = item["reasons"]
            
            logger.info(f"{idx}. {business.name}")
            logger.info(f"   Score: {score:.1f}/100")
            logger.info(f"   Location: {business.city}, {business.state}")
            logger.info(f"   Category: {business.category}")
            logger.info(f"   Rating: {business.rating}/5.0 ({business.review_count} reviews)")
            logger.info(f"   ID: {business.id}")
            logger.info(f"   Reasons: {', '.join(reasons)}")
            logger.info("")
        
        # Export to CSV
        if export_csv:
            filename = f"us_businesses_needing_sites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = Path(__file__).parent / filename
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'rank', 'score', 'id', 'name', 'category',
                    'city', 'state', 'country',
                    'rating', 'review_count',
                    'phone', 'address',
                    'gmb_place_id', 'reasons'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for idx, item in enumerate(scored_businesses, 1):
                    business = item["business"]
                    writer.writerow({
                        'rank': idx,
                        'score': f"{item['score']:.1f}",
                        'id': str(business.id),
                        'name': business.name,
                        'category': business.category,
                        'city': business.city,
                        'state': business.state,
                        'country': business.country,
                        'rating': business.rating,
                        'review_count': business.review_count,
                        'phone': business.phone,
                        'address': business.address,
                        'gmb_place_id': business.gmb_place_id,
                        'reasons': '; '.join(item['reasons'])
                    })
            
            logger.info(f"✅ Exported to: {filepath}")
            logger.info("")
        
        logger.info("="*80)
        logger.info("✅ Analysis complete!")
        logger.info("="*80)
        logger.info(f"Total qualified businesses: {len(scored_businesses)}")
        logger.info(f"Ready for website generation: {len([x for x in scored_businesses if x['score'] >= 60])}")
        logger.info("")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze US businesses needing sites'
    )
    parser.add_argument(
        '--export-csv',
        action='store_true',
        help='Export results to CSV file'
    )
    parser.add_argument(
        '--min-rating',
        type=float,
        default=3.5,
        help='Minimum rating threshold (default: 3.5)'
    )
    parser.add_argument(
        '--min-reviews',
        type=int,
        default=5,
        help='Minimum review count threshold (default: 5)'
    )
    
    args = parser.parse_args()
    
    asyncio.run(analyze_businesses(
        export_csv=args.export_csv,
        min_rating=args.min_rating,
        min_reviews=args.min_reviews
    ))


if __name__ == "__main__":
    main()

