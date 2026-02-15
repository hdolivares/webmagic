# 🏗️ Phase 2: Async Architecture with Real-Time Progress

**Status:** 📋 Implementation Plan  
**Timeline:** 6-8 hours  
**Priority:** High  

---

## 🎯 **Goals**

✅ **3 Separate Celery Queues** (scraping, validation, discovery)  
✅ **Real-Time Progress** via Server-Sent Events (SSE)  
✅ **Remove Circular Dependencies** (no auto-revalidation)  
✅ **Best Practices**: Separation of concerns, modular code, readable functions  

---

## 📐 **Architecture Overview**

### High-Level Flow

```
┌──────────────┐
│   FRONTEND   │
└──────┬───────┘
       │ POST /api/v1/scrapes/start
       ↓
┌──────────────────────────────────────────┐
│  API ENDPOINT (Instant Return)           │
│  • Create scrape_session record          │
│  • Queue async task                      │
│  • Return session_id                     │
└──────┬───────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│  QUEUE 1: Outscraper Scraping            │
│  • Fetch businesses (50-200)             │
│  • Create DB records one-by-one          │
│  • Publish progress to Redis             │
│  • Queue to QUEUE 2                      │
└──────┬───────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│  QUEUE 2: URL Validation                 │
│  • Prescreener → Playwright → LLM        │
│  • If valid: done ✅                     │
│  • If invalid: Queue to QUEUE 3 ↓        │
└──────┬───────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│  QUEUE 3: Website Discovery              │
│  • ScrapingDog + LLM                     │
│  • Update business with URL              │
│  • DO NOT auto-revalidate                │
└───────────────────────────────────────────┘
       │
       ↓
┌──────────────┐
│   FRONTEND   │ ← SSE Stream (/api/v1/scrapes/{id}/progress)
│  Progress Bar │ ← Updates in real-time
└──────────────┘
```

---

## 🔧 **Implementation Steps**

### **Module 1: Scrape Session Management** (New)
### **Module 2: Redis Progress Publisher** (New)
### **Module 3: Async Scraping Task** (Refactor)
### **Module 4: Queue Separation** (Configure)
### **Module 5: SSE Progress Endpoint** (New)
### **Module 6: Frontend Real-Time UI** (New)

---

## 📦 **Module 1: Scrape Session Management**

### Purpose
Track scrape lifecycle, store metadata, enable progress queries

### Database Schema

```sql
-- Migration: 014_create_scrape_sessions.sql

CREATE TABLE IF NOT EXISTS scrape_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id VARCHAR(255) NOT NULL,
    strategy_id UUID REFERENCES geo_strategies(id),
    
    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    -- Possible values: queued, scraping, validating, completed, failed, cancelled
    
    -- Progress metrics
    total_businesses INTEGER DEFAULT 0,
    scraped_businesses INTEGER DEFAULT 0,
    validated_businesses INTEGER DEFAULT 0,
    discovered_businesses INTEGER DEFAULT 0,
    
    -- Timestamps
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Error tracking
    error_message TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_scrape_sessions_zone ON scrape_sessions(zone_id);
CREATE INDEX idx_scrape_sessions_status ON scrape_sessions(status);
CREATE INDEX idx_scrape_sessions_created ON scrape_sessions(created_at DESC);
```

### SQLAlchemy Model

