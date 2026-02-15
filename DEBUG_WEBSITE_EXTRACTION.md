# Debug Website Extraction Issue

**Date:** February 15, 2026  
**Issue:** 91% of websites not being extracted (62 in raw_data, only 6 in website_url)  
**Status:** 🔴 **CRITICAL**

---

## Summary

**Confirmed Data:**
- 67 veterinarians scraped
- 62 have websites in `raw_data.website` (92%)
- Only 6 have `website_url` populated (9%)
- **56 websites lost during processing!**

**Example:**
```sql
Business: Sharp Pet Hospital
website_url: null
raw_data.website: "http://sharppethospital.com/" (28 chars)
```

---

## Debugging Steps

### Step 1: Check if logging is working

SSH into server and check log level:

```bash
ssh root@104.251.211.183
cd /var/www/webmagic/backend

# Check if DEBUG logs are enabled
grep -n "DEBUG" /var/log/webmagic/api.log | tail -5

# If no DEBUG logs, we need to enable them
```

### Step 2: Enable DEBUG logging temporarily

Edit uvicorn config or logging config to enable DEBUG level.

```bash
# Check current log level
cat core/logging_config.py | grep level

# Or check environment
env | grep LOG
```

### Step 3: Run test scrape with monitoring

```bash
# In one terminal, tail logs
tail -f /var/log/webmagic/api.log | grep -E "Processing business:|website field:|Final website_url:|Website detection|HTTP"

# In browser, trigger a scrape for a NEW zone
```

### Step 4: Analyze specific business

After scrape completes, search logs for a specific business that should have a website:

```bash
grep -A 30 "Processing business: [Business Name]" /var/log/webmagic/api.log | tail -50
```

Look for:
- `Processing business: X`
- `Website fields check:`
- `Final website_url: X`
- `Website detection -`
- `HTTP result:`

---

## Code Analysis

### Scraper Normalization (scraper.py:270-301)

```python
# ENHANCED: Try ALL possible website field names from Outscraper
website_url = (
    business.get("website") or      # ← Should get "http://sharppethospital.com/"
    business.get("site") or
    business.get("url") or
    # ... other fallbacks
)

# COMPREHENSIVE LOGGING
logger.info(f"Processing business: {business_name}")
logger.info(f"  Website fields check:")
logger.info(f"    - website: {business.get('website')}")  # ← Should log the URL
logger.info(f"  Final website_url: {website_url}")      # ← Should log the URL

normalized_business = {
    "website_url": website_url,  # ← Should be populated
    "raw_data": business         # ← Contains original with 'website' field
}
```

**Expected log output:**
```
Processing business: Sharp Pet Hospital
  Website fields check:
    - website: http://sharppethospital.com/
  Final website_url: http://sharppethospital.com/
```

**If this logs correctly, the scraper is working! The bug is later in the pipeline.**

---

### Data Quality Service (data_quality_service.py:193-268)

```python
def detect_website(self, business: Dict[str, Any]) -> Dict[str, Any]:
    raw_data = business.get("raw_data", {})
    
    # Primary: Check website field
    website = raw_data.get("website")
    logger.debug(f"  ├─ website field: {website}")  # ← DEBUG level!
    
    if website and isinstance(website, str) and len(website) > 10:
        return {
            "has_website": True,
            "website_url": website,  # ← Should return URL
            ...
        }
    
    # No online presence found
    return {
        "has_website": False,
        "website_url": None,  # ← This might be the problem!
        ...
    }
```

**Possible bug:** If `website` field doesn't pass validation (wrong type, too short, etc.), returns `None` and overwrites the scraped URL!

---

### Hunter Service (hunter_service.py:252-278)

```python
# Get website URL from detection or fallback to biz_data
website_url = website_detection.get("website_url") or biz_data.get("website_url")
#             ↑ If this is None                    ↑ This should be fallback

if website_url:
    # HTTP validation
    simple_validation = await website_validator.validate_url(website_url)
    
    if simple_validation.is_valid or simple_validation.is_real_website:
        biz_data["website_validation_status"] = "pending"
        biz_data["website_url"] = website_url  # ← Keep URL
    else:
        biz_data["website_validation_status"] = "needs_verification"
        biz_data["website_url"] = website_url  # ← Keep URL (changed in our fix)
else:
    biz_data["website_validation_status"] = "missing"
    # ← website_url stays as whatever it was (null?)
```

