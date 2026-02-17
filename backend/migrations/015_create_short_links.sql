-- Migration: Create short_links table for URL shortener
-- Date: 2026-02-17
-- Description: Stores short URL mappings with click tracking and optional expiration.
--              Used primarily for SMS campaigns to keep messages within 160 characters.

-- Create short_links table
CREATE TABLE IF NOT EXISTS short_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- The short slug (e.g., "a1B2c3") — unique, indexed for fast lookups
  slug VARCHAR(20) NOT NULL UNIQUE,

  -- Full destination URL
  destination_url TEXT NOT NULL,

  -- Link type for filtering and expiration logic
  -- Values: "site_preview" (never expires), "campaign", "custom", "other"
  link_type VARCHAR(30) NOT NULL DEFAULT 'other',

  -- Soft-disable without deleting
  is_active BOOLEAN NOT NULL DEFAULT TRUE,

  -- Expiration — NULL means never expires
  expires_at TIMESTAMP WITH TIME ZONE,

  -- Click tracking
  click_count INTEGER NOT NULL DEFAULT 0,
  last_clicked_at TIMESTAMP WITH TIME ZONE,

  -- Optional relations for context
  business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,
  site_id UUID REFERENCES generated_sites(id) ON DELETE SET NULL,
  campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,

  -- Flexible metadata (UTM params, source channel, etc.)
  metadata JSONB,

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Primary lookup index (hot path: every redirect does a slug lookup)
CREATE UNIQUE INDEX IF NOT EXISTS idx_short_links_slug ON short_links(slug);

-- Filtering indexes
CREATE INDEX IF NOT EXISTS idx_short_links_link_type ON short_links(link_type);
CREATE INDEX IF NOT EXISTS idx_short_links_is_active ON short_links(is_active);
CREATE INDEX IF NOT EXISTS idx_short_links_business ON short_links(business_id);
CREATE INDEX IF NOT EXISTS idx_short_links_site ON short_links(site_id);
CREATE INDEX IF NOT EXISTS idx_short_links_campaign ON short_links(campaign_id);
CREATE INDEX IF NOT EXISTS idx_short_links_created ON short_links(created_at DESC);

-- Deduplication index: find existing link for a destination URL + type
CREATE INDEX IF NOT EXISTS idx_short_links_dest_type
  ON short_links(destination_url, link_type)
  WHERE is_active = TRUE;

-- Trigger for updated_at (reuses existing function from other migrations)
CREATE TRIGGER update_short_links_updated_at
  BEFORE UPDATE ON short_links
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE short_links IS 'URL shortener: maps short slugs to destination URLs with click tracking';
COMMENT ON COLUMN short_links.slug IS 'Base62 short code (e.g., a1B2c3), unique identifier in the short URL';
COMMENT ON COLUMN short_links.link_type IS 'site_preview = never expires; campaign, custom, other = may expire';
COMMENT ON COLUMN short_links.expires_at IS 'NULL means link never expires; site_preview links are always NULL';
COMMENT ON COLUMN short_links.click_count IS 'Incremented atomically on every successful redirect';

-- Seed default shortener settings into system_settings
-- These can be changed from the admin UI at Settings > URL Shortener
INSERT INTO system_settings (id, key, value, value_type, category, label, description, is_secret, is_required, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'shortener_domain', '', 'string', 'shortener', 'Short Domain', 'The domain used for short URLs (e.g., wm.gt). Leave empty to disable shortener.', false, false, NOW(), NOW()),
  (gen_random_uuid(), 'shortener_protocol', 'https', 'string', 'shortener', 'URL Protocol', 'Protocol for short URLs (https recommended).', false, false, NOW(), NOW()),
  (gen_random_uuid(), 'shortener_slug_length', '6', 'int', 'shortener', 'Slug Length', 'Number of characters in generated slugs. 6 = 56B combinations.', false, false, NOW(), NOW()),
  (gen_random_uuid(), 'shortener_default_expiry_days', '0', 'int', 'shortener', 'Default Expiry (days)', 'Default expiration for non-site links. 0 = no expiry.', false, false, NOW(), NOW()),
  (gen_random_uuid(), 'shortener_enabled', 'true', 'bool', 'shortener', 'Enable Shortener', 'Enable or disable the URL shortener globally. When disabled, original URLs are used.', false, false, NOW(), NOW())
ON CONFLICT (key) DO NOTHING;
