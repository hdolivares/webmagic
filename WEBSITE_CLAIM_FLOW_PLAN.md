# Website Claim Flow - Comprehensive Implementation Plan

**Date:** January 24, 2026  
**Status:** 📋 Planning Phase  
**Author:** WebMagic Team

---

## 📊 Executive Summary

This document outlines the complete architecture and implementation plan for connecting the **"Claim for $495"** button on preview websites to a seamless account creation, checkout, and subscription management system. The flow ensures that each website purchase is uniquely tracked, accounts are scoped to specific websites, and customers have proper access to support tickets and billing.

---

## 🎯 Core Requirements

### Primary Goals
1. ✅ **Unique Site Identification**: Each claim button must generate a unique checkout session linked to the specific website
2. ✅ **Automatic Account Creation**: On successful payment, create a customer account scoped to that website
3. ✅ **Ticket System Scoping**: Support tickets must be associated with the customer's specific website
4. ✅ **Multi-Site Support**: If a customer purchases multiple sites, they should select which site when creating tickets
5. ✅ **Billing Transparency**: Backend must match billing records to the correct website and display subscription status

### Key User Flows
1. **First-Time Buyer**: Preview → Claim → Payment → Account Created → Dashboard Access
2. **Returning Customer**: Already owns Site A → Buys Site B → Gets upgrade prompt or multi-site dashboard
3. **Ticket Creation**: Dashboard → Create Ticket → (Select Site if multiple) → Submit → AI Processing

---

## 🏗️ System Architecture

### Current System State

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXISTING ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  businesses          generated_sites          customers                 │
│  ┌──────────┐       ┌──────────────┐         ┌──────────┐              │
│  │ gmb_id   │──────▶│ business_id  │────────▶│ site_id  │              │
│  │ name     │       │ subdomain    │         │ email    │              │
│  │ email    │       │ html_content │         │ status   │              │
│  │ phone    │       │ status       │         └──────────┘              │
│  │ slug     │       │              │              │                     │
│  └──────────┘       └──────────────┘              │                     │
│                            │                       ▼                     │
│                            │              ┌──────────────┐              │
│                            │              │subscriptions │              │
│                            │              │ amount_cents │              │
│                            │              │ status       │              │
│                            │              └──────────────┘              │
│                            │                       │                     │
│                            ▼                       ▼                     │
│                     ┌──────────────┐       ┌──────────┐                │
│                     │support_tickets│      │ payments │                │
│                     │ customer_id  │       │ status   │                │
│                     │ site_id      │       │ paid_at  │                │
│                     │ request_text │       └──────────┘                │
│                     └──────────────┘                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Phase 2 Enhancement (Customer System)

The system **already has** a Phase 2 customer system with:
- `Site` model (replaces `generated_sites`)
- `CustomerUser` model (authentication for customers)
- `SiteVersion` model (version history)
- `EditRequest` model (AI-powered edits)
- `SupportTicket` model (with site_id association)

**Key Insight:** The Phase 2 system is already designed for single-site ownership per customer. We need to **extend it** for multi-site support.

---

## 🔄 Proposed Flow Architecture