```python
# File: backend/models/scrape_session.py

from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from core.database import Base


class ScrapeSession(Base):
    """
    Tracks the lifecycle of a scraping operation.
    
    Separation of Concerns:
    - Business logic in services/scraping/
    - Progress tracking in services/progress/
    - This model only handles data structure
    """
    __tablename__ = "scrape_sessions"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(String(255), nullable=False, index=True)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("geo_strategies.id"))
    
    # Status tracking
    status = Column(String(50), nullable=False, default="queued", index=True)
    
    # Progress metrics
    total_businesses = Column(Integer, default=0)
    scraped_businesses = Column(Integer, default=0)
    validated_businesses = Column(Integer, default=0)
    discovered_businesses = Column(Integer, default=0)
    
    # Timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Error tracking
    error_message = Column(Text)
    
    # Metadata (flexible for future expansion)
    metadata = Column(JSONB, default=dict)
    
    # Relationships
    strategy = relationship("GeoStrategy", back_populates="scrape_sessions")
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "zone_id": self.zone_id,
            "status": self.status,
            "progress": {
                "total": self.total_businesses,
                "scraped": self.scraped_businesses,
                "validated": self.validated_businesses,
                "discovered": self.discovered_businesses,
                "percentage": round(
                    (self.scraped_businesses / self.total_businesses * 100)
                    if self.total_businesses > 0 else 0,
                    1
                )
            },
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
            "error": self.error_message
        }
```

---

## 📡 **Module 2: Redis Progress Publisher**

### Purpose
Centralized service for publishing real-time progress updates

### Service Implementation

```python
# File: backend/services/progress/progress_publisher.py

"""
Progress Publisher Service.

Responsibilities:
- Publish progress updates to Redis
- Maintain clean separation from business logic
- Provide simple, typed interface

Best Practices:
- Single Responsibility: Only handles publishing
- Dependency Injection: Redis client passed in
- Type Hints: Clear interface
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from redis import Redis

logger = logging.getLogger(__name__)


class ProgressPublisher:
    """
    Publishes scraping progress updates to Redis Pub/Sub.
    
    Usage:
        publisher = ProgressPublisher(redis_client)
        publisher.publish_scrape_progress(
            session_id=session_id,
            event="business_scraped",
            data={"business_name": "Joe's Plumbing", ...}
        )
    """
    
    def __init__(self, redis_client: Redis):
        """
        Initialize publisher.
        
        Args:
            redis_client: Connected Redis client
        """
        self.redis = redis_client
        self._channel_prefix = "scrape:progress"
    
    def publish_scrape_progress(
        self,
        session_id: str,
        event: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Publish a scraping progress event.
        
        Args:
            session_id: UUID of scrape session
            event: Event type (e.g., "business_scraped", "validation_complete")
            data: Event payload
            
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
            
            self.redis.publish(channel, json.dumps(message))
            logger.debug(f"Published {event} to {channel}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish progress: {e}")
            return False
    
    def publish_business_scraped(
        self,
        session_id: str,
        business_id: str,
        business_name: str,
        current: int,
        total: int
    ):
        """
        Convenience method for business scraped event.
        
        Args:
            session_id: Scrape session ID
            business_id: Business UUID
            business_name: Business name
            current: Current count of scraped businesses
            total: Total businesses to scrape
        """
        self.publish_scrape_progress(
            session_id=session_id,
            event="business_scraped",
            data={
                "business_id": business_id,
                "business_name": business_name,
                "progress": {
                    "current": current,
                    "total": total,
                    "percentage": round((current / total * 100) if total > 0 else 0, 1)
                }
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
        """Publish validation completion event."""
        self.publish_scrape_progress(
            session_id=session_id,
            event="validation_complete",
            data={
                "business_id": business_id,
                "status": status,
                "progress": {
                    "validated": validated_count,
                    "total": total_count
                }
            }
        )
    
    def publish_scrape_complete(
        self,
        session_id: str,
        total_businesses: int,
        valid_count: int,
        invalid_count: int,
        missing_count: int
    ):
        """Publish scrape completion event."""
        self.publish_scrape_progress(
            session_id=session_id,
            event="scrape_complete",
            data={
                "summary": {
                    "total": total_businesses,
                    "valid": valid_count,
                    "invalid": invalid_count,
                    "missing": missing_count
                }
            }
        )
    
    def publish_error(
        self,
        session_id: str,
        error_message: str,
        error_type: Optional[str] = None
    ):
        """Publish error event."""
        self.publish_scrape_progress(
            session_id=session_id,
            event="error",
            data={
                "error": error_message,
                "type": error_type
            }
        )
```

