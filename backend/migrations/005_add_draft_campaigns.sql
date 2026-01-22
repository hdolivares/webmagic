-- Migration 005: Add Draft Campaigns Table
--
-- Purpose: Enable "draft mode" for intelligent campaigns where businesses are
-- scraped and qualified, but outreach is held for manual review and approval.
--
-- Created: 2026-01-22

CREATE TABLE IF NOT EXISTS draft_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Strategy reference
    strategy_id UUID NOT NULL,
    
    -- Location and category
    city VARCHAR(100) NOT NULL,
    state VARCHAR(10) NOT NULL,
    category VARCHAR(100) NOT NULL,
    
    -- Zone information
    zone_id VARCHAR(50) NOT NULL,
    zone_lat VARCHAR(20),
    zone_lon VARCHAR(20),
    zone_radius_km VARCHAR(10),
    
    -- Results summary
    total_businesses_found INTEGER NOT NULL DEFAULT 0,
    qualified_leads_count INTEGER NOT NULL DEFAULT 0,
    qualification_rate INTEGER,
    
    -- Business IDs (JSON array of UUIDs)
    business_ids JSONB NOT NULL,
    
    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'pending_review',
    -- Status values: 'pending_review', 'approved', 'rejected', 'sent'
    
    -- Review information
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    review_notes VARCHAR(500),
    
    -- Outreach tracking (after approval)
    messages_sent INTEGER DEFAULT 0,
    messages_failed INTEGER DEFAULT 0,
    sent_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX idx_draft_campaigns_strategy ON draft_campaigns(strategy_id);
CREATE INDEX idx_draft_campaigns_status ON draft_campaigns(status);
CREATE INDEX idx_draft_campaigns_location ON draft_campaigns(city, state);
CREATE INDEX idx_draft_campaigns_category ON draft_campaigns(category);
CREATE INDEX idx_draft_campaigns_created ON draft_campaigns(created_at DESC);

-- Composite index for filtering pending reviews by location
CREATE INDEX idx_draft_campaigns_pending_location 
    ON draft_campaigns(status, city, state) 
    WHERE status = 'pending_review';

-- Comments for documentation
COMMENT ON TABLE draft_campaigns IS 
    'Stores scraping campaigns in draft mode - businesses found but outreach not yet sent. Enables manual review workflow.';

COMMENT ON COLUMN draft_campaigns.business_ids IS 
    'JSON array of business UUIDs that were found and qualified in this campaign';

COMMENT ON COLUMN draft_campaigns.status IS 
    'Campaign status: pending_review (awaiting approval), approved (approved but not sent), rejected (declined), sent (outreach completed)';

COMMENT ON COLUMN draft_campaigns.qualification_rate IS 
    'Percentage of found businesses that qualified as leads (0-100)';