### Overview Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    ENHANCED CLAIM-TO-OWNERSHIP FLOW                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  1. PREVIEW SITE                                                         │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │ https://sites.lavish.solutions/plumber-joe                 │         │
│  │                                                             │         │
│  │ ┌──────────────────────────────────────────────────────┐   │         │
│  │ │ 🏢 Is this your business?                            │   │         │
│  │ │ Claim this website for only $495                    │   │         │
│  │ │ Then just $99/month for hosting, maintenance & changes│   │         │
│  │ │                                                      │   │         │
│  │ │         [ Claim for $495 ]  ◄─ Click              │   │         │
│  │ └──────────────────────────────────────────────────────┘   │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                   │                                      │
│                                   ▼                                      │
│  2. CLAIM MODAL (Frontend JavaScript)                                   │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │ 📧 Email: ___________________                               │         │
│  │ 👤 Name:  ___________________                               │         │
│  │                                                             │         │
│  │ ✓ One-time setup: $495                                     │         │
│  │ ✓ Monthly: $99 (hosting, maintenance, changes)             │         │
│  │                                                             │         │
│  │         [ Proceed to Checkout → ]  ◄─ Submit              │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                   │                                      │
│                                   ▼                                      │
│  3. API CALL: POST /api/v1/sites/{slug}/purchase                        │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │ Body: {                                                     │         │
│  │   "customer_email": "joe@plumbing.com",                    │         │
│  │   "customer_name": "Joe Smith",                            │         │
│  │   "success_url": "https://sites.lavish.solutions/...",    │         │
│  │   "cancel_url": "https://sites.lavish.solutions/..."      │         │
│  │ }                                                           │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                   │                                      │
│                                   ▼                                      │
│  4. BACKEND PROCESSING                                                  │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │ A. Get Site by slug                                         │         │
│  │ B. Validate site is available (status = "preview")         │         │
│  │ C. Create Recurrente checkout with metadata:               │         │
│  │    {                                                        │         │
│  │      "site_id": "uuid",                                     │         │
│  │      "slug": "plumber-joe",                                 │         │
│  │      "business_id": "uuid",                                 │         │
│  │      "customer_email": "joe@plumbing.com"                   │         │
│  │    }                                                        │         │
│  │ D. Return checkout_url to frontend                          │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                   │                                      │
│                                   ▼                                      │
│  5. REDIRECT TO RECURRENTE                                              │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │ Recurrente Payment Page                                     │         │
│  │ - Enter credit card                                         │         │
│  │ - Complete payment ($495)                                   │         │
│  │ - Setup recurring ($99/month)                               │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                   │                                      │
│                                   ▼                                      │
│  6. WEBHOOK: POST /api/v1/payments/webhooks/recurrente                  │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │ Event: "checkout.completed"                                 │         │
│  │ Data: {                                                     │         │
│  │   "checkout_id": "xxx",                                     │         │
│  │   "metadata": { "site_id": "uuid", "slug": "..." },        │         │
│  │   "user_email": "joe@plumbing.com",                         │         │
│  │   "status": "paid"                                          │         │
│  │ }                                                           │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                   │                                      │
│                                   ▼                                      │
│  7. POST-PURCHASE PROCESSING (WebhookHandler)                           │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │ A. Check if CustomerUser exists with this email             │         │
│  │    - If NO: Create new CustomerUser                         │         │
│  │    - If YES: Check if they already own a site               │         │
│  │                                                             │         │
│  │ B. Update Site record:                                      │         │
│  │    - status: "preview" → "owned"                            │         │
│  │    - purchased_at: now                                      │         │
│  │    - subscription_status: "active"                          │         │
│  │                                                             │         │
│  │ C. Link Site to CustomerUser:                               │         │
│  │    - customer_user.site_id = site.id                        │         │
│  │                                                             │         │
│  │ D. Create Subscription record                               │         │
│  │                                                             │         │
│  │ E. Create Payment record (initial $495)                     │         │
│  │                                                             │         │
│  │ F. Send welcome email with:                                 │         │
│  │    - Password setup link                                    │         │
│  │    - Dashboard access instructions                          │         │
│  │    - Site URL                                               │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                   │                                      │
│                                   ▼                                      │
│  8. CUSTOMER DASHBOARD ACCESS                                           │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │ https://web.lavish.solutions/customer/dashboard             │         │
│  │                                                             │         │
│  │ My Site: plumber-joe                                        │         │
│  │ Status: Active ✓                                            │         │
│  │ Subscription: $99/month                                     │         │
│  │ Next Billing: Feb 24, 2026                                  │         │
│  │                                                             │         │
│  │ [ Create Support Ticket ]                                   │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Schema Enhancements

### Current Schema (Phase 2)

```sql
-- CustomerUser table (already exists)
CREATE TABLE customer_users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    phone VARCHAR(50),
    site_id UUID REFERENCES sites(id),  -- Currently single-site only
    email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Site table (already exists, replaces generated_sites)
CREATE TABLE sites (
    id UUID PRIMARY KEY,
    slug VARCHAR(255) UNIQUE NOT NULL,
    business_id UUID REFERENCES businesses(id),
    status VARCHAR(50) DEFAULT 'preview',  -- preview, owned, active, suspended
    purchased_at TIMESTAMP,
    purchase_amount NUMERIC(10,2) DEFAULT 495.00,
    subscription_status VARCHAR(50),  -- active, past_due, cancelled
    monthly_amount NUMERIC(10,2) DEFAULT 99.00,
    next_billing_date DATE,
    custom_domain VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- SupportTicket table (already exists)
CREATE TABLE support_tickets (
    id UUID PRIMARY KEY,
    customer_user_id UUID REFERENCES customer_users(id),
    site_id UUID REFERENCES sites(id),  -- Already has site association
    ticket_number VARCHAR(50) UNIQUE,
    subject TEXT NOT NULL,
    category VARCHAR(50),
    status VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Proposed Schema Enhancements

#### Option 1: Multi-Site Support via Junction Table (Recommended)

```sql
-- New junction table for multi-site ownership
CREATE TABLE customer_site_ownership (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_user_id UUID NOT NULL REFERENCES customer_users(id) ON DELETE CASCADE,
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    
    -- Ownership metadata
    role VARCHAR(50) DEFAULT 'owner',  -- owner, collaborator (for future)
    is_primary BOOLEAN DEFAULT FALSE,  -- Primary site in dashboard
    
    -- Timestamps
    acquired_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(customer_user_id, site_id)
);

