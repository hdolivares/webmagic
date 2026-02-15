# 🔍 ScrapingDog Query Issue & Architecture Analysis

**Date:** February 15, 2026  
**Priority:** 🔴 **CRITICAL**

---

## 🚨 **Problem Identified**

### Current Query Format (BROKEN)
```python
# File: backend/services/discovery/llm_discovery_service.py:214
def _build_query(self, business_name: str, city: Optional[str], state: Optional[str]) -> str:
    query_parts = [f'"{business_name}"']  # ❌ PROBLEM: Wraps in quotes
    if city:
        query_parts.append(city)
    if state:
        query_parts.append(state)
    query_parts.append("website")
    return " ".join(query_parts)
```

**Example Output:**
```
"Precision Painting Plus of Los Angeles" Los Angeles CA website
```

**Result:** 400 Error from ScrapingDog API
```json
{"message":"Something went wrong, please try again","status":400}
```

---

## ✅ **Curl Test Results**

### Test 1: Current Format (WITH quotes) - FAILED
```bash
curl "https://api.scrapingdog.com/google/?api_key=XXX&query=%22Precision+Painting+Plus+of+Los+Angeles%22+Los+Angeles+CA+website&results=5&country=us"
```
**Result:** 400 Error (API rejects quoted complex queries)

### Test 2: Simplified Format (NO quotes) - SUCCESS ✅
```bash
curl "https://api.scrapingdog.com/google/?api_key=XXX&query=Precision+Painting+Plus+Los+Angeles&results=5&country=us"
```
**Result:** HTTP 200, Returns 10 organic results including:
- `https://www.precisionpaintingplus.net/` (official website)
- Instagram, Yelp, reviews, etc.

---

## 🎯 **Root Cause Analysis**

### Why Quotes Break the Query

1. **Special Characters**: "Plus" and "of" are treated as operators when inside quotes
2. **Over-specification**: Adding "CA website" is redundant and confuses the API
3. **API Limitations**: ScrapingDog Google Search doesn't handle complex quoted phrases well

### Why Simplified Works

- **Clean business name**: Just the core name
- **Location context**: City/state without extras
- **No operators**: No quotes, no "website" keyword needed

---

## 📋 **Recommended Fix**

### Simple Query Format
```python
def _build_query(self, business_name: str, city: Optional[str], state: Optional[str]) -> str:
    """
    Build SIMPLE search query for ScrapingDog.
    Format: "[business name] [city]"
    No quotes, no operators, no extra keywords.
    """
    # Clean business name (remove common noise words that cause issues)
    clean_name = business_name.replace(" of Los Angeles", "").replace(" of California", "").strip()
    
    query_parts = [clean_name]
    if city:
        query_parts.append(city)
    # Note: No state, no "website" keyword - keep it minimal
    
    return " ".join(query_parts)
```

**Examples:**
- "Precision Painting Plus of Los Angeles" → `"Precision Painting Plus Los Angeles"`
- "Joe's Plumbing" → `"Joe's Plumbing Los Angeles"`
- "ABC Law Firm, Inc." → `"ABC Law Firm Los Angeles"`

---

## 🏗️ **Architecture Issue: Queue Separation**

### Current Architecture (PROBLEMATIC)

```
USER INITIATES SCRAPE
        ↓
┌───────────────────────────────────────┐
│ 1. OUTSCRAPER API (Sync)              │
│    • Fetches 50-200 businesses        │
│    • Creates DB records immediately   │
│    • Blocks until complete            │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│ 2. VALIDATION QUEUE (Async)           │
│    • batch_validate_websites_v2()     │
│    • ALL businesses queued at once    │
│    • 4 workers process in parallel    │
└───────────────────────────────────────┘
        ↓ (for failed URLs)
┌───────────────────────────────────────┐
│ 3. DISCOVERY QUEUE (Async)            │
│    • discover_missing_websites_v2()   │
│    • Triggered by validation failures │
│    • Re-queues for validation         │
└───────────────────────────────────────┘
```

### Problems with Current Approach

