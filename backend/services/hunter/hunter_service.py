"""
Main Hunter orchestration service - coordinates scraping workflow.
Now enhanced with Claude-powered intelligent zone placement strategies.
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
import logging

from services.hunter.scraper import OutscraperClient
from services.hunter.filters import LeadQualifier
from services.hunter.business_service import BusinessService
from services.hunter.coverage_service import CoverageService
from services.hunter.geo_strategy_service import GeoStrategyService
from services.hunter.data_quality_service import DataQualityService
# Simple HTTP-based validation for initial filtering
from services.hunter.website_validator import WebsiteValidator
from services.hunter.website_generation_queue_service import WebsiteGenerationQueueService
# Deep verification with ScrapingDog + LLM
from services.discovery.llm_discovery_service import LLMDiscoveryService
# Progress tracking for real-time updates
from services.progress.redis_service import RedisService
from services.progress.progress_publisher import ProgressPublisher
from core.exceptions import ExternalAPIException
from core.config import get_settings
import asyncio

logger = logging.getLogger(__name__)


class HunterService:
    """
    Main orchestration service for the Hunter module.
    
    Now uses Claude to generate intelligent zone placement strategies
    for maximum business discovery with minimum redundancy.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        scraper: Optional[OutscraperClient] = None,
        qualifier: Optional[LeadQualifier] = None,
        progress_publisher: Optional[ProgressPublisher] = None
    ):
        """
        Initialize Hunter service.
        
        Args:
            db: Database session
            scraper: Outscraper client (creates new if None)
            qualifier: Lead qualifier (creates new if None)
            progress_publisher: Optional progress publisher for real-time updates
        """
        self.db = db
        self.scraper = scraper or OutscraperClient()
        self.qualifier = qualifier or LeadQualifier(
            min_score=50,
            require_no_website=True,
            require_email=False
        )
        self.business_service = BusinessService(db)
        self.coverage_service = CoverageService(db)
        self.geo_strategy_service = GeoStrategyService(db)
        # New Phase 2 services
        self.generation_queue_service = WebsiteGenerationQueueService(db)
        # Progress publisher for real-time updates (optional)
        self.progress_publisher = progress_publisher
    
    async def scrape_with_intelligent_strategy(
        self,
        city: str,
        state: str,
        category: str,
        country: str = "US",
        limit_per_zone: int = 50,
        population: Optional[int] = None,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        force_new_strategy: bool = False,
        zone_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape a city using Claude-generated intelligent zone placement strategy.
        
        This is the NEW recommended method that replaces scrape_location_with_zones.
        Claude analyzes the city's geography and business distribution patterns to
        place zones optimally, avoiding wasted searches and ensuring complete coverage.
        
        Args:
            city: City name
            state: State code
            category: Business category
            country: Country code
            limit_per_zone: Maximum results per zone
            population: City population (optional, helps Claude's analysis)
            center_lat: City center latitude (will geocode if not provided)
            center_lon: City center longitude (will geocode if not provided)
            force_new_strategy: Generate new strategy even if one exists
            zone_id: Specific zone to scrape (if None, scrapes next unscraped zone)
            
        Returns:
            Dictionary with results:
            {
                "strategy_id": "uuid",
                "total_zones": 18,
                "zones_scraped": 1,
                "zones_remaining": 17,
                "businesses_found": 47,
                "qualified_leads": 12,
                "zone_results": {...},
                "strategy_status": "active|completed"
            }
        """
        logger.info(f"Starting intelligent strategy scrape: {city}, {state} - {category}")
        
        # Get or create strategy using Claude
        strategy = await self.geo_strategy_service.get_or_create_strategy(
            city=city,
            state=state,
            category=category,
            country=country,
            force_regenerate=force_new_strategy,
            population=population,
            center_lat=center_lat,
            center_lon=center_lon
        )
        
        # Capture as plain string now — ORM lazy-reload after a rolled-back savepoint
        # inside the business loop would trigger a greenlet_spawn crash at line ~541.
        strategy_id = str(strategy.id)
        
        logger.info(
            f"Using strategy {strategy_id}: {strategy.total_zones} zones, "
            f"{strategy.zones_completed} already completed"
        )
        
        # Get zone to scrape (specific zone or next available)
        if zone_id:
            # Find specific zone by ID
            next_zone = next((z for z in strategy.zones if z["zone_id"] == zone_id), None)
            if not next_zone:
                logger.error(f"Zone {zone_id} not found in strategy {strategy.id}")
                raise ValueError(f"Zone {zone_id} not found in strategy")
            logger.info(f"Using specified zone: {zone_id}")
        else:
            # Get next unscraped zone
            next_zone = strategy.get_next_zone()
            if not next_zone:
                logger.info(f"Strategy {strategy.id} is complete - all zones scraped")
                return {
                    "strategy_id": str(strategy.id),
                    "status": "completed",
                    "message": "All zones in this strategy have been scraped",
                    "total_zones": strategy.total_zones,
                    "zones_completed": strategy.zones_completed,
                    "total_businesses_found": strategy.businesses_found
                }
            zone_id = next_zone["zone_id"]
        target_city = next_zone.get("city") or next_zone.get("target_city")
        zone_lat = next_zone.get("lat")  # Keep for backwards compatibility
        zone_lon = next_zone.get("lon")  # Keep for backwards compatibility
        zone_radius = next_zone.get("radius_km", 3.0)
        
        logger.info(
            f"Scraping zone {zone_id} (City: {target_city}) "
            f"priority: {next_zone.get('priority')}"
        )
        
        # Scrape the zone (now city-based, not coordinate-based)
        try:
            logger.info(f"Scraper params: target_city={target_city}, limit={limit_per_zone}")
            
            results = await self.scraper.search_businesses(
                query=category,
                city=city,  # Metro area name (e.g., "Los Angeles")
                state=state,
                country=country,
                limit=limit_per_zone,
                zone_id=zone_id,
                target_city=target_city  # Specific city to scrape (e.g., "Pasadena")
            )
            
            raw_businesses = results.get("businesses", [])
            logger.info(f"Zone {zone_id} returned {len(raw_businesses)} businesses from scraper")
            logger.debug(f"Scraper result keys: {list(results.keys())}")
            
            # **FIX: Get or create coverage FIRST so we can link businesses to it**
            # Convert floats to strings for database schema compatibility
            coverage, created = await self.coverage_service.get_or_create_coverage(
                city=city,
                state=state,
                industry=category,
                country=country,
                zone_id=zone_id,
                zone_lat=str(zone_lat) if zone_lat is not None else None,
                zone_lon=str(zone_lon) if zone_lon is not None else None,
                zone_radius_km=str(zone_radius) if zone_radius is not None else None
            )
            coverage_id = coverage.id  # Capture as plain UUID before the business loop
            logger.info(f"Coverage grid {'created' if created else 'found'}: {coverage_id}")
            
            # Process and save ALL leads (we're paying for the Outscraper call!)
            total_saved = 0
            new_businesses = 0
            businesses_with_valid_websites = 0
            businesses_needing_websites = 0
            businesses_verified_by_llm = 0
            businesses_needing_generation = []
            businesses_to_validate = []  # For async Playwright validation
            
            # Initialize data quality service for enhanced processing
            data_quality_service = DataQualityService()
            
            # Initialize deep verification service (ScrapingDog + LLM)
            llm_discovery = LLMDiscoveryService()
            
            # Rate limiting for ScrapingDog (1 request per second to avoid throttling)
            scrapingdog_delay = 1.0  # seconds between ScrapingDog requests
            
            # Simple HTTP validator for initial filtering
            async with WebsiteValidator() as website_validator:
                for idx, biz_data in enumerate(raw_businesses):
                    business_name = biz_data.get('name', 'Unknown')
                    logger.info(f"🔍 [{idx+1}/{len(raw_businesses)}] Processing: {business_name}")
                    
                    # Publish progress event (real-time updates for frontend)
                    if self.progress_publisher:
                        try:
                            self.progress_publisher.publish_business_scraped(
                                session_id=str(coverage_id),
                                business_name=business_name,
                                current=idx + 1,
                                total=len(raw_businesses)
                            )
                        except Exception as e:
                            logger.warning(f"Failed to publish progress event: {e}")
                    
                    try:
                        # **ENHANCED: Use data quality service for comprehensive analysis**
                        
                        # 1. Geo-validation (ensure business is in correct region)
                        logger.debug(f"  ├─ Running geo-validation...")
                        # NOTE: biz_data already has "raw_data" key from scraper (line 303 in scraper.py)
                        is_valid_geo, geo_reasons = data_quality_service.validate_geo_targeting(
                            business=biz_data,
                            target_country=country,
                            target_state=state
                        )
                        if not is_valid_geo:
                            logger.warning(f"  └─ ❌ Geo-validation FAILED: {', '.join(geo_reasons)}")
                            continue  # Skip businesses outside target region
                        logger.debug(f"  ├─ ✅ Geo-validation PASSED")
                        
                        # 2. Multi-tier website detection
                        logger.debug(f"  ├─ Running multi-tier website detection...")
                        try:
                            website_detection = data_quality_service.detect_website(biz_data)
                            logger.debug(f"  │  └─ Result: type={website_detection.get('website_type')}, has_website={website_detection.get('has_website')}, url={website_detection.get('website_url')}")
                            biz_data["website_type"] = website_detection.get("website_type", "none")
                            biz_data["website_confidence"] = website_detection.get("confidence", 0.0)
                        except Exception as e:
                            logger.error(f"  │  └─ ❌ Website detection ERROR: {e}", exc_info=True)
                            biz_data["website_type"] = "none"
                            biz_data["website_confidence"] = 0.0
                            website_detection = {"has_website": False, "website_url": None}
                        
                        # 3. Quality scoring (for analytics only, NOT for generation decisions)
                        logger.debug(f"  ├─ Running quality scoring...")
                        try:
                            quality_analysis = data_quality_service.calculate_quality_score(biz_data)
                            logger.debug(f"  │  └─ Score: {quality_analysis['score']}, Verified: {quality_analysis['verified']}, Operational: {quality_analysis['operational']}")
                            biz_data["quality_score"] = quality_analysis["score"]
                            biz_data["verified"] = quality_analysis["verified"]
                            biz_data["operational"] = quality_analysis["operational"]
                        except Exception as e:
                            logger.error(f"  │  └─ ❌ Quality scoring ERROR: {e}", exc_info=True)
                            biz_data["quality_score"] = 0.0
                            biz_data["verified"] = False
                            biz_data["operational"] = True
                            quality_analysis = {"score": 0.0, "verified": False, "operational": True}
                        
                        # 4. HTTP validation for websites (quick check only)
                        logger.debug(f"  ├─ Checking website URL...")
                        website_url = website_detection.get("website_url") or biz_data.get("website_url")
                        logger.debug(f"  │  └─ URL from detection: {website_detection.get('website_url')}, from biz_data: {biz_data.get('website_url')}")
                        
                        if website_url:
                            logger.info(f"  ├─ 🌐 Quick HTTP check: {website_url}")
                            try:
                                simple_validation = await website_validator.validate_url(website_url)
                                logger.debug(f"  │  └─ HTTP result: valid={simple_validation.is_valid}, accessible={simple_validation.is_accessible}, real_website={simple_validation.is_real_website}, status={simple_validation.status_code}")
                                
                                if simple_validation.is_valid or simple_validation.is_real_website:
                                    # HTTP check passed - keep URL and queue for Playwright
                                    biz_data["website_validation_status"] = "pending"
                                    biz_data["website_url"] = website_url
                                    logger.info(f"  │  └─ ✅ HTTP PASS → Will validate with Playwright")
                                else:
                                    # HTTP check failed - DON'T clear URL, mark for deep verification
                                    biz_data["website_validation_status"] = "needs_verification"
                                    biz_data["website_url"] = website_url  # Keep URL for ScrapingDog+LLM check
                                    logger.info(f"  │  └─ ⚠️ HTTP FAIL → Will verify with ScrapingDog+LLM")
                            except Exception as e:
                                logger.error(f"  │  └─ ❌ HTTP check ERROR: {e}")
                                biz_data["website_validation_status"] = "needs_verification"
                                biz_data["website_url"] = website_url  # Keep URL
                        else:
                            # No URL found - will search with ScrapingDog
                            biz_data["website_validation_status"] = "missing"
                            logger.info(f"  ├─ 🚫 No website URL → Will search with ScrapingDog")
                        
                        # 5. DEEP VERIFICATION with ScrapingDog + LLM (CRITICAL FIX)
                        # Run for: missing URLs OR failed HTTP validation
                        if biz_data["website_validation_status"] in ["missing", "needs_verification"]:
                            logger.info(f"  ├─ 🔍 Running DEEP VERIFICATION (ScrapingDog + LLM)...")
                            
                            try:
                                # Use the llm_discovery service already initialized above
                                discovery_result = await llm_discovery.discover_website(
                                    business_name=biz_data["name"],
                                    phone=biz_data.get("phone"),
                                    address=biz_data.get("address"),
                                    city=city,
                                    state=state,
                                    country=country
                                )
                                
                                if discovery_result.get("found") and discovery_result.get("url"):
                                    verified_url = discovery_result["url"]
                                    confidence = discovery_result.get("confidence", 0)
                                    
                                    logger.info(
                                        f"  │  └─ ✅ LLM VERIFIED: {verified_url} "
                                        f"(confidence: {confidence:.0%})"
                                    )
                                    
                                    # Update business data with verified website
                                    biz_data["website_url"] = verified_url
                                    biz_data["website_validation_status"] = "pending"  # Queue for Playwright
                                    biz_data["verified"] = True
                                    biz_data["discovered_urls"] = [verified_url]
                                    
                                    # Store ALL discovery data (ScrapingDog results + LLM analysis)
                                    if not biz_data.get("raw_data"):
                                        biz_data["raw_data"] = {}
                                    biz_data["raw_data"]["llm_discovery"] = {
                                        "url": verified_url,
                                        "confidence": confidence,
                                        "reasoning": discovery_result.get("reasoning"),
                                        "verified_at": datetime.utcnow().isoformat(),
                                        "method": "scrapingdog_llm",
                                        "query": discovery_result.get("query"),
                                        "llm_model": discovery_result.get("llm_model"),
                                        # Store complete ScrapingDog search results
                                        "scrapingdog_results": discovery_result.get("search_results"),
                                        # Store LLM analysis details
                                        "llm_analysis": discovery_result.get("llm_analysis")
                                    }
                                else:
                                    logger.info(
                                        f"  │  └─ ❌ LLM: No website found - "
                                        f"{discovery_result.get('reasoning', 'Unknown')}"
                                    )
                                    
                                    # Confirmed no website by deep search
                                    biz_data["website_url"] = None
                                    biz_data["website_validation_status"] = "confirmed_missing"
                                    biz_data["verified"] = True  # Verified as having NO website
                                    
                                    # Store discovery data even when no website found (for debugging)
                                    if not biz_data.get("raw_data"):
                                        biz_data["raw_data"] = {}
                                    biz_data["raw_data"]["llm_discovery"] = {
                                        "url": None,
                                        "confidence": discovery_result.get("confidence", 0.95),
                                        "reasoning": discovery_result.get("reasoning"),
                                        "verified_at": datetime.utcnow().isoformat(),
                                        "method": "scrapingdog_llm",
                                        "query": discovery_result.get("query"),
                                        "llm_model": discovery_result.get("llm_model"),
                                        "scrapingdog_results": discovery_result.get("search_results"),
                                        "llm_analysis": discovery_result.get("llm_analysis")
                                    }
                                    
                            except Exception as e:
                                logger.error(f"  │  └─ ❌ Deep verification ERROR: {e}", exc_info=True)
                                # If deep verification fails, fall back to original status
                                if biz_data["website_validation_status"] == "needs_verification":
                                    # Keep the Outscraper URL but mark as unverified
                                    biz_data["website_validation_status"] = "pending"
                                    biz_data["verified"] = False
                                else:
                                    # No URL and verification failed
                                    biz_data["website_validation_status"] = "missing"
                                    biz_data["verified"] = False
                        
                        # 6. Lead qualification
                        logger.debug(f"  ├─ Running lead qualification...")
                        qualification_result = self.qualifier.qualify(biz_data)
                        score = qualification_result["score"]
                        reasons = qualification_result["reasons"]
                        logger.debug(f"  │  └─ Lead score: {score}, Reasons: {reasons}")
                        
                        # **SAVE ALL BUSINESSES** (we paid for them!)
                        logger.debug(f"  ├─ Saving to database...")
                        logger.debug(f"  │  └─ Final biz_data: website_url={biz_data.get('website_url')}, validation_status={biz_data.get('website_validation_status')}, verified={biz_data.get('verified')}")
                        business = await self.business_service.create_or_update_business(
                            data=biz_data,
                            source="outscraper_gmaps",
                            coverage_grid_id=coverage_id,
                            discovery_city=city,
                            discovery_state=state,
                            discovery_zone_id=zone_id,
                            discovery_zone_lat=zone_lat,
                            discovery_zone_lon=zone_lon,
                            lead_score=score,
                            qualification_reasons=reasons
                        )
                        
                        if business:
                            total_saved += 1
                            if hasattr(business, '_is_new') and business._is_new:
                                new_businesses += 1
                            
                            # Track website metrics
                            if business.website_validation_status == "pending":
                                businesses_to_validate.append(str(business.id))
                                businesses_with_valid_websites += 1
                                if biz_data.get("verified"):
                                    businesses_verified_by_llm += 1
                                    logger.info(f"  └─ 💾 SAVED - LLM verified website → Playwright queue")
                                else:
                                    logger.info(f"  └─ 💾 SAVED - Has website → Playwright queue")
                            elif business.website_validation_status in ["missing", "confirmed_missing"]:
                                businesses_needing_websites += 1
                                if business.website_validation_status == "confirmed_missing":
                                    businesses_verified_by_llm += 1
                                    logger.info(f"  └─ 💾 SAVED - LLM confirmed: No website exists ✓")
                                else:
                                    logger.info(f"  └─ 💾 SAVED - No website found")
                            else:
                                businesses_with_valid_websites += 1
                                logger.info(f"  └─ 💾 SAVED - Website status: {business.website_validation_status}")
                            
                            # Publish validation progress event
                            if self.progress_publisher:
                                try:
                                    self.progress_publisher.publish_validation_progress(
                                        session_id=str(coverage_id),
                                        validated_count=total_saved,
                                        total_count=len(raw_businesses),
                                        business_id=str(business.id),
                                        has_website=bool(business.website_url)
                                    )
                                except Exception as e:
                                    logger.warning(f"Failed to publish validation progress: {e}")
                        else:
                            logger.warning(f"  └─ ⚠️  Failed to save business")
                        
                        # Rate limiting for ScrapingDog (if we ran deep verification)
                        if biz_data.get("verified") or biz_data["website_validation_status"] == "confirmed_missing":
                            logger.debug(f"  └─ ⏱️  Rate limit: waiting {scrapingdog_delay}s...")
                            await asyncio.sleep(scrapingdog_delay)
                        
                    except Exception as e:
                        logger.error(f"  └─ ❌ CRITICAL ERROR processing {business_name}: {e}", exc_info=True)
                        continue
            
            # **Queue Playwright validation for businesses with websites**
            if businesses_to_validate:
                settings = get_settings()
                if settings.ENABLE_AUTO_VALIDATION:
                    logger.info(f"Queuing {len(businesses_to_validate)} businesses for V2 validation pipeline")
                    try:
                        from tasks.validation_tasks_enhanced import batch_validate_websites_v2
                        batch_validate_websites_v2.delay(businesses_to_validate)
                    except Exception as e:
                        logger.error(f"Failed to queue V2 validation tasks: {e}")
            
            # **Queue businesses for website generation**
            if businesses_needing_generation:
                queue_result = await self.generation_queue_service.queue_multiple(
                    business_ids=businesses_needing_generation,
                    priority=7  # High priority for newly scraped businesses
                )
                logger.info(
                    f"Queued {queue_result['queued']}/{len(businesses_needing_generation)} "
                    f"businesses for website generation"
                )
            
            # **FIX: Coverage was already created at the start, just update it now**
            # **NEW Phase 2 & 3: Store detailed scrape metrics**
            last_scrape_details = {
                "zone_id": zone_id,
                "raw_businesses": len(raw_businesses),
                "total_saved": total_saved,
                "new_businesses": new_businesses,
                "existing_businesses": total_saved - new_businesses,
                "with_valid_websites": businesses_with_valid_websites,
                "needing_websites": businesses_needing_websites,
                "verified_by_llm": businesses_verified_by_llm,
                "queued_for_playwright": len(businesses_to_validate),
                "verification_rate": f"{(businesses_verified_by_llm / total_saved * 100):.1f}%" if total_saved > 0 else "0%",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Calculate average metrics
            from sqlalchemy import select, func
            from models.business import Business
            
            # Get businesses for this coverage zone to calculate averages
            zone_businesses_query = select(
                func.avg(Business.qualification_score).label("avg_score"),
                func.avg(Business.rating).label("avg_rating")
            ).where(Business.coverage_grid_id == coverage_id)
            
            result = await self.db.execute(zone_businesses_query)
            averages = result.first()
            avg_qualification_score = float(averages.avg_score) if averages.avg_score else None
            avg_rating = float(averages.avg_rating) if averages.avg_rating else None
            
            # Update with comprehensive scraping results
            await self.coverage_service.update_coverage(
                coverage_id=coverage_id,
                updates={
                    "status": "completed",
                    "lead_count": total_saved,
                    "qualified_count": businesses_needing_websites,  # Qualified = needs website
                    "last_scrape_size": len(raw_businesses),
                    "last_scraped_at": datetime.utcnow(),
                    # New Phase 2 metrics
                    "businesses_with_websites": businesses_with_valid_websites,
                    "businesses_without_websites": businesses_needing_websites,
                    "invalid_websites": 0,  # Deprecated, now included in needing_websites
                    "generation_in_progress": len(businesses_needing_generation),
                    "avg_qualification_score": avg_qualification_score,
                    "avg_rating": avg_rating,
                    "last_scrape_details": last_scrape_details
                }
            )
            
            # Mark zone complete in strategy
            await self.geo_strategy_service.mark_zone_complete(
                strategy_id=strategy_id,
                zone_id=zone_id,
                businesses_found=total_saved
            )
            
            # Refresh strategy to get updated stats
            await self.db.refresh(strategy)
            
            logger.info(
                f"✅ Zone {zone_id} complete: Saved {total_saved} businesses "
                f"({businesses_needing_websites} need websites) from {len(raw_businesses)} raw results. "
                f"Progress: {strategy.zones_completed}/{strategy.total_zones} zones"
            )
            
            # Prepare enhanced response with Phase 2 metrics
            return {
                "strategy_id": strategy_id,
                "status": "active" if strategy.zones_completed < strategy.total_zones else "completed",
                "city": city,
                "state": state,
                "category": category,
                "zone_scraped": {
                    "zone_id": zone_id,
                    "priority": next_zone.get("priority"),
                    "lat": zone_lat,
                    "lon": zone_lon,
                    "radius_km": zone_radius,
                    "reason": next_zone.get("reason")
                },
                "results": {
                    "raw_businesses": len(raw_businesses),
                    "total_saved": total_saved,
                    "new_businesses": new_businesses,
                    # **NEW Phase 2 & 3: Website & Verification metrics**
                    "with_valid_websites": businesses_with_valid_websites,
                    "needing_websites": businesses_needing_websites,
                    "verified_by_llm": businesses_verified_by_llm,
                    "queued_for_playwright": len(businesses_to_validate),
                    "queued_for_generation": len(businesses_needing_generation)
                },
                "progress": {
                    "total_zones": strategy.total_zones,
                    "zones_completed": strategy.zones_completed,
                    "zones_remaining": strategy.total_zones - strategy.zones_completed,
                    "total_businesses_found": strategy.businesses_found,
                    "estimated_total_businesses": strategy.estimated_total_businesses,
                    "completion_pct": round((strategy.zones_completed / strategy.total_zones) * 100, 1)
                },
                "next_zone_preview": strategy.get_next_zone()
            }
            
        except Exception as e:
            logger.error(f"Error scraping zone {zone_id}: {e}")
            raise ExternalAPIException(f"Failed to scrape zone: {str(e)}")
    
    async def scrape_all_zones_for_strategy(
        self,
        strategy_id: str,
        limit_per_zone: int = 50,
        max_zones: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Continue scraping zones for an existing strategy until complete (or max reached).
        
        This is useful for background tasks that want to execute an entire strategy.
        
        Args:
            strategy_id: Strategy UUID
            limit_per_zone: Maximum results per zone
            max_zones: Maximum zones to scrape in this batch (None = all)
            
        Returns:
            Summary of batch execution
        """
        strategy = await self.geo_strategy_service.get_strategy_by_id(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")
        
        logger.info(
            f"Starting batch execution for strategy {strategy_id}: "
            f"{strategy.city}, {strategy.state} - {strategy.category}"
        )
        
        zones_scraped = 0
        total_businesses = 0
        total_qualified = 0
        
        while True:
            # Check if we've hit the max
            if max_zones and zones_scraped >= max_zones:
                logger.info(f"Reached max zones limit ({max_zones})")
                break
            
            # Get next zone
            next_zone = strategy.get_next_zone()
            if not next_zone:
                logger.info(f"Strategy {strategy_id} complete - no more zones")
                break
            
            # Scrape the zone
            try:
                result = await self.scrape_with_intelligent_strategy(
                    city=strategy.city,
                    state=strategy.state,
                    category=strategy.category,
                    country=strategy.country,
                    limit_per_zone=limit_per_zone,
                    center_lat=strategy.city_center_lat,
                    center_lon=strategy.city_center_lon
                )
                
                zones_scraped += 1
                total_businesses += result["results"]["raw_businesses"]
                total_qualified += result["results"]["qualified_leads"]
                
                # Refresh strategy
                await self.db.refresh(strategy)
                
            except Exception as e:
                logger.error(f"Error in batch execution for zone {next_zone['zone_id']}: {e}")
                # Continue with next zone even if one fails
                continue
        
        return {
            "strategy_id": strategy_id,
            "city": strategy.city,
            "state": strategy.state,
            "category": strategy.category,
            "batch_results": {
                "zones_scraped_in_batch": zones_scraped,
                "businesses_found_in_batch": total_businesses,
                "qualified_in_batch": total_qualified
            },
            "overall_progress": {
                "total_zones": strategy.total_zones,
                "zones_completed": strategy.zones_completed,
                "zones_remaining": strategy.total_zones - strategy.zones_completed,
                "total_businesses_found": strategy.businesses_found,
                "completion_pct": round((strategy.zones_completed / strategy.total_zones) * 100, 1)
            },
            "status": strategy.is_active
        }
    
    async def get_strategy_status(self, strategy_id: str) -> Dict[str, Any]:
        """
        Get current status of a strategy.
        
        Args:
            strategy_id: Strategy UUID
            
        Returns:
            Status dictionary
        """
        strategy = await self.geo_strategy_service.get_strategy_by_id(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")
        
        return strategy.to_dict()
    
    async def list_active_strategies(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List active strategies with optional filters.
        
        Args:
            city: Filter by city
            state: Filter by state
            category: Filter by category
            
        Returns:
            List of strategy dictionaries
        """
        strategies = await self.geo_strategy_service.list_strategies(
            city=city,
            state=state,
            category=category,
            status="active"
        )
        
        return [s.to_dict() for s in strategies]
    
    # Legacy method - kept for backward compatibility
    async def scrape_location(
        self,
        city: str,
        state: str,
        industry: str,
        country: str = "US",
        limit: int = 50,
        priority: int = 0,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        LEGACY: Simple single-query scraping without intelligent strategy.
        
        For new code, use scrape_with_intelligent_strategy instead.
        This method is kept for backward compatibility.
        """
        logger.warning(
            f"Using legacy scrape_location for {industry} in {city}, {state}. "
            "Consider using scrape_with_intelligent_strategy for better coverage."
        )
        
        # Use the old simple approach
        results = await self.scraper.search_businesses(
            query=industry,
            city=city,
            state=state,
            country=country,
            limit=limit,
            offset=offset
        )
        
        raw_businesses = results.get("businesses", [])
        settings = get_settings()
        
        # Process businesses with simple website validator for initial filtering
        qualified_count = 0
        businesses_to_validate = []  # Track businesses that need deep validation
        
        async with WebsiteValidator() as website_validator:
            for biz_data in raw_businesses:
                try:
                    # Simple validation: filter out social media, Google redirects, etc.
                    # This is FAST and prevents bad URLs from entering the system
                    website_url = biz_data.get("website_url")
                    if website_url:
                        simple_validation = await website_validator.validate_url(website_url)
                        
                        # If simple validation fails (social media, redirect, etc.), mark as invalid
                        if not simple_validation.is_valid and not simple_validation.is_real_website:
                            biz_data["website_validation_status"] = "invalid"
                            logger.debug(f"Rejected URL during scraping: {website_url} - {simple_validation.error_message}")
                        else:
                            # Passed simple checks, mark for deep validation later
                            biz_data["website_validation_status"] = "pending"
                    else:
                        biz_data["website_validation_status"] = "no_website"
                    
                    # Qualify
                    qualification_result = self.qualifier.qualify(biz_data)
                    is_qualified = qualification_result["qualified"]
                    score = qualification_result["score"]
                    reasons = qualification_result["reasons"]
                    
                    if is_qualified:
                        business = await self.business_service.create_or_update_business(
                            data=biz_data,
                            source="outscraper_gmaps",
                            discovery_city=city,
                            discovery_state=state,
                            lead_score=score,
                            qualification_reasons=reasons
                        )
                        qualified_count += 1
                        
                        # If business has a website that passed simple checks, queue for deep validation
                        if (business and 
                            business.website_url and 
                            business.website_validation_status == "pending"):
                            businesses_to_validate.append(str(business.id))
                            
                except Exception as e:
                    logger.error(f"Error processing business: {e}")
                    continue
        
        # Queue deep Playwright validation for businesses with websites
        if settings.ENABLE_AUTO_VALIDATION and businesses_to_validate:
            logger.info(f"Queuing {len(businesses_to_validate)} businesses for V2 validation pipeline")
            try:
                # Import here to avoid circular dependency
                from tasks.validation_tasks_enhanced import batch_validate_websites_v2
                
                # Queue in batches to avoid overwhelming the validation queue
                batch_size = settings.VALIDATION_BATCH_SIZE
                for i in range(0, len(businesses_to_validate), batch_size):
                    batch = businesses_to_validate[i:i + batch_size]
                    batch_validate_websites_v2.delay(batch)
                    logger.debug(f"Queued V2 validation batch {i//batch_size + 1}: {len(batch)} businesses")
                    
            except Exception as e:
                logger.error(f"Failed to queue V2 validation tasks: {e}", exc_info=True)
                # Don't fail scraping if validation queueing fails
        
        # Update coverage
        await self.coverage_service.update_or_create_coverage(
            city=city,
            state=state,
            country=country,
            industry=industry,
            priority=priority,
            total_found=len(raw_businesses),
            qualified=qualified_count
        )
        
        return {
            "city": city,
            "state": state,
            "industry": industry,
            "results": {
                "total_found": len(raw_businesses),
                "qualified_leads": qualified_count,
                "queued_for_validation": len(businesses_to_validate) if settings.ENABLE_AUTO_VALIDATION else 0
            }
        }
