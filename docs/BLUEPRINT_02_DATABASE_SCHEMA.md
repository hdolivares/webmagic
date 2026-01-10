# WebMagic: Database Schema

## PostgreSQL Database Design

This document details all database tables, relationships, indexes, and constraints.

---

## 🗺️ Entity Relationship Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  coverage_grid  │     │    businesses   │     │ generated_sites │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │◄────│ coverage_id(FK) │     │ id (PK)         │
│ state           │     │ id (PK)         │◄────│ business_id(FK) │
│ city            │     │ gmb_id          │     │ subdomain       │
│ industry        │     │ name            │     │ html_content    │
│ status          │     │ email           │     │ status          │
└─────────────────┘     │ creative_dna    │     └────────┬────────┘
                        └────────┬────────┘              │
                                 │                       │
                                 ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    customers    │     │    campaigns    │     │  support_tickets│
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │     │ id (PK)         │
│ business_id(FK) │◄────│ business_id(FK) │     │ site_id (FK)    │
│ recurrente_id   │     │ site_id (FK)    │     │ customer_id(FK) │
│ email           │     │ status          │     │ status          │
└────────┬────────┘     └─────────────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  subscriptions  │     │ prompt_settings │     │  admin_users    │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │     │ id (PK)         │
│ customer_id(FK) │     │ agent_name      │     │ email           │
│ recurrente_id   │     │ version         │     │ role            │
│ status          │     │ content         │     │ password_hash   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 📋 Table Definitions

### 1. coverage_grid

The "conquest map" - tracks which locations and industries have been processed.

```sql
CREATE TABLE coverage_grid (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Location
    state VARCHAR(50) NOT NULL,
    city VARCHAR(100) NOT NULL,
    country VARCHAR(50) DEFAULT 'US',
    
    -- Industry
    industry VARCHAR(100) NOT NULL,
    industry_category VARCHAR(100),  -- e.g., "Services", "Food", "Health"
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    -- Values: pending, in_progress, completed, cooldown, paused
    
    -- Prioritization
    priority INTEGER DEFAULT 0,  -- Higher = process first
    population INTEGER,          -- City population for prioritization
    
    -- Metrics
    lead_count INTEGER DEFAULT 0,
    qualified_count INTEGER DEFAULT 0,  -- Passed filters
    site_count INTEGER DEFAULT 0,       -- Sites generated
    conversion_count INTEGER DEFAULT 0, -- Purchases
    
    -- Timing
    last_scraped_at TIMESTAMP,
    cooldown_until TIMESTAMP,  -- Don't re-scrape until this date
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(country, state, city, industry)
);

-- Indexes
CREATE INDEX idx_coverage_status ON coverage_grid(status);
CREATE INDEX idx_coverage_priority ON coverage_grid(priority DESC);
CREATE INDEX idx_coverage_location ON coverage_grid(state, city);
```

### 2. businesses

The leads - businesses scraped from Google My Business.

```sql
CREATE TABLE businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- External IDs
    gmb_id VARCHAR(100) UNIQUE,  -- Google My Business ID
    gmb_place_id VARCHAR(100),   -- Google Place ID
    
    -- Basic Info
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    
    -- Contact
    email VARCHAR(255),
    phone VARCHAR(50),
    website_url VARCHAR(500),  -- If they already have one (should be NULL)
    
    -- Location
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'US',
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    
    -- GMB Data
    category VARCHAR(100),
    subcategory VARCHAR(100),
    rating DECIMAL(2, 1),
    review_count INTEGER DEFAULT 0,
    
    -- Extracted Data (from AI analysis)
    reviews_summary TEXT,           -- AI-extracted highlights
    review_highlight TEXT,          -- The "hook" for email
    brand_archetype VARCHAR(50),    -- The Sage, Hero, etc.
    
    -- Photos
    photos_urls JSONB DEFAULT '[]', -- Array of photo URLs
    logo_url TEXT,
    
    -- Processing Status
    website_status VARCHAR(30) DEFAULT 'none',
    -- Values: none, generating, generated, deployed, sold, archived
    
    contact_status VARCHAR(30) DEFAULT 'pending',
    -- Values: pending, emailed, opened, clicked, replied, purchased, unsubscribed, bounced
    
    qualification_score INTEGER DEFAULT 0,  -- 0-100 lead score
    
    -- Creative DNA (stored after AI generation)
    creative_dna JSONB,
    -- Structure: {
    --   "archetype": "The Magician",
    --   "angle": "Scientific precision",
    --   "visual_theme": "Cyber-Medical",
    --   "tone_of_voice": "Clinical, confident",
    --   "design_system": { ... }
    -- }
    
    -- Tracking
    coverage_grid_id UUID REFERENCES coverage_grid(id) ON DELETE SET NULL,
    
    -- Timestamps
    scraped_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_business_status ON businesses(website_status, contact_status);
CREATE INDEX idx_business_location ON businesses(state, city);
CREATE INDEX idx_business_category ON businesses(category);
CREATE INDEX idx_business_rating ON businesses(rating DESC);
CREATE INDEX idx_business_email ON businesses(email) WHERE email IS NOT NULL;
CREATE INDEX idx_business_gmb ON businesses(gmb_id);
```

