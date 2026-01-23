"""
Support Ticket Service

Handles ticket creation, AI categorization, message management, and status updates.
"""
import logging
import secrets
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from models.support_ticket import SupportTicket, TicketMessage, TicketTemplate
from models.site_models import CustomerUser, Site
from core.exceptions import NotFoundError, ValidationError, ForbiddenError
from anthropic import AsyncAnthropic
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TicketService:
    """Service for managing support tickets."""
    
    # Ticket categories
    CATEGORIES = [
        "billing",
        "technical_support",
        "site_edit",
        "question",
        "other"
    ]
    
    # Ticket statuses
    STATUSES = [
        "new",
        "in_progress",
        "waiting_customer",
        "waiting_ai",
        "resolved",
        "closed"
    ]
    
    # Priority levels
    PRIORITIES = [
        "low",
        "medium",
        "high",
        "urgent"
    ]
    
    @staticmethod
    def _generate_ticket_number() -> str:
        """Generate a unique ticket number."""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d')
        random_part = secrets.token_hex(3).upper()
        return f"TKT-{timestamp}-{random_part}"
    
    @staticmethod
    async def create_ticket(
        db: AsyncSession,
        customer_user_id: UUID,
        subject: str,
        description: str,
        category: str,
        site_id: Optional[UUID] = None
    ) -> SupportTicket:
        """
        Create a new support ticket.
        
        Args:
            db: Database session
            customer_user_id: ID of the customer creating the ticket
            subject: Ticket subject
            description: Ticket description
            category: Ticket category
            site_id: Optional site ID if ticket is site-specific
            
        Returns:
            Created SupportTicket instance
        """
        # Validate category
        if category not in TicketService.CATEGORIES:
            raise ValidationError(f"Invalid category. Must be one of: {', '.join(TicketService.CATEGORIES)}")
        
        # Verify customer exists
        customer_stmt = select(CustomerUser).where(CustomerUser.id == customer_user_id)
        customer_result = await db.execute(customer_stmt)
        customer = customer_result.scalar_one_or_none()
        
        if not customer:
            raise NotFoundError("Customer not found")
        
        # Verify site ownership if site_id provided
        if site_id:
            site_stmt = select(Site).where(
                and_(
                    Site.id == site_id,
                    Site.customer_user.has(CustomerUser.id == customer_user_id)
                )
            )
            site_result = await db.execute(site_stmt)
            site = site_result.scalar_one_or_none()
            
            if not site:
                raise ForbiddenError("Site not found or not owned by customer")
        
        # Generate unique ticket number
        ticket_number = TicketService._generate_ticket_number()
        
        # Ensure uniqueness (unlikely collision, but check anyway)
        existing_stmt = select(SupportTicket).where(SupportTicket.ticket_number == ticket_number)
        existing_result = await db.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            # Regenerate if collision (extremely rare)
            ticket_number = TicketService._generate_ticket_number()
        
        # Create ticket
        ticket = SupportTicket(
            customer_user_id=customer_user_id,
            site_id=site_id,
            ticket_number=ticket_number,
            subject=subject,
            description=description,
            category=category,
            priority="medium",  # Default, will be updated by AI
            status="new",
            last_customer_message_at=datetime.now(timezone.utc)
        )
        
        db.add(ticket)
        await db.flush()
        
        # Create initial message from customer
        initial_message = TicketMessage(
            ticket_id=ticket.id,
            customer_user_id=customer_user_id,
            message=description,
            message_type="customer",
            ai_generated=False
        )
        
        db.add(initial_message)
        await db.commit()
        await db.refresh(ticket)
        
        # Process with AI asynchronously (non-blocking)
        try:
            await TicketService._process_with_ai(db, ticket)
        except Exception as e:
            logger.error(f"AI processing failed for ticket {ticket.ticket_number}: {e}")
            # Continue even if AI processing fails
        
        return ticket
    
    @staticmethod
    async def _process_with_ai(
        db: AsyncSession,
        ticket: SupportTicket
    ) -> None:
        """
        Process ticket with AI for categorization, priority, and suggested response.
        
        Args:
            db: Database session
            ticket: Ticket to process
        """
        try:
            import json
            ai_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            
            # Build prompt for AI
            prompt = f"""You are a customer support AI assistant. Analyze the following support ticket and provide:
1. Category confidence scores (billing, technical_support, site_edit, question, other)
2. Priority level (low, medium, high, urgent)
3. A helpful, professional response

Ticket Information:
Subject: {ticket.subject}
Description: {ticket.description}
Current Category: {ticket.category}

Respond in JSON format:
{{
    "category_confidence": {{
        "billing": 0.0-1.0,
        "technical_support": 0.0-1.0,
        "site_edit": 0.0-1.0,
        "question": 0.0-1.0,
        "other": 0.0-1.0
    }},
    "suggested_category": "category_name",
    "priority": "low|medium|high|urgent",
    "priority_reasoning": "explanation",
    "suggested_response": "Your professional response here",
    "requires_human_review": true|false,
    "processing_notes": "Any important notes"
}}"""
            
            # Get AI response
            # Use streaming to avoid timeout limits on large max_tokens
            async with ai_client.messages.stream(
                model="claude-sonnet-4-5",
                max_tokens=65536,  # Max for Claude Sonnet 4.5
                temperature=0.3,
                system="You are a helpful customer support assistant.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            ) as stream:
                response_text = await stream.get_final_text()
            
            # Parse AI response
            try:
                ai_analysis = json.loads(response_text)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse AI response for ticket {ticket.ticket_number}")
                return
            
            # Update ticket with AI insights
            ticket.ai_processed = True
            ticket.ai_category_confidence = ai_analysis.get("category_confidence", {})
            ticket.ai_suggested_response = ai_analysis.get("suggested_response", "")
            ticket.ai_processing_notes = {
                "priority_reasoning": ai_analysis.get("priority_reasoning", ""),
                "requires_human_review": ai_analysis.get("requires_human_review", False),
                "processing_notes": ai_analysis.get("processing_notes", ""),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Update priority if AI suggests different
            suggested_priority = ai_analysis.get("priority", "medium")
            if suggested_priority in TicketService.PRIORITIES:
                ticket.priority = suggested_priority
            
            # If AI suggests different category with high confidence
            suggested_category = ai_analysis.get("suggested_category")
            if suggested_category and suggested_category in TicketService.CATEGORIES:
                confidence = ai_analysis.get("category_confidence", {}).get(suggested_category, 0)
                if confidence > 0.8 and suggested_category != ticket.category:
                    logger.info(
                        f"AI suggests recategorizing ticket {ticket.ticket_number} "
                        f"from {ticket.category} to {suggested_category} (confidence: {confidence})"
                    )
                    ticket.category = suggested_category
            
            # Auto-respond for simple questions if confidence is high
            if (
                ticket.category == "question" and
                not ai_analysis.get("requires_human_review", False) and
                ai_analysis.get("category_confidence", {}).get("question", 0) > 0.9
            ):
                # Create AI response message
                ai_message = TicketMessage(
                    ticket_id=ticket.id,
                    message=ticket.ai_suggested_response,
                    message_type="ai",
                    ai_generated=True,
                    ai_model="claude-sonnet-3.5",
                    ai_confidence=ai_analysis.get("category_confidence", {})
                )
                db.add(ai_message)
                
                ticket.status = "waiting_customer"
                ticket.first_response_at = datetime.now(timezone.utc)
                ticket.last_staff_message_at = datetime.now(timezone.utc)
            else:
                # Mark as waiting for staff review
                ticket.status = "in_progress"
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error in AI processing for ticket {ticket.ticket_number}: {e}")
            # Don't raise - ticket creation should succeed even if AI fails
    
    @staticmethod
    async def add_message(
        db: AsyncSession,
        ticket_id: UUID,
        message: str,
        author_id: UUID,
        author_type: str,  # 'customer' or 'staff'
        internal_only: bool = False
    ) -> TicketMessage:
        """
        Add a message to a ticket.
        
        Args:
            db: Database session
            ticket_id: ID of the ticket
            message: Message content
            author_id: ID of the author (customer_user_id or admin_user_id)
            author_type: Type of author ('customer' or 'staff')
            internal_only: Whether message is internal only (staff notes)
            
        Returns:
            Created TicketMessage instance
        """
        # Get ticket
        stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
        result = await db.execute(stmt)
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            raise NotFoundError("Ticket not found")
        
        # Create message
        ticket_message = TicketMessage(
            ticket_id=ticket_id,
            message=message,
            message_type=author_type,
            internal_only=internal_only,
            ai_generated=False
        )
        
        if author_type == "customer":
            ticket_message.customer_user_id = author_id
            ticket.last_customer_message_at = datetime.now(timezone.utc)
            
            # If customer responds, move from resolved/waiting_ai to in_progress
            if ticket.status in ["resolved", "waiting_ai", "waiting_customer"]:
                ticket.status = "in_progress"
        elif author_type == "staff":
            ticket_message.admin_user_id = author_id
            ticket.last_staff_message_at = datetime.now(timezone.utc)
            
            # First staff response
            if not ticket.first_response_at:
                ticket.first_response_at = datetime.now(timezone.utc)
            
            # If staff responds, move to waiting_customer
            if ticket.status in ["new", "in_progress"]:
                ticket.status = "waiting_customer"
        
        db.add(ticket_message)
        await db.commit()
        await db.refresh(ticket_message)
        
        return ticket_message
    
    @staticmethod
    async def get_ticket_by_id(
        db: AsyncSession,
        ticket_id: UUID,
        customer_user_id: Optional[UUID] = None
    ) -> SupportTicket:
        """
        Get ticket by ID with messages.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            customer_user_id: Optional customer ID for ownership verification
            
        Returns:
            SupportTicket instance with messages
        """
        stmt = select(SupportTicket).where(SupportTicket.id == ticket_id).options(
            selectinload(SupportTicket.messages)
        )
        
        # Add customer filter if provided
        if customer_user_id:
            stmt = stmt.where(SupportTicket.customer_user_id == customer_user_id)
        
        result = await db.execute(stmt)
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            raise NotFoundError("Ticket not found")
        
        return ticket
    
    @staticmethod
    async def list_customer_tickets(
        db: AsyncSession,
        customer_user_id: UUID,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[SupportTicket], int]:
        """
        List tickets for a customer.
        
        Args:
            db: Database session
            customer_user_id: Customer user ID
            status: Optional status filter
            category: Optional category filter
            limit: Number of results to return
            offset: Offset for pagination
            
        Returns:
            Tuple of (list of tickets, total count)
        """
        # Build query
        stmt = select(SupportTicket).where(
            SupportTicket.customer_user_id == customer_user_id
        )
        
        if status:
            stmt = stmt.where(SupportTicket.status == status)
        if category:
            stmt = stmt.where(SupportTicket.category == category)
        
        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Get tickets
        stmt = stmt.order_by(SupportTicket.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        tickets = result.scalars().all()
        
        return list(tickets), total
    
    @staticmethod
    async def update_ticket_status(
        db: AsyncSession,
        ticket_id: UUID,
        new_status: str,
        customer_user_id: Optional[UUID] = None
    ) -> SupportTicket:
        """
        Update ticket status.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            new_status: New status
            customer_user_id: Optional customer ID for ownership verification
            
        Returns:
            Updated SupportTicket instance
        """
        if new_status not in TicketService.STATUSES:
            raise ValidationError(f"Invalid status. Must be one of: {', '.join(TicketService.STATUSES)}")
        
        # Get ticket
        stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
        if customer_user_id:
            stmt = stmt.where(SupportTicket.customer_user_id == customer_user_id)
        
        result = await db.execute(stmt)
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            raise NotFoundError("Ticket not found")
        
        old_status = ticket.status
        ticket.status = new_status
        
        # Update timestamps based on status
        now = datetime.now(timezone.utc)
        if new_status == "resolved" and old_status != "resolved":
            ticket.resolved_at = now
        elif new_status == "closed" and old_status != "closed":
            ticket.closed_at = now
        
        await db.commit()
        await db.refresh(ticket)
        
        return ticket
    
    @staticmethod
    async def get_ticket_stats(
        db: AsyncSession,
        customer_user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get ticket statistics for a customer.
        
        Args:
            db: Database session
            customer_user_id: Customer user ID
            
        Returns:
            Dictionary with ticket statistics
        """
        # Get counts by status
        status_stmt = select(
            SupportTicket.status,
            func.count(SupportTicket.id)
        ).where(
            SupportTicket.customer_user_id == customer_user_id
        ).group_by(SupportTicket.status)
        
        status_result = await db.execute(status_stmt)
        status_counts = dict(status_result.fetchall())
        
        # Get counts by category
        category_stmt = select(
            SupportTicket.category,
            func.count(SupportTicket.id)
        ).where(
            SupportTicket.customer_user_id == customer_user_id
        ).group_by(SupportTicket.category)
        
        category_result = await db.execute(category_stmt)
        category_counts = dict(category_result.fetchall())
        
        # Get total count
        total_stmt = select(func.count(SupportTicket.id)).where(
            SupportTicket.customer_user_id == customer_user_id
        )
        total_result = await db.execute(total_stmt)
        total = total_result.scalar() or 0
        
        return {
            "total": total,
            "by_status": status_counts,
            "by_category": category_counts,
            "open": status_counts.get("new", 0) + status_counts.get("in_progress", 0),
            "waiting": status_counts.get("waiting_customer", 0) + status_counts.get("waiting_ai", 0),
            "resolved": status_counts.get("resolved", 0),
            "closed": status_counts.get("closed", 0)
        }