CREATE INDEX idx_ownership_customer ON customer_site_ownership(customer_user_id);
CREATE INDEX idx_ownership_site ON customer_site_ownership(site_id);

-- Modify customer_users table
ALTER TABLE customer_users DROP COLUMN site_id;  -- Remove single-site reference
ALTER TABLE customer_users ADD COLUMN primary_site_id UUID REFERENCES sites(id);
```

**Pros:**
- ✅ Supports unlimited sites per customer
- ✅ Clean separation of concerns
- ✅ Easy to query all sites for a customer
- ✅ Supports future features (team access, collaborators)
- ✅ No data duplication

**Cons:**
- ⚠️ Requires migration of existing data
- ⚠️ Adds join complexity to some queries

#### Option 2: Keep Single-Site, Add Multi-Site in Phase 3 (Simpler)

```sql
-- Keep customer_users as is (single site_id)
-- For multi-site customers, show upgrade prompt
-- Track in metadata for now:

ALTER TABLE customer_users 
ADD COLUMN has_multiple_sites BOOLEAN DEFAULT FALSE;

ALTER TABLE customer_users 
ADD COLUMN site_ids JSONB DEFAULT '[]';  -- Array of owned site UUIDs

-- Example: site_ids: ["uuid1", "uuid2"]
```

**Pros:**
- ✅ Minimal schema changes
- ✅ Backward compatible
- ✅ Quick to implement
- ✅ Keeps existing code working

**Cons:**
- ❌ JSONB is less relational
- ❌ Harder to query
- ❌ Manual array management

---

### 🎯 Recommended Approach: **Option 1 (Junction Table)**

**Reasoning:**
1. Proper relational design
2. Easier to maintain long-term
3. Supports complex queries
4. Scalable for future features
5. Migration is one-time effort

---

## 🔧 Implementation Plan

### Phase 1: Backend API Enhancements (Week 1)

#### Task 1.1: Database Migration
```bash
# File: backend/migrations/versions/XXX_add_multi_site_support.py
```

**Steps:**
1. Create `customer_site_ownership` table
2. Migrate existing `customer_users.site_id` → `customer_site_ownership`
3. Add `primary_site_id` to `customer_users`
4. Remove `site_id` from `customer_users`

**Migration Script:**
```python
"""Add multi-site support to customer system

Revision ID: 005_multi_site_support
Revises: 004_customer_system
Create Date: 2026-01-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

def upgrade():
    # 1. Create junction table
    op.create_table(
        'customer_site_ownership',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('site_id', UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), default='owner'),
        sa.Column('is_primary', sa.Boolean, default=False),
        sa.Column('acquired_at', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['customer_user_id'], ['customer_users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('customer_user_id', 'site_id', name='unique_customer_site')
    )
    
    # 2. Migrate existing ownership relationships
    op.execute("""
        INSERT INTO customer_site_ownership (id, customer_user_id, site_id, is_primary, acquired_at, created_at)
        SELECT 
            gen_random_uuid(),
            id as customer_user_id,
            site_id,
            TRUE as is_primary,
            created_at as acquired_at,
            NOW() as created_at
        FROM customer_users
        WHERE site_id IS NOT NULL
    """)
    
    # 3. Add primary_site_id to customer_users
    op.add_column('customer_users', sa.Column('primary_site_id', UUID(as_uuid=True), nullable=True))
    
    # 4. Copy site_id to primary_site_id
    op.execute("""
        UPDATE customer_users
        SET primary_site_id = site_id
        WHERE site_id IS NOT NULL
    """)
    
    # 5. Remove old site_id column
    op.drop_constraint('customer_users_site_id_fkey', 'customer_users', type_='foreignkey')
    op.drop_column('customer_users', 'site_id')
    
    # 6. Add foreign key for primary_site_id
    op.create_foreign_key(
        'customer_users_primary_site_id_fkey',
        'customer_users', 'sites',
        ['primary_site_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # 7. Create indexes
    op.create_index('idx_ownership_customer', 'customer_site_ownership', ['customer_user_id'])
    op.create_index('idx_ownership_site', 'customer_site_ownership', ['site_id'])

def downgrade():
    # Reverse migration (add site_id back, remove junction table)
    op.add_column('customer_users', sa.Column('site_id', UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE customer_users SET site_id = primary_site_id")
    op.drop_column('customer_users', 'primary_site_id')
    op.drop_table('customer_site_ownership')
```

#### Task 1.2: Create CustomerSiteOwnership Model

```python
# File: backend/models/site_models.py

class CustomerSiteOwnership(BaseModel):
    """Junction table for multi-site ownership."""
    
    __tablename__ = "customer_site_ownership"
    
    customer_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Ownership metadata
    role = Column(String(50), default="owner", nullable=False)
    is_primary = Column(Boolean, default=False)
    
    # Timestamps
    acquired_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    customer_user = relationship("CustomerUser", back_populates="owned_sites")
    site = relationship("Site", back_populates="owners")
    
    def __repr__(self):
        return f"<Ownership {self.customer_user_id} → {self.site_id}>"
```

**Update existing models:**

```python
# Update CustomerUser model
class CustomerUser(BaseModel):
    # ... existing fields ...
    
    # Remove: site_id = Column(...)
    
    # Add:
    primary_site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Relationships
    owned_sites = relationship(
        "CustomerSiteOwnership",
        back_populates="customer_user",
        cascade="all, delete-orphan"
    )
    
    primary_site = relationship("Site", foreign_keys=[primary_site_id])
    
    @property
    def sites(self) -> List[Site]:
        """Get all sites owned by this customer."""
        return [ownership.site for ownership in self.owned_sites]
    
    @property
    def has_multiple_sites(self) -> bool:
        """Check if customer owns multiple sites."""
        return len(self.owned_sites) > 1


# Update Site model
class Site(BaseModel):
    # ... existing fields ...
    
    # Add relationship
    owners = relationship(
        "CustomerSiteOwnership",
        back_populates="site",
        cascade="all, delete-orphan"
    )
    
    @property
    def primary_owner(self) -> Optional[CustomerUser]:
        """Get the primary owner of this site."""
        primary = next((o for o in self.owners if o.is_primary), None)
        return primary.customer_user if primary else None
```

#### Task 1.3: Update Site Purchase Service

```python
# File: backend/services/site_purchase_service.py

class SitePurchaseService:
    """Enhanced service with multi-site support."""
    
    async def process_purchase_webhook(
        self,
        db: AsyncSession,
        checkout_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process successful purchase webhook from Recurrente.
        Handles both first-time buyers and returning customers.
        """
        metadata = checkout_data.get("metadata", {})
        site_id = UUID(metadata.get("site_id"))
        customer_email = checkout_data.get("user_email")
        customer_name = checkout_data.get("user_name")
        
        # 1. Get the site
        site = await self._get_site_by_id(db, site_id)
        if not site:
            raise NotFoundError(f"Site not found: {site_id}")
        
        # 2. Check if customer already exists
        from sqlalchemy import select
        result = await db.execute(
            select(CustomerUser).where(CustomerUser.email == customer_email)
        )
        customer = result.scalar_one_or_none()
        
        if customer:
            # Existing customer buying another site
            logger.info(f"Existing customer {customer_email} purchasing site {site.slug}")
            
            # Check if they already own this site (shouldn't happen)
            existing_ownership = await db.execute(
                select(CustomerSiteOwnership).where(
                    CustomerSiteOwnership.customer_user_id == customer.id,
                    CustomerSiteOwnership.site_id == site_id
                )
            )
            if existing_ownership.scalar_one_or_none():
                logger.warning(f"Customer already owns site {site.slug}, skipping")
                return {"status": "already_owned"}
            
            # Add new site to customer's ownership
            is_first_site = len(customer.owned_sites) == 0
            
            ownership = CustomerSiteOwnership(
                customer_user_id=customer.id,
                site_id=site_id,
                is_primary=is_first_site,  # First site is primary
                acquired_at=datetime.now(timezone.utc)
            )
            db.add(ownership)
            
            # Update primary_site_id if this is their first site
            if is_first_site:
                customer.primary_site_id = site_id
            
        else:
            # New customer - create account
            logger.info(f"Creating new customer account for {customer_email}")
            
            customer = CustomerUser(
                email=customer_email,
                full_name=customer_name,
                password_hash=self._generate_temp_password_hash(),
                primary_site_id=site_id,
                email_verified=False,
                is_active=True
            )
            db.add(customer)
            await db.flush()  # Get customer.id
            
            # Create ownership record
            ownership = CustomerSiteOwnership(
                customer_user_id=customer.id,
                site_id=site_id,
                is_primary=True,
                acquired_at=datetime.now(timezone.utc)
            )
            db.add(ownership)
        
        # 3. Update site status
        site.status = "owned"
        site.purchased_at = datetime.now(timezone.utc)
        site.purchase_amount = 495.00
        site.subscription_status = "active"
        site.subscription_started_at = datetime.now(timezone.utc)
        site.monthly_amount = 99.00
        site.next_billing_date = (datetime.now(timezone.utc) + timedelta(days=30)).date()
        
        # 4. Create subscription record
        subscription = Subscription(
            customer_id=customer.id,
            site_id=site_id,
            recurrente_checkout_id=checkout_data.get("id"),
            amount_cents=9900,  # $99.00
            currency="USD",
            status="active",
            started_at=datetime.now(timezone.utc)
        )
        db.add(subscription)
        
        # 5. Create payment record
        payment = Payment(
            customer_id=customer.id,
            subscription_id=subscription.id,
            recurrente_checkout_id=checkout_data.get("id"),
            amount_cents=49500,  # $495.00
            currency="USD",
            payment_type="subscription_initial",
            status="completed",
            paid_at=datetime.now(timezone.utc)
        )
        db.add(payment)
        
        await db.commit()
        
        # 6. Send welcome email
        await self._send_welcome_email(customer, site)
        
        return {
            "status": "success",
            "customer_id": str(customer.id),
            "site_id": str(site_id),
            "is_new_customer": customer.created_at == datetime.now(timezone.utc)
        }
    
    def _generate_temp_password_hash(self) -> str:
        """Generate temporary password for new customers."""
        import secrets
        from passlib.context import CryptContext
        
        temp_password = secrets.token_urlsafe(16)
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(temp_password)
    
    async def _send_welcome_email(
        self,
        customer: CustomerUser,
        site: Site
    ) -> None:
        """Send welcome email with password setup link."""
        from services.email_service import EmailService
        
        # Generate password reset token
        token = secrets.token_urlsafe(32)
        customer.password_reset_token = token
        customer.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        
        email_service = EmailService()
        await email_service.send_welcome_email(
            to_email=customer.email,
            customer_name=customer.full_name or customer.email,
            site_slug=site.slug,
            site_url=f"https://sites.lavish.solutions/{site.slug}",
            dashboard_url=f"https://web.lavish.solutions/customer/dashboard",
            password_setup_url=f"https://web.lavish.solutions/auth/set-password?token={token}"
        )