### 3. generated_sites

The generated websites.

```sql
CREATE TABLE generated_sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    
    -- Identifiers
    subdomain VARCHAR(100) UNIQUE NOT NULL,
    custom_domain VARCHAR(255),
    
    -- Content
    html_content TEXT NOT NULL,
    css_content TEXT,
    js_content TEXT,
    
    -- Metadata
    design_brief JSONB,       -- Art Director output
    builder_prompt TEXT,      -- The prompt used to build
    
    -- Versioning
    version INTEGER DEFAULT 1,
    previous_version_id UUID REFERENCES generated_sites(id),
    
    -- Status
    status VARCHAR(30) DEFAULT 'draft',
    -- Values: draft, preview, live, archived, sold
    
    -- Assets
    screenshot_desktop_url TEXT,
    screenshot_mobile_url TEXT,
    assets_urls JSONB DEFAULT '[]',  -- Additional images, etc.
    
    -- Performance
    lighthouse_score INTEGER,
    load_time_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    deployed_at TIMESTAMP,
    sold_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sites_business ON generated_sites(business_id);
CREATE INDEX idx_sites_status ON generated_sites(status);
CREATE INDEX idx_sites_subdomain ON generated_sites(subdomain);
CREATE INDEX idx_sites_domain ON generated_sites(custom_domain) WHERE custom_domain IS NOT NULL;
```

### 4. campaigns

Email outreach tracking.

```sql
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    site_id UUID REFERENCES generated_sites(id) ON DELETE SET NULL,
    
    -- Email Content
    subject_line TEXT NOT NULL,
    email_body TEXT NOT NULL,
    preview_text VARCHAR(200),
    
    -- Personalization Data
    review_highlight TEXT,
    business_name VARCHAR(255),
    recipient_name VARCHAR(255),
    recipient_email VARCHAR(255) NOT NULL,
    
    -- Status
    status VARCHAR(30) DEFAULT 'pending',
    -- Values: pending, scheduled, sent, delivered, opened, clicked, replied, converted, bounced, complained
    
    -- Tracking
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    opened_at TIMESTAMP,
    opened_count INTEGER DEFAULT 0,
    clicked_at TIMESTAMP,
    clicked_count INTEGER DEFAULT 0,
    replied_at TIMESTAMP,
    converted_at TIMESTAMP,
    
    -- Provider Info
    email_provider VARCHAR(50),  -- ses, sendgrid
    message_id VARCHAR(255),
    
    -- A/B Testing
    variant VARCHAR(50),  -- For testing different subject lines, etc.
    
    -- Error Handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    scheduled_for TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_campaigns_business ON campaigns(business_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_campaigns_scheduled ON campaigns(scheduled_for) WHERE status = 'scheduled';
```

### 5. customers

Paying customers (businesses that purchased).

```sql
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,
    site_id UUID REFERENCES generated_sites(id) ON DELETE SET NULL,
    
    -- Recurrente Data
    recurrente_user_id VARCHAR(50) UNIQUE,
    
    -- Contact Info
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    phone VARCHAR(50),
    
    -- Billing Info (optional, from Recurrente)
    billing_name VARCHAR(255),
    billing_tax_id VARCHAR(50),  -- NIT in Guatemala
    billing_address TEXT,
    
    -- Status
    status VARCHAR(30) DEFAULT 'active',
    -- Values: active, past_due, cancelled, churned
    
    -- Metrics
    lifetime_value_cents INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_recurrente ON customers(recurrente_user_id);
CREATE INDEX idx_customers_status ON customers(status);
```

