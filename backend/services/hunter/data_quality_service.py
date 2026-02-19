"""
Data Quality Service for Outscraper Results

Analyzes and scores business data quality using the rich information
provided by Outscraper to:
1. Filter out irrelevant/low-quality results
2. Score businesses for lead prioritization
3. Verify geo-targeting accuracy
4. Identify businesses truly without websites

Best Practices:
- Use all available Outscraper fields
- Multi-tier website detection
- Geo-validation (country_code, state_code)
- Business quality scoring
"""
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Canadian NANP area codes (+1 prefix but NOT US).
# Source: CRTC / NANPA allocations.
_CANADIAN_AREA_CODES = {
    "204", "226", "236", "249", "250", "289",
    "306", "343", "354", "365", "367", "368",
    "403", "416", "418", "428", "431", "437", "438", "450",
    "506", "514", "519", "548", "579", "581", "587",
    "604", "613", "639", "647", "672",
    "705", "709", "742", "778", "780", "782",
    "807", "819", "825",
    "867", "873",
    "902", "905",
}


def infer_country_from_phone(phone: Optional[str]) -> Optional[str]:
    """
    Infer country from a phone number's international dialing prefix.

    Uses the E.164 international prefix to determine country without any
    API calls or LLM involvement. This is the fastest and most reliable
    country signal when Outscraper omits country_code.

    Returns a 2-letter ISO country code ("US", "GB", "CA", "AU", …) or
    None when the phone number is absent / unrecognisable.
    """
    if not phone:
        return None

    # Normalise: strip spaces, dashes, dots, parentheses
    normalized = re.sub(r"[\s\-\.\(\)]", "", phone)

    # +44 → GB (United Kingdom)
    if normalized.startswith("+44"):
        return "GB"

    # +61 → AU (Australia)
    if normalized.startswith("+61"):
        return "AU"

    # +52 → MX (Mexico)
    if normalized.startswith("+52"):
        return "MX"

    # +55 → BR (Brazil)
    if normalized.startswith("+55"):
        return "BR"

    # +49 → DE (Germany)
    if normalized.startswith("+49"):
        return "DE"

    # +33 → FR (France)
    if normalized.startswith("+33"):
        return "FR"

    # +34 → ES (Spain)
    if normalized.startswith("+34"):
        return "ES"

    # +39 → IT (Italy)
    if normalized.startswith("+39"):
        return "IT"

    # NANP (+1) — could be US or CA; use area code to distinguish
    if normalized.startswith("+1") and len(normalized) >= 5:
        area_code = normalized[2:5]
        if area_code in _CANADIAN_AREA_CODES:
            return "CA"
        return "US"

    # Bare 10-digit US/CA number (no country prefix)
    if re.match(r"^\d{10}$", normalized):
        area_code = normalized[:3]
        if area_code in _CANADIAN_AREA_CODES:
            return "CA"
        return "US"

    return None


