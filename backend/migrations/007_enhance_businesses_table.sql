-- Migration 007: Enhance businesses table for website validation and generation tracking
-- Date: 2026-02-04
-- Description: Adds columns for website validation status, generation queue tracking,
--              and discovered URLs from web results

-- Add website validation columns
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS website_validation_status VARCHAR(30) DEFAULT 'pending';
COMMENT ON COLUMN businesses.website_validation_status IS 'Validation status: pending, valid, invalid, missing, timeout';

ALTER TABLE businesses ADD COLUMN IF NOT EXISTS website_validation_result JSONB;
COMMENT ON COLUMN businesses.website_validation_result IS 'Full ValidationResult from WebsiteValidationService';

ALTER TABLE businesses ADD COLUMN IF NOT EXISTS website_validated_at TIMESTAMP;
COMMENT ON COLUMN businesses.website_validated_at IS 'Timestamp of last validation';

ALTER TABLE businesses ADD COLUMN IF NOT EXISTS discovered_urls JSONB DEFAULT '[]'::jsonb;
COMMENT ON COLUMN businesses.discovered_urls IS 'URLs found in Google web results that were not in the site field';

-- Add generation queue tracking columns
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS generation_queued_at TIMESTAMP;
COMMENT ON COLUMN businesses.generation_queued_at IS 'When business was queued for website generation';

ALTER TABLE businesses ADD COLUMN IF NOT EXISTS generation_started_at TIMESTAMP;
COMMENT ON COLUMN businesses.generation_started_at IS 'When website generation started';

ALTER TABLE businesses ADD COLUMN IF NOT EXISTS generation_completed_at TIMESTAMP;
COMMENT ON COLUMN businesses.generation_completed_at IS 'When website generation completed';

ALTER TABLE businesses ADD COLUMN IF NOT EXISTS generation_attempts INTEGER DEFAULT 0;
COMMENT ON COLUMN businesses.generation_attempts IS 'Number of generation attempts for this business';

-- Create indexes for efficient filtering and querying
CREATE INDEX IF NOT EXISTS idx_businesses_website_validation_status 
  ON businesses(website_validation_status);

CREATE INDEX IF NOT EXISTS idx_businesses_generation_queued 
  ON businesses(generation_queued_at) 
  WHERE website_status IN ('none', 'queued');

CREATE INDEX IF NOT EXISTS idx_businesses_website_status_category 
  ON businesses(website_status, category);

CREATE INDEX IF NOT EXISTS idx_businesses_state_city_category 
  ON businesses(state, city, category);

-- Update existing records to have pending validation status
UPDATE businesses 
SET website_validation_status = 'pending' 
WHERE website_validation_status IS NULL;

-- Log completion
DO $$ 
BEGIN 
    RAISE NOTICE 'Migration 007 completed: Enhanced businesses table with validation and generation tracking';
END $$;

