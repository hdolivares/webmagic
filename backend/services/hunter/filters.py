"""
Lead qualification and filtering logic.
"""
from typing import List, Dict, Any, Optional
import re
import logging

logger = logging.getLogger(__name__)


class LeadQualifier:
    """
    Qualify and score leads based on various criteria.
    
    Scoring system (0-100):
    - No website: +30 points (our primary target)
    - Has email: +25 points (can contact them)
    - High rating (4.5+): +20 points (quality business)
    - Many reviews (50+): +15 points (established business)
    - Local business (not chain): +10 points (better fit)
    """
    
    # Chain/franchise keywords to filter out
    CHAIN_KEYWORDS = [
        "mcdonald", "burger king", "subway", "starbucks", "wendy",
        "taco bell", "chipotle", "pizza hut", "domino", "papa john",
        "walmart", "target", "cvs", "walgreens", "kroger", "safeway",
        "marriott", "hilton", "holiday inn", "best western", "motel 6",
        "hertz", "enterprise", "budget", "avis", "national",
        "shell", "exxon", "chevron", "bp", "mobil",
        "home depot", "lowe", "ace hardware", "harbor freight",
        "petsmart", "petco", "bed bath", "bath & body works"
    ]
    
    # Email patterns to extract from text
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    def __init__(
        self,
        min_score: int = 50,
        require_no_website: bool = True,
        require_email: bool = False
    ):
        """
        Initialize lead qualifier.
        
        Args:
            min_score: Minimum score to qualify (0-100)
            require_no_website: Only qualify businesses without websites
            require_email: Only qualify businesses with email addresses
        """
        self.min_score = min_score
        self.require_no_website = require_no_website
        self.require_email = require_email
    
    def qualify(self, business: Dict[str, Any]) -> Dict[str, Any]:
        """
        Qualify a single business and return score with reasons.
        
        Args:
            business: Business dictionary
            
        Returns:
            Dictionary with "qualified", "score", and "reasons"
        """
        score = 0
        reasons = []
        
        # 1. Check for website (30 points)
        has_website = self._has_website(business)
        if not has_website:
            score += 30
            reasons.append("No website (30)")
        else:
            reasons.append("Has website (0)")
        
        # 2. Check for email (25 points)
        has_email = self._has_email(business)
        if has_email:
            score += 25
            reasons.append("Has email (25)")
        else:
            # Try to extract from reviews or description
            extracted_email = self._extract_email(business)
            if extracted_email:
                business["email"] = extracted_email
                score += 20
                reasons.append("Email extracted (20)")
            else:
                reasons.append("No email (0)")
        
        # 3. Check rating (20 points)
        rating = business.get("rating")
        if rating is not None and rating > 0:
            if rating >= 4.5:
                score += 20
                reasons.append(f"Excellent rating {rating} (20)")
            elif rating >= 4.0:
                score += 15
                reasons.append(f"Good rating {rating} (15)")
            elif rating >= 3.5:
                score += 10
                reasons.append(f"Decent rating {rating} (10)")
            else:
                reasons.append(f"Low rating {rating} (0)")
        else:
            reasons.append("No rating (0)")
        
        # 4. Check review count (15 points)
        review_count = business.get("review_count", 0)
        if review_count >= 100:
            score += 15
            reasons.append(f"{review_count} reviews (15)")
        elif review_count >= 50:
            score += 10
            reasons.append(f"{review_count} reviews (10)")
        elif review_count >= 20:
            score += 5
            reasons.append(f"{review_count} reviews (5)")
        else:
            reasons.append(f"{review_count} reviews (0)")
        
        # 5. Check if local business (10 points)
        is_local = not self._is_chain(business)
        if is_local:
            score += 10
            reasons.append("Local business (10)")
        else:
            score += 0
            reasons.append("Chain/Franchise (0)")
            # Heavily penalize chains
            score = max(0, score - 50)
        
        # Apply hard requirements
        qualified = score >= self.min_score
        
        if self.require_no_website and has_website:
            qualified = False
            reasons.append("❌ Required: No website")
        
        if self.require_email and not has_email:
            qualified = False
            reasons.append("❌ Required: Has email")
        
        return {
            "qualified": qualified,
            "score": score,
            "reasons": reasons,
            "has_website": has_website,
            "has_email": has_email or bool(self._extract_email(business)),
            "is_chain": not is_local
        }
    
    def filter_batch(
        self,
        businesses: List[Dict[str, Any]],
        update_in_place: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Filter a batch of businesses, keeping only qualified ones.
        
        Args:
            businesses: List of business dictionaries
            update_in_place: If True, adds "qualification_score" to each business dict
            
        Returns:
            List of qualified businesses
        """
        qualified = []
        
        for business in businesses:
            result = self.qualify(business)
            
            if update_in_place:
                business["qualification_score"] = result["score"]
                business["qualification_reasons"] = result["reasons"]
            
            if result["qualified"]:
                qualified.append(business)
        
        logger.info(
            f"Qualified {len(qualified)}/{len(businesses)} businesses "
            f"({len(qualified)/len(businesses)*100:.1f}%)"
        )
        
        return qualified
    
    def _has_website(self, business: Dict[str, Any]) -> bool:
        """
        Check if business has a valid, working website.
        
        Checks website_status if available (from website validation).
        Falls back to URL pattern checking if not validated yet.
        """
        # Check validation status if available
        website_status = business.get("website_status")
        if website_status == "valid":
            return True  # Has valid website
        elif website_status == "invalid":
            return False  # Website is invalid/unreachable
        
        # Check has_valid_website flag if set
        has_valid = business.get("has_valid_website")
        if has_valid is not None:
            return has_valid
        
        # Fall back to URL pattern checking (pre-validation)
        website = business.get("website_url") or ""  # Handle None values
        if not website:
            return False
        
        # Clean and validate
        website = website.strip().lower()
        
        # Ignore common non-website URLs
        ignore_patterns = [
            "facebook.com",
            "instagram.com",
            "twitter.com",
            "linkedin.com",
            "yelp.com",
            "google.com",
            "maps.google.com",
            "plus.google.com",
            "goo.gl",
            "g.page"
        ]
        
        for pattern in ignore_patterns:
            if pattern in website:
                return False
        
        return True
    
    def _has_email(self, business: Dict[str, Any]) -> bool:
        """Check if business has an email."""
        email = business.get("email", "")
        return bool(email and "@" in email)
    
    def _is_chain(self, business: Dict[str, Any]) -> bool:
        """Check if business is a chain/franchise."""
        name = (business.get("name") or "").lower()  # Handle None values
        
        for keyword in self.CHAIN_KEYWORDS:
            if keyword in name:
                logger.debug(f"Identified chain: {name}")
                return True
        
        return False
    
    def _extract_email(self, business: Dict[str, Any]) -> Optional[str]:
        """
        Try to extract email from reviews or other text fields.
        
        Args:
            business: Business dictionary
            
        Returns:
            Email string or None
        """
        # Check reviews
        reviews_data = business.get("reviews_data", [])
        if reviews_data:
            for review in reviews_data:
                text = review.get("text") or ""  # Handle None values
                if text:
                    matches = self.EMAIL_PATTERN.findall(text)
                    if matches:
                        return matches[0]
        
        # Check raw_data if available
        raw_data = business.get("raw_data", {})
        if raw_data:
            description = raw_data.get("description") or ""  # Handle None values
            if description:
                matches = self.EMAIL_PATTERN.findall(description)
                if matches:
                    return matches[0]
        
        return None
    
    def get_statistics(self, businesses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about a batch of businesses.
        
        Args:
            businesses: List of business dictionaries
            
        Returns:
            Statistics dictionary
        """
        total = len(businesses)
        if total == 0:
            return {
                "total": 0,
                "qualified": 0,
                "qualification_rate": 0,
                "avg_score": 0
            }
        
        scores = []
        qualified_count = 0
        
        for business in businesses:
            result = self.qualify(business)
            scores.append(result["score"])
            if result["qualified"]:
                qualified_count += 1
        
        return {
            "total": total,
            "qualified": qualified_count,
            "qualification_rate": (qualified_count / total) * 100,
            "avg_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores)
        }
