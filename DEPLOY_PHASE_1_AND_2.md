# Deploy Phase 1 & 2 to Production

**Status:** ✅ Code pushed to GitHub  
**Commit:** `d634efe` - "feat: Phase 1 & 2 CRM Implementation"

---

## 🚀 Quick Deploy (Recommended)

SSH into your VPS and run the automated deployment script:

```bash
ssh root@your-vps
cd /var/www/webmagic
./scripts/deploy.sh
```

The deploy script will automatically:
1. Pull latest code from GitHub
2. Install any new Python dependencies
3. Rebuild frontend (if needed)
4. Restart all services in correct order

---

## 📋 Manual Deployment Steps

If you prefer to deploy manually or if the script fails:

### Step 1: Pull Latest Code
```bash
ssh root@your-vps
cd /var/www/webmagic
git pull origin main
```

**Expected output:**
```
Updating abc123..d634efe
Fast-forward
 16 files changed, 3720 insertions(+), 13 deletions(-)
 create mode 100644 backend/services/crm/__init__.py
 create mode 100644 backend/services/crm/lead_service.py
 create mode 100644 backend/services/crm/lifecycle_service.py
 ...
```

### Step 2: Install Dependencies
```bash
cd /var/www/webmagic/backend
source venv/bin/activate
pip install -r requirements.txt
```

**Note:** No new dependencies in Phase 1 & 2, but this ensures everything is up to date.

### Step 3: Restart Services
```bash
cd /var/www/webmagic
./scripts/restart_services.sh
```

**Expected output:**
```
🔄 Restarting WebMagic services...

Stopping services (safe shutdown)...
✓ Stopped webmagic-celery-beat
✓ Stopped webmagic-celery
✓ Stopped webmagic-api

Starting services (with health checks)...
✓ webmagic-api started successfully (PID: 12345)
✓ webmagic-celery started successfully (PID: 12346)
✓ webmagic-celery-beat started successfully (PID: 12347)

✅ All services restarted successfully!
```

### Step 4: Verify Deployment
```bash
# Check service status
sudo supervisorctl status

# Should show:
# webmagic-api                 RUNNING   pid 12345, uptime 0:00:30
# webmagic-celery              RUNNING   pid 12346, uptime 0:00:25
# webmagic-celery-beat         RUNNING   pid 12347, uptime 0:00:20
```

```bash
# Check API logs for errors
sudo supervisorctl tail -f webmagic-api

# Should see:
# INFO:     Application startup complete.
# INFO:     Started server process [12345]
# INFO:uvicorn.access: ...
```

---

## ✅ Post-Deployment Verification

### Test 1: API Health Check
```bash
curl -I https://web.lavish.solutions/api/health

# Expected: HTTP/2 200
```

### Test 2: Login to Admin Panel
Visit: https://web.lavish.solutions/

- Login with your admin credentials
- Verify no errors in browser console

### Test 3: Check Database
```bash
# SSH into VPS
ssh root@your-vps

# Connect to database
sudo -u postgres psql webmagic

# Verify CRM services table structure (no changes, just check)
\d businesses

# Should show columns:
# - contact_status (varchar)
# - website_status (varchar)
# - qualification_score (integer)

\q
```

### Test 4: Generate a Test Site
1. Go to admin panel → Businesses
2. Select a business
3. Click "Generate Site"
4. Watch logs: `sudo supervisorctl tail -f webmagic-api`
5. Verify logs show:
   ```
   INFO: Business {id}: website_status = generating (AI started)
   ...
   INFO: Business {id}: website_status = generated (site ready)
   ```

### Test 5: Send a Test Campaign (Optional)
1. Create an email or SMS campaign
2. Send it to a test recipient
3. Verify logs show:
   ```
   INFO: Business {id}: contact_status = emailed (campaign sent)
   ```

---

## 🐛 Troubleshooting

### Issue: Services won't start
```bash
# Check logs for specific error
sudo supervisorctl tail -f webmagic-api stderr

# Common fixes:
# 1. Syntax error in new code
sudo supervisorctl tail -f webmagic-api | grep "SyntaxError"

# 2. Import error (missing module)
sudo supervisorctl tail -f webmagic-api | grep "ModuleNotFoundError"

# 3. Permission error
ls -la /var/www/webmagic/backend/services/crm/
# Should show: -rw-r--r-- files owned by your user
```

### Issue: Import errors
```bash
# Ensure new CRM package is importable
cd /var/www/webmagic/backend
source venv/bin/activate
python3 -c "from services.crm import LeadService, BusinessLifecycleService; print('✅ CRM services imported successfully')"

# If error, check file permissions
chmod 644 /var/www/webmagic/backend/services/crm/*.py
```

### Issue: Services running but webhook errors
```bash
# Check API logs during webhook processing
sudo supervisorctl tail -f webmagic-api

# Trigger a test webhook (Twilio or Recurrente test mode)
# Look for CRM status update logs:
# "Updated business {id}: contact_status=..."
```

---

## 📊 What Changed

### New Files
```
backend/services/crm/
├── __init__.py              # Package exports
├── lead_service.py          # Business/lead management (350 lines)
└── lifecycle_service.py     # Automated status transitions (470 lines)
```

### Modified Files
```
backend/api/v1/
├── sites.py                 # Integrated lifecycle tracking
├── webhooks.py              # Recurrente webhook CRM integration
└── webhooks_twilio.py       # Twilio webhook CRM integration

backend/services/
├── site_purchase_service.py # Ensures business records always exist
└── pitcher/
    ├── campaign_service.py  # Email campaign CRM integration
    └── sms_campaign_helper.py # SMS campaign CRM integration
```

### Documentation
```
├── PHASE_1_IMPLEMENTATION_COMPLETE.md  # CRM Foundation docs
├── PHASE_1_SUMMARY.md                  # Quick reference
├── PHASE_2_IMPLEMENTATION_COMPLETE.md  # Webhook integration docs
├── CRM_ANALYSIS_AND_PLAN.md            # Overall CRM strategy
├── CRM_FIX_SUMMARY.md                  # Orphaned site fix
└── backend/migrations/
    └── 20260122_fix_orphaned_plumbing_site.sql # Data fix
```

---

## 🎯 Expected Behavior After Deployment

### When a site is generated:
```
Business Status Flow:
none → generating (AI starts)
      ↓
   generated (AI completes)
```

### When a campaign is sent:
```
Contact Status Flow:
pending → emailed (email sent)
   OR
pending → sms_sent (SMS sent)
```

### When SMS is delivered:
```
Twilio Webhook → contact_status confirmed as "sms_sent"
```

### When customer replies to SMS:
```
Regular reply → contact_status: replied
STOP keyword → contact_status: unsubscribed (TERMINAL)
```

### When site is purchased:
```
Business Status Update:
- website_status: sold
- contact_status: purchased (TERMINAL)
```

### When subscription is cancelled:
```
Recurrente Webhook → website_status: archived
```

---

## 📞 Support

If you encounter any issues during deployment:

1. **Check logs first:**
   ```bash
   sudo supervisorctl tail -f webmagic-api stderr
   ```

2. **Restart services:**
   ```bash
   cd /var/www/webmagic
   ./scripts/restart_services.sh
   ```

3. **Rollback if needed:**
   ```bash
   cd /var/www/webmagic
   git log --oneline -5  # Find previous commit
   git checkout abc123   # Replace with previous commit hash
   ./scripts/restart_services.sh
   ```

---

**Deployment Prepared By:** AI Assistant  
**Date:** January 22, 2026  
**Commit Hash:** `d634efe`  
**Status:** ✅ Ready to Deploy

