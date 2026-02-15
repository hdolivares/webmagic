# Monitoring Commands for Debug Scrape

**DEBUG Logging: ✅ ENABLED**  
**Ready to test scrape!**

---

## Before You Start Scraping

### Open SSH Terminal for Live Monitoring

```bash
ssh root@104.251.211.183
cd /var/www/webmagic/backend
```

---

## Real-Time Log Monitoring

### Monitor Website Extraction (MOST IMPORTANT)

```bash
tail -f /var/log/webmagic/api.log | grep -E "Processing business:|website field:|Final website_url:|Website detection|has_website"
```

**What to look for:**
```
Processing business: Sharp Pet Hospital
  Available keys: [...]
  Website fields check:
    - website: http://sharppethospital.com/    ← Should see URL here
  Final website_url: http://sharppethospital.com/  ← Should see URL here
```

**If you see:**
- `Final website_url: http://...` ✅ Scraper is extracting correctly
- `Final website_url: None` ❌ Scraper is NOT extracting

---

### Monitor Full Scraping Pipeline

```bash
tail -f /var/log/webmagic/api.log | grep -E "Outscraper query:|Processing business:|Geo-validation|HTTP|DEEP VERIFICATION|LLM VERIFIED"
```

**What to look for:**
```
Outscraper query: veterinarians, Los Angeles, CA, USA
Outscraper API call: region=US, language=en
Processing business: VCA Animal Hospital
  ✅ Geo-validation PASSED
  🌐 Quick HTTP check: http://vcahospitals.com/
  ✅ HTTP PASS → Will validate with Playwright
```

---

### Monitor Data Quality Service

```bash
tail -f /var/log/webmagic/api.log | grep -E "Website detection|detect_website|has_website|website_type"
```

**What to look for:**
```
🔍 Website detection - raw_data has 50 keys
  ├─ website field: http://example.com/
  └─ ✅ Found website (primary): http://example.com/
```

**If you see:**
- `└─ ✅ Found website` ✅ Data quality service working
- `└─ ❌ No website found` ❌ Data quality service failed validation

---

### Monitor Specific Business

After scrape, search for a specific business:

```bash
grep -A 50 "Processing business: [Business Name]" /var/log/webmagic/api.log | tail -70
```

Example:
```bash
grep -A 50 "Processing business: Sharp Pet Hospital" /var/log/webmagic/api.log | tail -70
```

---

## After Scrape - Database Verification

### Check if websites were extracted

```sql
-- Connect to database
psql webmagic

-- Check latest scraped businesses
SELECT 
    name,
    website_url,
    raw_data->>'website' as raw_website,
    website_validation_status,
    created_at
FROM businesses 
WHERE created_at > NOW() - INTERVAL '10 minutes'
ORDER BY created_at DESC
LIMIT 10;
```

**Expected:**
- `website_url` should match `raw_website`
- If `website_url` is NULL but `raw_website` has a URL → **BUG CONFIRMED**

---

### Count extraction success rate

```sql
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE website_url IS NOT NULL) as extracted,
    COUNT(*) FILTER (WHERE raw_data->>'website' IS NOT NULL) as in_raw_data,
    ROUND(100.0 * COUNT(*) FILTER (WHERE website_url IS NOT NULL) / NULLIF(COUNT(*), 0), 1) as extraction_rate
FROM businesses 
WHERE created_at > NOW() - INTERVAL '10 minutes';
```

**Target:** extraction_rate should be 60-80% (some businesses legitimately have no website)

---

## Debug-Level Log Examples

### Successful Website Extraction

```
2026-02-15 07:30:15 - services.hunter.scraper - INFO - Processing business: Pet Hospital
2026-02-15 07:30:15 - services.hunter.scraper - INFO -   Available keys: ['name', 'website', 'phone', ...]
2026-02-15 07:30:15 - services.hunter.scraper - INFO -   Website fields check:
2026-02-15 07:30:15 - services.hunter.scraper - INFO -     - website: http://pethospital.com/
2026-02-15 07:30:15 - services.hunter.scraper - INFO -     - site: None
2026-02-15 07:30:15 - services.hunter.scraper - INFO -   Final website_url: http://pethospital.com/
2026-02-15 07:30:15 - services.hunter.data_quality_service - DEBUG - 🔍 Website detection - raw_data has 45 keys
2026-02-15 07:30:15 - services.hunter.data_quality_service - DEBUG -   ├─ website field: http://pethospital.com/
2026-02-15 07:30:15 - services.hunter.data_quality_service - DEBUG -   └─ ✅ Found website (primary): http://pethospital.com/
2026-02-15 07:30:15 - services.hunter.hunter_service - INFO -   ├─ 🌐 Quick HTTP check: http://pethospital.com/
2026-02-15 07:30:16 - services.hunter.hunter_service - INFO -   │  └─ ✅ HTTP PASS → Will validate with Playwright
```

### Failed Website Extraction (Bug)

```
2026-02-15 07:30:15 - services.hunter.scraper - INFO - Processing business: Pet Hospital
2026-02-15 07:30:15 - services.hunter.scraper - INFO -   Final website_url: http://pethospital.com/  ← EXTRACTED!
2026-02-15 07:30:15 - services.hunter.data_quality_service - DEBUG - 🔍 Website detection - raw_data has 45 keys
2026-02-15 07:30:15 - services.hunter.data_quality_service - DEBUG -   ├─ website field: None  ← LOST!
2026-02-15 07:30:15 - services.hunter.data_quality_service - DEBUG -   └─ ❌ No website found in any field  ← BUG!
2026-02-15 07:30:15 - services.hunter.hunter_service - INFO -   ├─ 🚫 No website URL → Will search with ScrapingDog
```

This would indicate the bug is between scraper normalization and data_quality_service.

---

## Quick Commands

### Clear old logs (optional)
```bash
> /var/log/webmagic/api.log
echo "Logs cleared"
```

### Check service status
```bash
supervisorctl status
```

### Restart if needed
```bash
supervisorctl restart webmagic-api
```

### Disable DEBUG logging after testing
```bash
cd /var/www/webmagic/backend
sed -i 's/DEBUG=true/DEBUG=false/' .env
sed -i 's/ --log-level debug//' /etc/supervisor/conf.d/webmagic-api.conf
supervisorctl restart webmagic-api
```

---

## Test Scrape Recommendations

### Option 1: Scrape a NEW zone (veterinarians)
- **Pro:** Fresh data, can see full extraction pipeline
- **Con:** Uses more Outscraper credits

### Option 2: Scrape a DIFFERENT category (small test)
- **Pro:** Won't pollute veterinarians data
- **Con:** Different category might have different field structure

**Recommended:** Scrape one more veterinarians zone to see if the bug is consistent

---

## What to Report Back

After your test scrape, share:

1. **Did you see website URLs in the logs?**
   - `Final website_url: http://...` (from scraper)
   - `website field: http://...` (from data_quality_service)

2. **Database query results:**
   ```sql
   SELECT 
       name,
       website_url,
       raw_data->>'website' as raw_website
   FROM businesses 
   WHERE created_at > NOW() - INTERVAL '10 minutes'
   LIMIT 5;
   ```

3. **Any errors in logs:**
   ```bash
   tail -100 /var/log/webmagic/api_error.log
   ```

---

**STATUS:** ✅ Ready to test!  
**Next:** Run a test scrape and monitor logs in real-time