### Redis Client Service

```python
# File: backend/services/progress/redis_service.py

"""
Redis connection management.

Responsibilities:
- Manage Redis connection
- Provide singleton access
- Handle connection errors gracefully

Best Practices:
- Singleton pattern for connection pooling
- Lazy initialization
- Error handling with fallbacks
"""

import logging
from redis import Redis, ConnectionPool
from core.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """
    Redis connection manager (Singleton).
    
    Usage:
        redis = RedisService.get_client()
        redis.publish("channel", "message")
    """
    
    _instance: Redis = None
    _pool: ConnectionPool = None
    
    @classmethod
    def get_client(cls) -> Redis:
        """
        Get Redis client (singleton).
        
        Returns:
            Connected Redis client
        """
        if cls._instance is None:
            cls._initialize()
        return cls._instance
    
    @classmethod
    def _initialize(cls):
        """Initialize Redis connection pool and client."""
        try:
            cls._pool = ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                max_connections=10
            )
            cls._instance = Redis(connection_pool=cls._pool)
            
            # Test connection
            cls._instance.ping()
            logger.info("✅ Redis connection established")
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            # Create dummy client that fails gracefully
            cls._instance = _DummyRedis()
    
    @classmethod
    def close(cls):
        """Close Redis connection."""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
        if cls._pool:
            cls._pool.disconnect()
            cls._pool = None


class _DummyRedis:
    """Dummy Redis client that fails gracefully when Redis is unavailable."""
    
    def __getattr__(self, name):
        def method(*args, **kwargs):
            logger.warning(f"Redis unavailable, skipping: {name}")
            return None
        return method
```

---

## 🔄 **Module 3: Async Scraping Task**

### Purpose
Move Outscraper scraping to background with progress tracking

### Celery Task