class DataQualityService:
    """
    Analyzes Outscraper data quality and filters/scores results.
    """
    
    # Geo-targeting filters
    VALID_COUNTRY_CODES = {"US", "CA", "GB", "AU"}  # Expand as needed
    
    # Business status filters
    OPERATIONAL_STATUSES = {"OPERATIONAL"}
    EXCLUDED_STATUSES = {"CLOSED_TEMPORARILY", "CLOSED_PERMANENTLY"}
    
    def __init__(
        self,
        strict_geo_filter: bool = True,
        require_operational: bool = True,
        min_quality_score: float = 30.0
    ):
        """
        Initialize Data Quality Service.
        
        Args:
            strict_geo_filter: If True, filter out businesses outside target geo
            require_operational: If True, filter out closed businesses
            min_quality_score: Minimum quality score threshold (0-100)
        """
        self.strict_geo_filter = strict_geo_filter
        self.require_operational = require_operational
        self.min_quality_score = min_quality_score
    
    def validate_geo_targeting(
        self,
        business: Dict[str, Any],
        target_country: str,
        target_state: Optional[str] = None,
        target_city: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate that business matches target geographic location.
        
        CRITICAL: Prevents getting UK results when searching for US businesses.
        
        Args:
            business: Normalized business data (from scraper)
            target_country: Target country code (e.g., "US")
            target_state: Target state code (e.g., "TX")
            target_city: Target city name (e.g., "Houston")
            
        Returns:
            Tuple of (is_valid, reasons)
        """
        raw_data = business.get("raw_data", {})
        reasons = []
        
        # Try normalized fields first (from scraper.py), then fall back to raw_data
        # This handles cases where Outscraper field names vary
        country_code = business.get("country") or raw_data.get("country_code") or raw_data.get("country")
        
        # For state, check both normalized "state" field and raw_data variants
        state_from_normalized = business.get("state", "")
        state_code = raw_data.get("state_code")
        state_name = raw_data.get("state")
        
        # Extract state code from state name if needed (e.g., "California" -> "CA")
        if not state_code and state_from_normalized:
            # Map full state names to codes
            state_name_to_code = {
                "california": "CA", "texas": "TX", "new york": "NY", 
                "florida": "FL", "illinois": "IL", "pennsylvania": "PA",
                "ohio": "OH", "georgia": "GA", "north carolina": "NC",
                "michigan": "MI", "new jersey": "NJ", "virginia": "VA",
                "washington": "WA", "arizona": "AZ", "massachusetts": "MA",
                "tennessee": "TN", "indiana": "IN", "missouri": "MO",
                "maryland": "MD", "wisconsin": "WI", "colorado": "CO",
                "minnesota": "MN", "south carolina": "SC", "alabama": "AL",
                "louisiana": "LA", "kentucky": "KY", "oregon": "OR",
                "oklahoma": "OK", "connecticut": "CT", "utah": "UT",
                "iowa": "IA", "nevada": "NV", "arkansas": "AR",
                "mississippi": "MS", "kansas": "KS", "new mexico": "NM",
                "nebraska": "NE", "west virginia": "WV", "idaho": "ID",
                "hawaii": "HI", "new hampshire": "NH", "maine": "ME",
                "montana": "MT", "rhode island": "RI", "delaware": "DE",
                "south dakota": "SD", "north dakota": "ND", "alaska": "AK",
                "vermont": "VT", "wyoming": "WY"
            }
            state_code = state_name_to_code.get(state_from_normalized.lower())
        
        # If country_code is missing, try phone-based inference first (fast, free, reliable)
        if not country_code:
            phone = business.get("phone") or raw_data.get("phone")
            phone_country = infer_country_from_phone(phone)
            if phone_country:
                logger.info(
                    f"📞 Country inferred from phone {phone!r} → {phone_country} "
                    f"(business: {business.get('name')})"
                )
                country_code = phone_country
                # Write back so downstream code (including callers) can use it
                business["country"] = phone_country
            else:
                logger.debug(f"⚠️  country_code is None/empty and phone gave no signal, falling back to state validation")

        # **ENHANCED**: If country_code is still missing after phone inference, use state validation
        if not country_code:
            # If we have a target state and the state matches, assume it's the right country
            if target_state and state_code:
                if state_code.upper() == target_state.upper():
                    logger.debug(f"✅ State code matches ({state_code} == {target_state})")
                    return True, ["Geo-targeting validated via state code match"]
            
            # If state_code didn't match, try state name matching
            if target_state and state_from_normalized:
                # Map target state code to possible names
                state_name_map = {
                    "CA": ["california", "ca"],
                    "TX": ["texas", "tx"],
                    "NY": ["new york", "ny"],
                    "FL": ["florida", "fl"],
                    # More states handled above in state_name_to_code
                }
                target_state_names = state_name_map.get(target_state.upper(), [target_state.lower()])
                state_normalized = state_from_normalized.lower()
                
                # Check if state name matches target
                if state_normalized in target_state_names or any(name in state_normalized for name in target_state_names):
                    logger.debug(f"✅ State name matches ({state_from_normalized})")
                    return True, ["Geo-targeting validated via state name match"]
                
                # Also check if target state name is in the state field
                if target_state.lower() in state_normalized:
                    logger.debug(f"✅ Target state found in state field")
                    return True, ["Geo-targeting validated via state substring match"]
            
            # Nothing matched — reject
            reasons.append(f"Country missing and state mismatch: state_code={state_code}, state_name={state_from_normalized}, target={target_state}")
            logger.warning(f"❌ Geo-validation failed: {reasons[0]}")
            return False, reasons
        
        # Normal validation: country_code is present
        # Normalize country codes (handle "US" vs "USA" vs "United States")
        country_normalized = country_code.upper() if country_code else ""
        target_country_normalized = target_country.upper() if target_country else ""
        
        # Map variations
        country_code_map = {
            "US": ["US", "USA", "UNITED STATES"],
            "CA": ["CA", "CAN", "CANADA"],
            "GB": ["GB", "UK", "UNITED KINGDOM"],
            "AU": ["AU", "AUS", "AUSTRALIA"]
        }
        
        target_variants = country_code_map.get(target_country_normalized, [target_country_normalized])
        
        if country_normalized not in target_variants:
            reasons.append(f"Country mismatch: {country_code} != {target_country}")
            logger.warning(f"❌ Country mismatch: {country_code} != {target_country}")
            return False, reasons
        
        logger.debug(f"✅ Country validated: {country_code}")
        
        # Check state code (if provided)
        if target_state and state_code:
            if state_code.upper() != target_state.upper():
                reasons.append(f"State mismatch: {state_code} != {target_state}")
                logger.debug(f"⚠️  State mismatch: {state_code} != {target_state}")
                if self.strict_geo_filter:
                    return False, reasons
        
        # Check city (less reliable due to spelling variations)
        if target_city:
            city_from_data = business.get("city") or raw_data.get("city", "")
            city_normalized = city_from_data.lower() if city_from_data else ""
            target_city_normalized = target_city.lower()
            
            if target_city_normalized not in city_normalized and city_normalized not in target_city_normalized:
                reasons.append(f"City mismatch: {city_from_data} != {target_city}")
                logger.debug(f"⚠️  City mismatch: {city_from_data} != {target_city}")
                # Don't fail on city mismatch (metro areas have many cities)
        
        logger.debug(f"✅ Geo-targeting fully validated")
        return True, ["Geo-targeting validated"]
    
    def detect_website(self, business: Dict[str, Any]) -> Dict[str, Any]:
        """
        Multi-tier website detection strategy.
        
        Checks multiple fields to determine if business has an online presence:
        1. website field (primary)
        2. booking_appointment_link (alternative)
        3. order_links (alternative for restaurants/retail)
        
        Args:
            business: Raw Outscraper business data
            
        Returns:
            Dict with:
                - has_website: bool
                - website_url: str or None
                - website_type: "website" | "booking" | "ordering" | "none"
                - confidence: float (0-1)
        """
        raw_data = business.get("raw_data", {})
        
        logger.debug(f"🔍 Website detection - raw_data has {len(raw_data)} keys")
        
        # Primary: Check website field
        website = raw_data.get("website")
        logger.debug(f"  ├─ website field: {website}")
        if website and isinstance(website, str) and len(website) > 10:
            logger.debug(f"  └─ ✅ Found website (primary): {website}")
            return {
                "has_website": True,
                "website_url": website,
                "website_type": "website",
                "confidence": 1.0
            }
        
        # Secondary: Check booking link (some businesses only have this)
        booking_link = raw_data.get("booking_appointment_link")
        logger.debug(f"  ├─ booking_appointment_link field: {booking_link}")
        if booking_link and isinstance(booking_link, str):
            logger.debug(f"  └─ ✅ Found booking link (secondary): {booking_link}")
            return {
                "has_website": True,
                "website_url": booking_link,
                "website_type": "booking",
                "confidence": 0.8
            }
        
        # Tertiary: Check order links (restaurants/retail)
        order_links = raw_data.get("order_links")
        logger.debug(f"  ├─ order_links field: {order_links}")
        if order_links:
            if isinstance(order_links, list) and len(order_links) > 0:
                logger.debug(f"  └─ ✅ Found order link (tertiary): {order_links[0]}")
                return {
                    "has_website": True,
                    "website_url": order_links[0],
                    "website_type": "ordering",
                    "confidence": 0.7
                }
            elif isinstance(order_links, str):
                logger.debug(f"  └─ ✅ Found order link (tertiary): {order_links}")
                return {
                    "has_website": True,
                    "website_url": order_links,
                    "website_type": "ordering",
                    "confidence": 0.7
                }
        
        # No online presence found
        logger.debug(f"  └─ ❌ No website found in any field")
        return {
            "has_website": False,
            "website_url": None,
            "website_type": "none",
            "confidence": 1.0  # High confidence they have NO website
        }
    
    def calculate_quality_score(self, business: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive business quality score.
        
        Scoring factors (0-100 total):
        - Verification status (0-15 points)
        - Operational status (0-10 points)
        - Review quality (0-25 points)
        - Review quantity (0-20 points)
        - Engagement (photos, description) (0-15 points)
        - Data completeness (0-15 points)
        
        Args:
            business: Raw Outscraper business data
            
        Returns:
            Dict with score, breakdown, and recommendations
        """
        raw_data = business.get("raw_data", {})
        score = 0.0
        breakdown = {}
        
        logger.debug(f"🎯 Quality scoring - raw_data has {len(raw_data)} keys")
        
        # 1. Verification (0-15 points)
        verified = raw_data.get("verified", False)
        verification_score = 15 if verified else 0
        score += verification_score
        breakdown["verification"] = verification_score
        logger.debug(f"  ├─ Verification: {verification_score} pts (verified={verified})")
        
        # 2. Operational Status (0-10 points)
        business_status = raw_data.get("business_status", "").upper()
        if business_status == "OPERATIONAL":
            operational_score = 10
        elif business_status in self.EXCLUDED_STATUSES:
            operational_score = 0
        else:
            operational_score = 5  # Unknown status
        score += operational_score
        breakdown["operational"] = operational_score
        logger.debug(f"  ├─ Operational: {operational_score} pts (status={business_status})")
        
        # 3. Review Quality (0-25 points) - based on rating and distribution
        rating = raw_data.get("rating")
        reviews_per_score = raw_data.get("reviews_per_score", {})
        
        if rating:
            # Base rating score (0-20)
            rating_score = (rating / 5.0) * 20
            
            # Bonus for high % of 5-star reviews (0-5)
            if reviews_per_score:
                total_reviews = sum(reviews_per_score.values())
                five_star = reviews_per_score.get("5", 0)
                if total_reviews > 0:
                    five_star_pct = five_star / total_reviews
                    rating_score += five_star_pct * 5
            
            score += rating_score
            breakdown["review_quality"] = rating_score
        else:
            breakdown["review_quality"] = 0
        
        # 4. Review Quantity (0-20 points)
        review_count = raw_data.get("reviews", 0)
        if review_count:
            # Logarithmic scale: 10 reviews = 10 pts, 100 reviews = 16 pts, 500+ = 20 pts
            import math
            review_quantity_score = min(20, 10 + math.log10(review_count) * 5)
            score += review_quantity_score
            breakdown["review_quantity"] = review_quantity_score
        else:
            breakdown["review_quantity"] = 0
        
        # 5. Engagement (0-15 points)
        engagement_score = 0
        
        # Photos (0-8 points)
        photos_count = raw_data.get("photos_count", 0)
        if photos_count:
            engagement_score += min(8, photos_count / 20)  # 160+ photos = max
        
        # Description (0-5 points)
        description = raw_data.get("description")
        if description and len(str(description)) > 50:
            engagement_score += 5
        
        # Working hours (0-2 points)
        working_hours = raw_data.get("working_hours")
        if working_hours:
            engagement_score += 2
        
        score += engagement_score
        breakdown["engagement"] = engagement_score
        
        # 6. Data Completeness (0-15 points)
        completeness_score = 0
        required_fields = [
            "phone", "address", "city", "state_code", "postal_code",
            "category", "latitude", "longitude"
        ]
        filled_fields = sum(1 for field in required_fields if raw_data.get(field))
        completeness_score = (filled_fields / len(required_fields)) * 15
        
        score += completeness_score
        breakdown["completeness"] = completeness_score
        
        final_score = round(score, 2)
        logger.debug(f"  └─ FINAL SCORE: {final_score} pts")
        
        return {
            "score": final_score,
            "breakdown": breakdown,
            "verified": verified,
            "operational": business_status == "OPERATIONAL",
            "high_quality": score >= 70,
            "medium_quality": 50 <= score < 70,
            "low_quality": score < 50
        }
    
    def should_generate_website(self, business: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine if we should generate a website for this business.
        
        Criteria:
        1. No existing website (all detection methods failed)
        2. Business is operational
        3. Business meets minimum quality threshold
        4. Business is verified (preferred)
        
        Args:
            business: Raw Outscraper business data
            
        Returns:
            Dict with recommendation and reasoning
        """
        # Check website detection
        website_info = self.detect_website(business)
        
        if website_info["has_website"]:
            return {
                "should_generate": False,
                "reason": f"Business has {website_info['website_type']}: {website_info['website_url']}",
                "confidence": website_info["confidence"]
            }
        
        # Check quality score
        quality_info = self.calculate_quality_score(business)
        
        if quality_info["score"] < self.min_quality_score:
            return {
                "should_generate": False,
                "reason": f"Quality score too low: {quality_info['score']} < {self.min_quality_score}",
                "confidence": 0.9,
                "quality_score": quality_info["score"]
            }
        
        if not quality_info["operational"]:
            return {
                "should_generate": False,
                "reason": "Business not operational",
                "confidence": 1.0
            }
        
        # Recommend generation
        return {
            "should_generate": True,
            "reason": "No website found, business is operational and high quality",
            "confidence": website_info["confidence"],
            "quality_score": quality_info["score"],
            "priority": "high" if quality_info["verified"] else "medium"
        }
    
    def filter_and_score_results(
        self,
        businesses: List[Dict[str, Any]],
        target_country: str,
        target_state: Optional[str] = None,
        target_city: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Filter and score a batch of Outscraper results.
        
        Args:
            businesses: List of raw Outscraper business data
            target_country: Target country code
            target_state: Target state code (optional)
            target_city: Target city name (optional)
            
        Returns:
            Dict with filtered businesses, statistics, and recommendations
        """
        results = {
            "total_received": len(businesses),
            "filtered_businesses": [],
            "excluded_businesses": [],
            "statistics": {
                "geo_filtered": 0,
                "quality_filtered": 0,
                "closed_filtered": 0,
                "passed": 0
            },
            "generation_candidates": []
        }
        
        for business in businesses:
            # Geo-validation
            geo_valid, geo_reasons = self.validate_geo_targeting(
                business, target_country, target_state, target_city
            )
            
            if not geo_valid:
                results["excluded_businesses"].append({
                    "business": business,
                    "reason": "geo_filter",
                    "details": geo_reasons
                })
                results["statistics"]["geo_filtered"] += 1
                logger.warning(f"Geo-filtered: {business.get('name')} - {geo_reasons}")
                continue
            
            # Calculate quality score
            quality_info = self.calculate_quality_score(business)
            business["quality_score"] = quality_info["score"]
            business["quality_breakdown"] = quality_info["breakdown"]
            
            # Check operational status
            if self.require_operational and not quality_info["operational"]:
                results["excluded_businesses"].append({
                    "business": business,
                    "reason": "not_operational",
                    "details": ["Business is closed or not operational"]
                })
                results["statistics"]["closed_filtered"] += 1
                continue
            
            # Check quality threshold
            if quality_info["score"] < self.min_quality_score:
                results["excluded_businesses"].append({
                    "business": business,
                    "reason": "low_quality",
                    "details": [f"Score {quality_info['score']} < {self.min_quality_score}"]
                })
                results["statistics"]["quality_filtered"] += 1
                continue
            
            # Passed all filters
            results["filtered_businesses"].append(business)
            results["statistics"]["passed"] += 1
            
            # Check if generation candidate
            generation_rec = self.should_generate_website(business)
            if generation_rec["should_generate"]:
                results["generation_candidates"].append({
                    "business": business,
                    "recommendation": generation_rec
                })
        
        # Add summary
        results["summary"] = {
            "pass_rate": results["statistics"]["passed"] / max(1, results["total_received"]) * 100,
            "geo_filter_rate": results["statistics"]["geo_filtered"] / max(1, results["total_received"]) * 100,
            "generation_candidates_count": len(results["generation_candidates"]),
            "generation_rate": len(results["generation_candidates"]) / max(1, results["statistics"]["passed"]) * 100
        }
        
        logger.info(f"Filtered {results['total_received']} businesses:")
        logger.info(f"  ✅ Passed: {results['statistics']['passed']}")
        logger.info(f"  🌍 Geo-filtered: {results['statistics']['geo_filtered']}")
        logger.info(f"  📊 Quality-filtered: {results['statistics']['quality_filtered']}")
        logger.info(f"  🚫 Closed: {results['statistics']['closed_filtered']}")
        logger.info(f"  🎯 Generation candidates: {len(results['generation_candidates'])}")
        
        return results

