# Validation System V2 - Deployment Guide

## 🎯 Overview

This is a **complete rewrite** of the website validation system with proper architecture, metadata tracking, and ScrapingDog discovery pipeline.

### **What's New**

✅ **Proper ScrapingDog Triggering** - Triggers when Outscraper URLs are rejected  
✅ **Complete Audit Trail** - Full validation history and discovery attempts  
✅ **URL Source Tracking** - Know where each URL came from  
✅ **Enhanced States** - Clear, actionable validation states  
✅ **Modular Design** - Separation of concerns, testable code  
✅ **Invalid Reason Tracking** - Categorize why URLs are rejected  

---

## 📁 New Files Created

### **Core**
- **`backend/core/validation_enums.py`** - Centralized enums and constants
  - ValidationState enum (pending, valid_outscraper, needs_discovery, etc.)
  - ValidationRecommendation enum (keep_url, trigger_scrapingdog, etc.)
  - URLSource enum (outscraper, scrapingdog, manual)
  - InvalidURLReason enum (directory, technical, mismatch)
  - Domain categorization helpers

### **Services**
- **`backend/services/validation/validation_metadata_service.py`** - Metadata management
  - ValidationHistoryEntry dataclass
  - DiscoveryAttempt dataclass
  - WebsiteMetadata dataclass
  - ValidationMetadataService (CRUD operations)

### **Tasks**
- **`backend/tasks/validation_tasks_enhanced.py`** - Enhanced validation flow
  - validate_business_website_v2() - Main validation task
  - Proper recommendation handling
  - Metadata tracking
  - ScrapingDog triggering logic

- **`backend/tasks/discovery_tasks.py`** - Discovery pipeline
  - discover_missing_websites_v2() - ScrapingDog search
  - Metadata tracking
  - Status management

### **Database**
- **`backend/migrations/013_add_website_metadata.sql`** - Migration script
  - Adds `website_metadata` JSONB field
  - Creates GIN index for performance
  - Backfills existing businesses

### **Modified Files**
- **`backend/models/business.py`** - Added helper methods
  - `url_source` property
  - `has_valid_website` property
  - `needs_discovery` property
  - `has_attempted_scrapingdog()` method

- **`backend/services/validation/validation_orchestrator.py`** - Enhanced recommendations
  - Uses new ValidationRecommendation enum
  - Adds invalid_reason tracking
  - Maps to new validation states

---

## 🗂️ New Database Schema

### **`businesses.website_metadata` (JSONB)**

```json
{
  "source": "outscraper | scrapingdog | manual",
  "source_timestamp": "2026-02-15T01:00:00Z",
  "validation_history": [
    {
      "timestamp": "2026-02-15T01:00:00Z",
      "url": "https://yelp.com/business",
      "verdict": "invalid",
      "confidence": 0.95,
      "reasoning": "Directory - Yelp",
      "recommendation": "trigger_scrapingdog",
      "invalid_reason": "directory"
    }
  ],
  "discovery_attempts": {
    "outscraper": {
      "attempted": true,
      "timestamp": "2026-02-15T01:00:00Z",
      "found_url": true,
      "url_found": "https://yelp.com/business",
      "valid": false
    },
    "scrapingdog": {
      "attempted": true,
      "timestamp": "2026-02-15T01:05:00Z",
      "found_url": true,
      "url_found": "https://realbusiness.com",
      "valid": true
    }
  }
}
```

---

## 🚀 Deployment Steps

### **Phase 1: Database Migration**

```bash
# 1. Connect to VPS
ssh user@webmagic.lavish.solutions

# 2. Navigate to project
cd /var/www/webmagic

# 3. Pull latest code
git pull origin main

# 4. Run migration
cd backend
psql -U webmagic_user -d webmagic -f migrations/013_add_website_metadata.sql

# Expected output:
# NOTICE:  Migration 013 completed: website_metadata field added
# NOTICE:  Backfilled 672 businesses
```

**Verify migration:**
```sql
-- Check field exists
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'businesses' AND column_name = 'website_metadata';

-- Check backfill worked
SELECT COUNT(*) FROM businesses WHERE website_metadata IS NOT NULL;
```

### **Phase 2: Update Celery Configuration**

The new tasks use different names to avoid conflicts with old system:

**New Task Names:**
- `tasks.validation.validate_business_website_v2` (new)
- `tasks.discovery.discover_missing_websites_v2` (new)

**Old Task Names (still work):**
- `tasks.validation.validate_business_website` (old)
- `tasks.validation.discover_missing_websites` (old)

