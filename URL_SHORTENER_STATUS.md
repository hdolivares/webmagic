# URL Shortener — Status & Integration Guide

> **Date:** 2026-02-17  
> **Status:** Built, pending integration into existing files

---

## What Was Built (New Files)

All new files are self-contained and do not modify any existing code.

| File | Purpose |
|------|---------|
| `backend/models/short_link.py` | `ShortLink` SQLAlchemy model (`short_links` table) |
| `backend/services/shortener/__init__.py` | Module init, exports `ShortLinkService` and `generate_slug` |
| `backend/services/shortener/slug_generator.py` | Base62 slug generation (`a-zA-Z0-9`, default 6 chars) |
| `backend/services/shortener/short_link_service.py` | Core service: create, resolve, deactivate, list, stats |
| `backend/api/redirect.py` | Public `GET /r/{slug}` redirect handler (no auth) |
| `backend/api/v1/shortener.py` | Admin API: CRUD, stats, config (`/api/v1/shortener/*`) |
| `backend/migrations/015_create_short_links.sql` | SQL migration: table + indexes + default settings |
| `frontend/src/pages/Settings/ShortenerSettings.tsx` | Admin UI: shortener config + stats |
| `frontend/src/pages/Settings/ShortenerSettings.css` | Styles (matches existing MessagingSettings pattern) |

---

## Integration Steps (Minimal Changes to Existing Files)

### 1. Run the Database Migration

```bash
psql "$DATABASE_URL" -f backend/migrations/015_create_short_links.sql
```

This creates the `short_links` table and seeds default settings into `system_settings`.

### 2. Register the ShortLink model — `backend/models/__init__.py`

Add the import and export so SQLAlchemy discovers the model:

```python
# After the existing imports, add:
from models.short_link import ShortLink

# In the __all__ list, add:
    "ShortLink",
```

Full diff:

```diff
 from models.scrape_session import ScrapeSession
+from models.short_link import ShortLink
 
 __all__ = [
     ...
     "ScrapeSession",
+    # URL Shortener
+    "ShortLink",
 ]
```

### 3. Register the redirect handler — `backend/api/main.py`

Add the public redirect router **before** the API router (order matters):

```diff
 # Import and include routers
 from api.v1.router import api_router
+from api.redirect import router as redirect_router
 
+app.include_router(redirect_router)  # Public redirect — no prefix
 app.include_router(api_router, prefix=f"/api/{settings.API_VERSION}")
```

This makes `GET /r/{slug}` available at the top level.

### 4. Register the admin API — `backend/api/v1/router.py`

Add the shortener admin routes alongside existing routers:

```diff
 from api.v1 import (
     auth,
     businesses,
     ...
+    shortener,  # URL Shortener admin API
 )
 
 api_router.include_router(shortener.router)  # URL Shortener
```

### 5. Add the settings tab — `frontend/src/pages/Settings/SettingsPage.tsx`

```diff
 import { User, Key, Bot, MessageSquare } from 'lucide-react'
+import { Link2 } from 'lucide-react'
 import { AccountSettings } from './AccountSettings'
 import { AISettingsTab } from './AISettingsTab'
 import { PromptsSettings } from './PromptsSettings'
 import { MessagingSettings } from './MessagingSettings'
+import { ShortenerSettings } from './ShortenerSettings'
 
-type SettingsTab = 'account' | 'ai' | 'prompts' | 'messaging'
+type SettingsTab = 'account' | 'ai' | 'prompts' | 'messaging' | 'shortener'
 
   const tabs = [
     ...existing tabs...
+    {
+      id: 'shortener' as SettingsTab,
+      label: 'URL Shortener',
+      icon: Link2,
+      description: 'Configure short URLs for SMS campaigns',
+    },
   ]
 
   // In the tab content section:
+  {activeTab === 'shortener' && <ShortenerSettings />}
```

### 6. Add the API methods (ALREADY DONE)

The shortener API methods were already added to `frontend/src/services/api.ts` — no further changes needed there.

### 7. Update system settings router (ALREADY DONE)

The `shortener_` prefix was already added to `backend/api/v1/system.py` category detection — no further changes needed.

---

## Integrate Into SMS Campaign Flow (Future Step)

When ready to wire it up, the change is in your campaign service (wherever SMS campaigns are created). Before calling `sms_generator.generate_sms()`:

