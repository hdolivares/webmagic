"""Add checkout_sessions table for abandoned cart tracking

Revision ID: add_checkout_sessions
Revises: 
Create Date: 2026-02-14

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_checkout_sessions'
down_revision: Union[str, None] = None
head_label: Union[str, None] = None
depends_on: Union[str, Sequence[Union[str, None]], None] = None


def upgrade() -> None:
    """Create checkout_sessions table."""
    op.create_table(
        'checkout_sessions',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False, autoincrement=True),
        sa.Column('session_id', sa.String(255), unique=True, nullable=False, index=True, 
                  comment='Unique identifier for this checkout session'),
        
        # Customer Information
        sa.Column('customer_email', sa.String(255), nullable=False, index=True,
                  comment='Customer email address'),
        sa.Column('customer_name', sa.String(255), nullable=False,
                  comment='Customer full name'),
        
        # Site Information
        sa.Column('site_slug', sa.String(255), nullable=False, index=True,
                  comment='Slug of the site being purchased'),
        sa.Column('site_id', sa.Integer(), nullable=True,
                  comment='Foreign key to sites table'),
        
        # Recurrente Checkout Details
        sa.Column('checkout_id', sa.String(255), nullable=True, index=True,
                  comment='Recurrente checkout ID'),
        sa.Column('checkout_url', sa.String(500), nullable=True,
                  comment='Recurrente checkout URL sent to customer'),
        
        # Pricing
        sa.Column('purchase_amount', sa.Numeric(10, 2), nullable=False,
                  comment='One-time purchase amount in USD'),
        sa.Column('monthly_amount', sa.Numeric(10, 2), nullable=False,
                  comment='Monthly subscription amount in USD'),
        
        # Payment Status
        sa.Column('status', sa.String(50), nullable=False, default='initiated', index=True,
                  comment='Status: initiated, checkout_created, payment_pending, completed, abandoned'),
        sa.Column('payment_intent_id', sa.String(255), nullable=True, index=True,
                  comment='Recurrente payment intent ID when payment completes'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Timestamp when payment was completed'),
        
        # Abandoned Cart Recovery
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True, index=True,
                  comment='Timestamp when abandoned cart email was sent'),
        sa.Column('reminder_discount_code', sa.String(100), nullable=True,
                  comment='Discount code sent in abandoned cart email'),
        
        # Metadata
        sa.Column('user_agent', sa.String(500), nullable=True,
                  comment='User agent string for analytics'),
        sa.Column('referrer', sa.String(500), nullable=True,
                  comment='Referrer URL for analytics'),
        sa.Column('ip_address', sa.String(45), nullable=True,
                  comment='Customer IP address'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), 
                  nullable=False, index=True,
                  comment='Timestamp when checkout session was initiated'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'),
                  onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=False,
                  comment='Last update timestamp'),
        
        # Indexes for performance
        sa.Index('idx_checkout_sessions_email_status', 'customer_email', 'status'),
        sa.Index('idx_checkout_sessions_created_status', 'created_at', 'status'),
        sa.Index('idx_checkout_sessions_abandoned', 'created_at', 'status', 'reminder_sent_at'),
    )
    
    # Add comment to table
    op.execute("""
        COMMENT ON TABLE checkout_sessions IS 
        'Tracks all checkout sessions for abandoned cart recovery and analytics'
    """)


def downgrade() -> None:
    """Drop checkout_sessions table."""
    op.drop_table('checkout_sessions')