---

## Hypothesis: The Bug

### Theory #1: data_quality_service returns None, overrides scraper
1. Scraper extracts: `website_url = "http://sharppethospital.com/"`
2. Stores in: `biz_data["website_url"] = "http://..."`
3. AND stores in: `biz_data["raw_data"]["website"] = "http://..."`
4. Hunter calls: `website_detection = data_quality_service.detect_website(biz_data)`
5. Data quality checks: `raw_data.get("website")` → **Something goes wrong here**
6. Returns: `{"has_website": False, "website_url": None}`
7. Hunter line 252: `website_url = None or biz_data.get("website_url")`  
   → **Should fallback to biz_data, but maybe biz_data["website_url"] was already cleared?**

### Theory #2: biz_data structure issue
Maybe `biz_data` from the scraper doesn't have `website_url` at the top level when it reaches hunter_service?

Check normalized_business structure in scraper.py line 293-328.

### Theory #3: Async timing issue
Maybe the website_url gets set, but then cleared by a later operation before saving to database?

---

## Diagnostic Query

Check if ANY businesses have BOTH website_url AND raw_data.website:

```sql
SELECT 
    name,
    website_url,
    raw_data->>'website' as raw_website,
    website_validation_status
FROM businesses 
WHERE category IN ('Veterinarian', 'Animal hospital', 'Veterinary care')
AND website_url IS NOT NULL
AND raw_data->>'website' IS NOT NULL;
```

**Expected:** 6 rows (the ones that worked)

Then check if the working ones have anything in common (specific validation status, specific format, etc.)

---

## Quick Test Script

Create `/tmp/test_website_extraction.py`:

```python
# Test if data_quality_service.detect_website works correctly

business_data = {
    "name": "Test Vet",
    "website_url": "http://testvet.com/",
    "raw_data": {
        "name": "Test Vet",
        "website": "http://testvet.com/",
        "phone": "+1 555-1234"
    }
}

from services.hunter.data_quality_service import DataQualityService

dq = DataQualityService()
result = dq.detect_website(business_data)

print(f"Result: {result}")
# Expected: {'has_website': True, 'website_url': 'http://testvet.com/', ...}
```

Run:
```bash
cd /var/www/webmagic/backend
python3 /tmp/test_website_extraction.py
```

---

## Resolution Plan

Once we identify where websites are being lost:

### If scraper is the problem:
- Fix website extraction logic
- Re-scrape all zones

### If data_quality_service is the problem:
- Fix detect_website validation logic
- Backfill website_url from raw_data for existing businesses

### If hunter_service is the problem:
- Fix the website_url assignment logic
- Backfill from raw_data

### Backfill Script (once bug is fixed):

```sql
-- Update businesses that have website in raw_data but not in website_url
UPDATE businesses 
SET 
    website_url = raw_data->>'website',
    website_validation_status = 'pending',
    updated_at = NOW()
WHERE 
    category IN ('Veterinarian', 'Animal hospital', 'Veterinary care')
    AND website_url IS NULL
    AND raw_data->>'website' IS NOT NULL
    AND LENGTH(raw_data->>'website') > 10;

-- Check how many would be updated
SELECT COUNT(*) 
FROM businesses 
WHERE 
    category IN ('Veterinarian', 'Animal hospital', 'Veterinary care')
    AND website_url IS NULL
    AND raw_data->>'website' IS NOT NULL;
```

Expected: ~56 businesses

---

## Next Steps

1. **Enable DEBUG logging** on the server
2. **Run ONE test scrape** for a new zone (not veterinarians - try a different category)
3. **Monitor logs** in real-time during scrape
4. **Check database** immediately after scrape
5. **Identify** which step is losing the websites
6. **Fix** the bug
7. **Backfill** the 56 lost websites for veterinarians
8. **Re-test** with fresh scrape

---

**Priority:** 🔴 **CRITICAL** - This affects 91% of data quality!

