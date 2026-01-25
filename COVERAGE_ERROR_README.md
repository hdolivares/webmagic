# Coverage Page Error - Quick Start

**Problem:** Coverage page showing 500 errors when clicking "Start Scraping This Zone"

**Solution:** Run the diagnostic script, apply fixes, restart services

**Time Required:** 5-10 minutes

---

## 🚀 Quick Fix (3 Steps)

### Step 1: SSH into VPS
```bash
ssh root@104.251.211.183
```

### Step 2: Run Quick Fix Script
```bash
cd /root/webmagic/backend/scripts
chmod +x quick_fix_coverage.sh
./quick_fix_coverage.sh
```

### Step 3: Test
1. Clear browser cache (Ctrl+Shift+Delete)
2. Reload Coverage page (Ctrl+F5)
3. Try creating an intelligent strategy

**Done!** ✅

---

## 📖 Alternative: Manual Fix

If the quick fix script doesn't work:

### 1. Run Diagnostic
```bash
cd /root/webmagic/backend
python3 scripts/diagnose_coverage_errors.py
```

### 2. Apply Migrations (if needed)
```bash
cd /root/webmagic/backend/migrations
psql $DATABASE_URL -f 004_add_geo_strategies.sql
psql $DATABASE_URL -f 005_add_draft_campaigns.sql
```

### 3. Restart Services
```bash
pm2 restart webmagic-api
```

### 4. Verify
```bash
curl http://localhost:8000/health
pm2 logs webmagic-api --lines 50
```

---

## 📚 Documentation Files

| File | What It's For |
|------|---------------|
| **COVERAGE_ERROR_SUMMARY.md** | 📊 Start here - Executive summary |
| **COVERAGE_ERROR_FIX_GUIDE.md** | 🛠️ Detailed fix instructions |
| **COVERAGE_SYSTEM_ERROR_ANALYSIS.md** | 🔍 Deep technical analysis |
| **backend/scripts/diagnose_coverage_errors.py** | 🔧 Diagnostic tool |
| **backend/scripts/quick_fix_coverage.sh** | ⚡ Automated fix script |

---

## 🎯 What's Wrong?

The Coverage Page uses two new database tables that might not exist in production:

1. **`geo_strategies`** - Stores Claude AI-generated scraping strategies
2. **`draft_campaigns`** - Stores campaigns awaiting manual review

These tables are created by migrations 004 and 005, which may not have been run yet.

---

## 🔍 How to Diagnose

The diagnostic script checks:
- ✅ Database connection
- ✅ Required tables exist
- ✅ Data integrity
- ✅ Query functionality
- ✅ Service initialization

It will tell you exactly what's wrong and how to fix it.

---

## ✅ Success Criteria

You'll know it's fixed when:
1. No errors in browser console
2. Coverage page loads successfully
3. Can create intelligent strategies
4. Can scrape zones without errors
5. Draft campaigns stats display

---

## 🆘 Still Having Issues?

1. **Check API logs:**
   ```bash
   pm2 logs webmagic-api --lines 100
   ```

2. **Test endpoints directly:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/api/v1/coverage/campaigns/stats \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **Verify database:**
   ```bash
   psql $DATABASE_URL -c "\dt"
   ```

4. **Share diagnostic output** for further help

---

## 📝 Quick Reference

```bash
# SSH
ssh root@104.251.211.183

# Quick fix (automated)
cd /root/webmagic/backend/scripts && ./quick_fix_coverage.sh

# Diagnostic (manual)
cd /root/webmagic/backend && python3 scripts/diagnose_coverage_errors.py

# Apply migrations (if needed)
cd /root/webmagic/backend/migrations
psql $DATABASE_URL -f 004_add_geo_strategies.sql
psql $DATABASE_URL -f 005_add_draft_campaigns.sql

# Restart
pm2 restart webmagic-api

# Check logs
pm2 logs webmagic-api --lines 50

# Test
curl http://localhost:8000/health
```

---

**Ready?** Run the quick fix script and you should be good to go! 🚀


