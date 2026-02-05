# Website Validation Workflow Integration

## 🎯 Architecture Overview

We now have a **two-tier validation system** that balances speed and accuracy:

### Tier 1: Simple HTTP Validation (During Scraping)
- **When**: During Outscraper business scraping
- **Speed**: ~100ms per business
- **Purpose**: Filter out obviously bad URLs
- **Technology**: Simple HTTP HEAD/GET requests
- **Rejects**:
  - Social media profiles (Facebook, Instagram, LinkedIn, etc.)
  - Google Maps redirects
  - Directory listings (Yelp, YellowPages, etc.)
  - Invalid URL formats

### Tier 2: Deep Playwright Validation (After Scraping)
- **When**: Asynchronously after businesses are saved
- **Speed**: ~4-5 seconds per business
- **Purpose**: Deep content analysis and quality scoring
- **Technology**: Playwright headless browser with stealth
- **Extracts**:
  - Contact information (phone, email, address)
  - Business hours
  - Content quality metrics
  - Quality score (0-100)
  - Placeholder detection

## 🔄 Complete Workflow

```
┌─────────────────────────────────────────────────────────┐
│  1. SCRAPING (Outscraper)                               │
│     Get businesses from Google Maps                     │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  2. SIMPLE VALIDATION (Fast - 100ms)                    │
│     ✅ Valid HTML website → PASS (status=pending)       │
│     ❌ Social media → REJECT (status=invalid)           │
│     ❌ Google redirect → REJECT (status=invalid)        │
│     ❌ No URL → SKIP (status=no_website)                │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  3. QUALIFICATION & SAVE                                │
│     Calculate lead score, save to database              │
│     Collect business IDs that passed simple validation  │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  4. QUEUE DEEP VALIDATION (Async)                       │
│     Batch businesses (10 per task)                      │
│     Queue Celery tasks for Playwright validation        │
│     → Scraping completes here (FAST!)                   │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼ (Asynchronous in background)
┌─────────────────────────────────────────────────────────┐
│  5. PLAYWRIGHT VALIDATION (Slow - 4-5s per business)    │
│     Launch headless browser with stealth                │
│     Extract contact info, analyze content               │
│     Calculate quality score                             │
│     Update business.website_validation_result           │
│     Update business.website_validation_status           │
└─────────────────────────────────────────────────────────┘
```

## ⚙️ Configuration

All validation settings are in `backend/core/config.py`:

```python
# Enable/disable auto-validation after scraping
ENABLE_AUTO_VALIDATION: bool = True

# Max businesses per validation batch (controls queue size)
VALIDATION_BATCH_SIZE: int = 10

# Disable screenshots for performance
VALIDATION_CAPTURE_SCREENSHOTS: bool = False

# Timeout per website (milliseconds)
VALIDATION_TIMEOUT_MS: int = 30000  # 30 seconds
```

### Environment Variables

Add to `.env` file (optional - defaults shown above):

```bash
# Validation Configuration
ENABLE_AUTO_VALIDATION=true
VALIDATION_BATCH_SIZE=10
VALIDATION_CAPTURE_SCREENSHOTS=false
VALIDATION_TIMEOUT_MS=30000
```

## 📊 Database Schema

### Business Fields

```sql
-- Simple validation status (set during scraping)
website_validation_status VARCHAR(30)
  -- Values: pending, valid, invalid, no_website, error

-- Deep validation result (JSONB, set by Playwright)
website_validation_result JSONB
  -- Contains: quality_score, phones, emails, has_contact_info, etc.

-- Validation timestamp
website_validated_at TIMESTAMP

-- Screenshot URL (optional - currently disabled)
website_screenshot_url TEXT
```

## 🔍 Validation Status Flow

```
┌──────────────┐
│   Scraping   │
└──────┬───────┘
       │
       ▼
  Has Website?
       │
    ┌──┴──┐
    NO    YES
    │     │
    ▼     ▼
no_website  Simple Check
            │
         ┌──┴──┐
      PASS   FAIL
       │      │
       ▼      ▼
   pending  invalid
       │
       ▼
  Queue Deep
  Validation
       │
       ▼
┌──────────────┐
│  Playwright  │
│  Validation  │
└──────┬───────┘
       │
    ┌──┴──┐
   PASS  FAIL
    │     │
    ▼     ▼
  valid  invalid
```

## 🚀 Performance Impact

### Before (Blocking Validation)
```
Scrape 100 businesses
├─ Outscraper API: ~5s
├─ Simple validation: 100 * 0.1s = 10s
└─ Deep validation: 100 * 4s = 400s  ❌ BLOCKS SCRAPING
─────────────────────────────────────
Total: 415 seconds (7 minutes)
```

### After (Async Validation)
```
Scrape 100 businesses
├─ Outscraper API: ~5s
├─ Simple validation: 100 * 0.1s = 10s
├─ Save & queue: ~1s
└─ Deep validation: ASYNC (doesn't block) ✅
─────────────────────────────────────
Total scraping: 16 seconds
Deep validation: Happens in background via Celery
```

**Result: ~25x faster scraping!** 🎉

## 📝 Code Examples