```python
# File: backend/tasks/scraping_tasks.py

"""
Asynchronous Scraping Tasks.

Responsibilities:
- Fetch businesses from Outscraper
- Create database records
- Publish progress updates
- Queue validation tasks

Best Practices:
- Single Responsibility per task
- Idempotent operations
- Comprehensive error handling
- Progress tracking at each step
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
from celery import shared_task
from sqlalchemy import select

from core.database import get_db_session_sync
from models.business import Business
from models.scrape_session import ScrapeSession
from services.hunter.outscraper_client import OutscraperClient
from services.crm.lead_service import LeadService
from services.progress.progress_publisher import ProgressPublisher
from services.progress.redis_service import RedisService
from tasks.validation_tasks_enhanced import validate_business_website_v2

logger = logging.getLogger(__name__)


@shared_task(
    name="tasks.scraping.scrape_zone_async",
    bind=True,
    max_retries=2,
    time_limit=600,  # 10 minutes
    soft_time_limit=570
)
def scrape_zone_async(
    self,
    session_id: str,
    zone_id: str,
    strategy_id: str,
    query: str
) -> Dict[str, Any]:
    """
    Asynchronously scrape businesses for a zone.
    
    This task:
    1. Fetches businesses from Outscraper
    2. Creates DB records one-by-one
    3. Publishes progress updates
    4. Queues validation tasks
    
    Args:
        session_id: UUID of scrape session
        zone_id: Zone identifier
        strategy_id: Strategy UUID
        query: Outscraper search query
        
    Returns:
        Summary dictionary with counts and status
    """
    try:
        logger.info(f"🚀 Starting async scrape for zone {zone_id}, session {session_id}")
        
        # Initialize services
        redis = RedisService.get_client()
        publisher = ProgressPublisher(redis)
        outscraper = OutscraperClient()
        lead_service = LeadService()
        
        with get_db_session_sync() as db:
            # Update session status
            session = db.query(ScrapeSession).filter(
                ScrapeSession.id == session_id
            ).first()
            
            if not session:
                error_msg = f"Session {session_id} not found"
                logger.error(error_msg)
                return {"error": error_msg}
            
            session.status = "scraping"
            session.started_at = datetime.utcnow()
            db.commit()
            
            # Step 1: Fetch from Outscraper
            logger.info(f"📡 Fetching businesses from Outscraper: {query}")
            publisher.publish_scrape_progress(
                session_id=session_id,
                event="scraping_started",
                data={"query": query}
            )
            
            try:
                raw_businesses = outscraper.search_businesses(query)
                total_businesses = len(raw_businesses)
                
                session.total_businesses = total_businesses
                db.commit()
                
                logger.info(f"✅ Fetched {total_businesses} businesses")
                
            except Exception as e:
                error_msg = f"Outscraper fetch failed: {str(e)}"
                logger.error(error_msg)
                _handle_session_error(db, session, error_msg, publisher)
                raise
            
            # Step 2: Process businesses one-by-one
            created_count = 0
            skipped_count = 0
            businesses_to_validate = []
            
            for index, business_data in enumerate(raw_businesses, start=1):
                try:
                    # Create/update business
                    business, is_new = await lead_service.get_or_create_business(
                        business_data=business_data,
                        coverage_grid_id=None  # Will be set by coverage service
                    )
                    
                    if is_new:
                        created_count += 1
                        if business.website_url:
                            businesses_to_validate.append(str(business.id))
                    else:
                        skipped_count += 1
                    
                    # Update session progress
                    session.scraped_businesses = index
                    db.commit()
                    
                    # Publish progress
                    publisher.publish_business_scraped(
                        session_id=session_id,
                        business_id=str(business.id),
                        business_name=business.name,
                        current=index,
                        total=total_businesses
                    )
                    
                    logger.info(
                        f"{'✨ Created' if is_new else '♻️ Found existing'}: "
                        f"{business.name} ({index}/{total_businesses})"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"❌ Failed to process business {index}: {e}",
                        exc_info=True
                    )
                    # Continue with next business
                    continue
            
            # Step 3: Queue validation tasks
            logger.info(f"📋 Queueing {len(businesses_to_validate)} businesses for validation")
            
            for business_id in businesses_to_validate:
                validate_business_website_v2.delay(business_id)
            
            # Step 4: Update session to completed
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            db.commit()
            
            # Publish completion
            publisher.publish_scrape_complete(
                session_id=session_id,
                total_businesses=total_businesses,
                valid_count=len(businesses_to_validate),
                invalid_count=0,  # Will be updated by validation
                missing_count=total_businesses - len(businesses_to_validate)
            )
            
            summary = {
                "session_id": session_id,
                "status": "completed",
                "total": total_businesses,
                "created": created_count,
                "skipped": skipped_count,
                "queued_for_validation": len(businesses_to_validate)
            }
            
            logger.info(f"🎉 Scrape completed: {summary}")
            return summary
            
    except Exception as e:
        logger.error(f"💥 Scrape task failed: {e}", exc_info=True)
        
        # Update session with error
        try:
            with get_db_session_sync() as db:
                session = db.query(ScrapeSession).filter(
                    ScrapeSession.id == session_id
                ).first()
                if session:
                    _handle_session_error(
                        db, session, str(e),
                        ProgressPublisher(RedisService.get_client())
                    )
        except:
            pass
        
        # Retry logic
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            return {"error": str(e), "status": "failed"}


def _handle_session_error(
    db,
    session: ScrapeSession,
    error_message: str,
    publisher: ProgressPublisher
):
    """Helper to handle session errors consistently."""
    session.status = "failed"
    session.error_message = error_message
    session.completed_at = datetime.utcnow()
    db.commit()
    
    publisher.publish_error(
        session_id=str(session.id),
        error_message=error_message
    )
```

---

## 🌐 **Module 4: SSE Progress Endpoint**