### 6. subscriptions

Recurring billing tracking.

```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    site_id UUID REFERENCES generated_sites(id) ON DELETE SET NULL,
    
    -- Recurrente Data
    recurrente_subscription_id VARCHAR(50) UNIQUE,
    recurrente_checkout_id VARCHAR(50),
    
    -- Pricing
    amount_cents INTEGER NOT NULL,  -- Monthly amount
    currency VARCHAR(3) DEFAULT 'GTQ',
    
    -- Status
    status VARCHAR(30) DEFAULT 'active',
    -- Values: active, past_due, paused, cancelled
    
    -- Periods
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    
    -- Timestamps
    started_at TIMESTAMP DEFAULT NOW(),
    cancelled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_subscriptions_customer ON subscriptions(customer_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_recurrente ON subscriptions(recurrente_subscription_id);
```

### 7. payments

Individual payment records.

```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    
    -- Recurrente Data
    recurrente_payment_id VARCHAR(50) UNIQUE,
    recurrente_checkout_id VARCHAR(50),
    
    -- Amount
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'GTQ',
    fee_cents INTEGER,  -- Recurrente fee
    net_cents INTEGER,  -- Amount after fees
    
    -- Type
    payment_type VARCHAR(30) NOT NULL,
    -- Values: one_time, subscription, refund
    
    -- Status
    status VARCHAR(30) DEFAULT 'pending',
    -- Values: pending, succeeded, failed, refunded
    
    -- Payment Method
    payment_method VARCHAR(30),  -- card, bank_transfer
    card_last4 VARCHAR(4),
    card_network VARCHAR(20),  -- visa, mastercard
    
    -- Timestamps
    paid_at TIMESTAMP,
    refunded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_payments_customer ON payments(customer_id);
CREATE INDEX idx_payments_subscription ON payments(subscription_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_recurrente ON payments(recurrente_payment_id);
```

### 8. prompt_settings

Dynamic prompt configuration (editable via admin UI).

```sql
CREATE TABLE prompt_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Agent Identification
    agent_name VARCHAR(50) NOT NULL,
    -- Values: analyst, concept, director, architect, email_composer
    
    -- Section within the agent
    section_name VARCHAR(100) NOT NULL,
    -- Examples: "review_highlight", "vibe_code", "typography_rules"
    
    -- Content
    content TEXT NOT NULL,
    description TEXT,  -- Help text for admin UI
    
    -- Versioning
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    
    -- A/B Testing
    variant VARCHAR(50),  -- For testing different versions
    weight INTEGER DEFAULT 100,  -- Percentage weight for A/B
    
    -- Performance Tracking
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,  -- Conversions when used
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES admin_users(id),
    
    -- Constraints
    UNIQUE(agent_name, section_name, version)
);

-- Indexes
CREATE INDEX idx_prompts_agent ON prompt_settings(agent_name);
CREATE INDEX idx_prompts_active ON prompt_settings(is_active) WHERE is_active = true;
```

### 9. prompt_templates

Master prompt templates (rarely changed).

```sql
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identification
    agent_name VARCHAR(50) NOT NULL UNIQUE,
    
    -- Template
    system_prompt TEXT NOT NULL,      -- The base instructions
    output_format TEXT,               -- Expected output structure
    
    -- Placeholders (which sections can be injected)
    placeholder_sections JSONB DEFAULT '[]',
    -- Example: ["frontend_aesthetics", "vibe_list", "banned_fonts"]
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 10. support_tickets

Customer change requests.

```sql
CREATE TABLE support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    site_id UUID NOT NULL REFERENCES generated_sites(id) ON DELETE CASCADE,
    
    -- Request
    request_text TEXT NOT NULL,
    screenshot_urls JSONB DEFAULT '[]',
    
    -- Status
    status VARCHAR(30) DEFAULT 'open',
    -- Values: open, in_progress, completed, rejected
    
    -- AI Processing
    ai_interpretation TEXT,  -- What the AI understood
    ai_changes_made TEXT,    -- Description of changes
    
    -- Resolution
    resolved_by VARCHAR(20),  -- ai, human
    resolution_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_tickets_customer ON support_tickets(customer_id);