### Triggering Validation Manually

```python
from tasks.validation_tasks import validate_business_website

# Validate a single business
task = validate_business_website.delay("business-uuid-here")
print(f"Queued validation: {task.id}")
```

### Batch Validation

```python
from tasks.validation_tasks import batch_validate_websites

# Validate multiple businesses
business_ids = ["uuid-1", "uuid-2", "uuid-3"]
task = batch_validate_websites.delay(business_ids)
```

### Checking Validation Results

```python
from models.business import Business
from core.database import get_sync_db

db = next(get_sync_db())
business = db.query(Business).filter(Business.id == "uuid").first()

print(f"Status: {business.website_validation_status}")
print(f"Quality Score: {business.website_validation_result.get('quality_score')}")
print(f"Has Phone: {business.website_validation_result.get('has_phone')}")
print(f"Has Email: {business.website_validation_result.get('has_email')}")
```

## 🧪 Testing

### Test Simple Validation

```bash
cd /var/www/webmagic/backend
source .venv/bin/activate
python scripts/test_validation_workflow.py
```

Expected output:
```
🔍 Testing Simple Validation (Used During Scraping)
============================================================

✅ PASS - Valid site
  URL: https://example.com
  Valid: True
  Real Website: True

❌ REJECT - Social media (should reject)
  URL: https://facebook.com/somebusiness
  Valid: False
  Real Website: False
  Reason: Social media or directory listing, not a real website
```

### Test Playwright Validation

```bash
python scripts/test_playwright_validation.py
```

## 🔧 Celery Worker Configuration

Make sure the validation queue is enabled:

```bash
# Check current workers
supervisorctl status

# Update celery worker config
nano /etc/supervisor/conf.d/webmagic.conf

# Add validation to queue list:
command=/var/www/webmagic/backend/.venv/bin/celery -A celery_app worker \
  -Q celery,generation,scraping,campaigns,monitoring,validation \
  --loglevel=info

# Reload supervisor
supervisorctl reread
supervisorctl update
supervisorctl restart webmagic-celery
```

## 📈 Monitoring

### Check Validation Queue

```bash
# In Python/iPython
from celery_app import celery_app
inspect = celery_app.control.inspect()

# See queued validation tasks
inspect.active_queues()

# See running validation tasks
inspect.active()
```

### Check Validation Stats

```bash
curl "https://web.lavish.solutions/api/v1/validation/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response:
```json
{
  "total_businesses": 500,
  "total_with_websites": 350,
  "pending": 50,
  "valid": 200,
  "invalid": 100,
  "no_website": 150,
  "error": 0
}
```

## 🎛️ Disabling Auto-Validation

If you want to disable automatic validation after scraping:

```bash
# In .env file
ENABLE_AUTO_VALIDATION=false
```

Then trigger validation manually:

```bash
curl -X POST "https://web.lavish.solutions/api/v1/validation/validate-all-pending" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔒 Security & Best Practices

1. **Rate Limiting**: Validation is batched (10 per task) to avoid overwhelming target websites
2. **Timeouts**: Each validation has a 30-second timeout to prevent hanging
3. **Error Handling**: Failures don't crash scraping - they're logged and retried
4. **Resource Management**: Playwright processes are properly cleaned up
5. **Bot Detection**: Stealth measures in place to avoid being blocked
6. **No Screenshots**: Disabled by default to save resources and speed up validation

## 🐛 Troubleshooting

### Validation Tasks Not Running

```bash
# Check if validation queue is active
supervisorctl status webmagic-celery

# Check celery logs
tail -f /var/log/webmagic/celery.log | grep validation
```

### High Validation Queue

```bash
# Check queue size
celery -A celery_app inspect active_queues

# Temporarily increase batch size in .env
VALIDATION_BATCH_SIZE=20

# Or disable auto-validation
ENABLE_AUTO_VALIDATION=false
```

### Validation Timing Out

```bash
# Increase timeout in .env (milliseconds)
VALIDATION_TIMEOUT_MS=60000  # 60 seconds
```

## 📚 Related Documentation

- [PLAYWRIGHT_VALIDATION_DESIGN.md](./PLAYWRIGHT_VALIDATION_DESIGN.md) - Complete system architecture
- [PLAYWRIGHT_SETUP_INSTRUCTIONS.md](./PLAYWRIGHT_SETUP_INSTRUCTIONS.md) - Installation guide
- [PLAYWRIGHT_IMPLEMENTATION_SUMMARY.md](./PLAYWRIGHT_IMPLEMENTATION_SUMMARY.md) - Implementation details

## ✅ Summary

**The validation workflow is now optimized for performance:**

✅ **Fast scraping** - Simple validation doesn't block (100ms per business)  
✅ **Deep analysis** - Playwright validation runs asynchronously in background  
✅ **No screenshots** - Disabled for performance (user requested)  
✅ **Configurable** - Enable/disable via environment variables  
✅ **Scalable** - Batched processing prevents queue overwhelm  
✅ **Reliable** - Comprehensive error handling and retries  

**This architecture ensures scraping stays fast while still providing comprehensive website validation!** 🚀

