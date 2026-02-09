-- Migration 010: Increase zone_id column length
-- Reason: Metro area zone IDs like "los_angeles_los_angeles" exceed 20 char limit
-- Date: 2026-02-09

-- Increase zone_id from VARCHAR(20) to VARCHAR(50)
ALTER TABLE coverage_grid 
ALTER COLUMN zone_id TYPE VARCHAR(50);

-- No data migration needed - existing values are all under 50 chars
