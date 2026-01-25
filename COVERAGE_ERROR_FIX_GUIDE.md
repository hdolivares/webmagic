# Coverage Page Error Fix Guide

## Date: January 25, 2026

## Quick Summary

The Coverage Page is experiencing 500 Internal Server Errors on multiple endpoints:
- `/api/v1/coverage/campaigns/categories`
- `/api/v1/draft-campaigns/stats`
- `/api/v1/intelligent-campaigns/scrape-zone`

**Most Likely Cause:** Missing database tables (`geo_strategies` and/or `draft_campaigns`)

---

## Step-by-Step Fix Instructions

### Step 1: SSH into VPS

```bash
ssh root@104.251.211.183
# Enter password when prompted
```

### Step 2: Run Diagnostic Script

```bash
cd /root/webmagic/backend
python3 scripts/diagnose_coverage_errors.py
```

This will check:
- ✅ Database connection
- ✅ Required tables exist
- ✅ Data integrity
- ✅ Query functionality
- ✅ Service initialization

### Step 3: Review Diagnostic Results

The script will tell you exactly what's wrong. Common issues:

#### Issue A: Missing Tables

**Symptoms:**
```
❌ geo_strategies - MISSING!
❌ draft_campaigns - MISSING!
```

**Fix:**
```bash
cd /root/webmagic/backend/migrations

# Apply missing migrations
psql $DATABASE_URL -f 004_add_geo_strategies.sql
psql $DATABASE_URL -f 005_add_draft_campaigns.sql
```

**Verify:**
```bash
psql $DATABASE_URL -c "\dt geo_strategies"
psql $DATABASE_URL -c "\dt draft_campaigns"
```

#### Issue B: Database Connection Failed

**Symptoms:**
```
❌ Database connection failed: connection refused
```

**Fix:**
```bash
# Check DATABASE_URL in .env
cd /root/webmagic/backend
cat .env | grep DATABASE_URL

# Test connection manually
psql $DATABASE_URL -c "SELECT 1"
```

If connection fails, check:
1. Supabase project is active
2. Database credentials are correct
3. IP whitelist includes VPS IP

#### Issue C: Service Import Errors

**Symptoms:**
```
❌ Service import/initialization failed: ModuleNotFoundError
```

**Fix:**
```bash
# Reinstall dependencies
cd /root/webmagic/backend
pip3 install -r requirements.txt

# Or use virtual environment
source venv/bin/activate
pip install -r requirements.txt
```

### Step 4: Check API Logs

```bash
# View recent API logs
pm2 logs webmagic-api --lines 100

# Look for specific errors
pm2 logs webmagic-api --lines 100 | grep -i error

# Check API status
pm2 status
```

Look for:
- Database connection errors
- Import errors
- Query failures
- Authentication issues

### Step 5: Restart Services

After applying fixes:

```bash
# Restart API
pm2 restart webmagic-api

# Restart worker (if needed)
pm2 restart webmagic-worker

# Restart beat scheduler (if needed)
pm2 restart webmagic-beat

# Check status
pm2 status

# Verify health
curl http://localhost:8000/health
```

### Step 6: Test Endpoints Directly

```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your-admin@email.com","password":"your-password"}' \
  | jq -r '.access_token')

# Test coverage stats
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/coverage/campaigns/stats

# Test categories
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/coverage/campaigns/categories?limit=20

# Test draft campaigns stats
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/draft-campaigns/stats
```

Expected response: JSON data (not 500 error)

### Step 7: Test from Frontend

1. Clear browser cache (Ctrl+Shift+Delete)
2. Reload the page (Ctrl+F5)
3. Navigate to Coverage page
4. Check browser console for errors

---

## Alternative: Quick Database Check (Manual)

If you can't run the Python script, check manually:

```bash
# Connect to database
psql $DATABASE_URL

# Check tables exist
\dt

# Should see:
# - coverage_grid
# - geo_strategies
# - draft_campaigns
# - businesses

# Check data
SELECT COUNT(*) FROM coverage_grid;
SELECT COUNT(*) FROM businesses;
SELECT COUNT(*) FROM geo_strategies;
SELECT COUNT(*) FROM draft_campaigns;

# Exit
\q
```

---

## Understanding the Coverage System

### How It Works

1. **User selects location + category** (e.g., Los Angeles, CA + Plumbers)

2. **Claude generates intelligent strategy:**
   - Analyzes city geography
   - Identifies business density patterns
   - Creates optimized zones with priorities
   - Stored in `geo_strategies` table

