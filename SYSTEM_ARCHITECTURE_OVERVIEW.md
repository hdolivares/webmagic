# WebMagic System Architecture Overview

**Last Updated:** February 14, 2026  
**Purpose:** High-level overview of how the business scraping system works

---

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                           │
│                                                                   │
│  Coverage Page (CoveragePage.tsx)                               │
│  └─ IntelligentCampaignPanel.tsx                                │
│     ├─ Strategy Creation UI                                     │
│     ├─ Zone Scraping Controls                                   │
│     └─ Results Display                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTPS
┌─────────────────────────────────────────────────────────────────┐
│                    NGINX REVERSE PROXY                           │
│                                                                   │
│  web.lavish.solutions:443                                        │
│  ├─ Static Files: /var/www/webmagic/frontend/dist/             │
│  └─ API Proxy: /api/* → http://127.0.0.1:8000/api/             │
│                                                                   │
│  Timeouts: 300s (proxy_read_timeout)                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTP
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                             │
│                                                                   │
│  Uvicorn (127.0.0.1:8000)                                        │
│  ├─ /api/v1/intelligent-campaigns/                              │
│  │  ├─ POST /strategies - Create strategy                       │
│  │  ├─ POST /scrape-zone - Scrape next zone                    │
│  │  ├─ POST /batch-scrape - Scrape multiple zones              │
│  │  └─ GET /strategies/{id} - Get strategy details             │
│  │                                                               │
│  └─ Services:                                                    │
│     ├─ HunterService (orchestration)                            │
│     ├─ GeoStrategyService (Claude/city-based strategies)        │
│     ├─ OutscraperClient (Google Maps scraping)                  │
│     ├─ DataQualityService (validation & scoring)                │
│     ├─ BusinessService (database operations)                    │
│     └─ CoverageService (progress tracking)                      │
└─────────────────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  OUTSCRAPER  │    │  POSTGRESQL  │    │    CELERY    │
│     API      │    │   DATABASE   │    │   WORKERS    │
│              │    │              │    │              │
│ Google Maps  │    │ geo_strats   │    │ Background   │
│ Business     │    │ coverage_gr  │    │ Jobs         │
│ Data         │    │ businesses   │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## Request Flow: Intelligent Scraping

### 1. Strategy Creation

```
User clicks "Generate Strategy"
    ↓
POST /api/v1/intelligent-campaigns/strategies
  {
    city: "Los Angeles",
    state: "CA", 
    category: "accountants"
  }
    ↓
GeoStrategyService.get_or_create_strategy()
    ↓
generate_city_based_strategy()
  - Looks up metro area (Los Angeles)
  - Finds all cities in metro (33 cities)
  - Creates zone for each city
  - Prioritizes by population
    ↓
Save to database: geo_strategies table
    ↓
Return strategy with 33 zones
```

**Response:**
```json
{
  "strategy_id": "da9f2bec-4d81-4d50-9e36-34fcd55136a3",
  "city": "Los Angeles",
  "state": "CA",
  "category": "accountants",
  "total_zones": 33,
  "zones": [
    {
      "zone_id": "los_angeles_los_angeles",
      "city": "Los Angeles",
      "priority": "high",
      "estimated_businesses": 3900
    },
    // ... 32 more zones
  ],
  "next_zone": { /* First uncompleted zone */ }
}
```

---

### 2. Zone Scraping

```
User clicks "Start Scraping This Zone"
    ↓
POST /api/v1/intelligent-campaigns/scrape-zone
  {
    strategy_id: "...",
    limit_per_zone: 50,
    draft_mode: true
  }
    ↓
HunterService.scrape_with_intelligent_strategy()
    ↓
┌─────────────────────────────────────────┐
│ STEP 1: Get Next Zone                  │
│ - strategy.get_next_zone()             │
│ - zone_id: "los_angeles_los_angeles"   │
│ - target_city: "Los Angeles"           │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ STEP 2: Search Businesses (15-30s)     │
│ OutscraperClient.search_businesses()    │
│   query: "accountants in LA, CA, US"   │
│   limit: 50                             │
│ → Calls Outscraper API                 │
│ → Returns 48 raw businesses            │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ STEP 3: Process Each Business (20-30s) │
│ FOR EACH business in results:          │
│   1. Geo-validation                     │
│      - Check country/state match       │
│      - Filter out-of-region            │
│   2. Website Detection                  │
│      - Multi-tier detection             │
│      - HTTP validation                  │
│   3. Quality Scoring                    │
│      - Rating, reviews, verification    │
│   4. Save to Database                   │
│      - Check for duplicates             │
│      - Link to coverage_grid            │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ STEP 4: Update Coverage & Strategy     │
│ - CoverageService.update_coverage()     │
│   - lead_count: 48                      │
│   - qualified_count: 4                  │
│   - status: "completed"                 │
│ - GeoStrategy.mark_zone_complete()      │
│   - zones_completed: 1                  │
│   - businesses_found: 48                │
└─────────────────────────────────────────┘
    ↓
