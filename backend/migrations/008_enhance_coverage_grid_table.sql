-- Migration 008: Enhance coverage_grid table for detailed scraping metrics
-- Date: 2026-02-04
-- Description: Adds detailed metrics for website counts, validation, and generation tracking

-- Add detailed scrape metrics
ALTER TABLE coverage_grid ADD COLUMN IF NOT EXISTS businesses_with_websites INTEGER DEFAULT 0;
COMMENT ON COLUMN coverage_grid.businesses_with_websites IS 'Count of businesses that have existing websites';

ALTER TABLE coverage_grid ADD COLUMN IF NOT EXISTS businesses_without_websites INTEGER DEFAULT 0;
COMMENT ON COLUMN coverage_grid.businesses_without_websites IS 'Count of businesses without websites';

ALTER TABLE coverage_grid ADD COLUMN IF NOT EXISTS invalid_websites INTEGER DEFAULT 0;
COMMENT ON COLUMN coverage_grid.invalid_websites IS 'Count of businesses with invalid/broken website URLs';

ALTER TABLE coverage_grid ADD COLUMN IF NOT EXISTS websites_generated INTEGER DEFAULT 0;
COMMENT ON COLUMN coverage_grid.websites_generated IS 'Count of websites generated for this zone';

ALTER TABLE coverage_grid ADD COLUMN IF NOT EXISTS generation_in_progress INTEGER DEFAULT 0;
COMMENT ON COLUMN coverage_grid.generation_in_progress IS 'Count of websites currently being generated';

ALTER TABLE coverage_grid ADD COLUMN IF NOT EXISTS generation_failed INTEGER DEFAULT 0;
COMMENT ON COLUMN coverage_grid.generation_failed IS 'Count of failed website generation attempts';

-- Add validation metrics
ALTER TABLE coverage_grid ADD COLUMN IF NOT EXISTS validation_completed_count INTEGER DEFAULT 0;
COMMENT ON COLUMN coverage_grid.validation_completed_count IS 'Count of businesses that have completed validation';

ALTER TABLE coverage_grid ADD COLUMN IF NOT EXISTS validation_pending_count INTEGER DEFAULT 0;
COMMENT ON COLUMN coverage_grid.validation_pending_count IS 'Count of businesses pending validation';

-- Add zone performance metrics
ALTER TABLE coverage_grid ADD COLUMN IF NOT EXISTS avg_qualification_score NUMERIC(5,2);
COMMENT ON COLUMN coverage_grid.avg_qualification_score IS 'Average qualification score for businesses in this zone';

ALTER TABLE coverage_grid ADD COLUMN IF NOT EXISTS avg_rating NUMERIC(2,1);
COMMENT ON COLUMN coverage_grid.avg_rating IS 'Average business rating for this zone';

-- Add last scrape details (persistent JSON storage)
ALTER TABLE coverage_grid ADD COLUMN IF NOT EXISTS last_scrape_details JSONB;
COMMENT ON COLUMN coverage_grid.last_scrape_details IS 'Detailed breakdown of last scrape: raw_businesses, qualified_leads, new_businesses, etc.';

-- Create indexes for efficient reporting queries
CREATE INDEX IF NOT EXISTS idx_coverage_grid_websites_generated 
  ON coverage_grid(websites_generated) 
  WHERE websites_generated > 0;

CREATE INDEX IF NOT EXISTS idx_coverage_grid_generation_pending 
  ON coverage_grid(businesses_without_websites) 
  WHERE businesses_without_websites > websites_generated;

CREATE INDEX IF NOT EXISTS idx_coverage_grid_zone_performance 
  ON coverage_grid(zone_id, status, last_scraped_at);

-- Initialize last_scrape_details for existing records
UPDATE coverage_grid 
SET last_scrape_details = jsonb_build_object(
    'raw_businesses', COALESCE(last_scrape_size, 0),
    'qualified_leads', COALESCE(qualified_count, 0),
    'timestamp', COALESCE(last_scraped_at, NOW())
)
WHERE last_scrape_details IS NULL AND last_scraped_at IS NOT NULL;

-- Log completion
DO $$ 
BEGIN 
    RAISE NOTICE 'Migration 008 completed: Enhanced coverage_grid table with detailed metrics';
END $$;

