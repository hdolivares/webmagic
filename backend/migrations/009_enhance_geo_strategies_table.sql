-- Migration 009: Enhance geo_strategies table for strategy-level aggregations
-- Date: 2026-02-04
-- Description: Adds aggregated metrics across all zones in a strategy

-- Add strategy-wide metrics
ALTER TABLE geo_strategies ADD COLUMN IF NOT EXISTS total_businesses_scraped INTEGER DEFAULT 0;
COMMENT ON COLUMN geo_strategies.total_businesses_scraped IS 'Total businesses scraped across all zones';

ALTER TABLE geo_strategies ADD COLUMN IF NOT EXISTS total_with_websites INTEGER DEFAULT 0;
COMMENT ON COLUMN geo_strategies.total_with_websites IS 'Total businesses with existing websites';

ALTER TABLE geo_strategies ADD COLUMN IF NOT EXISTS total_without_websites INTEGER DEFAULT 0;
COMMENT ON COLUMN geo_strategies.total_without_websites IS 'Total businesses without websites';

ALTER TABLE geo_strategies ADD COLUMN IF NOT EXISTS total_websites_generated INTEGER DEFAULT 0;
COMMENT ON COLUMN geo_strategies.total_websites_generated IS 'Total websites generated for this strategy';

ALTER TABLE geo_strategies ADD COLUMN IF NOT EXISTS avg_businesses_per_zone NUMERIC(6,2);
COMMENT ON COLUMN geo_strategies.avg_businesses_per_zone IS 'Average number of businesses per zone';

ALTER TABLE geo_strategies ADD COLUMN IF NOT EXISTS completion_rate NUMERIC(5,2);
COMMENT ON COLUMN geo_strategies.completion_rate IS 'Percentage of zones completed (0-100)';

-- Create indexes for strategy reporting
CREATE INDEX IF NOT EXISTS idx_geo_strategies_status_completion 
  ON geo_strategies(status, completion_rate);

CREATE INDEX IF NOT EXISTS idx_geo_strategies_city_state_category 
  ON geo_strategies(city, state, category, status);

-- Note: The zones JSONB field structure is already defined, but we'll enhance it
-- programmatically in the service layer to include:
-- - businesses_found (already exists)
-- - qualified_leads (already exists)  
-- - websites_generated (NEW - to be added by service)
-- - scraped_at (already exists)

-- Log completion
DO $$ 
BEGIN 
    RAISE NOTICE 'Migration 009 completed: Enhanced geo_strategies table with aggregated metrics';
END $$;