Return scrape results to frontend
```

**Response:**
```json
{
  "strategy_id": "...",
  "status": "completed",
  "zone_scraped": {
    "zone_id": "los_angeles_los_angeles",
    "priority": "high"
  },
  "results": {
    "raw_businesses": 48,
    "qualified_leads": 4,
    "new_businesses": 48,
    "with_websites": 0,
    "without_websites": 48
  },
  "progress": {
    "total_zones": 33,
    "zones_completed": 1,
    "zones_remaining": 32,
    "completion_pct": 3.03
  }
}
```

**Duration:** ~60-75 seconds total

---

## Database Schema

### geo_strategies
```sql
id                      UUID PRIMARY KEY
city                    VARCHAR (e.g., "Los Angeles")
state                   VARCHAR (e.g., "CA")
category                VARCHAR (e.g., "accountants")
zones                   JSONB (array of zone objects)
total_zones             INTEGER
zones_completed         INTEGER
businesses_found        INTEGER
is_active               VARCHAR (active|completed|paused)
created_at              TIMESTAMP
```

### coverage_grid
```sql
id                      UUID PRIMARY KEY
city                    VARCHAR
state                   VARCHAR
industry                VARCHAR
zone_id                 VARCHAR (e.g., "los_angeles_los_angeles")
status                  VARCHAR (pending|in_progress|completed|failed)
lead_count              INTEGER (total businesses found)
qualified_count         INTEGER (passed quality filters)
last_scraped_at         TIMESTAMP
created_at              TIMESTAMP
```

### businesses
```sql
id                      UUID PRIMARY KEY
gmb_id                  VARCHAR (Google My Business ID)
name                    VARCHAR
phone                   VARCHAR
website_url             VARCHAR
address                 TEXT
city                    VARCHAR
state                   VARCHAR
category                VARCHAR
rating                  NUMERIC
review_count            INTEGER
website_status          VARCHAR (none|queued|generated|published)
coverage_grid_id        UUID (FK to coverage_grid)
created_at              TIMESTAMP
```

---

## Key Services

### HunterService
**Purpose:** Main orchestration service  
**File:** `backend/services/hunter/hunter_service.py`

**Key Methods:**
- `scrape_with_intelligent_strategy()` - Execute zone scraping
- `scrape_all_zones_for_strategy()` - Batch scraping

---

### GeoStrategyService
**Purpose:** Strategy creation and management  
**File:** `backend/services/hunter/geo_strategy_service.py`

**Key Methods:**
- `get_or_create_strategy()` - Get existing or generate new
- `get_strategy_by_id()` - Retrieve strategy
- `refine_strategy()` - Claude-powered strategy refinement

**Strategy Generation:**
- Uses `metro_city_strategy.py` for city-based approach
- Alternative: `geo_strategy_agent.py` for Claude-powered (slower, more flexible)

---

### OutscraperClient
**Purpose:** Google Maps business scraping  
**File:** `backend/services/hunter/scraper.py`

**Key Methods:**
- `search_businesses()` - Search by city + category
- `_normalize_results()` - Convert to standard format

**Features:**
- Anti-duplicate search locking
- City-based targeting (not coordinate-based)
- Website field extraction
- Review and photo data capture

---

### DataQualityService
**Purpose:** Validation and quality scoring  
**File:** `backend/services/hunter/data_quality_service.py`

**Key Methods:**
- `validate_geo_targeting()` - Ensure business in target region
- `detect_website()` - Multi-tier website detection
- `calculate_quality_score()` - Rating, reviews, verification

---

## Configuration

### Nginx Timeouts
```nginx
proxy_connect_timeout 60s;   # Time to connect to backend
proxy_send_timeout 300s;      # Time to send request (5 minutes)
proxy_read_timeout 300s;      # Time to read response (5 minutes)
```

### Uvicorn (FastAPI)
```bash
# Supervisor config: /etc/supervisor/conf.d/webmagic.conf
uvicorn api.main:app 
  --host 127.0.0.1 
  --port 8000 
  --workers 2
