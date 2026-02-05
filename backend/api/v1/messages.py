"""
SMS Messages API endpoints - Inbox functionality.

Provides endpoints to view and manage SMS messages.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from pydantic import BaseModel

from core.database import get_db
from api.deps import get_current_user
from models.sms_message import SMSMessage
from models.business import Business
from models.user import AdminUser

router = APIRouter(prefix="/messages", tags=["SMS Messages"])


# ============================================================================
# SCHEMAS
# ============================================================================

class SMSMessageResponse(BaseModel):
    """Single SMS message response."""
    id: UUID
    campaign_id: Optional[UUID] = None
    business_id: Optional[UUID] = None
    direction: str
    from_phone: str
    to_phone: str
    body: str
    status: str
    telnyx_message_id: Optional[str] = None
    segments: Optional[int] = None
    cost: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    received_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime
    
    # Business info (if linked)
    business_name: Optional[str] = None
    business_city: Optional[str] = None
    business_state: Optional[str] = None
    
    class Config:
        from_attributes = True


class SMSMessageListResponse(BaseModel):
    """List of SMS messages with pagination."""
    messages: List[SMSMessageResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SMSStatsResponse(BaseModel):
    """SMS statistics."""
    total_messages: int
    inbound_count: int
    outbound_count: int
    delivered_count: int
    failed_count: int
    opt_out_count: int
    total_cost: float
    avg_cost_per_message: float
    
    # Recent activity
    messages_today: int
    messages_this_week: int
    inbound_today: int


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=SMSMessageListResponse)
async def list_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    direction: Optional[str] = Query(None, description="Filter: inbound, outbound"),
    status: Optional[str] = Query(None, description="Filter by status"),
    business_id: Optional[UUID] = Query(None, description="Filter by business"),
    search: Optional[str] = Query(None, description="Search in message body or phone"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    List all SMS messages with pagination and filtering.
    
    Returns messages sorted by created_at (newest first).
    """
    # Base query
    query = select(SMSMessage).order_by(desc(SMSMessage.created_at))
    count_query = select(func.count(SMSMessage.id))
    
    # Apply filters
    if direction:
        query = query.where(SMSMessage.direction == direction)
        count_query = count_query.where(SMSMessage.direction == direction)
    
    if status:
        query = query.where(SMSMessage.status == status)
        count_query = count_query.where(SMSMessage.status == status)
    
    if business_id:
        query = query.where(SMSMessage.business_id == business_id)
        count_query = count_query.where(SMSMessage.business_id == business_id)
    
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (SMSMessage.body.ilike(search_filter)) |
            (SMSMessage.from_phone.ilike(search_filter)) |
            (SMSMessage.to_phone.ilike(search_filter))
        )
        count_query = count_query.where(
            (SMSMessage.body.ilike(search_filter)) |
            (SMSMessage.from_phone.ilike(search_filter)) |
            (SMSMessage.to_phone.ilike(search_filter))
        )
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    skip = (page - 1) * page_size
    query = query.offset(skip).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    messages = result.scalars().all()
    
    # Fetch business info for each message
    response_messages = []
    for msg in messages:
        msg_dict = {
            "id": msg.id,
            "campaign_id": msg.campaign_id,
            "business_id": msg.business_id,
            "direction": msg.direction,
            "from_phone": msg.from_phone,
            "to_phone": msg.to_phone,
            "body": msg.body,
            "status": msg.status,
            "telnyx_message_id": msg.telnyx_message_id,
            "segments": msg.segments,
            "cost": float(msg.cost) if msg.cost else None,
            "error_code": msg.error_code,
            "error_message": msg.error_message,
            "received_at": msg.received_at,
            "sent_at": msg.sent_at,
            "delivered_at": msg.delivered_at,
            "created_at": msg.created_at,
            "business_name": None,
            "business_city": None,
            "business_state": None,
        }
        
        # Get business info if linked
        if msg.business_id:
            bus_result = await db.execute(
                select(Business).where(Business.id == msg.business_id)
            )
            business = bus_result.scalar_one_or_none()
            if business:
                msg_dict["business_name"] = business.name
                msg_dict["business_city"] = business.city
                msg_dict["business_state"] = business.state
        
        response_messages.append(SMSMessageResponse(**msg_dict))
    
    pages = (total + page_size - 1) // page_size
    
    return SMSMessageListResponse(
        messages=response_messages,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/stats", response_model=SMSStatsResponse)
async def get_message_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get SMS message statistics.
    """
    # Total counts
    total_result = await db.execute(select(func.count(SMSMessage.id)))
    total_messages = total_result.scalar() or 0
    
    # Direction counts
    inbound_result = await db.execute(
        select(func.count(SMSMessage.id)).where(SMSMessage.direction == "inbound")
    )
    inbound_count = inbound_result.scalar() or 0
    
    outbound_result = await db.execute(
        select(func.count(SMSMessage.id)).where(SMSMessage.direction == "outbound")
    )
    outbound_count = outbound_result.scalar() or 0
    
    # Status counts
    delivered_result = await db.execute(
        select(func.count(SMSMessage.id)).where(SMSMessage.status == "delivered")
    )
    delivered_count = delivered_result.scalar() or 0
    
    failed_result = await db.execute(
        select(func.count(SMSMessage.id)).where(SMSMessage.status == "failed")
    )
    failed_count = failed_result.scalar() or 0
    
    # Opt-out count (inbound messages with STOP keywords)
    # This is a simplified check - actual opt-outs are in sms_opt_outs table
    from models.sms_opt_out import SMSOptOut
    opt_out_result = await db.execute(select(func.count(SMSOptOut.id)))
    opt_out_count = opt_out_result.scalar() or 0
    
    # Cost stats
    cost_result = await db.execute(
        select(func.sum(SMSMessage.cost)).where(SMSMessage.cost.isnot(None))
    )
    total_cost = float(cost_result.scalar() or 0)
    
    avg_cost = total_cost / outbound_count if outbound_count > 0 else 0
    
    # Recent activity
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    
    today_result = await db.execute(
        select(func.count(SMSMessage.id)).where(SMSMessage.created_at >= today)
    )
    messages_today = today_result.scalar() or 0
    
    week_result = await db.execute(
        select(func.count(SMSMessage.id)).where(SMSMessage.created_at >= week_ago)
    )
    messages_this_week = week_result.scalar() or 0
    
    inbound_today_result = await db.execute(
        select(func.count(SMSMessage.id)).where(
            SMSMessage.created_at >= today,
            SMSMessage.direction == "inbound"
        )
    )
    inbound_today = inbound_today_result.scalar() or 0
    
    return SMSStatsResponse(
        total_messages=total_messages,
        inbound_count=inbound_count,
        outbound_count=outbound_count,
        delivered_count=delivered_count,
        failed_count=failed_count,
        opt_out_count=opt_out_count,
        total_cost=total_cost,
        avg_cost_per_message=avg_cost,
        messages_today=messages_today,
        messages_this_week=messages_this_week,
        inbound_today=inbound_today
    )


@router.get("/{message_id}", response_model=SMSMessageResponse)
async def get_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get a single SMS message by ID.
    """
    result = await db.execute(
        select(SMSMessage).where(SMSMessage.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Message not found")
    
    msg_dict = {
        "id": message.id,
        "campaign_id": message.campaign_id,
        "business_id": message.business_id,
        "direction": message.direction,
        "from_phone": message.from_phone,
        "to_phone": message.to_phone,
        "body": message.body,
        "status": message.status,
        "telnyx_message_id": message.telnyx_message_id,
        "segments": message.segments,
        "cost": float(message.cost) if message.cost else None,
        "error_code": message.error_code,
        "error_message": message.error_message,
        "received_at": message.received_at,
        "sent_at": message.sent_at,
        "delivered_at": message.delivered_at,
        "created_at": message.created_at,
        "business_name": None,
        "business_city": None,
        "business_state": None,
    }
    
    # Get business info if linked
    if message.business_id:
        bus_result = await db.execute(
            select(Business).where(Business.id == message.business_id)
        )
        business = bus_result.scalar_one_or_none()
        if business:
            msg_dict["business_name"] = business.name
            msg_dict["business_city"] = business.city
            msg_dict["business_state"] = business.state
    
    return SMSMessageResponse(**msg_dict)


@router.get("/business/{business_id}", response_model=SMSMessageListResponse)
async def get_business_messages(
    business_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get all SMS messages for a specific business (conversation view).
    """
    # Redirect to main list with business filter
    return await list_messages(
        page=page,
        page_size=page_size,
        direction=None,
        status=None,
        business_id=business_id,
        search=None,
        db=db,
        current_user=current_user
    )

