-- Migration: Add website validation fields to businesses table
-- Date: 2026-02-05
-- Purpose: Support Playwright-based website validation

-- Add validation status field
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS website_validation_status VARCHAR(30) DEFAULT 'pending';

-- Add validation result (stores full validation data)
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS website_validation_result JSONB;

-- Add validation timestamp
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS website_validated_at TIMESTAMP;

-- Add screenshot URL (optional - for S3 storage)
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS website_screenshot_url TEXT;

-- Create index for efficient querying by validation status
CREATE INDEX IF NOT EXISTS idx_businesses_validation_status 
ON businesses(website_validation_status);

-- Create index for finding recently validated businesses
CREATE INDEX IF NOT EXISTS idx_businesses_validated_at 
ON businesses(website_validated_at DESC);

-- Update existing businesses to have 'pending' status if they have a website
UPDATE businesses 
SET website_validation_status = 'pending'
WHERE website_url IS NOT NULL 
  AND website_validation_status IS NULL;

-- Update businesses without websites to 'no_website'
UPDATE businesses 
SET website_validation_status = 'no_website'
WHERE website_url IS NULL 
  AND website_validation_status IS NULL;

-- Add comment for documentation
COMMENT ON COLUMN businesses.website_validation_status IS 'Website validation status: pending, valid, invalid, no_website, error';
COMMENT ON COLUMN businesses.website_validation_result IS 'Full validation result from Playwright including quality score, contact info, etc.';
COMMENT ON COLUMN businesses.website_validated_at IS 'Timestamp of last validation attempt';
COMMENT ON COLUMN businesses.website_screenshot_url IS 'URL to website screenshot (if captured)';

