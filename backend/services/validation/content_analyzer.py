"""
Content analysis service for website validation.
Extracts business information, contact details, and quality metrics.
"""
import re
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """
    Analyzes web page content to extract business information.
    """
    
    # Phone number patterns (US, UK, International)
    PHONE_PATTERNS = [
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # US: 123-456-7890
        r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',      # US: (123) 456-7890
        r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International
        r'\+44\s?\d{4}\s?\d{6}',                # UK
        r'0\d{4}\s?\d{6}',                      # UK Local
    ]
    
    # Email pattern
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Address indicators
    ADDRESS_KEYWORDS = [
        'address', 'location', 'street', 'avenue', 'road', 'suite', 
        'floor', 'building', 'office', 'headquarters', 'visit us'
    ]
    
    # Business hours indicators
    HOURS_KEYWORDS = [
        'hours', 'open', 'closed', 'monday', 'tuesday', 'wednesday',
        'thursday', 'friday', 'saturday', 'sunday', 'am', 'pm'
    ]
    
    async def analyze_page(self, page: Page) -> Dict[str, Any]:
        """
        Analyze a web page and extract business information.
        
        Args:
            page: Playwright page object
            
        Returns:
            Dictionary containing extracted information
        """
        try:
            # Extract basic page info
            title = await self._get_title(page)
            meta_description = await self._get_meta_description(page)
            
            # Get page content
            content_html = await page.content()
            content_text = await self._get_text_content(page)
            
            # Extract contact information
            phones = self._extract_phones(content_text)
            emails = self._extract_emails(content_text)
            has_address = self._detect_address(content_text)
            has_hours = self._detect_hours(content_text)
            
            # Analyze content quality
            word_count = len(content_text.split())
            has_images = await self._has_images(page)
            has_forms = await self._has_forms(page)
            
            # Check for social media links
            social_links = await self._extract_social_links(page)
            
            # Detect if it's a real business site vs placeholder
            is_placeholder = self._is_placeholder_site(title, content_text)
            
            return {
                "title": title,
                "meta_description": meta_description,
                "phones": phones,
                "emails": emails,
                "has_phone": len(phones) > 0,
                "has_email": len(emails) > 0,
                "has_address": has_address,
                "has_hours": has_hours,
                "has_contact_info": len(phones) > 0 or len(emails) > 0 or has_address,
                "word_count": word_count,
                "content_length": len(content_html),
                "content_preview": content_text[:500] if content_text else None,
                "has_images": has_images,
                "has_forms": has_forms,
                "social_links": social_links,
                "is_placeholder": is_placeholder,
                "quality_score": self._calculate_quality_score({
                    "has_phone": len(phones) > 0,
                    "has_email": len(emails) > 0,
                    "has_address": has_address,
                    "has_hours": has_hours,
                    "word_count": word_count,
                    "has_images": has_images,
                    "has_forms": has_forms,
                    "is_placeholder": is_placeholder,
                })
            }
            
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            return {
                "title": None,
                "meta_description": None,
                "phones": [],
                "emails": [],
                "has_phone": False,
                "has_email": False,
                "has_address": False,
                "has_hours": False,
                "has_contact_info": False,
                "word_count": 0,
                "content_length": 0,
                "content_preview": None,
                "has_images": False,
                "has_forms": False,
                "social_links": [],
                "is_placeholder": True,
                "quality_score": 0,
                "error": str(e)
            }
    
    async def _get_title(self, page: Page) -> Optional[str]:
        """Extract page title."""
        try:
            return await page.title()
        except Exception:
            return None
    
    async def _get_meta_description(self, page: Page) -> Optional[str]:
        """Extract meta description."""
        try:
            return await page.evaluate("""
                () => {
                    const meta = document.querySelector('meta[name="description"]');
                    return meta ? meta.content : null;
                }
            """)
        except Exception:
            return None
    
    async def _get_text_content(self, page: Page) -> str:
        """Extract visible text content."""
        try:
            return await page.evaluate('document.body.innerText')
        except Exception:
            return ""
    
    def _extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers from text."""
        phones = []
        for pattern in self.PHONE_PATTERNS:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        
        # Deduplicate and clean
        phones = list(set(phones))
        return phones[:5]  # Limit to first 5 unique numbers
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text."""
        emails = re.findall(self.EMAIL_PATTERN, text)
        
        # Filter out common false positives
        emails = [
            email for email in emails
            if not any(fp in email.lower() for fp in ['example.com', 'test.com', 'domain.com'])
        ]
        
        # Deduplicate
        emails = list(set(emails))
        return emails[:5]  # Limit to first 5 unique emails
    
    def _detect_address(self, text: str) -> bool:
        """Detect if page contains address information."""
        text_lower = text.lower()
        
        # Check for address keywords
        keyword_matches = sum(1 for keyword in self.ADDRESS_KEYWORDS if keyword in text_lower)
        
        # Check for zip code patterns
        zip_pattern = r'\b\d{5}(?:-\d{4})?\b'  # US zip codes
        has_zip = bool(re.search(zip_pattern, text))
        
        # Require at least 2 address keywords or 1 keyword + zip code
        return keyword_matches >= 2 or (keyword_matches >= 1 and has_zip)
    
    def _detect_hours(self, text: str) -> bool:
        """Detect if page contains business hours."""
        text_lower = text.lower()
        
        # Check for hours keywords
        keyword_matches = sum(1 for keyword in self.HOURS_KEYWORDS if keyword in text_lower)
        
        # Require at least 3 matches (e.g., "hours", "monday", "am")
        return keyword_matches >= 3
    
    async def _has_images(self, page: Page) -> bool:
        """Check if page has images."""
        try:
            image_count = await page.evaluate('document.querySelectorAll("img").length')
            return image_count > 0
        except Exception:
            return False
    
    async def _has_forms(self, page: Page) -> bool:
        """Check if page has forms (contact forms)."""
        try:
            form_count = await page.evaluate('document.querySelectorAll("form").length')
            return form_count > 0
        except Exception:
            return False
    
    async def _extract_social_links(self, page: Page) -> List[str]:
        """Extract social media links."""
        try:
            links = await page.evaluate("""
                () => {
                    const socialDomains = ['facebook.com', 'twitter.com', 'instagram.com', 
                                          'linkedin.com', 'youtube.com', 'tiktok.com'];
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    const socialLinks = links
                        .map(a => a.href)
                        .filter(href => socialDomains.some(domain => href.includes(domain)));
                    return [...new Set(socialLinks)];  // Deduplicate
                }
            """)
            return links[:10]  # Limit to 10
        except Exception:
            return []
    
    def _is_placeholder_site(self, title: Optional[str], content: str) -> bool:
        """
        Detect if site is a placeholder/coming soon page.
        """
        if not title and len(content) < 100:
            return True
        
        placeholder_phrases = [
            'coming soon',
            'under construction',
            'site under development',
            'page not found',
            '404',
            'domain for sale',
            'parked domain',
            'this domain is',
            'default web page',
            'it works!',
            'apache',
            'nginx',
        ]
        
        content_lower = content.lower() if content else ""
        title_lower = title.lower() if title else ""
        
        # Check if any placeholder phrase exists
        for phrase in placeholder_phrases:
            if phrase in content_lower or phrase in title_lower:
                return True
        
        # Check if content is too short
        if len(content.split()) < 50:
            return True
        
        return False
    
    def _calculate_quality_score(self, metrics: Dict[str, Any]) -> int:
        """
        Calculate a quality score (0-100) based on extracted metrics.
        
        Scoring:
        - Has phone: +20
        - Has email: +15
        - Has address: +15
        - Has hours: +10
        - Word count > 200: +15
        - Has images: +10
        - Has forms: +10
        - Not placeholder: +5
        """
        score = 0
        
        if metrics.get("has_phone"):
            score += 20
        if metrics.get("has_email"):
            score += 15
        if metrics.get("has_address"):
            score += 15
        if metrics.get("has_hours"):
            score += 10
        if metrics.get("word_count", 0) > 200:
            score += 15
        if metrics.get("has_images"):
            score += 10
        if metrics.get("has_forms"):
            score += 10
        if not metrics.get("is_placeholder"):
            score += 5
        
        return min(score, 100)  # Cap at 100

