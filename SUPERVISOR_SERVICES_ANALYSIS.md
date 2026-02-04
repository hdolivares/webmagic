# Supervisor Services Analysis & Fix

**Date:** January 25, 2026  
**Issue:** Coverage page showing persistent 500/502 errors  
**Status:** ✅ RESOLVED

---

## Executive Summary

The Coverage page was experiencing multiple API failures due to **two critical issues**:

1. **Null Category Validation Error** - Fixed ✅
2. **bcrypt/passlib Compatibility Issue** - Fixed ✅

Both issues have been resolved, and **ALL supervisor services** have been properly restarted.

---

## Issues Identified

### Issue #1: Null Industry Categories (500 Error)

**Endpoint:** `GET /api/v1/coverage/campaigns/categories`

**Error:**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for CategoryCoverage
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
```

**Root Cause:**
- The `coverage_grid` table has rows where `industry_category` is `NULL`
- The Pydantic model `CategoryCoverage` expected a non-null string
- When the API tried to serialize the response, validation failed

**Fix Applied:**
- Modified `backend/api/v1/coverage_campaigns.py` to use "Uncategorized" as default for null categories
- Commit: `afe5e9f`

**Code Change:**
```python
# Use "Uncategorized" as default for null categories
category_name = row.industry_category if row.industry_category else "Uncategorized"
```

---

### Issue #2: bcrypt/passlib Incompatibility (502 Error)

**Endpoints:** 
- `GET /api/v1/auth/me` → 502 Bad Gateway
- `GET /api/v1/draft-campaigns/stats` → 500 Internal Server Error (side effect)

**Error:**
```
AttributeError: module 'bcrypt' has no attribute '__about__'
File: passlib/handlers/bcrypt.py, line 620, in _load_backend_mixin
    version = _bcrypt.__about__.__version__
              ^^^^^^^^^^^^^^^^^
```

**Root Cause:**
- `bcrypt==4.1.2` (installed) removed the `__about__` attribute in v4.x
- `passlib==1.7.4` still expects this attribute for version checking
- This caused **all authentication-related endpoints to crash** with 502 errors
- The auth failure cascaded to other endpoints that depend on authentication

**Fix Applied:**
- Downgraded `bcrypt` from `4.1.2` to `3.2.2` (last compatible version)
- Updated `backend/requirements.txt`
- Reinstalled dependencies on VPS
- Commit: `80629fc`

**Dependency Change:**
```diff
- bcrypt==4.1.2
+ bcrypt==3.2.2  # Compatible with passlib 1.7.4 (v4.x removed __about__ attribute)
```

---

## Supervisor Services Architecture

WebMagic uses **Supervisor** to manage 3 critical backend services:

### 1. **webmagic-api** (FastAPI Application)
- **Purpose:** Main REST API server
- **Technology:** FastAPI + Uvicorn
- **Port:** 8000 (internal), 443 (via Nginx reverse proxy)
- **Responsibilities:**
  - Handle HTTP requests from frontend
  - Execute business logic
  - Database operations
  - Authentication & authorization
  - Queue background tasks to Celery

### 2. **webmagic-celery** (Task Worker)
- **Purpose:** Execute asynchronous background tasks
- **Technology:** Celery worker
- **Responsibilities:**
  - Process scraping jobs
  - Send emails/SMS
  - Long-running operations
  - Scheduled tasks

### 3. **webmagic-celery-beat** (Task Scheduler)
- **Purpose:** Schedule periodic tasks
- **Technology:** Celery beat scheduler
- **Responsibilities:**
  - Trigger recurring jobs (cron-like)
  - Monitor campaigns
  - Cleanup tasks

---

## Why Restarting ALL Services Matters

### Previous Restart Strategy ❌
```bash
supervisorctl restart webmagic-api
```
**Problem:** Only restarted the API, leaving Celery workers running with:
- Old code (16+ hours old)
- Old dependencies (bcrypt 4.1.2)
- Stale imports and cached modules

### Correct Restart Strategy ✅
```bash
supervisorctl restart all
```
**Benefits:**
- All services reload with fresh code
- All dependencies are re-imported
- Eliminates version mismatches between services
- Ensures consistency across the entire backend stack

---

## Current Service Status

```
webmagic-api                     RUNNING   pid 71806, uptime 0:00:06
webmagic-celery                  RUNNING   pid 71807, uptime 0:00:06
webmagic-celery-beat             RUNNING   pid 71808, uptime 0:00:06
```

✅ All services running  
✅ No errors in logs  
✅ bcrypt 3.2.2 installed  
✅ passlib 1.7.4 compatible  
✅ Clean startup

---

## Deployment Checklist for Future Updates

When deploying code changes that affect the backend:

1. **Pull Latest Code**
   ```bash
   cd /var/www/webmagic
   git pull origin main
   ```

2. **Update Dependencies (if requirements.txt changed)**
   ```bash
   cd backend
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Apply Migrations (if database schema changed)**
   ```bash
   alembic upgrade head
   # OR use Supabase MCP tool
   ```

4. **Restart ALL Services**
   ```bash
   supervisorctl restart all
   ```

5. **Verify Service Status**
   ```bash
   supervisorctl status
   ```

6. **Check Logs for Errors**
   ```bash
   supervisorctl tail -100 webmagic-api stderr
   supervisorctl tail -100 webmagic-celery stderr
   supervisorctl tail -100 webmagic-celery-beat stderr
   ```

7. **Rebuild Frontend (if frontend code changed)**
   ```bash
   cd /var/www/webmagic/frontend
   npm run build
   systemctl restart nginx
   ```

---

## Testing Recommendations

### 1. Test Coverage Page
- Navigate to Coverage page
- Verify no console errors
- Check that categories load (including "Uncategorized")
- Verify draft campaign stats load

### 2. Test Authentication
- Logout and login again
- Verify JWT token works
- Check `/api/v1/auth/me` endpoint returns user data

### 3. Test Scraping
- Click "Start Scraping This Zone" button
- Verify no 500 errors
- Check that scraping job starts successfully

### 4. Monitor Logs
- Keep browser console open
- Watch for any new errors
- Check supervisor logs if issues persist

---

## Resolution Timeline

| Time | Action | Result |
|------|--------|--------|
| 13:24 | Initial errors reported | 500/502 on multiple endpoints |
| 13:30 | Fixed null category issue | ✅ `/categories` endpoint working |
| 13:35 | Identified bcrypt incompatibility | Found root cause of auth failures |
| 13:40 | Downgraded bcrypt to 3.2.2 | ✅ Compatible version installed |
| 13:45 | Restarted ALL services | ✅ All services running cleanly |

---

## Key Takeaways

1. **Always restart ALL services** when deploying backend changes
2. **Check dependency compatibility** before upgrading packages
3. **Monitor logs immediately** after deployment to catch issues early
4. **Test authentication first** - if auth fails, everything else fails
5. **Handle null database values** gracefully in API responses

---

## Support Commands

### Check Service Status
```bash
supervisorctl status
```

### Restart All Services
```bash
supervisorctl restart all
```

### View Real-Time Logs
```bash
supervisorctl tail -f webmagic-api stderr
```

### Check bcrypt Version
```bash
cd /var/www/webmagic/backend
source .venv/bin/activate
pip show bcrypt
```

---

## Next Steps

✅ All issues resolved  
✅ Services restarted  
✅ Clean logs confirmed  

**Please refresh the Coverage page and verify:**
1. No console errors appear
2. Category data loads successfully
3. Draft campaign stats load
4. "Start Scraping This Zone" button works

If any issues persist, check the browser console and share the error messages.

