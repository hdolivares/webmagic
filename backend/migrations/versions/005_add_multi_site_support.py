"""Add multi-site support to customer system

Revision ID: 005_add_multi_site_support
Revises: 004_customer_system
Create Date: 2026-01-24 10:00:00.000000

This migration enables customers to own multiple websites by:
1. Creating a junction table for customer-site relationships
2. Migrating existing single-site ownership data
3. Adding primary_site_id to customer_users
4. Removing the old site_id column

Author: WebMagic Team
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '005_add_multi_site_support'
down_revision = '004_customer_system'
branch_labels = None
depends_on = None


def upgrade():
    """
    Upgrade database schema to support multi-site ownership.
    """
    print("Starting multi-site support migration...")
    
    # ========================================================================
    # STEP 1: Create customer_site_ownership junction table
    # ========================================================================
    print("  → Creating customer_site_ownership table...")
    
    op.create_table(
        'customer_site_ownership',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('customer_user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('site_id', UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='owner'),
        sa.Column('is_primary', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('acquired_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(
            ['customer_user_id'], 
            ['customer_users.id'], 
            name='fk_ownership_customer',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['site_id'], 
            ['sites.id'], 
            name='fk_ownership_site',
            ondelete='CASCADE'
        ),
        sa.UniqueConstraint(
            'customer_user_id', 
            'site_id', 
            name='unique_customer_site_ownership'
        )
    )
    
    # Create indexes for performance
    op.create_index(
        'idx_ownership_customer', 
        'customer_site_ownership', 
        ['customer_user_id']
    )
    op.create_index(
        'idx_ownership_site', 
        'customer_site_ownership', 
        ['site_id']
    )
    op.create_index(
        'idx_ownership_primary', 
        'customer_site_ownership', 
        ['customer_user_id', 'is_primary']
    )
    
    # ========================================================================
    # STEP 2: Migrate existing site_id data to junction table
    # ========================================================================
    print("  → Migrating existing ownership data...")
    
    # Copy existing customer-site relationships to junction table
    # Only migrate where site_id is not NULL
    op.execute("""
        INSERT INTO customer_site_ownership (
            id,
            customer_user_id,
            site_id,
            role,
            is_primary,
            acquired_at,
            created_at,
            updated_at
        )
        SELECT 
            gen_random_uuid() as id,
            cu.id as customer_user_id,
            cu.site_id,
            'owner' as role,
            TRUE as is_primary,
            COALESCE(s.purchased_at, cu.created_at) as acquired_at,
            NOW() as created_at,
            NOW() as updated_at
        FROM customer_users cu
        JOIN sites s ON s.id = cu.site_id
        WHERE cu.site_id IS NOT NULL
    """)
    
    # ========================================================================
    # STEP 3: Add primary_site_id column to customer_users
    # ========================================================================
    print("  → Adding primary_site_id column...")
    
    op.add_column(
        'customer_users',
        sa.Column('primary_site_id', UUID(as_uuid=True), nullable=True)
    )
    
    # ========================================================================
    # STEP 4: Copy site_id values to primary_site_id
    # ========================================================================
    print("  → Copying site_id to primary_site_id...")
    
    op.execute("""
        UPDATE customer_users
        SET primary_site_id = site_id
        WHERE site_id IS NOT NULL
    """)
    
    # ========================================================================
    # STEP 5: Add foreign key constraint for primary_site_id
    # ========================================================================
    print("  → Adding foreign key constraint...")
    
    op.create_foreign_key(
        'fk_customer_primary_site',
        'customer_users',
        'sites',
        ['primary_site_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create index for performance
    op.create_index(
        'idx_customer_primary_site',
        'customer_users',
        ['primary_site_id']
    )
    
    # ========================================================================
    # STEP 6: Remove old site_id column and its constraint
    # ========================================================================
    print("  → Removing old site_id column...")
    
    # Drop foreign key constraint first
    op.drop_constraint(
        'customer_users_site_id_fkey',
        'customer_users',
        type_='foreignkey'
    )
    
    # Drop the column
    op.drop_column('customer_users', 'site_id')
    
    print("✅ Multi-site support migration completed successfully!")


def downgrade():
    """
    Downgrade database schema back to single-site ownership.
    
    WARNING: This will lose information about additional sites
    owned by customers (only primary site will be preserved).
    """
    print("Starting multi-site support rollback...")
    
    # ========================================================================
    # STEP 1: Add site_id column back to customer_users
    # ========================================================================
    print("  → Adding site_id column back...")
    
    op.add_column(
        'customer_users',
        sa.Column('site_id', UUID(as_uuid=True), nullable=True)
    )
    
    # ========================================================================
    # STEP 2: Copy primary_site_id back to site_id
    # ========================================================================
    print("  → Copying primary_site_id back to site_id...")
    
    op.execute("""
        UPDATE customer_users
        SET site_id = primary_site_id
        WHERE primary_site_id IS NOT NULL
    """)
    
    # ========================================================================
    # STEP 3: Add foreign key constraint for site_id
    # ========================================================================
    print("  → Adding foreign key constraint...")
    
    op.create_foreign_key(
        'customer_users_site_id_fkey',
        'customer_users',
        'sites',
        ['site_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # ========================================================================
    # STEP 4: Remove primary_site_id column
    # ========================================================================
    print("  → Removing primary_site_id column...")
    
    op.drop_constraint('fk_customer_primary_site', 'customer_users', type_='foreignkey')
    op.drop_index('idx_customer_primary_site', 'customer_users')
    op.drop_column('customer_users', 'primary_site_id')
    
    # ========================================================================
    # STEP 5: Drop customer_site_ownership table
    # ========================================================================
    print("  → Dropping customer_site_ownership table...")
    
    op.drop_index('idx_ownership_primary', 'customer_site_ownership')
    op.drop_index('idx_ownership_site', 'customer_site_ownership')
    op.drop_index('idx_ownership_customer', 'customer_site_ownership')
    op.drop_table('customer_site_ownership')
    
    print("✅ Multi-site support rollback completed!")
    print("⚠️  WARNING: Additional site ownership data has been lost!")
