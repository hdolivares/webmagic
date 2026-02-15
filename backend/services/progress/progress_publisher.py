"""
Progress Publisher Service.

Purpose:
    Publish real-time scraping progress updates to Redis Pub/Sub.
    Provides clean, typed interface for progress events.

Best Practices:
    - Single Responsibility: Only handles publishing
    - Dependency Injection: Redis client passed in
    - Type hints for IDE support
    - Comprehensive logging
    - Error handling without crashes
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from redis import Redis

logger = logging.getLogger(__name__)


class ProgressPublisher:
    """
    Publishes scraping progress to Redis Pub/Sub channels.
    
    Frontend subscribes to these channels via SSE to receive
    real-time updates as scraping progresses.
    
    Channel format: "scrape:progress:{session_id}"
    
    Usage:
        redis = RedisService.get_client()
        publisher = ProgressPublisher(redis)
        
        publisher.publish_business_scraped(
            session_id="uuid-here",
            business_name="Joe's Plumbing",
            current=50,
            total=200
        )
    """
    
    def __init__(self, redis_client: Redis):
        """
        Initialize publisher with Redis client.
        
        Args:
            redis_client: Connected Redis client from RedisService
        """
        self.redis = redis_client
        self._channel_prefix = "scrape:progress"
    
    # =========================================================================
    # CORE PUBLISHING
    # =========================================================================
    
    def publish_event(
        self,
        session_id: str,
        event: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Publish a progress event to Redis.
        
        Args:
            session_id: UUID of scrape session
            event: Event type (e.g., "business_scraped", "error")
            data: Event payload dictionary
            
        Returns:
            True if published successfully, False otherwise
        """
        try:
            channel = f"{self._channel_prefix}:{session_id}"
            
            message = {
                "session_id": session_id,
                "event": event,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Publish to Redis Pub/Sub
            self.redis.publish(channel, json.dumps(message))
            
            logger.debug(
                f"📡 Published {event} to {channel} "
                f"(data_keys: {list(data.keys())})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to publish progress event: {e}")
            return False
    
    # =========================================================================
    # CONVENIENCE METHODS (Typed, semantic events)
    # =========================================================================
    
    def publish_scraping_started(
        self,
        session_id: str,
        query: str,
        zone_id: str
    ):
        """
        Publish scraping started event.
        
        Args:
            session_id: Scrape session ID
            query: Outscraper search query
            zone_id: Geographic zone identifier
        """
        self.publish_event(
            session_id=session_id,
            event="scraping_started",
            data={
                "query": query,
                "zone_id": zone_id,
                "message": "Starting Outscraper search..."
            }
        )
    
    def publish_business_scraped(
        self,
        session_id: str,
        business_id: str,
        business_name: str,
        current: int,
        total: int
    ):
        """
        Publish business scraped event.
        
        Args:
            session_id: Scrape session ID
            business_id: Business UUID
            business_name: Business name
            current: Current count of scraped businesses
            total: Total businesses to scrape
        """
        percentage = round((current / total * 100) if total > 0 else 0, 1)
        
        self.publish_event(
            session_id=session_id,
            event="business_scraped",
            data={
                "business_id": business_id,
                "business_name": business_name,
                "progress": {
                    "current": current,
                    "total": total,
                    "percentage": percentage
                }
            }
        )
    
    def publish_validation_started(
        self,
        session_id: str,
        total_to_validate: int
    ):
        """
        Publish validation phase started.
        
        Args:
            session_id: Scrape session ID
            total_to_validate: Number of businesses to validate
        """
        self.publish_event(
            session_id=session_id,
            event="validation_started",
            data={
                "total_to_validate": total_to_validate,
                "message": "Starting website validation..."
            }
        )
    
    def publish_validation_complete(
        self,
        session_id: str,
        business_id: str,
        status: str,
        validated_count: int,
        total_count: int
    ):
        """
        Publish validation completion for a business.
        
        Args:
            session_id: Scrape session ID
            business_id: Business UUID
            status: Validation status (valid, invalid, etc.)
            validated_count: Number validated so far
            total_count: Total businesses to validate
        """
        self.publish_event(
            session_id=session_id,
            event="validation_complete",
            data={
                "business_id": business_id,
                "status": status,
                "progress": {
                    "validated": validated_count,
                    "total": total_count,
                    "percentage": round(
                        (validated_count / total_count * 100) if total_count > 0 else 0,
                        1
                    )
                }
            }
        )
    
    def publish_scrape_complete(
        self,
        session_id: str,
        summary: Dict[str, int]
    ):
        """
        Publish scrape completion event.
        
        Args:
            session_id: Scrape session ID
            summary: Summary statistics dictionary
        """
        self.publish_event(
            session_id=session_id,
            event="scrape_complete",
            data={
                "summary": summary,
                "message": "Scraping completed successfully!"
            }
        )
    
    def publish_error(
        self,
        session_id: str,
        error_message: str,
        error_type: Optional[str] = None,
        recoverable: bool = False
    ):
        """
        Publish error event.
        
        Args:
            session_id: Scrape session ID
            error_message: Human-readable error message
            error_type: Error classification (optional)
            recoverable: Whether scraping can continue
        """
        self.publish_event(
            session_id=session_id,
            event="error",
            data={
                "error": error_message,
                "type": error_type,
                "recoverable": recoverable
            }
        )
    
    def publish_heartbeat(self, session_id: str):
        """
        Publish heartbeat to keep connection alive.
        
        Args:
            session_id: Scrape session ID
        """
        self.publish_event(
            session_id=session_id,
            event="heartbeat",
            data={"status": "alive"}
        )