CREATE INDEX idx_tickets_status ON support_tickets(status);
```

### 11. admin_users

Dashboard access.

```sql
CREATE TABLE admin_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Auth
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Profile
    full_name VARCHAR(255),
    
    -- Role
    role VARCHAR(30) DEFAULT 'viewer',
    -- Values: viewer, editor, admin, super_admin
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    
    -- Timestamps
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 12. analytics_snapshots

Daily metrics snapshots.

```sql
CREATE TABLE analytics_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date DATE NOT NULL,
    
    -- Lead Metrics
    leads_scraped INTEGER DEFAULT 0,
    leads_qualified INTEGER DEFAULT 0,
    
    -- Site Metrics
    sites_generated INTEGER DEFAULT 0,
    sites_deployed INTEGER DEFAULT 0,
    
    -- Outreach Metrics
    emails_sent INTEGER DEFAULT 0,
    emails_opened INTEGER DEFAULT 0,
    emails_clicked INTEGER DEFAULT 0,
    
    -- Conversion Metrics
    checkouts_created INTEGER DEFAULT 0,
    purchases INTEGER DEFAULT 0,
    
    -- Revenue
    revenue_cents INTEGER DEFAULT 0,
    mrr_cents INTEGER DEFAULT 0,
    
    -- Costs
    api_costs_cents INTEGER DEFAULT 0,  -- Outscraper, Claude, etc.
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(snapshot_date)
);

-- Index
CREATE INDEX idx_snapshots_date ON analytics_snapshots(snapshot_date DESC);
```

### 13. activity_log

Audit trail for important actions.

```sql
CREATE TABLE activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- What happened
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- business, site, campaign, etc.
    entity_id UUID,
    
    -- Details
    details JSONB,
    
    -- Who/What triggered it
    actor_type VARCHAR(20),  -- user, system, webhook
    actor_id UUID,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_activity_entity ON activity_log(entity_type, entity_id);
CREATE INDEX idx_activity_action ON activity_log(action);
CREATE INDEX idx_activity_created ON activity_log(created_at DESC);
```

---

## 🔗 Key Relationships

```
coverage_grid (1) ──────────────────────────────────── (N) businesses
businesses (1) ─────────────────────────────────────── (N) generated_sites
businesses (1) ─────────────────────────────────────── (N) campaigns
businesses (1) ─────────────────────────────────────── (0..1) customers
customers (1) ──────────────────────────────────────── (N) subscriptions
customers (1) ──────────────────────────────────────── (N) payments
customers (1) ──────────────────────────────────────── (N) support_tickets
generated_sites (1) ────────────────────────────────── (N) support_tickets
subscriptions (1) ──────────────────────────────────── (N) payments
```

---

## 📊 Common Queries

### Get next target for autopilot
```sql
SELECT * FROM coverage_grid
WHERE status = 'pending'
  AND (cooldown_until IS NULL OR cooldown_until < NOW())
ORDER BY priority DESC, population DESC
LIMIT 1;
```

### Get qualified leads ready for site generation
```sql
SELECT * FROM businesses
WHERE website_status = 'none'
  AND email IS NOT NULL
  AND rating >= 4.0
  AND review_count >= 10
ORDER BY qualification_score DESC
LIMIT 50;
```

### Get sites ready for outreach
```sql
SELECT s.*, b.email, b.name as business_name
FROM generated_sites s
JOIN businesses b ON s.business_id = b.id
WHERE s.status = 'preview'
  AND b.contact_status = 'pending'
  AND s.screenshot_desktop_url IS NOT NULL;
```

### Dashboard metrics
```sql
SELECT 
    COUNT(*) FILTER (WHERE website_status = 'generated') as sites_generated,
    COUNT(*) FILTER (WHERE contact_status = 'purchased') as conversions,
    COUNT(*) FILTER (WHERE contact_status = 'emailed') as emails_sent
FROM businesses
WHERE created_at >= NOW() - INTERVAL '30 days';
```

---

## 🔄 Migrations

Initial migration file structure:

```
migrations/versions/
├── 001_initial_schema.py           # All tables above
├── 002_add_prompt_settings.py      # Prompt tables
├── 003_add_analytics.py            # Analytics tables
├── 004_add_activity_log.py         # Audit trail
└── ...
```
