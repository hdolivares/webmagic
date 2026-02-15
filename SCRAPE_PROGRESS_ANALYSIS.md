# Scrape Progress & Visibility Analysis
**Date:** 2026-02-15  
**Issue:** No frontend visibility for scrapes, no progress tracking, zero metrics

---

## 🔴 CRITICAL ISSUES FOUND

### 1. **Discovery Queue Not Running** ❌
**Problem:** Workers not listening to `discovery` queue

```bash
# Current supervisor config:
-Q celery,generation,scraping,campaigns,monitoring,validation
# MISSING: discovery
```

**Impact:** ScrapingDog discovery tasks (`discover_missing_websites_v2`) are never processed

**Celery Task Routes:**
```python
"tasks.scraping_tasks.*": {"queue": "scraping", "priority": 7},     # ✅ Workers listening
"tasks.discovery_tasks.*": {"queue": "discovery", "priority": 6},    # ❌ Workers NOT listening
"tasks.validation_tasks_enhanced.*": {"queue": "validation", "priority": 8}  # ✅ Workers listening
```

---

### 2. **Scrape Task Not Executing** ❌
**Problem:** `scrape_zone_async` registered but never runs

**Evidence:**
- ✅ Task registered: `tasks.scraping.scrape_zone_async`
- ✅ Session created: `9bf0bf6c-b428-45e8-b2c8-4d492d87a292`
- ❌ **Never saw:** `"🚀 Starting async scrape"` in logs
- ❌ **Session metrics:** Total=0, Scraped=0, Validated=0, Discovered=0
- ❌ **Completed in 4 minutes** with zero progress

**Expected Flow:**
```
API → scrape_zone_async.delay() → Celery Worker → HunterService → Validation → Discovery
```

**Actual Flow:**
```
API → scrape_zone_async.delay() → ??? (task never executes)
```

---

### 3. **No Progress Events** ❌
**Problem:** Redis progress channel empty

```bash
redis-cli KEYS "scrape:progress:*"
# Result: (empty array)
```

**Impact:** 
- No SSE events published
- Frontend EventSource receives nothing
- Zero real-time updates

---

### 4. **Zero Frontend Visibility** ❌
**User Experience:**
- ✅ User clicks "Scrape Next Zone"
- ✅ Gets "Scrape queued" message
- ❌ No progress bar appears
- ❌ No business counter updates
- ❌ No validation status
- ❌ No final summary
- ❌ No insight into what happened

**What Should Happen:**
```
┌─────────────────────────────────────┐
│ Scraping "therapists" in Los Angeles│
├─────────────────────────────────────┤
│ [████████████░░░░░] 60%             │
│                                      │
│ Phase: ScrapingDog Discovery        │
│ ✓ Found: 45 businesses              │
│ ✓ Valid URLs: 32                    │
│ ⚠ Need Discovery: 13                │
│ ⏳ In Progress: 5/13                 │
└─────────────────────────────────────┘
```

---

### 5. **No Scrape Result Logging** ❌
**User Request:**
> "We should log the results we get with each of the scrapes, so we can have visibility. The region, the business type, how many businesses were found, how many had websites, vs how many didn't have websites, etc."

**Current State:**
- No structured logging of scrape outcomes
- No analytics on website detection rate
- No regional performance metrics
- No category-specific insights
- No historical trend tracking

**Needed:**
```python
# Example of what should be logged:
{
    "scrape_id": "uuid",
    "timestamp": "2026-02-15T20:58:09Z",
    "region": {
        "city": "Los Angeles",
        "state": "CA",
        "zone_id": "la_losangel_therap"
    },
    "query": {
        "category": "therapists",
        "limit": 50
    },
    "results": {
        "total_found": 45,
        "with_valid_urls": 32,  # 71%
        "needs_discovery": 13,   # 29%
        "discovered": 8,         # 62% discovery success
        "confirmed_missing": 5,  # 38% truly no website
        "queued_for_generation": 5
    },
    "performance": {
        "duration_seconds": 235,
        "outscraper_calls": 1,
        "scrapingdog_calls": 13,
        "validation_time_avg_ms": 450
    },
    "quality": {
        "url_sources": {
            "outscraper": 32,
            "scrapingdog": 8
        },
        "validation_quality_avg": 0.85
    }
}
```