```

### Celery Workers
```bash
# Background task processing
celery -A celery_app worker 
  --loglevel=info 
  --concurrency=1 
  -Q celery,generation,scraping,campaigns,monitoring,validation
```

---

## Intelligent Campaign Features

### City-Based Strategy
Instead of Claude generating coordinates, we use predefined metro area mappings:

**Example: Los Angeles Metro**
```python
METRO_CITY_MAPPING = {
    "Los Angeles": {
        "cities": [
            {"name": "Los Angeles", "population": 3900000},
            {"name": "Long Beach", "population": 467000},
            {"name": "Pasadena", "population": 142000},
            # ... 30 more cities
        ]
    }
}
```

**Benefits:**
- ✅ Faster (no Claude API call)
- ✅ More accurate (Outscraper uses city names, not coordinates)
- ✅ Comprehensive coverage (all suburbs included)
- ✅ Priority-based (by population)

### Zone Priority Levels
- **High:** Population > 100,000
- **Medium:** Population 50,000-100,000  
- **Low:** Population < 50,000

### Draft Mode vs Live Mode
- **Draft Mode:** Save businesses for manual review (no outreach sent)
- **Live Mode:** Automatically send outreach messages (coming soon)

---

## Error Handling

### Common Issues

1. **504 Gateway Timeout**
   - **Cause:** Operation took > 60s (before fix) or > 300s (after fix)
   - **Fix:** Increased Nginx timeout to 300s
   - **Frontend:** Auto-checks results after timeout

2. **Outscraper API Errors**
   - **Error 0:** Out of credits or invalid API key
   - **Fix:** Check `OUTSCRAPER_API_KEY` env variable

3. **Geo-Validation Failures**
   - **Cause:** Business location doesn't match target region
   - **Result:** Business skipped (not saved)

4. **Duplicate Businesses**
   - **Detection:** `gmb_id` uniqueness constraint
   - **Result:** Duplicate skipped, count not incremented

---

## Monitoring & Logging

### Log Files
```
/var/log/nginx/error.log       - Nginx errors (timeouts, etc.)
/var/log/nginx/access.log      - All HTTP requests
/var/log/webmagic/api.log      - Application logs
/var/log/webmagic/api_error.log - Python exceptions
/var/log/webmagic/celery.log   - Celery worker logs
```

### Key Metrics to Monitor
- Strategy creation time
- Average scrape duration per zone
- Businesses found per zone
- Qualification rate (qualified / total)
- Website detection accuracy
- Database insert performance

---

## Performance Benchmarks

### Typical Operation Times
- **Strategy Creation:** 2-5 seconds
- **Single Zone Scrape:** 60-75 seconds
  - Outscraper API: 15-30s
  - Processing: 20-30s
  - Database: 10-15s
- **Batch Scrape (5 zones):** 5-6 minutes
- **Full City Campaign (30+ zones):** 30-45 minutes

### Database Performance
- **Business Insert:** ~200ms (with duplicate check)
- **Coverage Update:** ~100ms
- **Strategy Query:** ~50ms

---

## Next Steps for Scaling

### Phase 1: Background Jobs
Move scraping to Celery tasks:
```python
@celery_app.task
def scrape_zone_task(strategy_id, zone_id):
    # Long-running scrape
    pass

# API returns immediately with task_id
# Frontend polls for completion
```

### Phase 2: Real-Time Progress
Add Server-Sent Events (SSE):
```python
@router.post("/scrape-zone/stream")
async def scrape_zone_stream():
    async def event_generator():
        yield "data: started\n\n"
        # ... progress updates ...
        yield "data: completed\n\n"
    return StreamingResponse(event_generator())
```

### Phase 3: Distributed Processing
- Multiple Celery workers
- Redis for job queue
- Rate limiting per worker
- Parallel zone scraping

---

## Conclusion

The WebMagic scraping system is a sophisticated multi-stage pipeline that:

1. ✅ **Generates intelligent strategies** using city-based zone placement
2. ✅ **Scrapes Google Maps** via Outscraper API
3. ✅ **Validates and processes** business data with quality scoring
4. ✅ **Tracks progress** across zones and strategies
5. ✅ **Scales efficiently** with proper timeouts and error handling

The recent timeout fix ensures users see reliable feedback and successful operations complete without false errors.

---

**Architecture Review Date:** February 14, 2026  
**System Status:** ✅ Operational  
**Last Updated By:** AI Analysis
