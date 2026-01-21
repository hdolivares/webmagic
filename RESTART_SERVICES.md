# 🔄 Restart Services & Deploy Updated Code

**Date:** January 21, 2026  
**Changes:** Brevo email integration, Phase 4 & 5 planning  

---

## 📋 CHECKLIST

### **Backend Updates:**
```
✅ Brevo email provider added
✅ New email template (subscription activated)
✅ Requirements.txt updated (sib-api-v3-sdk)
✅ Email service routing updated
✅ Phase 4 & 5 plans created
```

### **Configuration Check:**
```
⏳ Verify .env has BREVO_API_KEY
⏳ Verify RECURRENTE keys are set
⏳ Install new Python dependencies
⏳ Restart API server
⏳ Test email sending
```

---

## 🚀 DEPLOYMENT STEPS

### **Step 1: Pull Latest Code (VPS)**
```bash
cd /var/www/webmagic
git pull origin main
```

### **Step 2: Install New Dependencies**
```bash
cd /var/www/webmagic/backend
source .venv/bin/activate  # Or just use supervisor restart
pip install -r requirements.txt
```

### **Step 3: Verify Environment Variables**
```bash
# Check .env file has:
cat .env | grep -E "(BREVO|RECURRENTE|EMAIL)"

# Should see:
# EMAIL_PROVIDER=brevo
# BREVO_API_KEY=xkeysib-...
# RECURRENTE_PUBLIC_KEY=...
# RECURRENTE_SECRET_KEY=...
# RECURRENTE_WEBHOOK_SECRET=...
# EMAIL_FROM=hugo@webmagic.com
```

### **Step 4: Restart Services**
```bash
# Restart API
supervisorctl restart webmagic-api

# Check status
supervisorctl status webmagic-api

# View logs
tail -f /var/log/supervisor/webmagic-api.log
```

### **Step 5: Test Email System**
```bash
# Test Brevo integration
cd /var/www/webmagic/backend
python3 << EOF
from services.emails.email_service import get_email_service
import asyncio

async def test():
    email_service = get_email_service()
    result = await email_service.send_welcome_email(
        to_email="your-test-email@example.com",
        customer_name="Test User",
        verification_token="test123"
    )
    print(f"Email sent: {result}")

asyncio.run(test())
EOF
```

---

## 🧪 TESTING CHECKLIST

### **Email Service:**
```bash
✓ Send test welcome email
✓ Send test verification email
✓ Send test password reset
✓ Send test purchase confirmation
✓ Send test subscription activated
✓ Check email deliverability
✓ Verify links work in emails
```

### **API Endpoints:**
```bash
# Test registration (will send email)
curl -X POST http://localhost:8000/api/v1/customer/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123456!"}'

# Should see success and email sent

# Test site info
curl http://localhost:8000/api/v1/sites/la-plumbing-pros

# Test subscription endpoints
curl http://localhost:8000/api/v1/subscriptions/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### **Subscription System:**
```bash
# Run Phase 3 tests
cd /var/www/webmagic/backend
python test_phase3.py

# Should see: ALL TESTS PASSED! 9/9 ✅
```

---

## 📧 EMAIL PROVIDER VERIFICATION

### **Brevo Dashboard Check:**
```
1. Login to Brevo (brevo.com)
2. Go to "Senders & IP"
3. Verify sender: hugo@webmagic.com is verified
4. Check API key is active
5. Monitor sending statistics
```

### **Email Testing:**
```
Send emails to:
- Gmail (test deliverability)
- Outlook (test compatibility)
- Yahoo (test spam filters)

Check:
✓ Emails arrive (not spam)
✓ Links work
✓ Images load
✓ Styling renders correctly
```

---

## 🔧 TROUBLESHOOTING

### **Issue: Email Not Sending**
```bash
# Check logs
tail -f /var/log/supervisor/webmagic-api.log | grep -i email

# Common causes:
1. BREVO_API_KEY invalid
   Solution: Regenerate key in Brevo dashboard