### Purpose
Stream real-time progress updates to frontend

### FastAPI Endpoint

```python
# File: backend/api/v1/endpoints/scrapes.py

"""
Scraping API Endpoints.

Responsibilities:
- Start scraping operations
- Stream progress via SSE
- Query scrape status

Best Practices:
- RESTful design
- Clear error responses
- Async/await for I/O operations
- Type hints and validation
"""

import logging
import asyncio
from typing import AsyncGenerator
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from core.database import get_db
from core.auth import get_current_user
from models.user import User
from models.scrape_session import ScrapeSession
from services.progress.redis_service import RedisService
from tasks.scraping_tasks import scrape_zone_async

router = APIRouter(prefix="/scrapes", tags=["scrapes"])
logger = logging.getLogger(__name__)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class StartScrapeRequest(BaseModel):
    """Request model for starting a scrape."""
    zone_id: str
    strategy_id: str
    query: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "zone_id": "la_losangeles",
                "strategy_id": "uuid-here",
                "query": "plumbers in Los Angeles, CA"
            }
        }


class StartScrapeResponse(BaseModel):
    """Response model for scrape start."""
    session_id: str
    status: str
    message: str
    progress_url: str


class ScrapeStatusResponse(BaseModel):
    """Response model for scrape status."""
    session_id: str
    zone_id: str
    status: str
    progress: dict
    started_at: str | None
    completed_at: str | None
    error: str | None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/start", response_model=StartScrapeResponse)
async def start_scrape(
    request: StartScrapeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start a new scraping operation.
    
    Returns immediately with session_id for progress tracking.
    Actual scraping runs asynchronously in Celery.
    
    Returns:
        Session ID and progress URL
    """
    try:
        # Create scrape session
        session = ScrapeSession(
            zone_id=request.zone_id,
            strategy_id=request.strategy_id,
            status="queued"
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        # Queue async scraping task
        scrape_zone_async.delay(
            session_id=str(session.id),
            zone_id=request.zone_id,
            strategy_id=request.strategy_id,
            query=request.query
        )
        
        logger.info(f"✅ Scrape queued: session {session.id}, zone {request.zone_id}")
        
        return StartScrapeResponse(
            session_id=str(session.id),
            status="queued",
            message="Scraping started successfully",
            progress_url=f"/api/v1/scrapes/{session.id}/progress"
        )
        
    except Exception as e:
        logger.error(f"Failed to start scrape: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scrape: {str(e)}"
        )


@router.get("/{session_id}/status", response_model=ScrapeStatusResponse)
async def get_scrape_status(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current status of a scrape session.
    
    Args:
        session_id: UUID of scrape session
        
    Returns:
        Current status and progress
    """
    result = await db.execute(
        select(ScrapeSession).where(ScrapeSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape session {session_id} not found"
        )
    
    return ScrapeStatusResponse(**session.to_dict())


@router.get("/{session_id}/progress")
async def stream_scrape_progress(
    session_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Stream real-time progress updates via Server-Sent Events (SSE).
    
    The client receives progress events as they occur without polling.
    
    Event types:
    - business_scraped: New business scraped
    - validation_complete: Business validation finished
    - scrape_complete: All scraping finished
    - error: Error occurred
    
    Returns:
        SSE stream of progress events
    """
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from Redis pub/sub."""
        redis = RedisService.get_client()
        pubsub = redis.pubsub()
        channel = f"scrape:progress:{session_id}"
        
        try:
            # Subscribe to Redis channel
            pubsub.subscribe(channel)
            logger.info(f"📡 Client connected to SSE stream: {session_id}")
            
            # Keep connection alive with heartbeat
            last_ping = asyncio.get_event_loop().time()
            
            while True:
                # Check for messages (non-blocking)
                message = pubsub.get_message(ignore_subscribe_messages=True)
                
                if message and message['type'] == 'message':
                    # Send progress event
                    data = message['data']
                    yield f"data: {data}\n\n"
                
                else:
                    # Send heartbeat every 15 seconds
                    now = asyncio.get_event_loop().time()
                    if now - last_ping > 15:
                        yield f": heartbeat\n\n"
                        last_ping = now
                
                # Sleep briefly to avoid busy loop
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            logger.info(f"📴 Client disconnected from SSE stream: {session_id}")
            pubsub.unsubscribe(channel)
            pubsub.close()
            raise
        
        except Exception as e:
            logger.error(f"SSE stream error: {e}", exc_info=True)
            yield f"event: error\ndata: {{\"error\": \"{str(e)}\"}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering
        }
    )
```

