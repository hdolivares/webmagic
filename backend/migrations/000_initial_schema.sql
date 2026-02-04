-- WebMagic Initial Schema Migration
-- Run this on a fresh PostgreSQL database
-- Generated: 2026-02-03

-- ============================================
-- EXTENSIONS
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. ADMIN USERS (Authentication)
-- ============================================
CREATE TABLE IF NOT EXISTS admin_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(30) DEFAULT 'viewer' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_admin_users_email ON admin_users(email);

-- ============================================
-- 2. COVERAGE GRID (Scraping Territories)
-- ============================================
CREATE TABLE IF NOT EXISTS coverage_grid (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    state VARCHAR(50) NOT NULL,
    city VARCHAR(100) NOT NULL,
    country VARCHAR(50) DEFAULT 'US',
    zone_id VARCHAR(20),
    zone_lat VARCHAR(20),
    zone_lon VARCHAR(20),
    zone_radius_km VARCHAR(10),
    industry VARCHAR(100) NOT NULL,
    industry_category VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    priority INTEGER DEFAULT 0 NOT NULL,
    population INTEGER,
    lead_count INTEGER DEFAULT 0 NOT NULL,
    qualified_count INTEGER DEFAULT 0 NOT NULL,
    site_count INTEGER DEFAULT 0 NOT NULL,
    conversion_count INTEGER DEFAULT 0 NOT NULL,
    scrape_count INTEGER DEFAULT 0 NOT NULL,
    scrape_offset INTEGER DEFAULT 0 NOT NULL,
    has_more_results BOOLEAN DEFAULT TRUE NOT NULL,
    max_results_available INTEGER,
    last_scrape_size INTEGER,
    estimated_businesses INTEGER,
    last_scraped_at TIMESTAMP,
    cooldown_until TIMESTAMP,
    next_scheduled TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_coverage_grid_state ON coverage_grid(state);
CREATE INDEX IF NOT EXISTS idx_coverage_grid_city ON coverage_grid(city);
CREATE INDEX IF NOT EXISTS idx_coverage_grid_industry ON coverage_grid(industry);
CREATE INDEX IF NOT EXISTS idx_coverage_grid_status ON coverage_grid(status);
CREATE INDEX IF NOT EXISTS idx_coverage_grid_priority ON coverage_grid(priority);
CREATE INDEX IF NOT EXISTS idx_coverage_grid_zone ON coverage_grid(zone_id);

-- ============================================
-- 3. BUSINESSES (Leads)
-- ============================================
CREATE TABLE IF NOT EXISTS businesses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gmb_id VARCHAR(100) UNIQUE,
    gmb_place_id VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    website_url VARCHAR(500),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'US',
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    rating NUMERIC(2, 1),
    review_count INTEGER DEFAULT 0,
    reviews_summary TEXT,
    review_highlight TEXT,
    brand_archetype VARCHAR(50),
    photos_urls JSONB DEFAULT '[]',
    logo_url TEXT,
    website_status VARCHAR(30) DEFAULT 'none',
    contact_status VARCHAR(30) DEFAULT 'pending',
    qualification_score INTEGER DEFAULT 0,
    creative_dna JSONB,
    coverage_grid_id UUID REFERENCES coverage_grid(id) ON DELETE SET NULL,
    scraped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_businesses_gmb_id ON businesses(gmb_id);
CREATE INDEX IF NOT EXISTS idx_businesses_slug ON businesses(slug);
CREATE INDEX IF NOT EXISTS idx_businesses_email ON businesses(email);
CREATE INDEX IF NOT EXISTS idx_businesses_city ON businesses(city);
CREATE INDEX IF NOT EXISTS idx_businesses_state ON businesses(state);
CREATE INDEX IF NOT EXISTS idx_businesses_category ON businesses(category);
CREATE INDEX IF NOT EXISTS idx_businesses_rating ON businesses(rating);
CREATE INDEX IF NOT EXISTS idx_businesses_website_status ON businesses(website_status);
CREATE INDEX IF NOT EXISTS idx_businesses_contact_status ON businesses(contact_status);

-- ============================================
-- 4. GENERATED SITES (AI Websites)
-- ============================================
CREATE TABLE IF NOT EXISTS generated_sites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    subdomain VARCHAR(100) UNIQUE NOT NULL,
    custom_domain VARCHAR(255),
    html_content TEXT NOT NULL,
    css_content TEXT,
    js_content TEXT,
    design_brief JSONB,
    builder_prompt TEXT,
    version INTEGER DEFAULT 1 NOT NULL,
    previous_version_id UUID REFERENCES generated_sites(id) ON DELETE SET NULL,
    status VARCHAR(30) DEFAULT 'draft' NOT NULL,
    screenshot_desktop_url TEXT,
    screenshot_mobile_url TEXT,
    assets_urls JSONB DEFAULT '[]',
    lighthouse_score INTEGER,
    load_time_ms INTEGER,
    deployed_at TIMESTAMP,
    sold_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_generated_sites_business ON generated_sites(business_id);
CREATE INDEX IF NOT EXISTS idx_generated_sites_subdomain ON generated_sites(subdomain);
CREATE INDEX IF NOT EXISTS idx_generated_sites_custom_domain ON generated_sites(custom_domain);
CREATE INDEX IF NOT EXISTS idx_generated_sites_status ON generated_sites(status);

-- ============================================
-- 5. CAMPAIGNS (Email/SMS Outreach)
-- ============================================
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    site_id UUID REFERENCES generated_sites(id) ON DELETE SET NULL,
    channel VARCHAR(20) DEFAULT 'email' NOT NULL,
    subject_line TEXT,
    email_body TEXT,
    preview_text VARCHAR(200),
    review_highlight TEXT,
    sms_body TEXT,
    sms_provider VARCHAR(50),
    sms_sid VARCHAR(255),
    sms_segments INTEGER,
    sms_cost NUMERIC(10, 4),
    business_name VARCHAR(255),
    recipient_name VARCHAR(255),
    recipient_email VARCHAR(255),
    recipient_phone VARCHAR(20),
    status VARCHAR(30) DEFAULT 'pending' NOT NULL,
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    opened_at TIMESTAMP,
    opened_count INTEGER DEFAULT 0 NOT NULL,
    clicked_at TIMESTAMP,
    clicked_count INTEGER DEFAULT 0 NOT NULL,
    replied_at TIMESTAMP,
    converted_at TIMESTAMP,
    email_provider VARCHAR(50),
    message_id VARCHAR(255),
    variant VARCHAR(50),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0 NOT NULL,
    scheduled_for TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_campaigns_business ON campaigns(business_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_site ON campaigns(site_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_channel ON campaigns(channel);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_recipient_email ON campaigns(recipient_email);
CREATE INDEX IF NOT EXISTS idx_campaigns_recipient_phone ON campaigns(recipient_phone);
CREATE INDEX IF NOT EXISTS idx_campaigns_message_id ON campaigns(message_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_sms_sid ON campaigns(sms_sid);
CREATE INDEX IF NOT EXISTS idx_campaigns_scheduled ON campaigns(scheduled_for);

-- ============================================
-- 6. CUSTOMERS (Payment Customers - Legacy)
-- ============================================
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,
    site_id UUID REFERENCES generated_sites(id) ON DELETE SET NULL,
    recurrente_user_id VARCHAR(50) UNIQUE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    phone VARCHAR(50),
    billing_name VARCHAR(255),
    billing_tax_id VARCHAR(50),
    billing_address TEXT,
    status VARCHAR(30) DEFAULT 'active' NOT NULL,
    lifetime_value_cents INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_customers_business ON customers(business_id);
CREATE INDEX IF NOT EXISTS idx_customers_site ON customers(site_id);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_recurrente ON customers(recurrente_user_id);
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);

-- ============================================
-- 7. SUBSCRIPTIONS
-- ============================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    site_id UUID REFERENCES generated_sites(id) ON DELETE SET NULL,
    recurrente_subscription_id VARCHAR(50) UNIQUE,
    recurrente_checkout_id VARCHAR(50),
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'GTQ' NOT NULL,
    status VARCHAR(30) DEFAULT 'active' NOT NULL,
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    started_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_subscriptions_customer ON subscriptions(customer_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_site ON subscriptions(site_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_recurrente ON subscriptions(recurrente_subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);

-- ============================================
-- 8. PAYMENTS
-- ============================================
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    recurrente_payment_id VARCHAR(50) UNIQUE,
    recurrente_checkout_id VARCHAR(50),
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'GTQ' NOT NULL,
    fee_cents INTEGER,
    net_cents INTEGER,
    payment_type VARCHAR(30) NOT NULL,
    status VARCHAR(30) DEFAULT 'pending' NOT NULL,
    payment_method VARCHAR(30),
    card_last4 VARCHAR(4),
    card_network VARCHAR(20),
    paid_at TIMESTAMP,
    refunded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_subscription ON payments(subscription_id);
CREATE INDEX IF NOT EXISTS idx_payments_recurrente ON payments(recurrente_payment_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

-- ============================================
-- 9. SITE VERSIONS (must be before sites for FK)
-- ============================================
CREATE TABLE IF NOT EXISTS site_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL,  -- FK added after sites table
    version_number INTEGER NOT NULL,
    html_content TEXT NOT NULL,
    css_content TEXT,
    js_content TEXT,
    assets JSONB,
    change_description TEXT,
    change_type VARCHAR(50),
    created_by_type VARCHAR(50),
    created_by_id UUID,
    is_current BOOLEAN DEFAULT FALSE,
    is_preview BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_site_versions_site ON site_versions(site_id);

-- ============================================
-- 10. SITES (Customer Sites - Phase 2)
-- ============================================
CREATE TABLE IF NOT EXISTS sites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug VARCHAR(255) UNIQUE NOT NULL,
    business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'preview' NOT NULL,
    purchased_at TIMESTAMP WITH TIME ZONE,
    purchase_amount NUMERIC(10, 2) DEFAULT 495.00,
    purchase_transaction_id VARCHAR(255),
    subscription_status VARCHAR(50),
    subscription_id VARCHAR(255),
    subscription_started_at TIMESTAMP WITH TIME ZONE,
    subscription_ends_at TIMESTAMP WITH TIME ZONE,
    monthly_amount NUMERIC(10, 2) DEFAULT 99.00,
    next_billing_date DATE,
    grace_period_ends TIMESTAMP WITH TIME ZONE,
    custom_domain VARCHAR(255) UNIQUE,
    domain_verified BOOLEAN DEFAULT FALSE,
    domain_verification_token VARCHAR(255),
    domain_verified_at TIMESTAMP WITH TIME ZONE,
    ssl_provisioned BOOLEAN DEFAULT FALSE,
    ssl_certificate_path VARCHAR(500),
    ssl_provisioned_at TIMESTAMP WITH TIME ZONE,
    current_version_id UUID REFERENCES site_versions(id) ON DELETE SET NULL,
    site_title VARCHAR(255),
    site_description TEXT,
    meta_tags JSONB,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sites_slug ON sites(slug);
CREATE INDEX IF NOT EXISTS idx_sites_business ON sites(business_id);
CREATE INDEX IF NOT EXISTS idx_sites_status ON sites(status);
CREATE INDEX IF NOT EXISTS idx_sites_subscription_status ON sites(subscription_status);
CREATE INDEX IF NOT EXISTS idx_sites_custom_domain ON sites(custom_domain);

-- Add FK from site_versions to sites
ALTER TABLE site_versions ADD CONSTRAINT fk_site_versions_site 
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE;

-- ============================================
-- 11. CUSTOMER USERS (Authentication - Phase 2)
-- ============================================
CREATE TABLE IF NOT EXISTS customer_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    phone VARCHAR(50),
    primary_site_id UUID REFERENCES sites(id) ON DELETE SET NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    email_verified_at TIMESTAMP WITH TIME ZONE,
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP WITH TIME ZONE,
    last_login TIMESTAMP WITH TIME ZONE,
    login_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_customer_users_email ON customer_users(email);
CREATE INDEX IF NOT EXISTS idx_customer_users_primary_site ON customer_users(primary_site_id);
CREATE INDEX IF NOT EXISTS idx_customer_users_verification_token ON customer_users(email_verification_token);

-- ============================================
-- 12. CUSTOMER SITE OWNERSHIP (Many-to-Many)
-- ============================================
CREATE TABLE IF NOT EXISTS customer_site_ownership (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_user_id UUID NOT NULL REFERENCES customer_users(id) ON DELETE CASCADE,
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'owner' NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    acquired_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_customer_site_ownership_customer ON customer_site_ownership(customer_user_id);
CREATE INDEX IF NOT EXISTS idx_customer_site_ownership_site ON customer_site_ownership(site_id);

-- ============================================
-- 13. EDIT REQUESTS (AI Edits)
-- ============================================
CREATE TABLE IF NOT EXISTS edit_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    request_text TEXT NOT NULL,
    request_type VARCHAR(50),
    target_section VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending' NOT NULL,
    ai_interpretation JSONB,
    ai_confidence NUMERIC(3, 2),
    changes_made JSONB,
    preview_version_id UUID REFERENCES site_versions(id),
    preview_url VARCHAR(500),
    customer_approved BOOLEAN,
    customer_feedback TEXT,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_reason TEXT,
    deployed_version_id UUID REFERENCES site_versions(id),
    deployed_at TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_edit_requests_site ON edit_requests(site_id);
CREATE INDEX IF NOT EXISTS idx_edit_requests_status ON edit_requests(status);

-- ============================================
-- 14. DOMAIN VERIFICATION RECORDS
-- ============================================
CREATE TABLE IF NOT EXISTS domain_verification_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    verification_method VARCHAR(50) NOT NULL,
    verification_token VARCHAR(255) NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP WITH TIME ZONE,
    verification_attempts INTEGER DEFAULT 0,
    last_check_at TIMESTAMP WITH TIME ZONE,
    dns_records JSONB,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_domain_verification_site ON domain_verification_records(site_id);

-- ============================================
-- 15. SUPPORT TICKETS
-- ============================================
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_user_id UUID NOT NULL REFERENCES customer_users(id) ON DELETE CASCADE,
    site_id UUID REFERENCES sites(id) ON DELETE SET NULL,
    ticket_number VARCHAR(20) UNIQUE NOT NULL,
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium' NOT NULL,
    status VARCHAR(30) DEFAULT 'new' NOT NULL,
    ai_processed BOOLEAN DEFAULT FALSE,
    ai_category_confidence JSONB,
    ai_suggested_response TEXT,
    ai_processing_notes JSONB,
    assigned_to_admin_id UUID REFERENCES admin_users(id) ON DELETE SET NULL,
    assigned_at TIMESTAMP WITH TIME ZONE,
    first_response_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    last_customer_message_at TIMESTAMP WITH TIME ZONE,
    last_staff_message_at TIMESTAMP WITH TIME ZONE,
    customer_satisfaction_rating VARCHAR(20),
    internal_notes TEXT,
    tags JSONB,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_support_tickets_customer ON support_tickets(customer_user_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_site ON support_tickets(site_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_number ON support_tickets(ticket_number);
CREATE INDEX IF NOT EXISTS idx_support_tickets_category ON support_tickets(category);
CREATE INDEX IF NOT EXISTS idx_support_tickets_priority ON support_tickets(priority);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_assigned ON support_tickets(assigned_to_admin_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status_created ON support_tickets(status, created_at);
CREATE INDEX IF NOT EXISTS idx_support_tickets_category_status ON support_tickets(category, status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_customer_status ON support_tickets(customer_user_id, status);

-- ============================================
-- 16. TICKET MESSAGES
-- ============================================
CREATE TABLE IF NOT EXISTS ticket_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    customer_user_id UUID REFERENCES customer_users(id) ON DELETE SET NULL,
    admin_user_id UUID REFERENCES admin_users(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    message_type VARCHAR(20) NOT NULL,
    ai_generated BOOLEAN DEFAULT FALSE,
    ai_model VARCHAR(50),
    ai_confidence JSONB,
    attachments JSONB,
    internal_only BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ticket_messages_ticket ON ticket_messages(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_messages_customer ON ticket_messages(customer_user_id);
CREATE INDEX IF NOT EXISTS idx_ticket_messages_admin ON ticket_messages(admin_user_id);
CREATE INDEX IF NOT EXISTS idx_ticket_messages_type ON ticket_messages(message_type);
CREATE INDEX IF NOT EXISTS idx_ticket_messages_ticket_created ON ticket_messages(ticket_id, created_at);

-- ============================================
-- 17. TICKET TEMPLATES
-- ============================================
CREATE TABLE IF NOT EXISTS ticket_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,
    subject_template VARCHAR(255),
    message_template TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    usage_count JSONB DEFAULT '0',
    created_by_admin_id UUID REFERENCES admin_users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ticket_templates_category ON ticket_templates(category);

-- ============================================
-- 18. PROMPT TEMPLATES
-- ============================================
CREATE TABLE IF NOT EXISTS prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(50) UNIQUE NOT NULL,
    system_prompt TEXT NOT NULL,
    output_format TEXT,
    placeholder_sections JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_agent ON prompt_templates(agent_name);

-- ============================================
-- 19. PROMPT SETTINGS
-- ============================================
CREATE TABLE IF NOT EXISTS prompt_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(50) NOT NULL,
    section_name VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    description TEXT,
    version INTEGER DEFAULT 1 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    variant VARCHAR(50),
    weight INTEGER DEFAULT 100 NOT NULL,
    usage_count INTEGER DEFAULT 0 NOT NULL,
    success_count INTEGER DEFAULT 0 NOT NULL,
    created_by UUID REFERENCES admin_users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prompt_settings_agent ON prompt_settings(agent_name);
CREATE INDEX IF NOT EXISTS idx_prompt_settings_active ON prompt_settings(is_active);

-- ============================================
-- 20. GEO STRATEGIES
-- ============================================
CREATE TABLE IF NOT EXISTS geo_strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(10) NOT NULL,
    country VARCHAR(10) DEFAULT 'US' NOT NULL,
    category VARCHAR(100) NOT NULL,
    city_center_lat FLOAT NOT NULL,
    city_center_lon FLOAT NOT NULL,
    population INTEGER,
    geographic_analysis TEXT,
    business_distribution_analysis TEXT,
    strategy_reasoning TEXT,
    zones JSONB NOT NULL,
    avoid_areas JSONB,
    total_zones INTEGER NOT NULL,
    estimated_total_businesses INTEGER,
    estimated_searches_needed INTEGER,
    coverage_area_km2 FLOAT,
    zones_completed INTEGER DEFAULT 0 NOT NULL,
    businesses_found INTEGER DEFAULT 0 NOT NULL,
    last_scrape_at TIMESTAMP,
    performance_data JSONB,
    adaptation_notes TEXT,
    model_used VARCHAR(50) DEFAULT 'claude-sonnet-4-5' NOT NULL,
    strategy_version INTEGER DEFAULT 1 NOT NULL,
    is_active VARCHAR(20) DEFAULT 'active' NOT NULL,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_strategy_location ON geo_strategies(city, state, country);
CREATE INDEX IF NOT EXISTS idx_geo_strategy_category ON geo_strategies(category);
CREATE INDEX IF NOT EXISTS idx_geo_strategy_active ON geo_strategies(is_active);
CREATE INDEX IF NOT EXISTS idx_geo_strategy_lookup ON geo_strategies(city, state, category, is_active);

-- ============================================
-- 21. DRAFT CAMPAIGNS
-- ============================================
CREATE TABLE IF NOT EXISTS draft_campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(10) NOT NULL,
    category VARCHAR(100) NOT NULL,
    zone_id VARCHAR(50) NOT NULL,
    zone_lat VARCHAR(20),
    zone_lon VARCHAR(20),
    zone_radius_km VARCHAR(10),
    total_businesses_found INTEGER DEFAULT 0 NOT NULL,
    qualified_leads_count INTEGER DEFAULT 0 NOT NULL,
    qualification_rate INTEGER,
    business_ids JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending_review' NOT NULL,
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    review_notes VARCHAR(500),
    messages_sent INTEGER DEFAULT 0,
    messages_failed INTEGER DEFAULT 0,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_draft_campaigns_strategy ON draft_campaigns(strategy_id);
CREATE INDEX IF NOT EXISTS idx_draft_campaigns_status ON draft_campaigns(status);

-- ============================================
-- 22. SMS OPT-OUTS (TCPA Compliance)
-- ============================================
CREATE TABLE IF NOT EXISTS sms_opt_outs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    opted_out_at TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(50) NOT NULL,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sms_opt_outs_phone ON sms_opt_outs(phone_number);
CREATE INDEX IF NOT EXISTS idx_sms_opt_outs_date ON sms_opt_outs(opted_out_at);

-- ============================================
-- 23. SYSTEM SETTINGS
-- ============================================
CREATE TABLE IF NOT EXISTS system_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    value_type VARCHAR(20) DEFAULT 'string' NOT NULL,
    category VARCHAR(50) NOT NULL,
    label VARCHAR(200) NOT NULL,
    description TEXT,
    options JSONB,
    is_secret BOOLEAN DEFAULT FALSE NOT NULL,
    is_required BOOLEAN DEFAULT FALSE NOT NULL,
    default_value TEXT,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(key);
CREATE INDEX IF NOT EXISTS idx_system_settings_category ON system_settings(category);

-- ============================================
-- 24. ACTIVITY LOG (Audit Trail)
-- ============================================
CREATE TABLE IF NOT EXISTS activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    details JSONB,
    actor_type VARCHAR(30),
    actor_id UUID,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_log_action ON activity_log(action);
CREATE INDEX IF NOT EXISTS idx_activity_log_entity_type ON activity_log(entity_type);
CREATE INDEX IF NOT EXISTS idx_activity_log_entity_id ON activity_log(entity_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_actor_type ON activity_log(actor_type);
CREATE INDEX IF NOT EXISTS idx_activity_log_actor_id ON activity_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_created ON activity_log(created_at);
CREATE INDEX IF NOT EXISTS idx_activity_entity ON activity_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_activity_actor ON activity_log(actor_type, actor_id);
CREATE INDEX IF NOT EXISTS idx_activity_action_date ON activity_log(action, created_at);

-- ============================================
-- 25. ANALYTICS SNAPSHOTS (Daily KPIs)
-- ============================================
CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    snapshot_date DATE UNIQUE NOT NULL,
    leads_scraped INTEGER DEFAULT 0,
    leads_qualified INTEGER DEFAULT 0,
    sites_generated INTEGER DEFAULT 0,
    sites_deployed INTEGER DEFAULT 0,
    emails_sent INTEGER DEFAULT 0,
    emails_opened INTEGER DEFAULT 0,
    emails_clicked INTEGER DEFAULT 0,
    checkouts_created INTEGER DEFAULT 0,
    purchases INTEGER DEFAULT 0,
    revenue_cents INTEGER DEFAULT 0,
    mrr_cents INTEGER DEFAULT 0,
    api_costs_cents INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_date ON analytics_snapshots(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_analytics_date_desc ON analytics_snapshots(snapshot_date DESC);

-- ============================================
-- MIGRATION COMPLETE
-- ============================================
-- Total: 25 tables created (excluding deprecated old_support_tickets_deprecated)