**Update `/etc/supervisor/conf.d/webmagic-celery.conf`:**
```ini
[program:webmagic-celery]
command=/var/www/webmagic/backend/.venv/bin/celery -A celery_app worker 
    --loglevel=info 
    --concurrency=4 
    -Q validation,discovery,generation,celery
directory=/var/www/webmagic/backend
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/webmagic/celery.log
stderr_logfile=/var/log/webmagic/celery_error.log
```

**Restart services:**
```bash
supervisorctl restart all
supervisorctl status
```

### **Phase 3: Update Task Registry**

**Update `backend/celery_app.py`:**
```python
# Add to autodiscover
app.autodiscover_tasks([
    'tasks.validation_tasks',
    'tasks.validation_tasks_enhanced',  # NEW
    'tasks.discovery_tasks',  # NEW
    'tasks.generation_tasks',
    'tasks.campaigns'
])
```

### **Phase 4: Test on Subset**

**Test script:**
```python
# backend/scripts/test_validation_v2.py
import asyncio
from core.database import get_db_session_sync
from models.business import Business
from tasks.validation_tasks_enhanced import validate_business_website_v2

# Get a business with a rejected URL
with get_db_session_sync() as db:
    business = db.query(Business).filter(
        Business.website_url.like('%yelp.com%')
    ).first()
    
    if business:
        print(f"Testing with: {business.name}")
        print(f"URL: {business.website_url}")
        
        # Queue validation
        task = validate_business_website_v2.delay(str(business.id))
        print(f"Task queued: {task.id}")
```

**Run test:**
```bash
cd /var/www/webmagic/backend
PYTHONPATH=/var/www/webmagic/backend .venv/bin/python scripts/test_validation_v2.py
```

**Monitor results:**
```sql
-- Check if ScrapingDog was triggered
SELECT 
    name,
    website_url,
    website_validation_status,
    website_metadata->'discovery_attempts'->>'scrapingdog' as scrapingdog_attempt
FROM businesses
WHERE name = 'Your Test Business';
```

### **Phase 5: Gradual Rollout**

#### **Option A: Dual-Run (Safest)**
Keep both systems running:
- Old system handles existing pending validations
- New system handles new scrapes

```python
# In hunter_service.py, use new task for new scrapes
from tasks.validation_tasks_enhanced import validate_business_website_v2

# Queue with new task
validate_business_website_v2.delay(str(business.id))
```

#### **Option B: Immediate Switch**
Replace old task calls with new ones:

```bash
# Find all references to old task
cd /var/www/webmagic/backend
grep -r "validate_business_website.delay" --include="*.py"

# Replace with new task
# validate_business_website.delay -> validate_business_website_v2.delay
```

---

## 📊 Monitoring & Verification

### **Check Validation States**
```sql
-- Distribution of new validation states
SELECT 
    website_validation_status,
    COUNT(*) as count
FROM businesses
GROUP BY website_validation_status
ORDER BY count DESC;

-- Should see new states:
-- needs_discovery, discovery_queued, discovery_in_progress
-- valid_outscraper, valid_scrapingdog
-- confirmed_no_website
```

### **Check ScrapingDog Triggers**
```sql
-- Businesses where Scraping Dog was triggered after rejection
SELECT 
    name,
    city,
    state,
    website_validation_status,
    jsonb_array_length(website_metadata->'validation_history') as validation_attempts,
    website_metadata->'discovery_attempts'->>'scrapingdog' IS NOT NULL as scrapingdog_attempted
FROM businesses
WHERE website_metadata->'validation_history' @> '[{"recommendation": "trigger_scrapingdog"}]'
LIMIT 20;
```

### **Audit Trail Example**
```sql
-- Get full audit trail for a business
SELECT 
    name,
    website_url,
    website_metadata->'source' as url_source,
    jsonb_pretty(website_metadata->'validation_history') as history,
    jsonb_pretty(website_metadata->'discovery_attempts') as discovery
FROM businesses
WHERE name = 'Business Name';
```

---

## 🔄 Migration Strategy for Existing Data

### **Reprocess "Missing" Businesses**

These are businesses currently marked as "missing" that should have triggered ScrapingDog but didn't:

```sql
-- Find businesses to reprocess
SELECT COUNT(*) FROM businesses
WHERE website_validation_status = 'missing'
  AND website_url IS NULL
  AND website_metadata->>'source' = 'outscraper'
  AND website_metadata->'discovery_attempts'->>'scrapingdog' IS NULL;
```