---

## 💻 **Module 5: Frontend Real-Time UI**

### Purpose
Display live progress without WebSockets, using native EventSource API

### React Hook for SSE

```typescript
// File: frontend/src/hooks/useScrapeProgress.ts

/**
 * React hook for real-time scrape progress via SSE.
 * 
 * Best Practices:
 * - Clean up connections on unmount
 * - Handle reconnection automatically
 * - Provide loading/error states
 * - Type-safe event handling
 */

import { useState, useEffect, useCallback } from 'react';

export interface ScrapeProgress {
  current: number;
  total: number;
  percentage: number;
}

export interface ScrapeEvent {
  session_id: string;
  event: string;
  data: any;
  timestamp: string;
}

export interface UseScrapeProgressReturn {
  progress: ScrapeProgress | null;
  lastBusiness: { id: string; name: string } | null;
  status: 'connecting' | 'connected' | 'completed' | 'error';
  error: string | null;
  events: ScrapeEvent[];
}

export function useScrapeProgress(
  sessionId: string | null
): UseScrapeProgressReturn {
  const [progress, setProgress] = useState<ScrapeProgress | null>(null);
  const [lastBusiness, setLastBusiness] = useState<any>(null);
  const [status, setStatus] = useState<'connecting' | 'connected' | 'completed' | 'error'>('connecting');
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<ScrapeEvent[]>([]);
  
  useEffect(() => {
    if (!sessionId) return;
    
    const eventSource = new EventSource(
      `/api/v1/scrapes/${sessionId}/progress`,
      { withCredentials: true }
    );
    
    eventSource.onopen = () => {
      console.log('✅ SSE connection opened');
      setStatus('connected');
      setError(null);
    };
    
    eventSource.onmessage = (event) => {
      try {
        const data: ScrapeEvent = JSON.parse(event.data);
        
        // Store event
        setEvents(prev => [...prev, data]);
        
        // Handle specific event types
        switch (data.event) {
          case 'business_scraped':
            setProgress(data.data.progress);
            setLastBusiness({
              id: data.data.business_id,
              name: data.data.business_name
            });
            break;
            
          case 'scrape_complete':
            setStatus('completed');
            eventSource.close();
            break;
            
          case 'error':
            setError(data.data.error);
            setStatus('error');
            eventSource.close();
            break;
        }
        
      } catch (err) {
        console.error('Failed to parse SSE message:', err);
      }
    };
    
    eventSource.onerror = (event) => {
      console.error('❌ SSE connection error:', event);
      setStatus('error');
      setError('Connection lost. Trying to reconnect...');
      eventSource.close();
    };
    
    // Cleanup on unmount
    return () => {
      console.log('📴 Closing SSE connection');
      eventSource.close();
    };
    
  }, [sessionId]);
  
  return {
    progress,
    lastBusiness,
    status,
    error,
    events
  };
}
```

### React Component