```python
from services.shortener import ShortLinkService

# Instead of passing the raw site URL directly:
# sms_body = await sms_generator.generate_sms(business_data, site_url=site.full_url)

# Create/reuse a short link first:
short_url = await ShortLinkService.get_or_create_short_link(
    db,
    destination_url=site.full_url,
    link_type="site_preview",
    business_id=business.id,
    site_id=site.id,
    campaign_id=campaign.id,
)
sms_body = await sms_generator.generate_sms(business_data, site_url=short_url)
```

**That's it.** The SMS generator, SMS sender, templates, and compliance footer logic all remain unchanged — they just receive a shorter URL.

### Graceful Fallback

If the shortener is disabled or the domain is not configured, `create_short_link()` and `get_or_create_short_link()` return the **original URL unchanged**. No crash, no exception — the system works exactly as it does today.

---

## Nginx Configuration for the Short Domain

Create a new Nginx server block for your short domain:

```nginx
# /etc/nginx/sites-available/webmagic-shortener
server {
    listen 443 ssl http2;
    server_name wm.gt;  # Replace with your short domain

    ssl_certificate /etc/letsencrypt/live/wm.gt/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wm.gt/privkey.pem;

    # Redirect all requests to the backend /r/ handler
    # This makes https://wm.gt/a1B2c3 → GET /r/a1B2c3 internally
    location / {
        proxy_pass http://127.0.0.1:8000/r/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# HTTP → HTTPS redirect
server {
    listen 80;
    server_name wm.gt;
    return 301 https://$host$request_uri;
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/webmagic-shortener /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL Certificate

```bash
sudo certbot certonly --nginx -d wm.gt
```

---

## How It Works (Architecture)

```
User receives SMS with: https://wm.gt/a1B2c3
                              │
                              ▼
                    Nginx (short domain)
                    proxy_pass → /r/a1B2c3
                              │
                              ▼
                  FastAPI GET /r/{slug}
                  (backend/api/redirect.py)
                              │
                              ▼
                  ShortLinkService.resolve()
                  - Lookup slug in short_links table
                  - Check is_active + not expired
                  - Increment click_count atomically
                  - Return destination_url
                              │
                              ▼
                  302 Redirect → https://sites.lavish.solutions/my-business-123
```

---

## Character Savings

| | Before | After |
|---|--------|-------|
| URL example | `https://sites.lavish.solutions/camarillo-chiropractic-rehab-1771191620461` | `https://wm.gt/a1B2c3` |
| Characters | ~74 | ~21 |
| **Savings** | — | **~53 characters** |
| SMS segments | 2 (typical) | 1 (typical) |
| Cost per SMS | ~$0.016 | ~$0.008 |

---

## Admin API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/r/{slug}` | Public | Redirect (302) to destination |
| `POST` | `/api/v1/shortener/links` | Admin | Create a short link |
| `GET` | `/api/v1/shortener/links` | Admin | List links (paginated) |
| `GET` | `/api/v1/shortener/links/{id}` | Admin | Get link details |
| `DELETE` | `/api/v1/shortener/links/{id}` | Admin | Deactivate link |
| `GET` | `/api/v1/shortener/stats` | Admin | Aggregate statistics |
| `GET` | `/api/v1/shortener/config` | Admin | Current configuration |

---

## Settings (Admin UI → Settings → URL Shortener)

| Setting | Key | Default | Notes |
|---------|-----|---------|-------|
| Short Domain | `shortener_domain` | `""` (empty) | Must be set for shortener to work |
| Protocol | `shortener_protocol` | `https` | Use https in production |
| Slug Length | `shortener_slug_length` | `6` | 6 chars = 56B combinations |
| Default Expiry | `shortener_default_expiry_days` | `0` | 0 = no expiry. Site preview links never expire regardless. |
| Enabled | `shortener_enabled` | `true` | Disable to fall back to original URLs |

---

## Expiration Rules

| Link Type | Expiration |
|-----------|-----------|
| `site_preview` | **Never** — always `expires_at = NULL` |
| `campaign` | Uses `shortener_default_expiry_days` (default: no expiry) |
| `custom` | Creator-specified, or uses default |
| `other` | Uses default |

Expired links return 404 at redirect time. No cleanup cron needed.

---

## Testing Checklist

After completing the integration steps above:

- [ ] Run migration against your database
- [ ] Restart the backend (`uvicorn` / `gunicorn`)
- [ ] Configure the short domain in Settings → URL Shortener
- [ ] Create a test link via `POST /api/v1/shortener/links`
- [ ] Visit the short URL in a browser — verify redirect works
- [ ] Check that click count incremented via `GET /api/v1/shortener/links`
- [ ] Set up Nginx for the short domain
- [ ] Test the short domain URL end-to-end
- [ ] Verify the Settings → URL Shortener tab shows stats
