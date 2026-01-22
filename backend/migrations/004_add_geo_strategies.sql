-- Migration 004: Add Geo-Strategies Table
-- Creates table for storing Claude-generated intelligent zone placement strategies

CREATE TABLE IF NOT EXISTS geo_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Location identification
    city VARCHAR(100) NOT NULL,
    state VARCHAR(10) NOT NULL,
    country VARCHAR(10) NOT NULL DEFAULT 'US',
    category VARCHAR(100) NOT NULL,
    
    -- Geographic metadata
    city_center_lat DOUBLE PRECISION NOT NULL,
    city_center_lon DOUBLE PRECISION NOT NULL,
    population INTEGER,
    
    -- Claude's analysis (stored as TEXT for readability)
    geographic_analysis TEXT,
    business_distribution_analysis TEXT,
    strategy_reasoning TEXT,
    
    -- Strategic zones (JSONB for efficient querying)
    zones JSONB NOT NULL,
    avoid_areas JSONB,
    
    -- Performance estimates
    total_zones INTEGER NOT NULL,
    estimated_total_businesses INTEGER,
    estimated_searches_needed INTEGER,
    coverage_area_km2 DOUBLE PRECISION,
    
    -- Execution tracking
    zones_completed INTEGER NOT NULL DEFAULT 0,
    businesses_found INTEGER NOT NULL DEFAULT 0,
    last_scrape_at TIMESTAMP,
    
    -- Adaptive learning
    performance_data JSONB,
    adaptation_notes TEXT,
    
    -- Strategy metadata
    model_used VARCHAR(50) NOT NULL DEFAULT 'claude-sonnet-4-5',
    strategy_version INTEGER NOT NULL DEFAULT 1,
    is_active VARCHAR(20) NOT NULL DEFAULT 'active',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX idx_geo_strategy_location ON geo_strategies(city, state, country);
CREATE INDEX idx_geo_strategy_category ON geo_strategies(category);
CREATE INDEX idx_geo_strategy_active ON geo_strategies(is_active);
CREATE INDEX idx_geo_strategy_lookup ON geo_strategies(city, state, category, is_active);

-- Index on JSONB zones for zone-level queries
CREATE INDEX idx_geo_strategy_zones ON geo_strategies USING GIN (zones);

-- Comments for documentation
COMMENT ON TABLE geo_strategies IS 'AI-generated geographic strategies for optimal business discovery';
COMMENT ON COLUMN geo_strategies.zones IS 'Array of strategic zones with lat/lon, radius, priority, and reasoning';
COMMENT ON COLUMN geo_strategies.performance_data IS 'Tracks actual vs estimated results for adaptive learning';
COMMENT ON COLUMN geo_strategies.is_active IS 'Status: active, completed, or superseded';