```typescript
// File: frontend/src/components/ScrapeProgress.tsx

/**
 * Real-time scrape progress display.
 * 
 * Shows:
 * - Progress bar with percentage
 * - Current business being scraped
 * - Event log (optional)
 * - Status indicators
 */

import React from 'react';
import { useScrapeProgress } from '../hooks/useScrapeProgress';
import { Progress } from './ui/Progress';
import { Alert } from './ui/Alert';
import { Card } from './ui/Card';

interface ScrapeProgressProps {
  sessionId: string;
  onComplete?: () => void;
}

export function ScrapeProgress({ 
  sessionId, 
  onComplete 
}: ScrapeProgressProps) {
  const { progress, lastBusiness, status, error, events } = useScrapeProgress(sessionId);
  
  // Call onComplete when scraping finishes
  React.useEffect(() => {
    if (status === 'completed' && onComplete) {
      onComplete();
    }
  }, [status, onComplete]);
  
  return (
    <Card className="p-6 space-y-4">
      {/* Status Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">
          {status === 'connecting' && '🔄 Connecting...'}
          {status === 'connected' && '📡 Scraping in progress'}
          {status === 'completed' && '✅ Scraping completed'}
          {status === 'error' && '❌ Error occurred'}
        </h3>
        
        {progress && (
          <span className="text-sm text-gray-500">
            {progress.current} / {progress.total}
          </span>
        )}
      </div>
      
      {/* Progress Bar */}
      {progress && (
        <div>
          <Progress value={progress.percentage} className="h-2" />
          <p className="text-sm text-gray-600 mt-2">
            {progress.percentage.toFixed(1)}% complete
          </p>
        </div>
      )}
      
      {/* Current Business */}
      {lastBusiness && status === 'connected' && (
        <div className="bg-blue-50 p-3 rounded-md">
          <p className="text-sm font-medium text-blue-900">
            Currently scraping:
          </p>
          <p className="text-sm text-blue-700">
            {lastBusiness.name}
          </p>
        </div>
      )}
      
      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <p>{error}</p>
        </Alert>
      )}
      
      {/* Event Log (Optional - for debugging) */}
      {process.env.NODE_ENV === 'development' && (
        <details className="text-xs">
          <summary className="cursor-pointer text-gray-500">
            View event log ({events.length} events)
          </summary>
          <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
            {events.map((event, i) => (
              <div key={i} className="bg-gray-100 p-2 rounded">
                <span className="font-mono">{event.event}</span>
                <span className="text-gray-500 ml-2">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </details>
      )}
    </Card>
  );
}
```

### Usage in Page

```typescript
// File: frontend/src/pages/IntelligentCampaigns.tsx

import { useState } from 'react';
import { ScrapeProgress } from '../components/ScrapeProgress';
import { startScrape } from '../api/scrapes';

export function IntelligentCampaigns() {
  const [scrapeSessionId, setScrapeSessionId] = useState<string | null>(null);
  const [isScraping, setIsScraping] = useState(false);
  
  const handleStartScrape = async (zoneId: string) => {
    try {
      setIsScraping(true);
      
      const response = await startScrape({
        zone_id: zoneId,
        strategy_id: currentStrategy.id,
        query: `plumbers in ${zoneId}`
      });
      
      // Store session ID to start SSE stream
      setScrapeSessionId(response.session_id);
      
    } catch (error) {
      console.error('Failed to start scrape:', error);
      setIsScraping(false);
    }
  };
  
  const handleScrapeComplete = () => {
    setIsScraping(false);
    setScrapeSessionId(null);
    // Refresh data, show success message, etc.
  };
  
  return (
    <div>
      <button 
        onClick={() => handleStartScrape('la_losangeles')}
        disabled={isScraping}
      >
        {isScraping ? 'Scraping...' : 'Start Scrape'}
      </button>
      
      {scrapeSessionId && (
        <ScrapeProgress 
          sessionId={scrapeSessionId}
          onComplete={handleScrapeComplete}
        />
      )}
    </div>
  );
}
```

---

## 🔧 **Module 6: Queue Configuration**

### Purpose
Separate Celery queues for different task types

### Celery Configuration

