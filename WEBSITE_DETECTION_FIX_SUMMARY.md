# Website Detection Fix & Re-validation System

**Date:** February 5, 2026  
**Status:** ✅ Complete

## Problem Analysis

### Issue 1: Auto-Generation Running Unchecked
- **Problem:** Auto-generation was running every hour, processing only 5 sites per run
- **Impact:** 162 businesses queued, only 15 processed, 147 stuck in queue
- **Root Cause:** `celery_app.py` had `generate-sites` task scheduled hourly

### Issue 2: Website URLs Not Being Captured
- **Problem:** Outscraper returns website URLs but they weren't being saved
- **Impact:** All 457 businesses show `website_url = NULL` in database
- **Root Cause:** Field name mismatch - code looked for `site` but Outscraper might use `website`, `url`, `domain`, etc.

### Issue 3: Raw Data Not Being Stored
- **Problem:** `raw_data` field was NULL for all businesses
- **Impact:** Cannot reprocess or debug Outscraper responses
- **Root Cause:** `business_service.py` filtered out `raw_data` if it was empty or None

### Issue 4: Insufficient Logging
- **Problem:** No visibility into what Outscraper actually returns
- **Impact:** Cannot debug field name issues
- **Root Cause:** Minimal logging in scraper

## Solutions Implemented

### 1. Disabled Auto-Generation ✅
**File:** `backend/celery_app.py`

```python
# DISABLED: Temporarily disabled until website detection is fixed
# "generate-sites": {
#     "task": "tasks.generation_sync.generate_pending_sites",
#     "schedule": crontab(minute=0),  # Every hour
# },
```

**Impact:** Prevents further incorrect site generation until validation is complete

### 2. Enhanced Website URL Capture ✅
**File:** `backend/services/hunter/scraper.py`

```python
# Try ALL possible website field names from Outscraper
website_url = (
    business.get("website") or
    business.get("site") or
    business.get("url") or
    business.get("domain") or
    business.get("website_url") or
    business.get("business_url") or
    business.get("web") or
    business.get("homepage")
)
```

**Impact:** Captures website URLs regardless of field name variation

### 3. Fixed Raw Data Storage ✅
**File:** `backend/services/hunter/business_service.py`

```python
# Always save raw_data regardless of value
if k == "raw_data":
    business_data[k] = v
    logger.info(f"Saving raw_data: {type(v)}, keys: {list(v.keys())}")
# For other fields, skip if None
elif v is not None:
    business_data[k] = v
```

**Impact:** All Outscraper responses now stored for debugging and reprocessing

### 4. Comprehensive Logging ✅
**File:** `backend/services/hunter/scraper.py`

```python
logger.info(f"Processing business: {business_name}")
logger.info(f"  Available keys: {list(business.keys())}")
logger.info(f"  Website fields check:")
logger.info(f"    - website: {business.get('website')}")
logger.info(f"    - site: {business.get('site')}")
logger.info(f"    - url: {business.get('url')}")
logger.info(f"  Final website_url: {website_url}")
```

**Impact:** Full visibility into Outscraper responses for debugging

### 5. Google Search Verification (Scrapingdog) ✅
**File:** `backend/services/hunter/google_search_service.py`

**Features:**
- Uses Scrapingdog API to search Google for business websites
- Smart domain validation (excludes Yelp, Facebook, directories)
- Rate limiting and error handling
- Batch processing capability
- Business name matching in search results

**Example Usage:**
```python
search_service = GoogleSearchService()
website = await search_service.search_business_website(
    business_name="Joe's Plumbing",
    city="Houston",
    state="TX",
    country="US"
)
```

### 6. Re-validation Script ✅
**File:** `backend/scripts/revalidate_with_google_search.py`

**Features:**
- Finds all businesses without website_url
- Uses Google Search to find missing websites
- Updates database with found URLs
- Marks businesses as "missing" if no website found
- Generates list of businesses truly needing sites

**Usage:**
```bash
# Dry run (no database updates)
python -m scripts.revalidate_with_google_search --limit 50 --dry-run

# Live run for US businesses
python -m scripts.revalidate_with_google_search --all --country US

# Process specific number
python -m scripts.revalidate_with_google_search --limit 100
```

### 7. Business Analysis Script ✅
**File:** `backend/scripts/analyze_us_businesses_needing_sites.py`

**Features:**
- Analyzes all US businesses without websites
- Prioritizes by:
  - Rating (0-50 points)
  - Review count (0-30 points)
  - Location - target states/cities (0-20 points)
  - Category - high-value services (0-10 points)
- Generates ranked list with scoring
- Exports to CSV for manual review
- Statistics by state, category, score distribution

**Usage:**
```bash
# Basic analysis
python -m scripts.analyze_us_businesses_needing_sites

# Export to CSV
python -m scripts.analyze_us_businesses_needing_sites --export-csv

# Custom thresholds
python -m scripts.analyze_us_businesses_needing_sites --min-rating 4.0 --min-reviews 10
```

## Configuration Changes

### Environment Variables Required

Add to `.env`:
```bash
# Scrapingdog API for Google Search
SCRAPINGDOG_API_KEY=your_api_key_here
```

### Config File Updated
**File:** `backend/core/config.py`

```python
SCRAPINGDOG_API_KEY: Optional[str] = None  # For Google search verification
```

