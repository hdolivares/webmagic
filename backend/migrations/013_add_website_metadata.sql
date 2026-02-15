-- Migration 013: Add website_metadata field for enhanced validation tracking
-- This migration adds comprehensive validation history and discovery tracking

-- Add website_metadata JSONB field
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS website_metadata JSONB DEFAULT '{}'::jsonb;

-- Create index on metadata for faster queries
CREATE INDEX IF NOT EXISTS idx_businesses_website_metadata 
ON businesses USING GIN (website_metadata);

-- Create index on validation status for filtering
CREATE INDEX IF NOT EXISTS idx_businesses_validation_status 
ON businesses (website_validation_status) 
WHERE website_validation_status IS NOT NULL;

-- Backfill existing businesses with initial metadata
UPDATE businesses
SET website_metadata = jsonb_build_object(
    'source', CASE 
        WHEN website_url IS NOT NULL THEN 'outscraper'
        ELSE 'none'
    END,
    'source_timestamp', COALESCE(website_validated_at, created_at)::text,
    'validation_history', '[]'::jsonb,
    'discovery_attempts', '{}'::jsonb
)
WHERE website_metadata = '{}'::jsonb OR website_metadata IS NULL;

-- Add comment for documentation
COMMENT ON COLUMN businesses.website_metadata IS 
'JSONB field storing validation history, discovery attempts, and URL source tracking. 
Structure: {source, source_timestamp, validation_history[], discovery_attempts{}}';

-- Verify migration
DO $$ 
BEGIN 
    RAISE NOTICE 'Migration 013 completed: website_metadata field added';
    RAISE NOTICE 'Backfilled % businesses', (SELECT COUNT(*) FROM businesses WHERE website_metadata IS NOT NULL);
END $$;