```

#### Task 1.4: Enhance Support Ticket API

```python
# File: backend/api/v1/tickets.py

@router.post("/tickets", response_model=TicketResponse)
async def create_ticket(
    request: CreateTicketRequest,
    db: AsyncSession = Depends(get_db),
    current_customer: CustomerUser = Depends(get_current_customer)
):
    """
    Create a new support ticket.
    If customer has multiple sites, site_id is required.
    """
    # Validate site ownership
    if request.site_id:
        # Check if customer owns this site
        from sqlalchemy import select
        ownership_result = await db.execute(
            select(CustomerSiteOwnership).where(
                CustomerSiteOwnership.customer_user_id == current_customer.id,
                CustomerSiteOwnership.site_id == request.site_id
            )
        )
        ownership = ownership_result.scalar_one_or_none()
        
        if not ownership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't own this site"
            )
        
        site_id = request.site_id
    
    else:
        # No site_id provided
        if current_customer.has_multiple_sites:
            # Customer has multiple sites, must select one
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "site_selection_required",
                    "message": "You own multiple sites. Please select which site this ticket is for.",
                    "sites": [
                        {
                            "id": str(ownership.site_id),
                            "slug": ownership.site.slug,
                            "title": ownership.site.site_title,
                            "is_primary": ownership.is_primary
                        }
                        for ownership in current_customer.owned_sites
                    ]
                }
            )
        
        else:
            # Single site, use primary
            if not current_customer.primary_site_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No site associated with your account"
                )
            
            site_id = current_customer.primary_site_id
    
    # Create ticket
    ticket_service = TicketService()
    ticket = await ticket_service.create_ticket(
        db=db,
        customer_user_id=current_customer.id,
        site_id=site_id,
        subject=request.subject,
        description=request.description,
        category=request.category
    )
    
    return TicketResponse.from_orm(ticket)
