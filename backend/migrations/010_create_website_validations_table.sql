-- Migration 010: Create website_validations table for validation audit trail
-- Date: 2026-02-04
-- Description: Stores audit trail of all website validation attempts with detailed results

CREATE TABLE IF NOT EXISTS website_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    
    -- Validation input
    url_tested VARCHAR(500),
    
    -- Validation results
    status VARCHAR(30) NOT NULL,
    -- Values: 'valid', 'invalid', 'missing', 'timeout', 'needs_generation'
    
    url_type VARCHAR(30),
    -- Values: 'html', 'pdf', 'image', 'redirect', 'archive', 'invalid', 'other'
    
    accessibility VARCHAR(30),
    -- Values: 'accessible', 'inaccessible', 'timeout', 'not_checked'
    
    http_status_code INTEGER,
    response_time_ms INTEGER,
    
    -- Issues found
    issues JSONB DEFAULT '[]'::jsonb,
    -- Example: ["redirects_to_pdf", "certificate_error", "timeout", "404_not_found"]
    
    -- Web results discovered
    web_results_urls JSONB DEFAULT '[]'::jsonb,
    -- URLs found in Google web results section
    
    recommended_url VARCHAR(500),
    -- Best URL to use (may differ from url_tested if web results found better one)
    
    recommendation VARCHAR(30),
    -- Values: 'keep', 'replace', 'generate'
    
    -- Metadata
    validation_method VARCHAR(50),
    -- Values: 'http_head', 'http_get', 'external_api', 'cached'
    
    validator_version VARCHAR(20) DEFAULT '1.0',
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT website_validations_business_id_fkey 
        FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_website_validations_business_id 
    ON website_validations(business_id);

CREATE INDEX IF NOT EXISTS idx_website_validations_status 
    ON website_validations(status);

CREATE INDEX IF NOT EXISTS idx_website_validations_created_at 
    ON website_validations(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_website_validations_recommendation 
    ON website_validations(recommendation);

-- Add comments for documentation
COMMENT ON TABLE website_validations IS 'Audit trail of website URL validation attempts';
COMMENT ON COLUMN website_validations.status IS 'Overall validation status';
COMMENT ON COLUMN website_validations.issues IS 'Array of issues detected during validation';
COMMENT ON COLUMN website_validations.web_results_urls IS 'Alternative URLs discovered from Google web results';
COMMENT ON COLUMN website_validations.recommendation IS 'Action recommendation based on validation';

-- Log completion
DO $$ 
BEGIN 
    RAISE NOTICE 'Migration 010 completed: Created website_validations table';
END $$;