---

## 🔍 DIAGNOSTICS RUN

### Database State
```sql
SELECT id::text, zone_id, status, 
       total_businesses, scraped_businesses, validated_businesses, discovered_businesses,
       started_at, completed_at
FROM scrape_sessions 
ORDER BY created_at DESC LIMIT 1;

-- Result:
-- id: 9bf0bf6c-b428-45e8-b2c8-4d492d87a292
-- zone: la_losangel_therap
-- status: completed
-- total: 0, scraped: 0, validated: 0, discovered: 0  ❌
-- started: 2026-02-15 20:58:10
-- completed: 2026-02-15 21:02:05 (4 min duration)
```

### Celery State
```bash
# Registered tasks
celery -A celery_app inspect registered | grep scrape_zone_async
# Result: tasks.scraping.scrape_zone_async  ✅

# Active/Reserved tasks
celery -A celery_app inspect active
celery -A celery_app inspect reserved
# Result: Empty (no tasks running)  ❌

# Queue lengths
redis-cli LLEN scraping
# Result: 0  ❌
```

### Supervisor Config
```ini
command=celery -A celery_app worker --loglevel=info --concurrency=4 
  -Q celery,generation,scraping,campaigns,monitoring,validation
#    ↑ MISSING: discovery queue
```

---

## 🎯 ROOT CAUSES

### Primary Issue: Task Execution Failure
**Hypothesis 1:** Import error in `scraping_tasks.py`
- Check: `from services.progress.progress_publisher import ProgressPublisher`
- Check: `from services.progress.redis_service import RedisService`
- Possible circular import or missing dependency

**Hypothesis 2:** Task signature mismatch
- Endpoint calls: `scrape_zone_async.delay(...)`
- Task definition: `@shared_task(name="tasks.scraping.scrape_zone_async", ...)`
- Possible mismatch in task name or autodiscovery

**Hypothesis 3:** Queue routing issue
- Task routed to `scraping` queue (correct)
- Workers listening to `scraping` queue (confirmed)
- But task never received → possible Redis connection issue?

### Secondary Issue: Missing Queue
- `discovery` queue not in supervisor config
- Discovery tasks will fail silently when queued
- Causes validation → discovery flow to break

### Tertiary Issues
- No logging infrastructure for scrape summaries
- Frontend ScrapeProgress component not displaying
- SSE stream working but no events to stream

---

## ✅ PROPOSED FIXES

### Fix 1: Add Discovery Queue ⚡ HIGH PRIORITY
```bash
# Update supervisor config
command=celery -A celery_app worker --loglevel=info --concurrency=4 
  -Q celery,generation,scraping,campaigns,monitoring,validation,discovery
#                                                                  ^^^^^^^^^ ADD THIS

# Then restart
supervisorctl restart webmagic-celery
```

### Fix 2: Debug Task Execution ⚡ CRITICAL
**Steps:**
1. Add explicit logging in `scraping_tasks.py` at task entry
2. Check if task is imported properly in `celery_app.py`
3. Test task manually: `scrape_zone_async.delay(...)` from Python shell
4. Verify Redis connection in task worker
5. Check for silent exceptions in task startup

### Fix 3: Add Scrape Result Logging 📊 HIGH PRIORITY
**Create: `services/scrape_analytics.py`**
```python
class ScrapeAnalytics:
    """Log and analyze scrape results for visibility and optimization."""
    
    async def log_scrape_complete(
        self,
        session_id: str,
        region: dict,
        query: dict,
        results: dict,
        performance: dict
    ):
        """
        Log comprehensive scrape results.
        
        Stores in:
        - Database (scrape_sessions.metadata)
        - Log file (structured JSON for parsing)
        - Analytics table (for dashboards)
        """
        pass
    
    async def generate_summary_report(self, session_id: str) -> str:
        """Generate human-readable summary of scrape results."""
        pass
```

