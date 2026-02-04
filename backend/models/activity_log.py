"""
Activity Log model for audit trail and event tracking.

Tracks all significant actions in the system for debugging,
compliance, and analytics purposes.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from core.database import Base


class ActivityLog(Base):
    """
    Activity log for tracking system events and user actions.
    
    This is an append-only audit trail - records should never be updated or deleted.
    """
    
    __tablename__ = "activity_log"
    
    # Primary key (not using BaseModel to avoid updated_at)
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Action details
    action = Column(String(100), nullable=False, index=True)
    # Examples: "created", "updated", "deleted", "login", "logout", 
    #           "email_sent", "site_generated", "payment_received"
    
    # Entity being acted upon
    entity_type = Column(String(50), nullable=False, index=True)
    # Examples: "business", "site", "campaign", "customer", "subscription"
    
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    # Reference to the specific entity (nullable for system-wide events)
    
    # Additional context
    details = Column(JSONB, nullable=True)
    # Flexible storage for action-specific data:
    # {
    #   "old_value": ...,
    #   "new_value": ...,
    #   "ip_address": "...",
    #   "user_agent": "...",
    #   "metadata": {...}
    # }
    
    # Who performed the action
    actor_type = Column(String(30), nullable=True, index=True)
    # Options: "admin", "customer", "system", "celery", "webhook"
    
    actor_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    # Reference to admin_users.id or customer_users.id
    
    # Timestamp (immutable - no updated_at)
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_activity_entity', 'entity_type', 'entity_id'),
        Index('idx_activity_actor', 'actor_type', 'actor_id'),
        Index('idx_activity_action_date', 'action', 'created_at'),
        Index('idx_activity_entity_date', 'entity_type', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ActivityLog {self.action} on {self.entity_type} by {self.actor_type}>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id) if self.entity_id else None,
            "details": self.details,
            "actor_type": self.actor_type,
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def log(
        cls,
        action: str,
        entity_type: str,
        entity_id: str = None,
        actor_type: str = None,
        actor_id: str = None,
        details: dict = None
    ) -> "ActivityLog":
        """
        Factory method to create a new activity log entry.
        
        Usage:
            log_entry = ActivityLog.log(
                action="created",
                entity_type="site",
                entity_id=site.id,
                actor_type="customer",
                actor_id=customer.id,
                details={"site_name": site.slug}
            )
            session.add(log_entry)
        """
        return cls(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_type=actor_type,
            actor_id=actor_id,
            details=details
        )

