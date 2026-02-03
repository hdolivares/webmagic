-- Migration: Fix Coverage Grid Unique Constraint to Support Multiple Zones
-- The old constraint didn't include zone_id, preventing multiple zones per city+industry
-- This migration drops the old constraint and creates a new one that includes zone_id

-- Drop the old unique constraint (country, state, city, industry)
ALTER TABLE coverage_grid 
DROP CONSTRAINT IF EXISTS coverage_grid_country_state_city_industry_key;

-- Create new unique constraint that includes zone_id
-- This allows multiple zones for the same city+industry combination
ALTER TABLE coverage_grid 
ADD CONSTRAINT coverage_grid_country_state_city_industry_zone_key 
UNIQUE (country, state, city, industry, zone_id);

-- Add comment for documentation
COMMENT ON CONSTRAINT coverage_grid_country_state_city_industry_zone_key ON coverage_grid 
IS 'Ensures unique combination of location, industry, and zone. Allows multiple zones per city+industry.';

