# Coverage System Error Analysis

## Date: January 25, 2026

## Summary
Multiple 500 Internal Server Errors occurring on the Coverage Page when clicking "Start Scraping This Zone" button. The errors affect several endpoints related to coverage campaigns and draft campaigns.

---

## Error Details

### Frontend Errors Observed

1. **`/api/v1/coverage/campaigns/categories?limit=20`** - 500 Internal Server Error
2. **`/api/v1/draft-campaigns/stats`** - 500 Internal Server Error  
3. **`/api/v1/intelligent-campaigns/scrape-zone`** - 500 Internal Server Error

### Error Pattern
```
SES Removing unpermitted intrinsics
Failed to load campaign data: AxiosError: Request failed with status code 500
```

---

## Coverage System Architecture

### How the Coverage Page Works

The Coverage Page has evolved into a **multi-strategy system** for discovering businesses across regions:

#### 1. **Intelligent Campaign Orchestration** (Primary Method)
**Location:** `frontend/src/components/coverage/IntelligentCampaignPanel.tsx`

**How it works:**
- User selects: State → City → Business Category
- Claude AI analyzes the city's geography and business distribution
- Generates optimal zone placement strategy with priorities
- Each zone has: lat/lon, radius, priority, reasoning
- User can scrape zones one-by-one or in batches
- Supports **Draft Mode** (save for review) and **Live Mode** (auto-send outreach)

**API Endpoints Used:**
- `POST /api/v1/intelligent-campaigns/strategies` - Create strategy
- `POST /api/v1/intelligent-campaigns/scrape-zone` - Scrape next zone
- `POST /api/v1/intelligent-campaigns/batch-scrape` - Scrape multiple zones
- `GET /api/v1/intelligent-campaigns/strategies/{id}` - Get strategy details

**Backend Services:**
- `GeoStrategyService` - Manages intelligent strategies
- `HunterService` - Executes scraping operations
- `DraftCampaignService` - Handles draft mode workflow

#### 2. **Geo-Grid Scraping** (Manual Method)
**Location:** `frontend/src/components/coverage/GeoGridPanel.tsx`

**How it works:**
- User manually inputs: City, State, Industry, Population, Lat/Lon
- System calculates grid zones based on population density
- Scrapes each zone systematically
- More manual, less intelligent than Claude-powered method

**API Endpoints Used:**
- `POST /api/v1/coverage/geo-grid/scrape` - Execute geo-grid scrape
- `GET /api/v1/coverage/geo-grid/compare` - Compare strategies

#### 3. **Coverage Campaign Stats** (Monitoring)
**Location:** `frontend/src/pages/Coverage/CoveragePage.tsx`

**How it works:**
- Displays overall campaign statistics
- Shows coverage by location and category
- Tracks progress across all campaigns

**API Endpoints Used:**
- `GET /api/v1/coverage/campaigns/stats` - Overall stats
- `GET /api/v1/coverage/campaigns/locations` - Location breakdown
- `GET /api/v1/coverage/campaigns/categories` - Category breakdown

---

## Root Cause Analysis

### Potential Issues

#### 1. **Database Connection Problems**
The endpoints are failing with 500 errors, which typically indicates:
- Database connection timeout
- Missing database tables
- Query execution failures
- Database credentials expired/invalid

**Evidence:**
- All failing endpoints query the database
- No specific error messages in frontend (generic 500)
- Supabase logs returned empty (no recent API calls logged)

#### 2. **Missing Database Tables**
The intelligent campaigns system uses these tables:
- `geo_strategies` - Stores Claude-generated strategies
- `geo_strategy_zones` - Individual zones within strategies
- `draft_campaigns` - Draft mode campaigns awaiting review
- `coverage_grid` - Coverage tracking data

**Action Needed:** Verify these tables exist in production database

#### 3. **Authentication/Authorization Issues**
The endpoints require authentication via `get_current_user` dependency.

**Possible causes:**
- JWT token expired
- User permissions incorrect
- Auth middleware failing silently

#### 4. **Missing Environment Variables**
Required environment variables:
- `DATABASE_URL` - PostgreSQL connection string
- `SUPABASE_PROJECT_URL` (optional)
- `SUPABASE_API_KEY` (optional)
- Claude API keys for intelligent strategies

#### 5. **Service Dependencies**
The intelligent campaigns system depends on:
- `GeoStrategyService` - May be failing to initialize
- `DraftCampaignService` - May have missing dependencies
- `HunterService` - Core scraping service

---

## Investigation Steps

### Step 1: Check Backend Logs
```bash
# SSH into VPS
ssh root@104.251.211.183

# Check API logs
pm2 logs webmagic-api --lines 100

# Check for errors
journalctl -u webmagic-api -n 100 --no-pager
```

