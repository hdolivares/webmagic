-- Migration: Add data quality and enhanced website detection fields
-- Date: 2026-02-05
-- Purpose: Support comprehensive Outscraper data analysis and quality scoring

-- Add quality score field (0-100 scale)
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS quality_score FLOAT;

-- Add website type field (website, booking, ordering, none)
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS website_type VARCHAR(20) DEFAULT 'none';

-- Add website detection confidence (0.0-1.0)
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS website_confidence FLOAT;

-- Add verified business flag (from Google Business Profile)
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS verified BOOLEAN DEFAULT FALSE;

-- Add operational status flag (from business_status field)
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS operational BOOLEAN DEFAULT TRUE;

-- Add business status from Outscraper
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS business_status VARCHAR(30);

-- Add photos count (engagement indicator)
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS photos_count INTEGER DEFAULT 0;

-- Add subtypes (additional services)
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS subtypes TEXT;

-- Create indexes for efficient querying

-- Index for quality-based filtering
CREATE INDEX IF NOT EXISTS idx_businesses_quality_score 
ON businesses(quality_score DESC) 
WHERE quality_score IS NOT NULL;

-- Index for verified businesses
CREATE INDEX IF NOT EXISTS idx_businesses_verified 
ON businesses(verified) 
WHERE verified = TRUE;

-- Index for operational businesses
CREATE INDEX IF NOT EXISTS idx_businesses_operational 
ON businesses(operational) 
WHERE operational = TRUE;

-- Index for website type filtering
CREATE INDEX IF NOT EXISTS idx_businesses_website_type 
ON businesses(website_type);

-- Composite index for generation candidates
CREATE INDEX IF NOT EXISTS idx_businesses_generation_candidates 
ON businesses(website_type, operational, quality_score DESC) 
WHERE website_type = 'none' AND operational = TRUE;

-- Update existing businesses with default values
UPDATE businesses 
SET 
    website_type = CASE 
        WHEN website_url IS NOT NULL THEN 'website'
        ELSE 'none'
    END,
    website_confidence = CASE 
        WHEN website_url IS NOT NULL THEN 1.0
        ELSE NULL
    END,
    operational = TRUE,  -- Assume existing businesses are operational
    verified = FALSE     -- Will be updated on next scrape
WHERE website_type IS NULL;

-- Add comments for documentation
COMMENT ON COLUMN businesses.quality_score IS 'Business quality score (0-100) based on verification, reviews, engagement, data completeness';
COMMENT ON COLUMN businesses.website_type IS 'Type of online presence: website, booking, ordering, none';
COMMENT ON COLUMN businesses.website_confidence IS 'Confidence level of website detection (0.0-1.0)';
COMMENT ON COLUMN businesses.verified IS 'Verified Google Business Profile (from Outscraper)';
COMMENT ON COLUMN businesses.operational IS 'Business operational status (from business_status field)';
COMMENT ON COLUMN businesses.business_status IS 'Raw business status from Outscraper (OPERATIONAL, CLOSED_TEMPORARILY, etc)';
COMMENT ON COLUMN businesses.photos_count IS 'Number of photos on Google Business Profile';
COMMENT ON COLUMN businesses.subtypes IS 'Additional business categories/services from Outscraper';

-- Create view for high-quality generation candidates
CREATE OR REPLACE VIEW v_generation_candidates AS
SELECT 
    b.*,
    CASE 
        WHEN quality_score >= 70 THEN 'high'
        WHEN quality_score >= 50 THEN 'medium'
        ELSE 'low'
    END as priority
FROM businesses b
WHERE 
    b.website_type = 'none'
    AND b.operational = TRUE
    AND b.country = 'US'
    AND (b.quality_score >= 50 OR b.quality_score IS NULL)
ORDER BY 
    b.quality_score DESC NULLS LAST,
    b.rating DESC NULLS LAST,
    b.review_count DESC;

COMMENT ON VIEW v_generation_candidates IS 'High-quality businesses without websites, prioritized for generation';

