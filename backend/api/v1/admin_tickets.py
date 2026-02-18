"""
Admin Support Ticket API Endpoints

Admin-only endpoints for viewing, managing, and responding to all support tickets.
Includes site-edit apply/reject workflow and AI analysis surfacing.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

from core.database import get_db
from api.deps import get_current_user
from core.exceptions import NotFoundError, ValidationError, ForbiddenError
from api.schemas.ticket import (
    TicketResponse,
    TicketMessageResponse,
    TicketMessageCreate,
    MessageResponse,
    ErrorResponse,
)
from pydantic import BaseModel, Field
from models.user import AdminUser
from services.support.ticket_service import TicketService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/tickets", tags=["Admin — Support Tickets"])


# ── Request/Response schemas specific to admin ────────────────────────────────

class AdminTicketListItem(BaseModel):
    """Lightweight ticket item for the admin list view."""
    id: UUID
    ticket_number: str
    subject: str
    category: str
    priority: str
    status: str
    ai_processed: bool = False
    site_slug: Optional[str] = None
    site_title: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    assigned_to_admin_id: Optional[UUID] = None
    created_at: datetime
    last_customer_message_at: Optional[datetime] = None
    last_staff_message_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminTicketListResponse(BaseModel):
    tickets: List[AdminTicketListItem]
    total: int
    limit: int
    offset: int


class AdminTicketDetailResponse(TicketResponse):
    """Full admin detail — includes customer and site info."""
    site_slug: Optional[str] = None
    site_title: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None

    class Config:
        from_attributes = True


class AdminStatusUpdate(BaseModel):
    status: str = Field(..., description="New ticket status")


class AdminAssignRequest(BaseModel):
    admin_user_id: Optional[UUID] = Field(None, description="Admin to assign; null to unassign")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _enrich_ticket(ticket) -> dict:
    """Add site/customer info to a ticket dict for admin display."""
    data = {
        "id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "subject": ticket.subject,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "ai_processed": ticket.ai_processed or False,
        "site_slug": ticket.site.slug if ticket.site else None,
        "site_title": ticket.site.site_title if ticket.site else None,
        "customer_name": (
            ticket.customer_user.full_name if ticket.customer_user else None
        ),
        "customer_email": (
            ticket.customer_user.email if ticket.customer_user else None
        ),
        "assigned_to_admin_id": ticket.assigned_to_admin_id,
        "created_at": ticket.created_at,
        "last_customer_message_at": ticket.last_customer_message_at,
        "last_staff_message_at": ticket.last_staff_message_at,
    }
    return data


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=AdminTicketListResponse,
    summary="List all support tickets (admin)",
)
async def list_all_tickets(
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    site_slug: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search ticket number or subject"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Paginated list of all support tickets across all customers.
    Filterable by status, category, priority, site_slug, and free-text search.
    """
    try:
        tickets, total = await TicketService.list_all_tickets(
            db=db,
            status=status_filter,
            category=category,
            priority=priority,
            site_slug=site_slug,
            search=search,
            limit=limit,
            offset=offset,
        )

        items = [AdminTicketListItem(**_enrich_ticket(t)) for t in tickets]
        return AdminTicketListResponse(tickets=items, total=total, limit=limit, offset=offset)

    except Exception as e:
        logger.error(f"Error listing admin tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list tickets")


@router.get(
    "/{ticket_id}",
    response_model=AdminTicketDetailResponse,
    summary="Get full ticket details (admin)",
)
async def get_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Get complete ticket details including all messages and full AI analysis.
    The response includes ai_suggested_response, ai_category_confidence, and
    ai_processing_notes for the admin AI analysis panel.
    """
    try:
        ticket = await TicketService.get_ticket_by_id(db=db, ticket_id=ticket_id)
        enriched = _enrich_ticket(ticket)
        enriched.update({
            "customer_user_id": ticket.customer_user_id,
            "site_id": ticket.site_id,
            "description": ticket.description,
            "ai_category_confidence": ticket.ai_category_confidence,
            "ai_suggested_response": ticket.ai_suggested_response,
            "ai_processing_notes": ticket.ai_processing_notes,
            "assigned_at": ticket.assigned_at,
            "first_response_at": ticket.first_response_at,
            "resolved_at": ticket.resolved_at,
            "closed_at": ticket.closed_at,
            "customer_satisfaction_rating": ticket.customer_satisfaction_rating,
            "internal_notes": ticket.internal_notes,
            "tags": ticket.tags,
            "updated_at": ticket.updated_at,
            "messages": [
                TicketMessageResponse.model_validate(m) for m in ticket.messages
                if not m.internal_only
            ],
        })
        return AdminTicketDetailResponse(**enriched)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get ticket")


@router.post(
    "/{ticket_id}/messages",
    response_model=TicketMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add staff reply to ticket",
)
async def reply_to_ticket(
    ticket_id: UUID,
    request: TicketMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Post a staff reply to a customer's ticket.
    Automatically notifies the customer by email.
    """
    try:
        message = await TicketService.add_message(
            db=db,
            ticket_id=ticket_id,
            message=request.message,
            author_id=current_user.id,
            author_type="staff",
        )
        logger.info(f"Admin {current_user.email} replied to ticket {ticket_id}")
        return message
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error replying to ticket {ticket_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add reply")


@router.patch(
    "/{ticket_id}/status",
    response_model=dict,
    summary="Update ticket status (admin)",
)
async def update_ticket_status(
    ticket_id: UUID,
    request: AdminStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Admin can set any ticket status (no customer restriction).
    """
    try:
        ticket = await TicketService.update_ticket_status(
            db=db,
            ticket_id=ticket_id,
            new_status=request.status,
        )
        logger.info(f"Admin {current_user.email} set ticket {ticket_id} to {request.status}")
        return {"id": str(ticket.id), "status": ticket.status, "ticket_number": ticket.ticket_number}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating ticket status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update status")


@router.patch(
    "/{ticket_id}/assign",
    response_model=dict,
    summary="Assign ticket to admin user",
)
async def assign_ticket(
    ticket_id: UUID,
    request: AdminAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Assign (or unassign) a ticket to an admin user.
    """
    from sqlalchemy import select
    from models.support_ticket import SupportTicket

    try:
        result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        ticket.assigned_to_admin_id = request.admin_user_id
        ticket.assigned_at = datetime.now(timezone.utc) if request.admin_user_id else None
        await db.commit()

        logger.info(
            f"Admin {current_user.email} assigned ticket {ticket_id} to {request.admin_user_id}"
        )
        return {
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "assigned_to_admin_id": str(request.admin_user_id) if request.admin_user_id else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to assign ticket")


@router.post(
    "/{ticket_id}/apply-edit",
    response_model=dict,
    summary="Apply AI-proposed site edit",
)
async def apply_site_edit(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    For site_edit tickets: promote the AI-proposed preview SiteVersion to live,
    deploy to disk, notify the customer, and resolve the ticket.
    """
    try:
        ticket = await TicketService.apply_site_edit(
            db=db,
            ticket_id=ticket_id,
            admin_user_id=current_user.id,
        )
        logger.info(
            f"Admin {current_user.email} applied site edit for ticket {ticket_id}"
        )
        return {
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "status": ticket.status,
            "message": "Site edit applied and deployed successfully.",
        }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error applying site edit for ticket {ticket_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to apply site edit")
