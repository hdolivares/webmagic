"""
LLM-Powered Website Discovery Service.

Uses LLM to intelligently analyze Google Search results and cross-reference
with business data (phone, address, name) to find the correct website.

Best Practices:
- Saves all ScrapingDog responses for debugging and improvement
- Uses LLM for intelligent decision-making (no hardcoded regex)
- Provides detailed reasoning for each decision
- Handles edge cases (franchises, aggregators, PDFs, etc.)
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from anthropic import AsyncAnthropic
from core.config import get_settings
from services.hunter.google_search_service import GoogleSearchService
from services.system_settings_service import SystemSettingsService

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMDiscoveryService:
    """
    Service that uses LLM to analyze Google Search results and find business websites.
    
    Pipeline:
    1. Query ScrapingDog for business
    2. Pass results + business data to LLM
    3. LLM analyzes and picks best match (or determines no match)
    4. Save all data for transparency
    """
    
    def __init__(self):
        """Initialize the LLM Discovery Service."""
        self.google_service = GoogleSearchService()
        self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = None
    
    async def _get_llm_model(self) -> str:
        """Get the LLM model for validation from database settings."""
        if self._model:
            return self._model
        
        try:
            # Try to get from database settings first
            from core.database import get_db_session_sync
            
            with get_db_session_sync() as db:
                from models.system_setting import SystemSetting
                
                validation_model_setting = db.query(SystemSetting).filter(
                    SystemSetting.key == "llm_validation_model"
                ).first()
                
                if validation_model_setting and validation_model_setting.value:
                    self._model = validation_model_setting.value
                    logger.info(f"Using validation model from database: {self._model}")
                    return self._model
        except Exception as e:
            logger.warning(f"Could not load validation model from database: {e}")
        
        # Fallback to Haiku for cost-effective discovery
        self._model = "claude-3-haiku-20240307"
        logger.info(f"Using default validation model: {self._model}")
        return self._model
    
    async def discover_website(
        self,
        business_name: str,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: str = "US"
    ) -> Dict[str, Any]:
        """
        Discover business website using LLM-powered analysis of Google Search results.
        
        Args:
            business_name: Name of the business
            phone: Business phone number (for cross-referencing)
            address: Business address (for cross-referencing)
            city: City location
            state: State location
            country: Country code
            
        Returns:
            Dict with:
                - url: Found website URL (or None)
                - found: Boolean indicating if website was found
                - confidence: Confidence score (0.0-1.0)
                - reasoning: LLM's explanation
                - search_results: Raw ScrapingDog response
                - query: Search query used
                - llm_analysis: Full LLM response
        """
        # Step 1: Get ScrapingDog results
        logger.info(f"🔍 Discovering website for: {business_name}")
        
        search_results = await self._get_search_results(
            business_name=business_name,
            city=city,
            state=state,
            country=country
        )
        
        if not search_results or not search_results.get("organic_results"):
            logger.info(f"❌ No search results found for {business_name}")
            return {
                "url": None,
                "found": False,
                "confidence": 0.95,
                "reasoning": "No Google search results found",
                "search_results": search_results,
                "query": self._build_query(business_name, city, state),
                "llm_analysis": None
            }
        
        # Step 2: Use LLM to analyze results
        logger.info(f"🤖 Analyzing {len(search_results['organic_results'])} search results with LLM...")
        
        llm_analysis = await self._analyze_with_llm(
            business_name=business_name,
            phone=phone,
            address=address,
            city=city,
            state=state,
            search_results=search_results["organic_results"]
        )
        
        found_url = llm_analysis.get("url")
        
        if found_url:
            logger.info(f"✅ Found website: {found_url} (confidence: {llm_analysis.get('confidence', 0)})")
        else:
            logger.info(f"❌ No matching website found")
        
        return {
            "url": found_url,
            "found": bool(found_url),
            "confidence": llm_analysis.get("confidence", 0),
            "reasoning": llm_analysis.get("reasoning", ""),
            "search_results": search_results,
            "query": self._build_query(business_name, city, state),
            "llm_analysis": llm_analysis,
            "llm_model": await self._get_llm_model()
        }
    
    async def _get_search_results(
        self,
        business_name: str,
        city: Optional[str],
        state: Optional[str],
        country: str
    ) -> Optional[Dict]:
        """Get raw search results from ScrapingDog."""
        if not self.google_service.api_key:
            logger.error("ScrapingDog API key not configured")
            return None
        
        # Build query
        query = self._build_query(business_name, city, state)
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                params = {
                    "api_key": self.google_service.api_key,
                    "query": query,
                    "results": 10,
                    "country": country.lower(),
                }
                
                async with session.get(
                    self.google_service.base_url,
                    params=params,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        logger.error(f"ScrapingDog API error: {response.status}")
                        text = await response.text()
                        logger.error(f"Response: {text}")
                        return None
                    
                    data = await response.json()
                    return data
                    
        except Exception as e:
            logger.error(f"Error fetching search results: {type(e).__name__}: {e}")
            return None
    
    def _build_query(self, business_name: str, city: Optional[str], state: Optional[str]) -> str:
        """Build search query for ScrapingDog."""
        query_parts = [f'"{business_name}"']
        if city:
            query_parts.append(city)
        if state:
            query_parts.append(state)
        query_parts.append("website")
        return " ".join(query_parts)
    
    async def _analyze_with_llm(
        self,
        business_name: str,
        phone: Optional[str],
        address: Optional[str],
        city: Optional[str],
        state: Optional[str],
        search_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze search results and find the best matching website.
        
        Args:
            business_name: Name of the business
            phone: Business phone number
            address: Business address
            city: City
            state: State
            search_results: List of organic search results from ScrapingDog
            
        Returns:
            Dict with url, confidence, reasoning, match_signals
        """
        # Prepare business context
        business_context = {
            "name": business_name,
            "phone": phone,
            "address": address,
            "city": city,
            "state": state
        }
        
        # Prepare search results for LLM
        formatted_results = []
        for i, result in enumerate(search_results[:10], 1):
            formatted_results.append({
                "rank": i,
                "title": result.get("title", ""),
                "url": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "displayed_link": result.get("displayed_link", "")
            })
        
        # Build LLM prompt
        prompt = self._build_discovery_prompt(business_context, formatted_results)
        
        try:
            model = await self._get_llm_model()
            
            response = await self.anthropic_client.messages.create(
                model=model,
                max_tokens=2000,
                temperature=0,
                system="""You are a business website discovery expert. Your job is to analyze Google search results and determine which URL (if any) is the official website for a specific business.

You must cross-reference the business information (phone, address, name) with the search result snippets to make an accurate determination.

Be cautious of:
- Franchise/aggregator sites (e.g., nationwide franchise page instead of local business)
- Directory listings (Yelp, BBB, etc. - these are NOT business websites)
- Member directories (Chamber of Commerce listings)
- Booking platforms (third-party scheduling sites)
- PDF files

Return your analysis in valid JSON format only.""",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse LLM response
            response_text = response.content[0].text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            
            llm_result = json.loads(response_text)
            
            logger.info(f"LLM analysis complete: {llm_result.get('verdict', 'unknown')}")
            
            return {
                "url": llm_result.get("url"),
                "confidence": llm_result.get("confidence", 0),
                "reasoning": llm_result.get("reasoning", ""),
                "match_signals": llm_result.get("match_signals", {}),
                "llm_model": model,
                "llm_tokens": response.usage.input_tokens + response.usage.output_tokens,
                "llm_raw_response": response_text
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Raw response: {response_text}")
            return {
                "url": None,
                "confidence": 0,
                "reasoning": f"LLM response parse error: {str(e)}",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"LLM analysis failed: {type(e).__name__}: {e}")
            return {
                "url": None,
                "confidence": 0,
                "reasoning": f"LLM analysis error: {str(e)}",
                "error": str(e)
            }
    
    def _build_discovery_prompt(
        self,
        business: Dict[str, Any],
        search_results: List[Dict]
    ) -> str:
        """Build the LLM prompt for website discovery."""
        
        prompt = f"""Analyze these Google search results to find the official website for this business.

**BUSINESS INFORMATION:**
- Name: {business['name']}
- Phone: {business.get('phone') or 'Not provided'}
- Address: {business.get('address') or 'Not provided'}
- City: {business.get('city') or 'Not provided'}
- State: {business.get('state') or 'Not provided'}

**GOOGLE SEARCH RESULTS (Top 10):**

"""
        
        for result in search_results:
            prompt += f"""
Result #{result['rank']}:
  Title: {result['title']}
  URL: {result['url']}
  Snippet: {result['snippet']}
  Displayed Link: {result['displayed_link']}
---
"""
        
        prompt += """

**YOUR TASK:**

Analyze ALL 10 results and determine which URL (if any) is the official website for this specific business location.

**CROSS-REFERENCING INSTRUCTIONS:**

1. **Phone Number Matching (HIGHEST PRIORITY):**
   - Check if the business phone appears in ANY snippet
   - Phone match = HIGH confidence this is the correct website
   
2. **Address Matching:**
   - Check if the full address or partial address appears in snippets
   - Exact address match = HIGH confidence
   
3. **Business Name Matching:**
   - Match the business name (accounting for variations)
   - Name alone is NOT sufficient (many businesses have similar names)

4. **Exclude These:**
   - Directory sites (Yelp, BBB, YellowPages, etc.)
   - Franchise aggregator pages (unless phone/address match)
   - Member directories (Chamber of Commerce listings)
   - Booking platforms (OpenTable, Resy, etc.)
   - PDF files
   - LinkedIn company pages

5. **Franchise Businesses:**
   - If it's a franchise (e.g., "Mr. Rooter of Seattle"), the local franchise page IS valid
   - Verify by checking if phone/address in snippet matches business data

**DECISION CRITERIA:**

- **Found & High Confidence (0.8-1.0):** Phone or address match in snippet
- **Found & Medium Confidence (0.5-0.7):** Business name + city/state match, no phone/address
- **Not Found:** No results match, or only directories found

**OUTPUT FORMAT (JSON only):**

{
  "url": "https://example.com" or null,
  "confidence": 0.95,
  "reasoning": "Phone number (XXX) XXX-XXXX from business data matches snippet in Result #2, confirming this is the correct website",
  "match_signals": {
    "phone_match": true,
    "address_match": false,
    "name_match": true,
    "location_match": true,
    "result_rank": 2
  }
}

**IMPORTANT:** Return ONLY valid JSON. No markdown, no explanation outside the JSON.
"""
        
        return prompt


async def test_llm_discovery():
    """Test the LLM discovery service."""
    service = LLMDiscoveryService()
    
    # Test with a known business
    result = await service.discover_website(
        business_name="Mr. Rooter Plumbing of Seattle",
        phone="(206) 866-2836",
        address="2000 S 116th St",
        city="Seattle",
        state="WA"
    )
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_llm_discovery())
