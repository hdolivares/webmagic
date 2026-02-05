-- Migration 009: Make html_content nullable during generation
-- This allows creating GeneratedSite records in "generating" status
-- before the actual HTML content is created.

ALTER TABLE generated_sites 
ALTER COLUMN html_content DROP NOT NULL;

-- Add comment explaining the change
COMMENT ON COLUMN generated_sites.html_content IS 'HTML content (nullable during generation status)';

