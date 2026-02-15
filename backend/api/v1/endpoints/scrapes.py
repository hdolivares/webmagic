"""
Scraping API Endpoints.

Purpose:
    Manage scraping operations with real-time progress tracking via SSE.
    Provides non-blocking scraping with Server-Sent Events for updates.

Best Practices:
    - RESTful design (POST to start, GET for status/progress)
    - Clear error responses with status codes
    - Async/await for I/O operations
    - Type hints and Pydantic validation
    - Comprehensive logging
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from core.database import get_db
from api.deps import get_current_user
from models.user import AdminUser
from models.scrape_session import ScrapeSession
from services.progress.redis_service import RedisService
from tasks.scraping_tasks import scrape_zone_async

router = APIRouter(prefix="/scrapes", tags=["scrapes"])
logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class StartScrapeRequest(BaseModel):
    """Request model for starting a scrape operation."""
    
    zone_id: str = Field(
        ...,
        description="Geographic zone identifier",
        examples=["la_losangeles", "la_pasadena"]
    )
    
    city: str = Field(
        ...,
        description="City name",
        examples=["Los Angeles", "Pasadena"]
    )
    
    state: str = Field(
        ...,
        description="State code",
        examples=["CA", "NY"]
    )
    
    category: str = Field(
        ...,
        description="Business category to scrape",
        examples=["plumbers", "lawyers", "accountants"]
    )
    
    country: str = Field(
        default="US",
        description="Country code"
    )
    
    limit_per_zone: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum businesses per zone"
    )
    
    strategy_id: Optional[str] = Field(
        default=None,
        description="Existing strategy UUID (optional)"
    )


class StartScrapeResponse(BaseModel):
    """Response model for scrape start."""
    
    session_id: str = Field(description="Scrape session UUID")
    status: str = Field(description="Initial status (queued)")
    message: str = Field(description="Human-readable message")
    progress_url: str = Field(description="SSE endpoint for real-time updates")
    status_url: str = Field(description="REST endpoint for status queries")


class ScrapeStatusResponse(BaseModel):
    """Response model for scrape status."""
    
    session_id: str
    zone_id: str
    status: str
    progress: dict
    timestamps: dict
    error: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/start", response_model=StartScrapeResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_scrape(
    request: StartScrapeRequest,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start a new scraping operation.
    
    Returns immediately with session ID for progress tracking.
    Actual scraping runs asynchronously in Celery.
    
    **Flow:**
    1. Creates scrape_session record
    2. Queues async Celery task
    3. Returns session_id and progress URL
    4. Client subscribes to SSE stream for updates
    
    **Returns:**
    - 202 Accepted: Scrape queued successfully
    - 400 Bad Request: Invalid parameters
    - 500 Internal Server Error: System error
    """
    try:
        logger.info(
            f"📨 Scrape request received: zone={request.zone_id}, "
            f"category={request.category}, user={current_user.email}"
        )
        
        # Create scrape session
        session = ScrapeSession(
            zone_id=request.zone_id,
            strategy_id=request.strategy_id,
            status="queued",
            meta={
                "city": request.city,
                "state": request.state,
                "category": request.category,
                "country": request.country,
                "limit_per_zone": request.limit_per_zone,
                "user_id": str(current_user.id)
            }
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        logger.info(f"✅ Created scrape session: {session.id}")
        
        # Queue async scraping task
        task = scrape_zone_async.delay(
            session_id=str(session.id),
            city=request.city,
            state=request.state,
            category=request.category,
            country=request.country,
            limit_per_zone=request.limit_per_zone,
            zone_id=request.zone_id,
            strategy_id=request.strategy_id
        )
        
        logger.info(
            f"🚀 Scrape task queued: session={session.id}, "
            f"task={task.id}, queue=scraping"
        )
        
        return StartScrapeResponse(
            session_id=str(session.id),
            status="queued",
            message="Scraping started successfully. Use progress_url to track real-time updates.",
            progress_url=f"/api/v1/scrapes/{session.id}/progress",
            status_url=f"/api/v1/scrapes/{session.id}/status"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start scrape: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scrape: {str(e)}"
        )


@router.get("/{session_id}/status", response_model=ScrapeStatusResponse)
async def get_scrape_status(
    session_id: UUID,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current status of a scrape session.
    
    **Polling endpoint** - for clients that don't support SSE.
    Use the `/progress` SSE endpoint for real-time updates instead.
    
    **Args:**
    - session_id: UUID of scrape session
    
    **Returns:**
    - 200 OK: Status retrieved
    - 404 Not Found: Session doesn't exist
    """
    result = await db.execute(
        select(ScrapeSession).where(ScrapeSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        logger.warning(f"⚠️ Session not found: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape session {session_id} not found"
        )
    
    logger.debug(f"📊 Status query: session={session_id}, status={session.status}")
    
    return ScrapeStatusResponse(**session.to_dict())


@router.get("/{session_id}/progress")
async def stream_scrape_progress(
    session_id: UUID,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stream real-time progress updates via Server-Sent Events (SSE).
    
    **Event Stream** - maintains persistent connection to send updates.
    
    **Event types:**
    - `scraping_started`: Outscraper search began
    - `business_scraped`: New business scraped (includes progress %)
    - `validation_started`: Validation phase started
    - `validation_complete`: Business validation finished
    - `scrape_complete`: All scraping finished (close connection)
    - `error`: Error occurred
    - `heartbeat`: Keep-alive ping (every 15s)
    
    **Connection:**
    - Frontend: `new EventSource('/api/v1/scrapes/{id}/progress')`
    - Auto-reconnects on disconnect
    - Close on `scrape_complete` or `error` events
    
    **Returns:**
    - 200 OK: SSE stream
    - 404 Not Found: Session doesn't exist
    """
    # Verify session exists
    result = await db.execute(
        select(ScrapeSession).where(ScrapeSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape session {session_id} not found"
        )
    
    logger.info(f"📡 SSE client connected: session={session_id}, user={current_user.email}")
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """
        Generate SSE events from Redis pub/sub.
        
        Yields:
            SSE-formatted strings: "data: {json}\n\n"
        """
        redis = RedisService.get_client()
        
        # Check if Redis is available
        if not RedisService.is_available():
            logger.warning("⚠️ Redis unavailable, SSE will not receive updates")
            yield f"event: error\ndata: {{\"error\": \"Progress tracking unavailable\"}}\n\n"
            return
        
        pubsub = redis.pubsub()
        channel = f"scrape:progress:{session_id}"
        
        try:
            # Subscribe to Redis channel
            pubsub.subscribe(channel)
            logger.info(f"📻 Subscribed to Redis channel: {channel}")
            
            # Send initial connection success
            yield f"event: connected\ndata: {{\"session_id\": \"{session_id}\"}}\n\n"
            
            # Keep connection alive with heartbeat
            last_ping = asyncio.get_event_loop().time()
            
            while True:
                # Check for messages (non-blocking)
                message = pubsub.get_message(ignore_subscribe_messages=True)
                
                if message and message['type'] == 'message':
                    # Parse message data
                    try:
                        data = json.loads(message['data'])
                        event_type = data.get('event', 'update')
                        
                        # Send SSE event
                        yield f"event: {event_type}\ndata: {message['data']}\n\n"
                        
                        logger.debug(f"📤 SSE event sent: {event_type}")
                        
                        # Close connection on completion or error
                        if event_type in ('scrape_complete', 'error'):
                            logger.info(f"🏁 Closing SSE stream: {event_type}")
                            break
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Redis message: {e}")
                
                else:
                    # Send heartbeat every 15 seconds
                    now = asyncio.get_event_loop().time()
                    if now - last_ping > 15:
                        yield f": heartbeat\n\n"
                        last_ping = now
                
                # Sleep briefly to avoid busy loop
                await asyncio.sleep(0.1)
            
        except asyncio.CancelledError:
            logger.info(f"📴 SSE client disconnected: session={session_id}")
            raise
        
        except Exception as e:
            logger.error(f"❌ SSE stream error: {e}", exc_info=True)
            yield f"event: error\ndata: {{\"error\": \"{str(e)}\"}}\n\n"
        
        finally:
            try:
                pubsub.unsubscribe(channel)
                pubsub.close()
                logger.info(f"🔌 Redis channel unsubscribed: {channel}")
            except Exception as e:
                logger.error(f"Error closing pubsub: {e}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Access-Control-Allow-Origin": "*",  # CORS for dev (restrict in prod)
        }
    )


@router.get("/", response_model=list[ScrapeStatusResponse])
async def list_scrape_sessions(
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    status_filter: Optional[str] = None
):
    """
    List recent scrape sessions.
    
    **Args:**
    - limit: Maximum results (default 20, max 100)
    - status_filter: Filter by status (queued, scraping, completed, failed)
    
    **Returns:**
    - 200 OK: List of sessions
    """
    query = select(ScrapeSession).order_by(ScrapeSession.created_at.desc()).limit(min(limit, 100))
    
    if status_filter:
        query = query.where(ScrapeSession.status == status_filter)
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    return [ScrapeStatusResponse(**session.to_dict()) for session in sessions]
