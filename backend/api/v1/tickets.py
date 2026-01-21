"""
Support Ticket API Endpoints

Customer-facing API for creating and managing support tickets.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
import logging

from core.database import get_db
from core.customer_security import get_current_customer
from core.exceptions import NotFoundError, ValidationError, ForbiddenError
from api.schemas.ticket import (
    TicketCreateRequest,
    TicketMessageCreate,
    TicketStatusUpdate,
    TicketResponse,
    TicketListResponse,
    TicketStatsResponse,
    TicketCategoriesResponse,
    TicketMessageResponse,
    MessageResponse,
    ErrorResponse
)
from models.site_models import CustomerUser
from services.support.ticket_service import TicketService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["Support Tickets"])


@router.get(
    "/categories",
    response_model=TicketCategoriesResponse,
    summary="Get available ticket categories"
)
async def get_ticket_categories():
    """
    Get list of available ticket categories with descriptions.
    """
    return TicketCategoriesResponse(
        categories=TicketService.CATEGORIES,
        descriptions={
            "billing": "Questions about payments, subscriptions, invoices, or billing issues",
            "technical_support": "Technical problems with your website or platform features",
            "site_edit": "Requests for changes or updates to your website",
            "question": "General questions about features, how-to guides, or information",
            "other": "Any other topic not covered by the above categories"
        }
    )


@router.post(
    "/",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new support ticket",
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Site not owned by customer"}
    }
)
async def create_ticket(
    request: TicketCreateRequest,
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new support ticket.
    
    - **subject**: Brief summary of the issue (5-255 characters)
    - **description**: Detailed description of the issue (minimum 10 characters)
    - **category**: One of: billing, technical_support, site_edit, question, other
    - **site_id**: Optional - include if ticket is about a specific site
    
    The ticket will be automatically processed by AI to:
    - Verify the category is correct
    - Assign appropriate priority
    - Generate an initial response for simple questions
    """
    try:
        ticket = await TicketService.create_ticket(
            db=db,
            customer_user_id=current_customer.id,
            subject=request.subject,
            description=request.description,
            category=request.category,
            site_id=request.site_id
        )
        
        logger.info(
            f"Ticket {ticket.ticket_number} created by customer {current_customer.email} "
            f"(category: {ticket.category})"
        )
        
        return ticket
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ticket"
        )


@router.get(
    "/",
    response_model=TicketListResponse,
    summary="List customer's tickets",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    }
)
async def list_tickets(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a list of tickets for the authenticated customer.
    
    Supports filtering by status and category, with pagination.
    Results are ordered by creation date (newest first).
    """
    try:
        tickets, total = await TicketService.list_customer_tickets(
            db=db,
            customer_user_id=current_customer.id,
            status=status_filter,
            category=category,
            limit=limit,
            offset=offset
        )
        
        return TicketListResponse(
            tickets=tickets,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error listing tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tickets"
        )


@router.get(
    "/stats",
    response_model=TicketStatsResponse,
    summary="Get ticket statistics",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    }
)
async def get_ticket_stats(
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Get ticket statistics for the authenticated customer.
    
    Returns counts by status and category, plus aggregated metrics.
    """
    try:
        stats = await TicketService.get_ticket_stats(
            db=db,
            customer_user_id=current_customer.id
        )
        
        return TicketStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting ticket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ticket statistics"
        )


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Get ticket details",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Ticket not found"}
    }
)
async def get_ticket(
    ticket_id: UUID,
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific ticket, including all messages.
    
    Only accessible to the customer who created the ticket.
    """
    try:
        ticket = await TicketService.get_ticket_by_id(
            db=db,
            ticket_id=ticket_id,
            customer_user_id=current_customer.id
        )
        
        return ticket
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ticket"
        )


@router.post(
    "/{ticket_id}/messages",
    response_model=TicketMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add message to ticket",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Ticket not found"}
    }
)
async def add_ticket_message(
    ticket_id: UUID,
    request: TicketMessageCreate,
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a message to an existing ticket.
    
    This will reopen the ticket if it was in a waiting or resolved state.
    """
    try:
        # Verify customer owns the ticket first
        ticket = await TicketService.get_ticket_by_id(
            db=db,
            ticket_id=ticket_id,
            customer_user_id=current_customer.id
        )
        
        # Add message
        message = await TicketService.add_message(
            db=db,
            ticket_id=ticket_id,
            message=request.message,
            author_id=current_customer.id,
            author_type="customer"
        )
        
        logger.info(
            f"Customer {current_customer.email} added message to ticket {ticket.ticket_number}"
        )
        
        return message
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding message to ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add message"
        )


@router.patch(
    "/{ticket_id}/status",
    response_model=TicketResponse,
    summary="Update ticket status",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid status"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Ticket not found"}
    }
)
async def update_ticket_status(
    ticket_id: UUID,
    request: TicketStatusUpdate,
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the status of a ticket.
    
    Customers can typically only move tickets to 'resolved' or 'closed'.
    Other status changes are handled automatically or by staff.
    """
    try:
        # Customers should only be able to close/resolve their own tickets
        allowed_statuses = ["resolved", "closed"]
        if request.status not in allowed_statuses:
            raise ValidationError(
                f"Customers can only set status to: {', '.join(allowed_statuses)}"
            )
        
        ticket = await TicketService.update_ticket_status(
            db=db,
            ticket_id=ticket_id,
            new_status=request.status,
            customer_user_id=current_customer.id
        )
        
        logger.info(
            f"Customer {current_customer.email} updated ticket {ticket.ticket_number} "
            f"status to {request.status}"
        )
        
        return ticket
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating ticket {ticket_id} status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update ticket status"
        )

