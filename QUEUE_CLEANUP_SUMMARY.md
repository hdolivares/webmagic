# Website Generation Queue - Cleanup & Fix Summary

**Date**: February 5, 2026  
**Status**: ✅ **READY FOR TESTING**

---

## 🎯 **What Was Fixed**

### **1. Critical Bug: Async Celery Tasks Don't Execute** ❌→✅
**Problem**: Tasks were defined as `async def` but Celery can ONLY execute synchronous functions.

**Solution**:
- Created `backend/tasks/generation_sync.py` with synchronous wrappers
- Uses `run_async()` helper to execute async code within sync context
- Added proper idempotency checks to prevent duplicate generation

### **2. Queue Validation Guard** ❌→✅
**Problem**: Businesses with valid websites were being queued for generation.

**Solution**:
- Added validation check in `queue_for_generation()` method
- Now returns `'has_valid_website'` status if `website_validation_status == 'valid'`
- Prevents wasting generation credits on businesses that don't need sites

### **3. Raw Data Storage** ❌→✅
**Problem**: Losing all Outscraper JSON responses - can't reprocess data.

**Solution**:
- Added `raw_data` JSONB column to `businesses` table (Migration 008)
- Updated Business model and BusinessService to save raw data
- Future scrapes will preserve full API responses for reprocessing

### **4. Transaction Safety** ❌→✅
**Problem**: No proper rollback on generation failures.

**Solution**:
- Implemented proper `try/except` with rollback in generation task
- Database changes are atomic and safe
- Failed generations don't leave database in inconsistent state

---

## 📊 **Queue Status**

### **Before Cleanup:**
```
Total Queued: 208
├─ 13 with VALID websites (❌ shouldn't be queued)
├─ 146 pending validation
├─ 33 marked invalid (likely false positives)
└─ 16 missing websites
```

### **After Cleanup:**
```
Total Queued: 195 ✅
├─ 0 with valid websites (removed!)
├─ 146 pending (143 no URL, 3 need validation)
├─ 33 invalid (need re-validation)
└─ 16 missing (confirmed no URL)
```

**Businesses Removed from Queue:**
1. Dautriel's Plumbing
2. Raymark Plumbing & Sewer
3. Apollo Plumbing, LLC
4. South West Plumbing
5. 2 Sons Plumbing
6. Mr. Rooter Plumbing of Seattle
7. Beacon Plumbing - Tacoma
8. Fox Plumbing & Heating
9. Beacon Plumbing - Seattle
10. Rescue Rooter
11. McComb Plumbing
12. JD Precision Plumbing Services
13. Acacias Plumbing

---

## 🚀 **Next Steps**

### **Immediate (Before Full Generation):**

1. **Re-validate the 33 "invalid" websites**
   ```bash
   cd /var/www/webmagic/backend
   .venv/bin/python -m scripts.revalidate_websites
   ```
   Many of these are likely legitimate sites with anti-bot protection (403/429).

2. **Restart Celery workers** to load new sync tasks
   ```bash
   pkill -f "celery.*worker"
   cd /var/www/webmagic/backend
   nohup .venv/bin/celery -A celery_app worker --loglevel=info --concurrency=2 > /var/log/webmagic/celery_worker.log 2>&1 &
   ```

3. **Test with 1-2 businesses first**
   - Pick businesses with `website_validation_status = 'missing'` and high ratings
   - Manually trigger generation
   - Verify site is created successfully
   - Check database updates correctly

### **After Testing:**

4. **Enable automatic generation**
   - Celery workers will process the queue automatically
   - Monitor logs: `/var/log/webmagic/celery_worker.log`
   - Track progress in database

5. **Monitor queue health**
   ```sql
   SELECT 
       website_status,
       COUNT(*) as count,
       COUNT(*) FILTER (WHERE generation_started_at IS NOT NULL) as started,
       COUNT(*) FILTER (WHERE generation_completed_at IS NOT NULL) as completed
   FROM businesses
   WHERE website_status IN ('queued', 'generating', 'generated')
   GROUP BY website_status;
   ```

---

## 📁 **Files Changed**

### **New Files:**
- `backend/migrations/008_add_raw_data_storage.sql` - Raw data JSONB column
- `backend/tasks/generation_sync.py` - Synchronous Celery tasks
- `backend/scripts/cleanup_invalid_queue.py` - Remove invalid queue entries
- `backend/scripts/revalidate_websites.py` - Re-validate "invalid" websites

### **Modified Files:**
- `backend/models/business.py` - Added `raw_data` field
- `backend/services/hunter/business_service.py` - Save `raw_data`
- `backend/services/hunter/website_generation_queue_service.py` - Validation guard
- `frontend/src/components/business/BusinessFilterPanel.css` - Horizontal layout
- `frontend/src/components/business/BusinessFilterPanel.tsx` - Fixed filter values

---

## ⚠️ **Important Notes**

1. **Celery Tasks MUST Be Sync**: Never use `async def` for Celery tasks
2. **Always Validate Before Queueing**: Check `website_validation_status` first
3. **Idempotency is Critical**: Tasks should be safe to run multiple times
4. **Save Raw Data**: Always preserve API responses for reprocessing
5. **Test Before Scale**: Always test with 1-2 businesses before processing hundreds

---

## 🔧 **Useful Commands**

### Check Celery Status:
```bash
cd /var/www/webmagic/backend
.venv/bin/celery -A celery_app inspect active
.venv/bin/celery -A celery_app inspect registered
```

### Monitor Queue:
```sql
SELECT 
    website_status,
    website_validation_status,
    COUNT(*) as count
FROM businesses
GROUP BY website_status, website_validation_status
ORDER BY count DESC;
```

### Check Generation Progress:
```sql
SELECT 
    name,
    website_status,
    generation_queued_at,
    generation_started_at,
    generation_completed_at
FROM businesses
WHERE website_status IN ('queued', 'generating')
ORDER BY generation_queued_at DESC
LIMIT 20;
```

---

## ✅ **Success Criteria**

Before considering this complete:
- [ ] Re-validate 33 "invalid" websites
- [ ] Test generation with 1-2 businesses
- [ ] Verify Celery workers are processing
- [ ] Confirm database updates correctly
- [ ] Monitor for errors in logs
- [ ] Verify generated sites are accessible

---

**Status**: Ready for re-validation and testing phase.