```

---

### Phase 2: Frontend Enhancements (Week 2)

#### Task 2.1: Customer Dashboard - Multi-Site Support

**File:** `frontend/src/pages/CustomerDashboard/MySites.tsx`

```tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

interface Site {
  id: string;
  slug: string;
  site_title: string;
  site_url: string;
  status: string;
  subscription_status: string;
  next_billing_date: string;
  is_primary: boolean;
}

export const MySitesPage: React.FC = () => {
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchSites();
  }, []);

  const fetchSites = async () => {
    try {
      const response = await fetch('/api/v1/customer/my-sites', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setSites(data.sites);
    } catch (error) {
      console.error('Failed to fetch sites:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading your sites...</div>;
  }

  if (sites.length === 0) {
    return (
      <div className="empty-state">
        <h2>No Sites Yet</h2>
        <p>You haven't purchased any sites yet.</p>
      </div>
    );
  }

  return (
    <div className="my-sites-page">
      <h1>My Websites</h1>
      <div className="sites-grid">
        {sites.map(site => (
          <div
            key={site.id}
            className="site-card"
            onClick={() => navigate(`/customer/site/${site.id}`)}
          >
            <div className="site-header">
              <h3>{site.site_title || site.slug}</h3>
              {site.is_primary && <span className="badge primary">Primary</span>}
            </div>
            
            <div className="site-url">
              <a href={site.site_url} target="_blank" rel="noopener noreferrer">
                {site.site_url}
              </a>
            </div>
            
            <div className="site-status">
              <StatusBadge status={site.status} />
              <StatusBadge status={site.subscription_status} />
            </div>
            
            <div className="site-billing">
              <p>Next Billing: {new Date(site.next_billing_date).toLocaleDateString()}</p>
            </div>
            
            <div className="site-actions">
              <button onClick={(e) => {
                e.stopPropagation();
                navigate(`/customer/tickets/new?site=${site.id}`);
              }}>
                Create Ticket
              </button>
              <button onClick={(e) => {
                e.stopPropagation();
                window.open(site.site_url, '_blank');
              }}>
                View Site
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

#### Task 2.2: Ticket Creation with Site Selection

**File:** `frontend/src/pages/CustomerDashboard/CreateTicket.tsx`

```tsx
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

interface Site {
  id: string;
  slug: string;
  site_title: string;
  is_primary: boolean;
}

export const CreateTicketPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSite, setSelectedSite] = useState<string>('');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('site_edit');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchSites();
    
    // Pre-select site from URL if provided
    const siteId = searchParams.get('site');
    if (siteId) {
      setSelectedSite(siteId);
    }
  }, [searchParams]);

  const fetchSites = async () => {
    try {
      const response = await fetch('/api/v1/customer/my-sites', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setSites(data.sites);
      
      // Auto-select if only one site
      if (data.sites.length === 1) {
        setSelectedSite(data.sites[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch sites:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/v1/tickets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          site_id: selectedSite,
          subject,
          description,
          category
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        
        // Handle site selection error
        if (errorData.error === 'site_selection_required') {
          setError(errorData.message);
          setSites(errorData.sites);
          return;
        }
        
        throw new Error(errorData.detail || 'Failed to create ticket');
      }

      const ticket = await response.json();
      navigate(`/customer/tickets/${ticket.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="create-ticket-page">
      <h1>Create Support Ticket</h1>
      
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit}>
        {/* Site Selection (if multiple sites) */}
        {sites.length > 1 && (
          <div className="form-group">
            <label htmlFor="site">Which website is this ticket for? *</label>
            <select
              id="site"
              value={selectedSite}
              onChange={(e) => setSelectedSite(e.target.value)}
              required
            >
              <option value="">-- Select a website --</option>
              {sites.map(site => (
                <option key={site.id} value={site.id}>
                  {site.site_title || site.slug}
                  {site.is_primary && ' (Primary)'}
                </option>
              ))}
            </select>
          </div>
        )}
        
        {/* Category */}
        <div className="form-group">
          <label htmlFor="category">Category *</label>
          <select
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            required
          >
            <option value="site_edit">Website Edit Request</option>
            <option value="technical_support">Technical Support</option>
            <option value="billing">Billing Question</option>
            <option value="question">General Question</option>
            <option value="other">Other</option>
          </select>
        </div>
        
        {/* Subject */}
        <div className="form-group">
          <label htmlFor="subject">Subject *</label>
          <input
            type="text"
            id="subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Brief description of your request"
            required
            maxLength={200}
          />
        </div>
        
        {/* Description */}
        <div className="form-group">
          <label htmlFor="description">Description *</label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Please describe your request in detail..."
            required
            rows={8}
          />
          <small>
            For edit requests, please be as specific as possible. 
            You can also attach screenshots after creating the ticket.
          </small>
        </div>
        
        {/* Submit */}
        <div className="form-actions">
          <button
            type="button"
            onClick={() => navigate('/customer/tickets')}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading || !selectedSite}
          >
            {loading ? 'Creating...' : 'Create Ticket'}
          </button>
        </div>
      </form>
    </div>
  );
};
```

---

### Phase 3: Testing & Edge Cases (Week 3)

#### Test Cases

**1. First-Time Purchase**
- [ ] Preview site displays claim bar
- [ ] Click "Claim for $495" opens modal
- [ ] Enter email and name
- [ ] Redirect to Recurrente works
- [ ] Complete payment
- [ ] Webhook processes correctly
- [ ] Customer account created
- [ ] Welcome email sent
- [ ] Dashboard accessible
- [ ] Site shows as "owned"
- [ ] Subscription active

**2. Returning Customer (Single Site)**
- [ ] Login to dashboard
- [ ] See current site
- [ ] Purchase second site
- [ ] Both sites show in dashboard
- [ ] Can create tickets for each site separately

**3. Multi-Site Customer**
- [ ] Dashboard shows all sites
- [ ] Primary site marked correctly
- [ ] Ticket creation requires site selection
- [ ] Billing page shows all subscriptions
- [ ] Can manage each site independently

**4. Edge Cases**
- [ ] Customer already owns site (prevent duplicate purchase)
- [ ] Invalid site slug
- [ ] Expired password reset token
- [ ] Payment fails on Recurrente
- [ ] Webhook received twice (idempotency)
- [ ] Customer with no sites tries to create ticket

---

## 🎨 UI/UX Considerations

### Design Principles

1. **Semantic CSS Variables**
```css
/* File: frontend/src/styles/customer-dashboard.css */

:root {
  /* Site Status Colors */
  --status-preview: #94a3b8;
  --status-owned: #10b981;
  --status-active: #3b82f6;
  --status-suspended: #ef4444;
  
  /* Subscription Status Colors */
  --subscription-active: #10b981;
  --subscription-past-due: #f59e0b;
  --subscription-cancelled: #ef4444;
  
  /* Dashboard Layout */
  --dashboard-sidebar-width: 280px;
  --dashboard-content-padding: 32px;
  --dashboard-card-radius: 12px;
  
  /* Typography */
  --font-heading: 'Inter', system-ui, sans-serif;
  --font-body: 'Inter', system-ui, sans-serif;
  
  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
}

.site-card {
  background: var(--surface-primary);
  border-radius: var(--dashboard-card-radius);
  padding: var(--space-lg);
  transition: transform 0.2s, box-shadow 0.2s;
}

.site-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-md);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-badge.active {
  background: color-mix(in srgb, var(--subscription-active) 15%, transparent);
  color: var(--subscription-active);
}

.status-badge.past-due {
  background: color-mix(in srgb, var(--subscription-past-due) 15%, transparent);
  color: var(--subscription-past-due);
}
```

2. **Responsive Design**
- Mobile-first approach
- Breakpoints: 640px (mobile), 768px (tablet), 1024px (desktop)
- Touch-friendly tap targets (min 44x44px)
- Accessible keyboard navigation

3. **Loading States**
- Skeleton loaders for content
- Progress indicators for long operations
- Optimistic UI updates where possible

4. **Error Handling**
- Clear, actionable error messages
- Retry buttons for failed operations
- Graceful degradation

---

## 📊 Metrics & Monitoring

### Key Metrics to Track

1. **Conversion Funnel**
   - Preview page views
   - Claim button clicks
   - Checkout initiated
   - Payment completed
   - Account activations

2. **Customer Behavior**
   - Time to first ticket creation
   - Average tickets per customer
   - Multi-site adoption rate
   - Subscription retention

3. **System Health**
   - Webhook processing time
   - Email delivery rate
   - API response times
   - Error rates

### Monitoring Setup

```python
# File: backend/core/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Conversion metrics
claim_button_clicks = Counter(
    'claim_button_clicks_total',
    'Total number of claim button clicks',
    ['site_slug']
)

checkout_created = Counter(
    'checkout_created_total',
    'Total checkouts created',
    ['site_slug']
)

purchase_completed = Counter(
    'purchase_completed_total',
    'Total purchases completed',
    ['is_new_customer']
)

# Performance metrics
webhook_processing_time = Histogram(
    'webhook_processing_seconds',
    'Time to process webhook',
    ['event_type']
)

# Customer metrics
active_customers = Gauge(
    'active_customers_total',
    'Total active customers'
)

multi_site_customers = Gauge(
    'multi_site_customers_total',
    'Customers with multiple sites'
)
```

---

## 🔐 Security Considerations

### 1. Webhook Security
- ✅ Verify Recurrente signature on all webhooks
- ✅ Use HTTPS only
- ✅ Rate limiting on webhook endpoint
- ✅ Idempotency checks (prevent duplicate processing)

### 2. Customer Authentication
- ✅ JWT tokens with short expiration (15 minutes)
- ✅ Refresh tokens (7 days)
- ✅ Password reset tokens expire in 24 hours
- ✅ Email verification required

### 3. Site Ownership Validation
- ✅ Always verify customer owns site before operations
- ✅ Use junction table to prevent unauthorized access
- ✅ Audit log for all ownership changes

### 4. Data Privacy
- ✅ Hash all passwords with bcrypt
- ✅ Don't store credit card data (use Recurrente)
- ✅ GDPR-compliant data deletion

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] All tests passing (unit, integration, e2e)
- [ ] Database migration tested on staging
- [ ] Webhook endpoint verified with Recurrente sandbox
- [ ] Email templates tested
- [ ] Customer dashboard accessible
- [ ] Multi-site flow tested end-to-end

### Deployment Steps
1. [ ] Run database migration
2. [ ] Deploy backend API
3. [ ] Deploy frontend
4. [ ] Update Recurrente webhook URL
5. [ ] Monitor webhook processing
6. [ ] Verify email delivery
7. [ ] Test purchase flow end-to-end

### Post-Deployment
- [ ] Monitor error logs
- [ ] Track conversion metrics
- [ ] Customer support ready
- [ ] Rollback plan prepared

---

## 📚 Documentation Updates Needed

1. **Customer Portal Guide** (`docs/CUSTOMER_PORTAL_GUIDE.md`)
   - How to purchase a site
   - How to access dashboard
   - How to create tickets
   - How to manage multiple sites
   - Billing FAQs

2. **API Documentation** (`docs/API_DOCUMENTATION.md`)
   - Updated endpoints
   - Webhook payload examples
   - Authentication flows

3. **Admin Guide** (`docs/ADMIN_GUIDE.md`)
   - How to handle multi-site customers
   - How to manually link sites
   - Troubleshooting purchase issues

---

## ✅ Success Criteria

### Functional Requirements
- ✅ Customer can click "Claim for $495" and complete purchase
- ✅ Account automatically created on successful payment
- ✅ Customer receives welcome email
- ✅ Customer can access dashboard with purchased site
- ✅ Customer can create tickets for their site
- ✅ Multi-site customers can select which site when creating tickets
- ✅ Billing page shows correct subscription status

### Performance Requirements
- ✅ Webhook processing < 2 seconds
- ✅ Dashboard loads < 1 second
- ✅ Email delivery < 30 seconds
- ✅ 99.9% uptime

### User Experience Requirements
- ✅ Mobile-friendly UI
- ✅ Clear error messages
- ✅ Intuitive multi-site navigation
- ✅ Accessible (WCAG 2.1 AA)

---

## 📅 Timeline Estimate

### Week 1: Backend (8-10 hours)
- Day 1-2: Database migration & models
- Day 3-4: Site purchase service updates
- Day 5: Ticket API enhancements
- Day 6-7: Testing & debugging

### Week 2: Frontend (8-10 hours)
- Day 1-2: Dashboard multi-site UI
- Day 3-4: Ticket creation with site selection
- Day 5-6: Styling & responsive design
- Day 7: Integration testing

### Week 3: Testing & Polish (4-6 hours)
- Day 1-2: End-to-end testing
- Day 3: Edge case handling
- Day 4-5: Documentation
- Day 6-7: Deployment

**Total Estimate:** 20-26 hours over 3 weeks

---

## 🎓 Best Practices Applied

### 1. **Modular Code**
- Separate services for purchase, tickets, emails
- Clear single responsibility
- Easy to test and maintain

### 2. **Semantic CSS**
- Variables for colors, spacing, typography
- Consistent naming conventions
- Easy theming and updates

### 3. **Readable Functions**
- Max 50 lines per function
- Clear function names
- Type hints everywhere
- Comprehensive docstrings

### 4. **Error Handling**
- Try-except blocks around external calls
- Clear error messages for users
- Logging for debugging
- Graceful degradation

### 5. **Security First**
- Input validation
- SQL injection prevention (SQLAlchemy ORM)
- Authentication required for sensitive endpoints
- Webhook signature verification

---

## 🔮 Future Enhancements

### Phase 4: Advanced Features
1. **Team Access**: Allow customers to add team members
2. **Site Transfer**: Transfer site ownership between customers
3. **API Access**: Public API for programmatic site management
4. **White Label**: Custom branding for resellers
5. **Analytics**: Built-in site analytics dashboard

### Phase 5: Optimization
1. **AI-Powered Ticket Routing**: Auto-categorize and prioritize
2. **Predictive Billing**: Warn customers before subscription issues
3. **Bulk Operations**: Manage multiple sites at once
4. **Advanced Reporting**: Revenue, churn, customer health scores

---

## 📞 Support & Escalation

### Customer Support Flow
1. **AI First**: Auto-respond to common questions
2. **Ticket System**: For edit requests and issues
3. **Email Escalation**: For complex billing issues
4. **Phone Support**: For urgent matters (Phase 3)

### SLA Targets
- AI Response: Instant
- First Human Response: 4 hours
- Edit Request Completion: 24 hours
- Critical Issues: 2 hours

---

## 🎉 Summary

This comprehensive plan provides a **production-ready** architecture for connecting the website claim button to a complete customer management system. Key highlights:

✅ **Unique Site Tracking**: Each claim generates a unique checkout session  
✅ **Seamless Account Creation**: Automatic on successful payment  
✅ **Multi-Site Support**: Customers can own multiple websites  
✅ **Scoped Tickets**: Support tickets linked to specific sites  
✅ **Transparent Billing**: Clear subscription status per site  
✅ **Best Practices**: Modular code, semantic CSS, security-first design  
✅ **Scalable**: Ready for thousands of customers and sites  

**Next Steps:**
1. Review and approve this plan
2. Start with Phase 1 (Backend) implementation
3. Run through test cases as we build
4. Deploy to staging for QA
5. Launch to production! 🚀

---

**Questions or Clarifications?** Let's discuss any aspect of this plan before implementation begins.