## Next Steps

### Immediate Actions (Required)

1. **Add Scrapingdog API Key**
   ```bash
   # On server
   nano /var/www/webmagic/backend/.env
   # Add: SCRAPINGDOG_API_KEY=xxx
   ```

2. **Deploy Changes**
   ```bash
   cd /var/www/webmagic
   git pull origin main
   supervisorctl restart webmagic-celery
   supervisorctl restart webmagic-api
   ```

3. **Test Scraper Logging**
   ```bash
   # Trigger a small scrape to see new logging
   tail -f /var/log/webmagic/celery.log | grep "Available keys"
   ```

4. **Run Re-validation (Dry Run First)**
   ```bash
   cd /var/www/webmagic/backend
   source .venv/bin/activate
   
   # Test with 10 businesses
   PYTHONPATH=/var/www/webmagic/backend python -m scripts.revalidate_with_google_search --limit 10 --dry-run
   
   # If successful, run for all US businesses
   PYTHONPATH=/var/www/webmagic/backend python -m scripts.revalidate_with_google_search --all --country US
   ```

5. **Analyze Results**
   ```bash
   # Generate prioritized list
   PYTHONPATH=/var/www/webmagic/backend python -m scripts.analyze_us_businesses_needing_sites --export-csv
   
   # Review the CSV file
   ls -lh backend/scripts/us_businesses_needing_sites_*.csv
   ```

6. **Verify Database Updates**
   ```sql
   -- Check how many websites were found
   SELECT 
       COUNT(*) FILTER (WHERE website_url IS NOT NULL) as with_website,
       COUNT(*) FILTER (WHERE website_url IS NULL) as without_website,
       COUNT(*) FILTER (WHERE website_validation_status = 'missing') as confirmed_missing
   FROM businesses
   WHERE country = 'US';
   ```

### Follow-up Actions (After Validation)

1. **Review Top 20 Businesses**
   - Check CSV export
   - Verify they truly need websites
   - Confirm target regions and categories

2. **Queue Selective Generation**
   - Only queue businesses with score >= 60
   - Focus on target states first
   - Batch in groups of 10-20

3. **Re-enable Auto-Generation (Carefully)**
   - Uncomment in `celery_app.py`
   - Reduce frequency to every 6 hours
   - Keep limit at 5 per run
   - Monitor closely

## Success Metrics

### Before Fix
- ❌ 162 businesses queued for generation
- ❌ 15 sites generated (9.3%)
- ❌ 147 stuck in queue
- ❌ 457 businesses with NULL website_url
- ❌ 457 businesses with NULL raw_data
- ❌ No visibility into Outscraper responses

### After Fix (Expected)
- ✅ Auto-generation disabled (controlled)
- ✅ All website field names captured
- ✅ Raw data stored for all businesses
- ✅ Comprehensive logging enabled
- ✅ Google Search fallback implemented
- ✅ Accurate list of businesses needing sites
- ✅ Prioritization system in place

### Target Outcomes
- **Website Detection Rate:** 70-80% (from Outscraper + Google Search)
- **Businesses Truly Needing Sites:** ~100-150 (down from 457)
- **High-Priority Businesses:** ~50 (score >= 60)
- **Generation Success Rate:** 95%+ (with proper validation)

## Architecture Improvements

### Two-Tier Website Detection
1. **Primary:** Outscraper GMB data (fast, bulk)
2. **Secondary:** Google Search via Scrapingdog (slower, accurate)

### Data Quality
- All Outscraper responses stored in `raw_data`
- Comprehensive logging for debugging
- Multiple field name attempts for robustness

### Smart Prioritization
- Multi-factor scoring system
- Target region focus
- High-value category focus
- Quality thresholds (rating, reviews)

### Controlled Generation
- Manual triggering preferred
- Batch processing (5-10 at a time)
- Validation before generation
- Monitoring and logging

## Best Practices Applied

✅ **Defensive Programming:** Try multiple field names, handle None/empty  
✅ **Comprehensive Logging:** Log all inputs, decisions, outputs  
✅ **Idempotency:** Scripts can be run multiple times safely  
✅ **Rate Limiting:** Respect API limits (1 req/sec for Scrapingdog)  
✅ **Error Handling:** Graceful degradation, retry logic  
✅ **Data Preservation:** Store raw data for reprocessing  
✅ **Dry Run Mode:** Test before making changes  
✅ **Prioritization:** Focus on high-value targets first  
✅ **Documentation:** Clear comments, usage examples  
✅ **Separation of Concerns:** Dedicated services for each function

## Files Changed

### Modified
- `backend/celery_app.py` - Disabled auto-generation
- `backend/services/hunter/scraper.py` - Enhanced URL capture, logging
- `backend/services/hunter/business_service.py` - Fixed raw_data storage
- `backend/core/config.py` - Added SCRAPINGDOG_API_KEY

### Created
- `backend/services/hunter/google_search_service.py` - Google Search via Scrapingdog
- `backend/scripts/revalidate_with_google_search.py` - Re-validation script
- `backend/scripts/analyze_us_businesses_needing_sites.py` - Business analysis

### Documentation
- `WEBSITE_DETECTION_FIX_SUMMARY.md` - This file

---

**Status:** ✅ All code changes complete, ready for deployment and testing  
**Next:** Deploy to server, add API key, run re-validation