2. Sender not verified
   Solution: Verify hugo@webmagic.com in Brevo

3. Rate limit exceeded
   Solution: Check Brevo quota

4. Import error
   Solution: pip install sib-api-v3-sdk
```

### **Issue: API Not Restarting**
```bash
# Check supervisor status
supervisorctl status

# If stopped, start manually
supervisorctl start webmagic-api

# Check for errors
tail -f /var/log/supervisor/webmagic-api-stderr.log

# If module import error:
cd /var/www/webmagic/backend
source .venv/bin/activate
pip install -r requirements.txt
supervisorctl restart webmagic-api
```

### **Issue: Tests Failing**
```bash
# Check database connection
psql $DATABASE_URL -c "SELECT 1;"

# Check Python environment
which python3
python3 --version

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

---

## 📱 FRONTEND REBUILD (If Needed)

### **Frontend Changes:**
```bash
cd /var/www/webmagic/frontend

# Install dependencies (if new)
npm install

# Build for production
npm run build

# The dist/ folder is served by nginx
# nginx.conf should point to: /var/www/webmagic/frontend/dist
```

### **Nginx Configuration:**
```nginx
# Frontend (app.lavish.solutions)
server {
    listen 443 ssl http2;
    server_name app.lavish.solutions;
    
    root /var/www/webmagic/frontend/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### **Test Frontend:**
```bash
# Visit in browser
https://app.lavish.solutions

# Should see:
✓ Login page loads
✓ Can register new account
✓ Dashboard accessible
✓ API calls work
```

---

## ✅ POST-DEPLOYMENT VERIFICATION

### **Critical Checks:**
```
✓ API responding (200 OK)
✓ Database connected
✓ Email sending works
✓ All 83 routes registered
✓ Tests passing (28/28)
✓ Site hosting working
✓ SSL certificates active
✓ Logs showing no errors
```

### **Monitoring:**
```bash
# Watch API logs
tail -f /var/log/supervisor/webmagic-api.log

# Watch Nginx access
tail -f /var/log/nginx/access.log

# Watch Nginx errors
tail -f /var/log/nginx/error.log

# Check system resources
htop
df -h
free -m
```

---

## 🎯 READY STATUS

### **Once Complete, You Should Have:**
```
✅ Backend API running (port 8000)
✅ Brevo email integration working
✅ Recurrente payment processing ready
✅ 83 API endpoints active
✅ 28/28 tests passing
✅ Email notifications sending
✅ Sites hosting at sites.lavish.solutions
✅ SSL certificates active
✅ Phase 4 & 5 plans documented
```

---

## 📞 SUPPORT COMMANDS

### **Quick Status Check:**
```bash
# One-liner to check everything
cd /var/www/webmagic && \
  git status && \
  supervisorctl status webmagic-api && \
  curl -s http://localhost:8000/api/v1/sites/la-plumbing-pros | head -5
```

### **Force Restart Everything:**
```bash
# Nuclear option (if needed)
supervisorctl restart all
sudo systemctl reload nginx
```

### **Rollback (If Needed):**
```bash
# Rollback to previous commit
cd /var/www/webmagic
git log --oneline -5
git checkout <previous-commit-hash>
supervisorctl restart webmagic-api
```

---

## 🎉 SUCCESS INDICATORS

### **Everything Working When You See:**
```
1. supervisorctl status webmagic-api
   → webmagic-api RUNNING ✅

2. curl http://localhost:8000/api/v1/sites/la-plumbing-pros
   → Returns site JSON ✅

3. python backend/test_phase3.py
   → ALL TESTS PASSED! 9/9 ✅

4. Check email inbox
   → Test emails arriving ✅

5. Browser: https://sites.lavish.solutions/la-plumbing-pros
   → Site loads with SSL ✅
```

---

_Deployment Guide Created: January 21, 2026_  
_Last Updated Code: Phase 3 Complete + Brevo Integration_  
_Next Steps: Deploy Phase 4 or 5_

**Ready to restart and test!** 🚀
