-- Migration 016: Fix Short Links Uniqueness
-- Prevents duplicate short links for same destination
-- Adds unique constraint to ensure one link per (destination + type + active status)

-- Step 1: Clean up existing duplicates (keep oldest, deactivate newer ones)
WITH ranked_links AS (
    SELECT 
        id,
        destination_url,
        link_type,
        ROW_NUMBER() OVER (
            PARTITION BY destination_url, link_type, is_active
            ORDER BY created_at ASC  -- Keep oldest
        ) as rn
    FROM short_links
    WHERE is_active = true
)
UPDATE short_links
SET is_active = false, updated_at = NOW()
WHERE id IN (
    SELECT id FROM ranked_links WHERE rn > 1
);

-- Step 2: Add unique constraint to prevent future duplicates
-- Note: This allows multiple inactive links for same destination (for history)
CREATE UNIQUE INDEX idx_short_links_unique_active_destination
ON short_links (destination_url, link_type)
WHERE is_active = true;

-- Step 3: Add helpful comment
COMMENT ON INDEX idx_short_links_unique_active_destination IS 
'Ensures only one active short link per destination+type combination. Multiple inactive links allowed for history.';