3. **User scrapes zones:**
   - Can scrape one zone at a time
   - Or batch scrape multiple zones
   - Each zone finds ~50 businesses

4. **Draft Mode (optional):**
   - Businesses saved to `draft_campaigns` table
   - Admin reviews before sending outreach
   - Can approve/reject campaigns

5. **Live Mode:**
   - Businesses found and outreach sent automatically
   - No manual review step

### Database Tables

#### `geo_strategies`
Stores Claude-generated strategies:
- Zone locations (lat/lon/radius)
- Priorities and reasoning
- Performance tracking
- Adaptive learning data

#### `draft_campaigns`
Stores campaigns awaiting review:
- Business IDs found
- Qualification metrics
- Review status
- Approval workflow

#### `coverage_grid`
Tracks overall coverage:
- What's been scraped
- Business counts
- Status tracking
- Metrics

---

## Common Error Patterns

### Error: "Table does not exist"

**Cause:** Migrations not run
**Fix:** Run migrations (Step 3, Issue A)

### Error: "Connection refused"

**Cause:** Database not accessible
**Fix:** Check DATABASE_URL and network

### Error: "Authentication failed"

**Cause:** JWT token expired or invalid
**Fix:** Re-login from frontend

### Error: "Module not found"

**Cause:** Missing Python dependencies
**Fix:** Reinstall requirements.txt

### Error: "Internal Server Error" (generic)

**Cause:** Multiple possible issues
**Fix:** Check API logs for specific error

---

## Prevention

To avoid these errors in the future:

1. **Always run migrations after pulling new code:**
   ```bash
   cd /root/webmagic/backend/migrations
   ls -la *.sql
   # Run any new migrations
   ```

2. **Monitor API logs regularly:**
   ```bash
   pm2 logs webmagic-api --lines 50
   ```

3. **Set up health check monitoring:**
   - Use UptimeRobot or similar
   - Monitor `/health` endpoint
   - Alert on failures

4. **Keep dependencies updated:**
   ```bash
   pip3 install -r requirements.txt --upgrade
   ```

---

## Files Created for Debugging

1. **`COVERAGE_SYSTEM_ERROR_ANALYSIS.md`** - Comprehensive error analysis
2. **`backend/scripts/diagnose_coverage_errors.py`** - Diagnostic script
3. **`COVERAGE_ERROR_FIX_GUIDE.md`** - This file (step-by-step fix)

---

## Need More Help?

If the issue persists after following these steps:

1. **Capture full error details:**
   ```bash
   pm2 logs webmagic-api --lines 200 > api_logs.txt
   python3 scripts/diagnose_coverage_errors.py > diagnostic_output.txt
   ```

2. **Check database directly:**
   ```bash
   psql $DATABASE_URL
   \dt
   \d geo_strategies
   \d draft_campaigns
   SELECT * FROM geo_strategies LIMIT 1;
   ```

3. **Verify environment:**
   ```bash
   cd /root/webmagic/backend
   cat .env | grep -E "(DATABASE|API|ANTHROPIC)"
   ```

4. **Test minimal endpoint:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/
   ```

---

## Success Criteria

You'll know it's fixed when:

1. ✅ Diagnostic script shows all checks passing
2. ✅ API logs show no errors
3. ✅ Coverage page loads without errors
4. ✅ Can create intelligent strategies
5. ✅ Can scrape zones successfully
6. ✅ Draft campaigns stats load

---

## Quick Reference Commands

```bash
# SSH into VPS
ssh root@104.251.211.183

# Run diagnostics
cd /root/webmagic/backend && python3 scripts/diagnose_coverage_errors.py

# Apply migrations
cd /root/webmagic/backend/migrations
psql $DATABASE_URL -f 004_add_geo_strategies.sql
psql $DATABASE_URL -f 005_add_draft_campaigns.sql

# Restart services
pm2 restart all

# Check logs
pm2 logs webmagic-api --lines 50

# Test health
curl http://localhost:8000/health
```

---

## Next Steps After Fix

Once the errors are resolved:

1. **Test the intelligent campaign flow:**
   - Create a strategy for a city
   - Scrape a zone in draft mode
   - Review the draft campaign
   - Approve and send (or reject)

2. **Consider UI improvements:**
   - Remove redundant Geo-Grid panel (per COVERAGE_PAGE_ANALYSIS.md)
   - Enhance Intelligent Campaign panel
   - Simplify manual testing section

3. **Add monitoring:**
   - Set up error alerting
   - Monitor API response times
   - Track campaign success rates


