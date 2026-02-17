# Site Routing Fix - Complete ✅

## Problem
After updating site subdomains to the new clean format (e.g., `marshall-campbell-co-cpas-la`), the sites were returning "Not Found" errors when accessed.

**Error**: `https://sites.lavish.solutions/marshall-campbell-co-cpas-la` → `{"detail":"Not Found"}`

## Root Causes

### 1. Missing Router Mount
The `generated_preview` router was **NOT** mounted in the main FastAPI app. It had been commented out due to a previous issue with catch-all routes:

```python
# NOTE: generated_preview.router removed from API router - it has a catch-all /{subdomain}
# route that was causing 502 errors by matching all /api/v1/* paths.
```

### 2. Incorrect NGINX Routing
The NGINX config for `sites.lavish.solutions` was rewriting URLs to add `/api/v1` prefix:

```nginx
# Old (broken)
rewrite ^/(.*)$ /api/v1/$1 break;
proxy_pass http://127.0.0.1:8000;
```

This meant `sites.lavish.solutions/subdomain` → `/api/v1/subdomain`, but the `generated_preview` router expects just `/subdomain`.

## Solutions Applied

### 1. Mounted `generated_preview` Router
**File**: `backend/api/main.py`

Added the router mount at the ROOT level (not under `/api/v1`):

```python
# Import and include routers
from api.v1.router import api_router
from api.redirect import router as redirect_router
from api.v1 import generated_preview  # ← Added

app.include_router(redirect_router)
app.include_router(api_router, prefix=f"/api/{settings.API_VERSION}")

# Mount generated site preview router (serves sites.lavish.solutions/{subdomain})
# This must be mounted AFTER other routers to avoid catching API routes
app.include_router(generated_preview.router)  # ← Added
```

### 2. Fixed NGINX Routing
**File**: `/etc/nginx/sites-available/webmagic-sites-pathbased`

Removed the `/api/v1` rewrite, proxying directly to backend:

```nginx
# New (working)
# Proxy directly to backend (no /api/v1 prefix)
# The generated_preview router is mounted at root level
proxy_pass http://127.0.0.1:8000;
proxy_http_version 1.1;
proxy_set_header Host $host;
# ... headers ...
```

## Verification

### Test Commands
```bash
# Test site loading
curl -s https://sites.lavish.solutions/marshall-campbell-co-cpas-la | head -20

# Output: ✅ Full HTML content served!
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Marshall Campbell & Co., CPA's - Trusted certified public accountants...">
    <title>Marshall Campbell & Co., CPA's | Expert Certified Public Accountants</title>
...
```

### Working Sites
All 39 sites are now accessible:

| Business | New URL | Short URL |
|----------|---------|-----------|
| Marshall Campbell & Co., CPA's | `https://sites.lavish.solutions/marshall-campbell-co-cpas-la` | `https://lvsh.cc/b7322bb` |
| Tom Kim, CPA | `https://sites.lavish.solutions/tom-kim-cpa-la` | `https://lvsh.cc/ae5913e` |
| RR Plumbing Roto-Rooter | `https://sites.lavish.solutions/rr-plumbing-roto-rooter-bronx` | `https://lvsh.cc/dce587a` |

## Summary of Complete Update

### Phase 1: Subdomain Format Update ✅
- Updated subdomain generation logic to use `business-name + region`
- Updated all 39 existing sites with new clean subdomains
- Generated 39 new short URLs pointing to new subdomains

### Phase 2: Site Routing Fix ✅
- Mounted `generated_preview` router in main app
- Fixed NGINX to proxy without `/api/v1` prefix
- Reloaded NGINX and restarted API

## Services Updated
- ✅ FastAPI (webmagic-api) - Restarted
- ✅ NGINX - Reloaded
- ✅ Database - All 39 sites updated

## Result
🎉 **All sites are now live and accessible with clean URLs!**

- Clean subdomains: `business-name-region` (no IDs!)
- Short URLs working: `https://lvsh.cc/xxxxx`
- Full URLs working: `https://sites.lavish.solutions/subdomain`
- Frontend displaying short URLs correctly