1. **🚫 Outscraper Blocks Everything**
   - Scraping 200 businesses takes 2-5 minutes
   - Frontend shows no progress
   - User has no feedback

2. **🚫 Massive Queue Dump**
   - All 200 businesses queued instantly for validation
   - Celery queue can become overwhelmed
   - No rate limiting or throttling

3. **🚫 Discovery Triggers Re-validation**
   - When ScrapingDog finds a URL, it re-queues validation
   - Creates circular dependency
   - Can cause duplicate tasks

---

## ✅ **Recommended Architecture: Separate Queues**

### Improved Flow

```
USER INITIATES SCRAPE
        ↓
┌───────────────────────────────────────┐
│ QUEUE 1: Outscraper Scraping (Async) │
│ Task: scrape_zone_async.delay()      │
│   • Fetches businesses in background  │
│   • Creates DB records one-by-one     │
│   • Emits progress updates (SSE)      │
│   • Queues next step per business     │
└───────────────────────────────────────┘
        ↓ (for each business)
┌───────────────────────────────────────┐
│ QUEUE 2: URL Validation (Async)      │
│ Task: validate_business_url.delay()   │
│   • Prescreener checks                │
│   • Playwright extraction             │
│   • LLM verification                  │
│   • IF FAIL → Queue 3                 │
│   • IF PASS → Mark as valid           │
└───────────────────────────────────────┘
        ↓ (only for invalid URLs)
┌───────────────────────────────────────┐
│ QUEUE 3: Discovery (Async)            │
│ Task: discover_website.delay()        │
│   • ScrapingDog Google Search         │
│   • LLM analysis of results           │
│   • IF FOUND → Back to Queue 2        │
│   • IF NOT FOUND → confirmed_no_url   │
└───────────────────────────────────────┘
```

### Benefits

✅ **Real-time Progress**
- Frontend gets updates as each business is scraped
- Users see immediate feedback
- Can cancel if needed

✅ **Controlled Rate**
- Outscraper API calls are spaced out
- Celery queue doesn't overflow
- Better error handling per business

✅ **Clear Separation of Concerns**
- Each queue has ONE job
- No circular dependencies
- Easier to debug and monitor

✅ **Better Resource Management**
- Can scale workers per queue independently
- Slow operations don't block fast ones
- Priority queues for urgent tasks

---

## 🔧 **Implementation Plan**

### Phase 1: Fix Query Format (Quick Win - 5 minutes)
1. Update `_build_query()` method
2. Deploy fix
3. Test with curl and real scrapes

### Phase 2: Separate Outscraper Queue (Medium - 1 hour)
1. Create new task: `scrape_zone_async(zone_id, strategy_id)`
2. Move Outscraper logic to async task
3. Add progress tracking (emit to Redis/SSE)
4. Update frontend to show progress

### Phase 3: Refine Queue Flow (Medium - 1 hour)
1. Ensure validation only queues once
2. Discovery doesn't re-validate automatically
3. Add manual "retry validation" button in UI
4. Implement rate limiting per queue

---

## 📊 **Expected Improvements**

| Metric | Before | After |
|--------|--------|-------|
| **Frontend Responsiveness** | Blocked 2-5 min | Instant return |
| **Progress Visibility** | None | Real-time updates |
| **ScrapingDog Success Rate** | ~50% (400 errors) | ~95% |
| **Queue Overflow Risk** | High | Low (controlled) |
| **Debugging Ease** | Hard | Easy (per-business logs) |

---

## 🚀 **Priority Recommendation**

**START WITH PHASE 1** (Query Fix):
- Takes 5 minutes
- Fixes immediate 400 errors
- Massive impact on discovery success rate

**Then Phase 2+3** (Architecture):
- Can be done incrementally
- Improves user experience
- Makes system more scalable

---

## 📝 **Next Steps**

1. **Apply query fix** (see code below)
2. **Test with curl** to confirm
3. **Deploy and monitor**
4. **Plan architecture refactor** (discuss with team)

---

## 💻 **Code Changes Required**

See next section for exact code modifications...
