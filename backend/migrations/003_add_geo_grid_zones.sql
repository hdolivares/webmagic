-- Migration: Add Geo-Grid Zone Support to Coverage Grid
-- This enables subdividing cities into geographic zones for better coverage

ALTER TABLE coverage_grid 
ADD COLUMN zone_id VARCHAR(20),
ADD COLUMN zone_lat VARCHAR(20),
ADD COLUMN zone_lon VARCHAR(20),
ADD COLUMN zone_radius_km VARCHAR(10);

-- Add index for zone_id lookups
CREATE INDEX idx_coverage_grid_zone_id ON coverage_grid(zone_id);

-- Add comment for documentation
COMMENT ON COLUMN coverage_grid.zone_id IS 'Geographic zone identifier (e.g., "2x3" for row 2, col 3)';
COMMENT ON COLUMN coverage_grid.zone_lat IS 'Center latitude of search zone';
COMMENT ON COLUMN coverage_grid.zone_lon IS 'Center longitude of search zone';
COMMENT ON COLUMN coverage_grid.zone_radius_km IS 'Search radius for this zone in kilometers';

