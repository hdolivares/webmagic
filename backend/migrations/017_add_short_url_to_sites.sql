-- Migration 017: Add short_url column to generated_sites
-- Stores the lvsh.cc short link directly on the site for fast access

-- Add short_url column (nullable for existing sites)
ALTER TABLE generated_sites
ADD COLUMN short_url VARCHAR(255) NULL;

-- Add index for fast lookups
CREATE INDEX idx_generated_sites_short_url ON generated_sites(short_url);

-- Add comment
COMMENT ON COLUMN generated_sites.short_url IS 
'Pre-generated lvsh.cc short link created at site generation time. Used in all campaigns for this site.';

-- Backfill existing sites with their short links (if they have one)
UPDATE generated_sites gs
SET short_url = (
    SELECT CONCAT('https://lvsh.cc/', sl.slug)
    FROM short_links sl
    WHERE sl.site_id = gs.id
      AND sl.is_active = true
      AND sl.link_type = 'site_preview'
    ORDER BY sl.created_at DESC
    LIMIT 1
)
WHERE gs.short_url IS NULL
  AND EXISTS (
    SELECT 1 FROM short_links sl
    WHERE sl.site_id = gs.id
      AND sl.is_active = true
  );
