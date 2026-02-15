"""
Scrape Analytics Service.

Purpose:
    Provide comprehensive visibility into scraping operations by logging
    detailed metrics, results, and performance data for each scrape.

Best Practices:
    - Structured logging for easy parsing and analysis
    - Store analytics in session metadata for historical tracking
    - Provide human-readable summaries
    - Track success rates and patterns over time
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.scrape_session import ScrapeSession
from models.business import Business

logger = logging.getLogger(__name__)


class ScrapeAnalytics:
    """
    Analyze and log scrape results for visibility and optimization.
    
    Tracks:
    - Businesses found vs. validated
    - Website detection sources (Outscraper, ScrapingDog)
    - Geographic coverage
    - Performance metrics (duration, API calls)
    - Success rates by category/region
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_scrape_complete(
        self,
        session_id: str,
        scrape_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Log comprehensive scrape results.
        
        Args:
            session_id: UUID of scrape session
            scrape_result: Result dictionary from HunterService
            
        Returns:
            Analytics summary dictionary
        """
        try:
            # Get session
            result = await self.db.execute(
                select(ScrapeSession).where(ScrapeSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            
            if not session:
                logger.error(f"❌ Session {session_id} not found for analytics")
                return {}
            
            # Extract metrics
            meta = session.meta or {}
            city = meta.get("city", "Unknown")
            state = meta.get("state", "Unknown")
            category = meta.get("category", "Unknown")
            
            # Query business stats for this session
            stats = await self._get_business_stats(session.zone_id)
            
            # Build analytics
            analytics = {
                "session_id": str(session_id),
                "timestamp": datetime.utcnow().isoformat(),
                "region": {
                    "city": city,
                    "state": state,
                    "zone_id": session.zone_id
                },
                "query": {
                    "category": category,
                    "limit": meta.get("limit_per_zone", 50)
                },
                "results": {
                    "total_found": session.total_businesses or 0,
                    "scraped": session.scraped_businesses or 0,
                    "validated": session.validated_businesses or 0,
                    "discovered": session.discovered_businesses or 0,
                    "with_valid_urls": stats["valid_urls"],
                    "needs_discovery": stats["needs_discovery"],
                    "confirmed_missing": stats["confirmed_missing"],
                    "queued_for_generation": stats["queued_for_gen"]
                },
                "performance": {
                    "duration_seconds": self._calculate_duration(session),
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "completed_at": session.completed_at.isoformat() if session.completed_at else None
                },
                "quality": {
                    "url_sources": stats["url_sources"],
                    "validation_success_rate": self._calc_validation_rate(stats)
                }
            }
            
            # Store in session metadata
            if not session.meta:
                session.meta = {}
            session.meta["analytics"] = analytics
            
            # Commit update
            await self.db.commit()
            
            # Log structured JSON for parsing
            logger.info(
                f"📊 SCRAPE_ANALYTICS: {json.dumps(analytics, indent=2)}"
            )
            
            # Log human-readable summary
            summary = self._format_summary(analytics)
            logger.info(f"\n{summary}\n")
            
            return analytics
            
        except Exception as e:
            logger.error(f"❌ Failed to log analytics: {e}", exc_info=True)
            return {}
    
    async def _get_business_stats(self, zone_id: str) -> Dict[str, Any]:
        """Query business statistics for the zone."""
        try:
            # Count by validation state
            result = await self.db.execute(
                select(
                    Business.validation_state,
                    Business.website_url,
                    Business.website_metadata,
                    func.count().label('count')
                ).where(
                    Business.zone_id == zone_id
                ).group_by(
                    Business.validation_state,
                    Business.website_url,
                    Business.website_metadata
                )
            )
            
            stats = {
                "valid_urls": 0,
                "needs_discovery": 0,
                "confirmed_missing": 0,
                "queued_for_gen": 0,
                "url_sources": {
                    "outscraper": 0,
                    "scrapingdog": 0,
                    "unknown": 0
                }
            }
            
            for row in result:
                state = row[0]
                has_url = row[1] is not None
                metadata = row[2] or {}
                count = row[3]
                
                # Count by state
                if state in ["valid_outscraper", "valid_manual"]:
                    stats["valid_urls"] += count
                elif state == "needs_discovery":
                    stats["needs_discovery"] += count
                elif state == "confirmed_missing":
                    stats["confirmed_missing"] += count
                    stats["queued_for_gen"] += count
                
                # Count by source
                if has_url and isinstance(metadata, dict):
                    source = metadata.get("source", "unknown")
                    if source == "outscraper":
                        stats["url_sources"]["outscraper"] += count
                    elif source == "scrapingdog":
                        stats["url_sources"]["scrapingdog"] += count
                    else:
                        stats["url_sources"]["unknown"] += count
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get business stats: {e}")
            return {
                "valid_urls": 0,
                "needs_discovery": 0,
                "confirmed_missing": 0,
                "queued_for_gen": 0,
                "url_sources": {"outscraper": 0, "scrapingdog": 0, "unknown": 0}
            }
    
    def _calculate_duration(self, session: ScrapeSession) -> Optional[float]:
        """Calculate scrape duration in seconds."""
        if session.started_at and session.completed_at:
            delta = session.completed_at - session.started_at
            return round(delta.total_seconds(), 2)
        return None
    
    def _calc_validation_rate(self, stats: Dict[str, Any]) -> float:
        """Calculate validation success rate."""
        total = stats["valid_urls"] + stats["needs_discovery"] + stats["confirmed_missing"]
        if total == 0:
            return 0.0
        return round(stats["valid_urls"] / total * 100, 2)
    
    def _format_summary(self, analytics: Dict[str, Any]) -> str:
        """Format human-readable summary."""
        region = analytics["region"]
        query = analytics["query"]
        results = analytics["results"]
        performance = analytics["performance"]
        quality = analytics["quality"]
        
        total = results["total_found"]
        valid = results["with_valid_urls"]
        discovery_needed = results["needs_discovery"]
        discovered = results["discovered"]
        missing = results["confirmed_missing"]
        queued = results["queued_for_generation"]
        
        valid_pct = round(valid / total * 100, 1) if total > 0 else 0
        discovery_pct = round(discovery_needed / total * 100, 1) if total > 0 else 0
        
        sources = quality["url_sources"]
        duration = performance["duration_seconds"]
        
        summary = f"""
╔═══════════════════════════════════════════════════════════════╗
║                    SCRAPE SUMMARY                             ║
╠═══════════════════════════════════════════════════════════════╣
║ Region:     {region['city']}, {region['state']:<40} ║
║ Category:   {query['category']:<49} ║
║ Zone ID:    {region['zone_id']:<49} ║
║ Duration:   {f"{duration}s" if duration else "N/A":<49} ║
╠═══════════════════════════════════════════════════════════════╣
║                        RESULTS                                ║
╠═══════════════════════════════════════════════════════════════╣
║ Total Businesses:        {total:>5}                              ║
║ With Valid Websites:     {valid:>5} ({valid_pct:>5.1f}%)                    ║
║ Needed Discovery:        {discovery_needed:>5} ({discovery_pct:>5.1f}%)                    ║
║   - Discovered:          {discovered:>5}                              ║
║   - Confirmed Missing:   {missing:>5}                              ║
║ Queued for Generation:   {queued:>5}                              ║
╠═══════════════════════════════════════════════════════════════╣
║                    WEBSITE SOURCES                            ║
╠═══════════════════════════════════════════════════════════════╣
║ Outscraper:              {sources['outscraper']:>5}                              ║
║ ScrapingDog:             {sources['scrapingdog']:>5}                              ║
║ Unknown:                 {sources['unknown']:>5}                              ║
╠═══════════════════════════════════════════════════════════════╣
║ Validation Success Rate: {quality['validation_success_rate']:>5.1f}%                       ║
╚═══════════════════════════════════════════════════════════════╝
"""
        return summary
    
    async def get_recent_scrapes(self, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Get analytics for recent scrapes.
        
        Args:
            limit: Number of recent scrapes to return
            
        Returns:
            List of analytics dictionaries
        """
        try:
            result = await self.db.execute(
                select(ScrapeSession)
                .where(ScrapeSession.status == "completed")
                .order_by(ScrapeSession.completed_at.desc())
                .limit(limit)
            )
            sessions = result.scalars().all()
            
            analytics_list = []
            for session in sessions:
                if session.meta and "analytics" in session.meta:
                    analytics_list.append(session.meta["analytics"])
            
            return analytics_list
            
        except Exception as e:
            logger.error(f"❌ Failed to get recent scrapes: {e}")
            return []
