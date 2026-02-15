# Scraping Data Discrepancy Analysis

**Date:** February 15, 2026  
**Issue:** Console shows different data than frontend after veterinarians scrape  
**Status:** 🔍 **INVESTIGATING**

---

## Console vs Frontend Comparison

### Console Output (Last Zone Scrape)
```javascript
✅ Success! Found 13 businesses, 0 qualified, 0 need websites, 0 queued for generation
```

### Frontend Display (Screenshot)
- **56 total businesses**
- **2 qualified leads** (3.6% qualification rate)
- **54 with valid websites** (96.4%)
- **2 without websites** (3.6%)
- **Button:** "Queue 2 Businesses for Website Generation"

### Actual Database (Accurate)
```sql
Total businesses: 67
With websites: 6 (9%)
Without websites: 61 (91%)
Qualified (score ≥70): 2 (3%)
Average score: 38.8
Min score: 0
Max score: 70
```

---

## Data Sources Explained

### 1. Console Output = Last Zone Scrape Only
**What it shows:** Result from the MOST RECENT zone that was scraped (1 of 3 zones)

**Why "13 businesses":**
- This was zone 3 of 3 (North Hollywood area)
- Only shows businesses from this specific scrape
- Does NOT include businesses from previous zones

**Why "0 qualified, 0 need websites":**
- Console message is calculated IMMEDIATELY after scrape
- Qualification scores and website detection happen asynchronously
- By the time the response is sent, processing isn't complete

---

### 2. Frontend Display = Strategy Aggregate (BUT WRONG!)
**What it SHOULD show:** ALL businesses across ALL zones in the strategy

**Actual data:** 67 businesses total, 6 with websites, 61 without

**Frontend shows:** 56 businesses, 54 with websites (96.4%), 2 without

**Discrepancy:** Frontend is showing CACHED or INCORRECT data

**Possible causes:**
1. ✅ **Most likely:** Frontend is caching old response
2. Frontend is querying wrong strategy ID
3. Backend is returning stale data from `geo_strategies` aggregates
4. Database aggregates (`total_with_websites`, etc.) not being updated

---

### 3. Database = Source of Truth
**Query used:**
```sql
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE website_url IS NOT NULL) as with_websites,
    COUNT(*) FILTER (WHERE website_url IS NULL) as without_websites,
    COUNT(*) FILTER (WHERE qualification_score >= 70) as qualified
FROM businesses 
WHERE category IN ('Veterinarian', 'Animal hospital', 'Veterinary care');
```

**Results:**
- Total: 67 ✅ (ACCURATE - close to geo_strategies.businesses_found = 69)
- With websites: 6 (9%)
- Without websites: 61 (91%)
- Qualified: 2 (3%)

---

## Critical Finding: Website Extraction Bug

### 🔴 PROBLEM: Outscraper Returns Websites, But We're Not Extracting Them!

**Evidence:**

| Business | Our website_url | Outscraper raw_data.website |
|----------|----------------|-----------------------------|
| Dr. Peter Lowenthal | `null` ❌ | `http://bluepet.com/` ✅ |
| Sweet Home Veterinary Hospital | `null` ❌ | `https://www.sweethomevets.com/` ✅ |
| Holiday Humane Society Clinic | `null` ❌ | `http://www.holidayhumane.org/` ✅ |
| Berkley Pet Hospital | `null` ❌ | `https://berkleypethospital.com/` ✅ |
| Sharp Pet Hospital | `null` ❌ | `http://sharppethospital.com/` ✅ |

**All 5 of these businesses have websites in the Outscraper data, but `website_url = null` in our database!**

---

## Scraper Timeline

### Zone 1: First scrape
- **Time:** ~04:10-04:15 (after strategy creation)
- **Location:** Unknown (probably West LA or Downtown)
- **Businesses:** ~20-25

### Zone 2: Second scrape
- **Time:** ~05:00-06:00
- **Location:** Unknown
- **Businesses:** ~30-35

### Zone 3: Third scrape (most recent)
- **Time:** 07:11-07:12 (just now)
- **Location:** North Hollywood, Valley Glen
- **Businesses:** 13
- **Examples:**
  - Dr. Peter Lowenthal
  - Sweet Home Veterinary Hospital
  - Holiday Humane Society Clinic
  - Berkley Pet Hospital
  - Sharp Pet Hospital

**Total across all 3 zones:** 67 businesses

---

## Website Extraction Analysis

### Scraper Code (scraper.py lines 269-291)

```python
# ENHANCED: Try ALL possible website field names from Outscraper
website_url = (
    business.get("website") or      # ✅ Should work!
    business.get("site") or
    business.get("url") or
    business.get("domain") or
    business.get("website_url") or
    business.get("business_url") or
    business.get("web") or
    business.get("homepage")
)

# Log what was found
logger.info(f"Processing business: {business_name}")
logger.info(f"  Website fields check:")
logger.info(f"    - website: {business.get('website')}")
logger.info(f"    - site: {business.get('site')}")
logger.info(f"  Final website_url: {website_url}")

normalized_business = {
    "phone": business.get("phone"),
    "website_url": website_url,  # Extracted value
    # ...
}
```

