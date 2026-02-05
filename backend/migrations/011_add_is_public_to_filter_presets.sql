-- Migration: Add is_public field to business_filter_presets table
-- Date: 2026-02-05
-- Purpose: Allow filter presets to be shared publicly

-- Add is_public column
ALTER TABLE business_filter_presets 
ADD COLUMN IF NOT EXISTS is_public INTEGER DEFAULT 0 NOT NULL;

-- Create index for efficient querying of public presets
CREATE INDEX IF NOT EXISTS idx_business_filter_presets_is_public 
ON business_filter_presets(is_public);

-- Add comment for documentation
COMMENT ON COLUMN business_filter_presets.is_public IS 'Whether this preset is shared with all users (1) or private (0)';