### Fix 4: Frontend Progress Display 🎨 HIGH PRIORITY
**Issues:**
- `ScrapeProgress` component exists but not rendering
- Need to check if component is mounted when `scrapeSessionId` is set
- EventSource connection may be working but showing no UI

**Verify:**
1. Is `ScrapeProgress` component actually mounted?
2. Is EventSource receiving events? (Check browser DevTools → Network → EventStream)
3. Are progress states being rendered correctly?

### Fix 5: Summary Report at Completion 📄 MEDIUM PRIORITY
**After scrape completes, show:**
```
┌────────────────────────────────────────────┐
│ Scrape Complete: Therapists, Los Angeles  │
├────────────────────────────────────────────┤
│ Region:       Los Angeles, CA              │
│ Zone:         la_losangel_therap           │
│ Category:     therapists                   │
│ Duration:     3m 54s                       │
│                                             │
│ Results:                                    │
│ • Total businesses: 45                     │
│ • Valid websites:   32 (71%)               │
│ • Needs discovery:  13 (29%)               │
│   - Discovered:     8 (62% success)        │
│   - No website:     5 (11% of total)       │
│                                             │
│ Website Generation Queue:                  │
│ • Ready to generate: 5 businesses          │
│                                             │
│ [View Businesses] [Generate Websites]      │
└────────────────────────────────────────────┘
```

---

## 🚀 ACTION PLAN

### Phase 1: Critical Fixes (DO NOW)
1. ✅ Add `discovery` queue to supervisor config
2. ✅ Debug why `scrape_zone_async` isn't executing
3. ✅ Verify task imports and dependencies
4. ✅ Test manual task execution

### Phase 2: Visibility & Logging (NEXT)
5. ⏳ Add comprehensive scrape result logging
6. ⏳ Create `ScrapeAnalytics` service
7. ⏳ Verify frontend `ScrapeProgress` component rendering
8. ⏳ Add scrape completion summary UI

### Phase 3: Analytics & Optimization (FUTURE)
9. 📊 Create scrape analytics dashboard
10. 📊 Add regional performance metrics
11. 📊 Track website detection rate trends
12. 📊 Category-specific insights

---

## 📝 NOTES

### User Feedback
> "I have no visibility on the frontend. I thought I would be able to see more of what was happening with each of the businesses and in which step they are. See a progress bar for all of the results, and at the end of the entire process see a summary of what was achieved."

**Expectation:** Real-time progress with granular business-level updates

**Reality:** Zero updates, black box operation

### State-Based Triggers
> "the scraping queue should only kick in on certain states right?"

**Correct!** The Validation V2 state machine should trigger discovery only for:
- `ValidationState.NEEDS_DISCOVERY`
- `ValidationRecommendation.TRIGGER_SCRAPINGDOG`

**Current Issue:** Even if these states are correct, tasks aren't executing due to the bugs above.

---

## 🔗 RELATED FILES

- `backend/tasks/scraping_tasks.py` - Async scraping task (not executing)
- `backend/api/v1/endpoints/scrapes.py` - Scrape API (creating sessions correctly)
- `backend/services/progress/progress_publisher.py` - Redis event publisher
- `frontend/src/components/coverage/ScrapeProgress.tsx` - Progress UI component
- `frontend/src/components/coverage/IntelligentCampaignPanel.tsx` - Scrape initiator
- `/etc/supervisor/conf.d/webmagic-celery.conf` - Worker queue config (needs update)

---

**Generated:** 2026-02-15 15:20 UTC  
**Status:** 🔴 CRITICAL - Zero visibility, zero progress tracking