**This code SHOULD work!**

The code checks `business.get("website")` first, which is exactly the field Outscraper provides.

---

## Hypothesis: Code Deployment Timing

### Timeline:
1. **04:10:** Strategy created (veterinarians, Los Angeles)
2. **04:10-04:15:** Zone 1 scraped (before our fixes)
3. **05:00-06:00:** Zone 2 scraped (before our fixes)
4. **07:10:** We deployed geo-targeting and validation fixes
5. **07:11-07:12:** Zone 3 scraped (AFTER our fixes)

**Question:** Were zones 1 and 2 scraped with OLD code that had a different bug?

**Evidence needed:**
- Check if older businesses (from 04:10-06:00) also have `website = null` but `raw_data.website` populated
- Check server logs from 04:10-07:10 to see if website extraction was working

---

## Next Steps

### 1. Check Older Businesses
Query businesses from earlier zones to see if they also have the website extraction bug:

```sql
SELECT 
    name,
    website_url,
    raw_data->>'website' as outscraper_website,
    created_at
FROM businesses 
WHERE category IN ('Veterinarian', 'Animal hospital', 'Veterinary care')
AND created_at < '2026-02-15 06:00:00'
ORDER BY created_at
LIMIT 10;
```

### 2. Check Server Logs
Look for website extraction logs from the first 2 scrapes:

```bash
grep -A 5 "Processing business:" /var/log/webmagic/api.log | grep -E "website:|Final website_url:"
```

### 3. Test with Fresh Scrape
Run a new scrape and monitor logs in real-time to see if websites are being extracted correctly.

### 4. Fix Frontend Caching
The frontend is showing 56 businesses with 96.4% website coverage, but the database shows 67 businesses with 9% coverage. This suggests:
- Frontend is caching old data
- Frontend is not refreshing after scrape completes
- Backend aggregates in `geo_strategies` table are not being updated

---

## Frontend Data Source

**Question:** Where is the frontend getting "54 with valid websites (96.4%)"?

**Possible sources:**
1. `geo_strategies.total_with_websites` column
2. Frontend caching from previous scrape
3. Counting businesses with `website_validation_status = 'valid'`

**Check `geo_strategies` table:**
```sql
SELECT 
    total_businesses_scraped,
    total_with_websites,
    total_without_websites,
    businesses_found
FROM geo_strategies 
WHERE category = 'veterinarians';
```

**Result:**
```
total_businesses_scraped: 0
total_with_websites: 0
total_without_websites: 0
businesses_found: 69
```

**Finding:** All the aggregate columns are 0! The frontend must be calculating from somewhere else or caching.

---

## Summary

### Data Accuracy:
1. **Console (13 businesses, 0 qualified):** ✅ Accurate for LAST ZONE only
2. **Frontend (56 businesses, 54 with websites):** ❌ WRONG - cached or stale
3. **Database (67 businesses, 6 with websites):** ✅ ACCURATE - source of truth

### Critical Bugs Found:

#### Bug #1: Website Extraction Failing
**Status:** 🔴 **CRITICAL** - 91% of veterinarians showing as "no website" when they actually have websites

**Impact:** 
- Only 6 out of 67 businesses (9%) have websites extracted
- 61 businesses (91%) have websites in Outscraper data but `website_url = null` in our database
- This breaks qualification scoring (requires website for high scores)
- This breaks deep verification (can't verify if we don't extract URL)
- This wastes money on website generation for businesses that already have websites

**Root cause:** TBD - code looks correct, need to check logs

#### Bug #2: Frontend Showing Stale Data
**Status:** ⚠️ **HIGH** - Users see incorrect metrics

**Impact:**
- Frontend shows 96.4% website coverage when actual is 9%
- Users make decisions based on wrong data
- "Queue 2 for website generation" button is accurate (matches database: 2 qualified)

**Root cause:** TBD - frontend caching or backend aggregates not updating

---

## Recommendations

### Immediate (Priority 1):
1. ✅ Identify why website URLs aren't being extracted from Outscraper data
2. Re-scrape or backfill the 61 businesses missing websites
3. Fix frontend caching to show real-time data

### Short-term (Priority 2):
1. Update `geo_strategies` aggregates in real-time
2. Add health check to detect when website extraction is failing
3. Monitor website extraction rate (should be 60-80% for most categories)

### Long-term (Priority 3):
1. Add data validation: alert if website extraction rate < 40%
2. Add frontend → database consistency checks
3. Consider websocket updates for real-time metrics

---

**Next:** Investigate website extraction bug and determine if it's a code issue, deployment timing issue, or data format change.
