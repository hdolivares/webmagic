-- Migration: Create scrape_sessions table
-- Purpose: Track scraping operations lifecycle and progress
-- Date: 2026-02-15

-- =============================================================================
-- SCRAPE SESSIONS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS scrape_sessions (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id VARCHAR(255) NOT NULL,
    strategy_id UUID REFERENCES geo_strategies(id) ON DELETE SET NULL,
    
    -- Status tracking
    -- Possible values: queued, scraping, validating, completed, failed, cancelled
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    
    -- Progress metrics
    total_businesses INTEGER DEFAULT 0,
    scraped_businesses INTEGER DEFAULT 0,
    validated_businesses INTEGER DEFAULT 0,
    discovered_businesses INTEGER DEFAULT 0,
    
    -- Timestamps
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Error tracking
    error_message TEXT,
    
    -- Metadata (flexible for future expansion)
    metadata JSONB DEFAULT '{}'::jsonb
);

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_scrape_sessions_zone 
    ON scrape_sessions(zone_id);

CREATE INDEX IF NOT EXISTS idx_scrape_sessions_status 
    ON scrape_sessions(status);

CREATE INDEX IF NOT EXISTS idx_scrape_sessions_created 
    ON scrape_sessions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_scrape_sessions_strategy 
    ON scrape_sessions(strategy_id);

-- =============================================================================
-- UPDATE TRIGGER
-- =============================================================================

-- Automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_scrape_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_scrape_sessions_updated_at
    BEFORE UPDATE ON scrape_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_scrape_sessions_updated_at();

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE scrape_sessions IS 
    'Tracks the lifecycle of scraping operations with real-time progress';

COMMENT ON COLUMN scrape_sessions.status IS 
    'Current status: queued, scraping, validating, completed, failed, cancelled';

COMMENT ON COLUMN scrape_sessions.metadata IS 
    'Flexible JSONB field for storing additional scrape-specific data';
