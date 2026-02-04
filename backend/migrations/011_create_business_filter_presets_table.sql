-- Migration 011: Create business_filter_presets table for saved filter combinations
-- Date: 2026-02-04
-- Description: Allows users to save and reuse complex filter combinations

CREATE TABLE IF NOT EXISTS business_filter_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
    
    -- Preset details
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Filter criteria (stored as JSON)
    filters JSONB NOT NULL,
    -- Example structure:
    -- {
    --   "website_status": ["none", "invalid"],
    --   "has_website": false,
    --   "min_rating": 4.0,
    --   "location": {"state": "CA", "city": "Los Angeles"},
    --   "categories": ["plumbers", "electricians"],
    --   "min_review_count": 10,
    --   "scraped_after": "2026-01-01"
    -- }
    
    -- Usage tracking
    last_used_at TIMESTAMP,
    use_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT business_filter_presets_user_name_unique 
        UNIQUE(user_id, name)
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_business_filter_presets_user_id 
    ON business_filter_presets(user_id);

CREATE INDEX IF NOT EXISTS idx_business_filter_presets_last_used 
    ON business_filter_presets(last_used_at DESC);

CREATE INDEX IF NOT EXISTS idx_business_filter_presets_use_count 
    ON business_filter_presets(use_count DESC);

-- Create a GIN index on the filters JSONB for efficient filtering
CREATE INDEX IF NOT EXISTS idx_business_filter_presets_filters 
    ON business_filter_presets USING GIN (filters);

-- Add comments for documentation
COMMENT ON TABLE business_filter_presets IS 'User-defined filter presets for business queries';
COMMENT ON COLUMN business_filter_presets.filters IS 'JSON object containing filter criteria';
COMMENT ON COLUMN business_filter_presets.use_count IS 'Number of times this preset has been used';

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_business_filter_presets_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_business_filter_presets_updated_at
    BEFORE UPDATE ON business_filter_presets
    FOR EACH ROW
    EXECUTE FUNCTION update_business_filter_presets_updated_at();

-- Log completion
DO $$ 
BEGIN 
    RAISE NOTICE 'Migration 011 completed: Created business_filter_presets table';
END $$;