### Step 2: Verify Database Connection
```bash
# Check if backend can connect to database
cd /root/webmagic/backend
python3 -c "from core.config import get_settings; print(get_settings().DATABASE_URL)"

# Test database connection
python3 -c "
from core.database import engine
import asyncio
async def test():
    async with engine.connect() as conn:
        result = await conn.execute('SELECT 1')
        print('DB Connected:', result.scalar())
asyncio.run(test())
"
```

### Step 3: Verify Database Schema
```sql
-- Check if required tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'geo_strategies',
    'geo_strategy_zones', 
    'draft_campaigns',
    'coverage_grid',
    'businesses'
);

-- Check coverage_grid structure
\d coverage_grid

-- Check if data exists
SELECT COUNT(*) FROM coverage_grid;
SELECT COUNT(*) FROM businesses;
```

### Step 4: Test Endpoints Directly
```bash
# Get auth token first
curl -X POST https://api.webmagic.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}'

# Test coverage stats endpoint
curl https://api.webmagic.com/api/v1/coverage/campaigns/stats \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test categories endpoint
curl https://api.webmagic.com/api/v1/coverage/campaigns/categories?limit=20 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test draft campaigns stats
curl https://api.webmagic.com/api/v1/draft-campaigns/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Step 5: Check Service Status
```bash
# Check if API is running
pm2 status

# Check API health
curl https://api.webmagic.com/health

# Check API version
curl https://api.webmagic.com/
```

---

## Expected Fixes

### Fix 1: Database Schema Migration
If tables are missing, run migrations:
```bash
cd /root/webmagic/backend
python3 scripts/quick_init.py
```

### Fix 2: Environment Variables
Ensure `.env` file has correct values:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
ANTHROPIC_API_KEY=sk-...
```

### Fix 3: Restart Services
```bash
pm2 restart webmagic-api
pm2 restart webmagic-worker
pm2 restart webmagic-beat
```

### Fix 4: Add Error Handling
Update endpoints to return better error messages:
```python
try:
    # Query execution
except Exception as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"Database error: {str(e)}"
    )
```

---

## Coverage Strategy Explanation

### How Businesses Are Scraped in a Region

The system uses a **zone-based approach** to comprehensively cover a geographic region:

#### Traditional Approach (Geo-Grid)
1. Calculate city area based on population
2. Divide into uniform grid zones (e.g., 2km x 2km)
3. Scrape each zone sequentially
4. Each zone gets ~50 businesses

**Pros:** Systematic, predictable
**Cons:** Doesn't account for business density variations

#### Intelligent Approach (Claude-Powered)
1. **Analysis Phase:**
   - Claude analyzes city geography (downtown, suburbs, industrial areas)
   - Identifies business distribution patterns
   - Considers population density, commercial zones

2. **Strategy Generation:**
   - Creates variable-sized zones based on expected business density
   - Assigns priorities (high-density areas first)
   - Provides reasoning for each zone placement

3. **Adaptive Execution:**
   - Scrapes high-priority zones first
   - Learns from results (actual vs expected businesses)
   - Can refine strategy based on findings
   - Adjusts future zones dynamically

4. **Draft Mode Workflow:**
   - Scrapes businesses and saves to `draft_campaigns` table
   - Admin reviews businesses before sending outreach
   - Can approve/reject entire campaigns
   - Prevents accidental spam or low-quality leads

**Pros:** Intelligent, adaptive, efficient
**Cons:** Requires Claude API, more complex

---

## Next Steps

1. ✅ **Immediate:** Access VPS and check backend logs
2. ✅ **Verify:** Database connection and schema
3. ✅ **Test:** Endpoints directly with curl
4. ✅ **Fix:** Identified issues (likely missing tables or connection)
5. ✅ **Deploy:** Restart services after fixes
6. ✅ **Validate:** Test coverage page functionality

---

## Files to Review

### Backend
- `backend/api/v1/intelligent_campaigns.py` - Main endpoint logic
- `backend/api/v1/draft_campaigns.py` - Draft mode endpoints
- `backend/api/v1/coverage_campaigns.py` - Coverage stats endpoints
- `backend/services/hunter/geo_strategy_service.py` - Strategy service
- `backend/services/draft_campaign_service.py` - Draft campaign service
- `backend/models/geo_strategy.py` - Database models
- `backend/core/database.py` - Database connection

### Frontend
- `frontend/src/components/coverage/IntelligentCampaignPanel.tsx` - Main UI
- `frontend/src/pages/Coverage/CoveragePage.tsx` - Coverage page
- `frontend/src/services/api.ts` - API client (lines 716-789)

---

## Recommendations

### Short-term
1. Fix the 500 errors by investigating logs
2. Ensure database schema is complete
3. Add better error messages to endpoints

### Long-term
1. Remove redundant Geo-Grid panel (as per COVERAGE_PAGE_ANALYSIS.md)
2. Enhance Intelligent Campaign panel as primary interface
3. Add monitoring/alerting for API errors
4. Implement retry logic for failed scrapes
5. Add progress tracking for batch scrapes