**Reprocessing script:**
```python
# backend/scripts/reprocess_missing_businesses.py
import asyncio
from sqlalchemy import select, and_
from core.database import get_db_session_sync
from models.business import Business
from tasks.validation_tasks_enhanced import validate_business_website_v2

async def reprocess_missing():
    """Re-queue businesses that need ScrapingDog discovery."""
    with get_db_session_sync() as db:
        # Find businesses marked as "missing" without ScrapingDog attempt
        businesses = db.query(Business).filter(
            and_(
                Business.website_validation_status == 'missing',
                Business.website_url.is_(None),
                # No ScrapingDog attempt in metadata
                ~Business.website_metadata['discovery_attempts'].has_key('scrapingdog')
            )
        ).limit(100).all()  # Process in batches
        
        print(f"Found {len(businesses)} to reprocess")
        
        for business in businesses:
            # Update status to needs_discovery
            business.website_validation_status = 'needs_discovery'
            db.commit()
            
            # Queue for validation (will trigger ScrapingDog)
            validate_business_website_v2.delay(str(business.id))
            print(f"Queued: {business.name}")

if __name__ == "__main__":
    asyncio.run(reprocess_missing())
```

---

## 🧪 Testing Checklist

- [ ] Migration ran successfully
- [ ] All businesses have `website_metadata` field
- [ ] Celery workers recognize new tasks
- [ ] Test business with no URL → triggers ScrapingDog
- [ ] Test business with Yelp URL → rejects, triggers ScrapingDog
- [ ] Test business with valid URL → marks as valid_outscraper
- [ ] Test business with 404 → marks as invalid_technical
- [ ] Check logs for proper state transitions
- [ ] Verify metadata is being populated
- [ ] Confirm ScrapingDog is triggered only once per business
- [ ] Verify audit trail is complete

---

## 🐛 Troubleshooting

### **Issue: Tasks not found**
```bash
# Check Celery can see new tasks
cd /var/www/webmagic/backend
source .venv/bin/activate
celery -A celery_app inspect registered | grep validate_business_website_v2
```

**Fix:** Update `celery_app.py` autodiscover_tasks list.

### **Issue: Migration fails**
```bash
# Check if field already exists
psql -U webmagic_user -d webmagic -c "SELECT column_name FROM information_schema.columns WHERE table_name='businesses' AND column_name='website_metadata';"
```

**Fix:** If exists, modify migration to use `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.

### **Issue: Metadata not populating**
```sql
-- Check if validation is using new task
SELECT COUNT(*) FROM businesses 
WHERE website_validated_at > NOW() - INTERVAL '1 hour'
  AND website_metadata IS NULL;
```

**Fix:** Ensure `validate_business_website_v2` is being called, not old task.

### **Issue: ScrapingDog not triggering**
```python
# Check business state
from core.database import get_db_session_sync
from models.business import Business

with get_db_session_sync() as db:
    business = db.query(Business).filter(Business.id == 'uuid').first()
    print(f"Status: {business.website_validation_status}")
    print(f"URL: {business.website_url}")
    print(f"Metadata: {business.website_metadata}")
```

**Fix:** Verify recommendation is `trigger_scrapingdog` in validation result.

---

## 📈 Expected Improvements

### **Before (Old System)**
- 183 businesses marked as "missing"
- Unknown how many actually have websites
- No ScrapingDog trigger on rejection
- Lost opportunities

### **After (New System)**
- Clear distinction: `needs_discovery` vs `confirmed_no_website`
- ScrapingDog triggered automatically on rejection
- Complete audit trail for every decision
- Estimated 30-50% of "missing" will find valid websites

### **Cost Optimization**
- **Old System:** Wasted ScrapingDog calls on businesses with valid websites
- **New System:** Only calls ScrapingDog when needed
- **Savings:** ~50% reduction in ScrapingDog API calls

---

## 📝 Next Steps After Deployment

1. **Monitor for 24 hours** - Watch logs, check for errors
2. **Analyze Results** - How many discoveries succeeded?
3. **Tune Thresholds** - Adjust confidence levels if needed
4. **Update Frontend** - Display new validation states
5. **Create Dashboard** - Show discovery pipeline metrics
6. **Documentation** - Update API docs with new states

---

## 🎓 Key Architectural Improvements

### **Separation of Concerns**
- **Enums** - Centralized constants
- **Metadata Service** - Dedicated metadata management
- **Tasks** - Single responsibility (validate OR discover)
- **Orchestrator** - Only handles validation pipeline

### **Data Integrity**
- **Immutable History** - Validation history never changes
- **Audit Trail** - Every decision is logged
- **Source Tracking** - Always know where data came from

### **Maintainability**
- **Type Safety** - Enums prevent typos
- **Modular** - Easy to test components independently
- **Documented** - Clear docstrings and comments
- **Extensible** - Easy to add new discovery methods

---

## 🤝 Support

If you encounter issues during deployment:

1. Check logs: `/var/log/webmagic/celery.log`
2. Verify database migration completed
3. Test with single business first
4. Review this guide's Troubleshooting section

**Remember:** This is a major refactor. Take it slow, test thoroughly, and monitor closely.

