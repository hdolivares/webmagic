# Subdomain Format Update - Complete ✓

## Problem
- Old subdomain format included long IDs making URLs spammy-looking:
  - Example: `marshall-campbell-co-cpa-s-1771101149157-7ca646d7`
- Short URLs were resolving to these ugly old URLs
- User requested clean format: `business-name + region` (e.g., `bodycare-la`)

## Solution Implemented

### 1. Updated Subdomain Generation Logic
**File**: `backend/tasks/generation_helpers.py`

Created new `build_site_subdomain()` function that:
- Takes business name + city (instead of business ID)
- Sanitizes name: removes special chars, lowercase, hyphens
- Abbreviates major cities (Los Angeles → la, New York → ny, etc.)
- Shortens long names intelligently (max 30 chars for name part)
- Ensures DNS compliance (max 63 chars total)
- Format: `{clean-business-name}-{region}`

**Examples**:
- `Marshall Campbell & Co., CPA's` in `Los Angeles` → `marshall-campbell-co-cpas-la`
- `RR Plumbing Roto-Rooter` in `Bronx` → `rr-plumbing-roto-rooter-bronx`
- `Tom Kim, CPA` in `Los Angeles` → `tom-kim-cpa-la`

### 2. Updated Existing Sites (39 sites)
Used SQL via Nimly MCP for reliable bulk updates:

**Step 1**: Created PostgreSQL function `generate_clean_subdomain()`
```sql
-- Handles business name sanitization, city abbreviation, length limits
```

**Step 2**: Deactivated old short links (39 links)
```sql
UPDATE short_links SET is_active = false 
WHERE link_type = 'site_preview' AND destination_url LIKE 'https://sites.lavish.solutions/%';
```

**Step 3**: Updated all site subdomains (39 sites)
```sql
UPDATE generated_sites gs
SET subdomain = generate_clean_subdomain(b.name, b.city)
FROM businesses b WHERE gs.business_id = b.id;
```

**Step 4**: Created new short links (39 links)
```sql
INSERT INTO short_links (destination_url, slug, link_type, business_id, site_id, ...)
-- Generated new lvsh.cc short URLs pointing to new clean subdomains
```

**Step 5**: Updated sites with short URLs (39 sites)
```sql
UPDATE generated_sites gs
SET short_url = 'https://lvsh.cc/' || sl.slug
FROM short_links sl WHERE sl.site_id = gs.id;
```

### 3. Code Changes Deployed
**Files Modified**:
- `backend/tasks/generation_helpers.py` - New subdomain generation logic
- `backend/tasks/generation.py` - Pass city to subdomain function
- `backend/api/v1/sites.py` - Include short_url in API response (already fixed)
- `frontend/src/pages/Sites/GeneratedSitesPage.tsx` - Display short URLs (already fixed)

**Database Changes**:
- Created `generate_clean_subdomain()` SQL function
- Updated 39 sites with new subdomains
- Deactivated 39 old short links
- Created 39 new short links
- Updated 39 sites with new short_url values

## Results

### Before
- Subdomain: `marshall-campbell-co-cpa-s-1771101149157-7ca646d7`
- Short URL: `https://lvsh.cc/old123` → `https://sites.lavish.solutions/marshall-campbell-co-cpa-s-1771101149157-7ca646d7`

### After
- Subdomain: `marshall-campbell-co-cpas-la` ✓
- Short URL: `https://lvsh.cc/b7322bb` → `https://sites.lavish.solutions/marshall-campbell-co-cpas-la` ✓

## Verification

All 39 sites updated successfully:
```sql
SELECT subdomain, short_url, b.name
FROM generated_sites gs
JOIN businesses b ON gs.business_id = b.id
WHERE gs.status IN ('completed', 'published', 'live');
```

## Services Restarted
- ✓ webmagic-api (restarted)
- ✓ webmagic-celery (restarted)
- ✓ webmagic-celery-beat (running)

## Future Site Generations
All new sites will automatically use the clean subdomain format:
- `{business-name}-{region}` (no IDs!)
- Short URLs created at generation time
- Stored in `generated_sites.short_url`

## Status: ✅ COMPLETE
- All existing sites updated with clean subdomains
- All short URLs regenerated and pointing to new clean URLs
- Frontend displaying new short URLs
- API serving updated data
- Code deployed and services restarted