```python
# File: backend/celery_app.py (additions)

# Define queue routing
celery_app.conf.task_routes = {
    # Queue 1: Outscraper scraping (I/O bound, slow)
    'tasks.scraping.scrape_zone_async': {
        'queue': 'scraping',
        'priority': 5
    },
    
    # Queue 2: URL validation (CPU + I/O bound, medium)
    'tasks.validation_tasks_enhanced.validate_business_website_v2': {
        'queue': 'validation',
        'priority': 7
    },
    'tasks.validation_tasks_enhanced.batch_validate_websites_v2': {
        'queue': 'validation',
        'priority': 7
    },
    
    # Queue 3: Website discovery (I/O bound, slow)
    'tasks.discovery_tasks.discover_missing_websites_v2': {
        'queue': 'discovery',
        'priority': 6
    },
}

# Set queue priorities (0-10, 10 = highest)
celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5
```

### Supervisor Configuration

```ini
# File: /etc/supervisor/conf.d/webmagic-celery.conf

[program:webmagic-celery-scraping]
command=/var/www/webmagic/backend/.venv/bin/celery -A celery_app worker 
  --loglevel=info 
  --concurrency=2
  --queue=scraping
  -n scraping@%%h
directory=/var/www/webmagic/backend
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/webmagic/celery-scraping.log
stderr_logfile=/var/log/webmagic/celery-scraping-error.log

[program:webmagic-celery-validation]
command=/var/www/webmagic/backend/.venv/bin/celery -A celery_app worker 
  --loglevel=info 
  --concurrency=8
  --queue=validation
  -n validation@%%h
directory=/var/www/webmagic/backend
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/webmagic/celery-validation.log
stderr_logfile=/var/log/webmagic/celery-validation-error.log

[program:webmagic-celery-discovery]
command=/var/www/webmagic/backend/.venv/bin/celery -A celery_app worker 
  --loglevel=info 
  --concurrency=4
  --queue=discovery
  -n discovery@%%h
directory=/var/www/webmagic/backend
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/webmagic/celery-discovery.log
stderr_logfile=/var/log/webmagic/celery-discovery-error.log

[program:webmagic-celery-beat]
command=/var/www/webmagic/backend/.venv/bin/celery -A celery_app beat 
  --loglevel=info
directory=/var/www/webmagic/backend
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/webmagic/celery-beat.log
stderr_logfile=/var/log/webmagic/celery-beat-error.log
```

---

## ✅ **Best Practices Summary**

### Separation of Concerns
- **Models**: Data structure only
- **Services**: Business logic, reusable
- **Tasks**: Async operations, Celery-specific
- **API**: Request handling, validation
- **Frontend**: UI/UX, no business logic

### Modular Code
- Each module has single responsibility
- Clear interfaces between modules
- Easy to test independently
- Can be developed in parallel

### Readable Functions
- Descriptive names
- Type hints everywhere
- Docstrings with purpose, args, returns
- Maximum ~50 lines per function

### Error Handling
- Try/except at each layer
- Graceful degradation
- User-friendly error messages
- Comprehensive logging

---

## 📅 **Implementation Timeline**

### Day 1 (3-4 hours)
- [ ] Module 1: Database migration + Model
- [ ] Module 2: Redis services
- [ ] Module 3: Async scraping task (basic)

### Day 2 (3-4 hours)
- [ ] Module 4: SSE endpoint
- [ ] Module 5: Frontend hook + component
- [ ] Module 6: Queue configuration
- [ ] Integration testing

---

## 🧪 **Testing Plan**

### Unit Tests
- ProgressPublisher
- RedisService fallback
- Session status transitions

### Integration Tests
- Full scrape flow end-to-end
- SSE connection and events
- Queue routing

### Manual Tests
1. Start scrape, watch progress bar
2. Disconnect/reconnect SSE stream
3. Multiple concurrent scrapes
4. Error scenarios (Outscraper down, Redis down)

---

**Ready to begin implementation?** 🚀
