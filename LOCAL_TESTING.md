# WebMagic Local Testing Guide

Complete guide to testing the entire WebMagic system on your local machine (Windows).

## 🎯 Overview

We'll test all 7 phases locally:
1. ✅ **Foundation** - Database, Auth, Config
2. ✅ **Hunter** - Scraping and lead qualification
3. ✅ **Creative** - AI website generation
4. ✅ **Pitcher** - Email campaigns
5. ✅ **Payments** - Recurrente integration
6. ✅ **Frontend** - Admin dashboard
7. ✅ **Automation** - Celery and Conductor

## 📋 Prerequisites

### 1. Install Dependencies

#### Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### Redis (Required for Celery)
**Windows:**
- Download Redis from: https://github.com/microsoftarchive/redis/releases
- Or use Docker just for Redis: `docker run -d -p 6379:6379 redis`
- Or use WSL: `wsl -d Ubuntu redis-server`

**Verify Redis is running:**
```bash
redis-cli ping
# Should return: PONG
```

#### Node.js (for frontend)
```bash
cd frontend
npm install
```

### 2. Environment Setup

Create `.env` file in `backend/`:

```bash
# Copy from template
cp env.template .env
```

Edit `.env` with your credentials:
```bash
# Database (Supabase)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Security
SECRET_KEY=your-secret-key-here

# APIs
ANTHROPIC_API_KEY=sk-ant-xxx
OUTSCRAPER_API_KEY=xxx

# Email (Optional for testing)
EMAIL_PROVIDER=ses
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
EMAIL_FROM=test@webmagic.com

# Recurrente (Optional for testing)
RECURRENTE_PUBLIC_KEY=xxx
RECURRENTE_SECRET_KEY=xxx
RECURRENTE_WEBHOOK_SECRET=xxx

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## 🧪 Testing Phase by Phase

### Phase 1: Foundation (Auth & Database)

**1. Start the API:**
```bash
cd backend
python start.py
```

**2. Test in another terminal:**
```bash
python test_api.py
```

**Expected output:**
```
✓ Health check passed
✓ Login successful
✓ User profile retrieved
```

**3. Check API docs:**
Open: http://localhost:8000/docs

### Phase 2: Hunter (Scraping)

**1. Seed the database:**
```bash
cd backend
python -c "from models import *; from core.database import engine; BaseModel.metadata.create_all(engine)"
```

**2. Run Hunter tests:**
```bash
python test_phase2.py
```

**Expected output:**
```
✓ Coverage grid created
✓ Scraping initiated
✓ Businesses saved
✓ Lead qualified
```

**3. Manual test via API:**
```bash
curl -X POST "http://localhost:8000/api/v1/coverage/scrape" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"location": "Guatemala City", "category": "restaurant"}'
```

### Phase 3: Creative (AI Website Generation)

**1. Seed prompt templates:**
```bash
cd backend
python scripts/seed_prompt_templates.py
```

**2. Run Creative tests:**
```bash
python test_phase3.py
```

**Expected output:**
```
✓ Prompt templates loaded
✓ Business analyzed
✓ Brand concept generated
✓ Design brief created
✓ Website generated
```

**Note:** This will make real API calls to Claude and costs money. Skip if you want to save credits.

### Phase 4: Pitcher (Email Campaigns)

**1. Run Pitcher tests:**
```bash
cd backend
python test_phase4.py
```

**Expected output:**
```
✓ Campaign created
✓ Email generated
✓ Email sent (or queued)
✓ Tracking configured
```

**Note:** Set `EMAIL_PROVIDER=mock` in `.env` to test without sending real emails.

### Phase 5: Payments (Recurrente)

**1. Run Payment tests:**
```bash
cd backend
python test_phase5.py
```

**Expected output:**
```
✓ Checkout session created
✓ Customer created
✓ Webhook handler configured
```

**Note:** Uses Recurrente sandbox mode by default.

### Phase 6: Frontend (Admin Dashboard)

**1. Configure API URL:**

Create `frontend/.env`:
```bash
VITE_API_URL=http://localhost:8000/api/v1
```

**2. Start frontend dev server:**
```bash
cd frontend
npm run dev
```

**3. Open browser:**
```
http://localhost:3000
```

**4. Test login:**
- Email: Your admin email
- Password: Your admin password

**5. Test all pages:**
- ✅ Dashboard - View metrics
- ✅ Businesses - View scraped leads
- ✅ Sites - View generated sites
- ✅ Campaigns - View email campaigns
- ✅ Customers - View paying customers
- ✅ Settings - Edit prompt settings

### Phase 7: Automation (Celery & Conductor)

#### Test 1: Celery Workers

**Terminal 1 - Start Redis:**
```bash
redis-server
```

**Terminal 2 - Start Celery Worker:**
```bash
cd backend
python start_worker.py
```

**Terminal 3 - Start Celery Beat:**
```bash
cd backend
python start_beat.py
```

**Terminal 4 - Test tasks:**
```bash
cd backend
python -c "
from tasks.monitoring import health_check
import asyncio
result = asyncio.run(health_check())
print(result)
"
```

#### Test 2: Conductor (Single Cycle)

**1. Check pipeline status:**
```bash
cd backend
python conductor.py --status
```

**Expected output:**
```
========== WEBMAGIC PIPELINE STATUS ==========
Timestamp: 2026-01-10T...
Coverage:
  Pending territories: X
Businesses:
  Total: X
  Qualified: X
Sites:
  Total: X
  ...
```

**2. Run single cycle:**
```bash
python conductor.py --mode once
```

**Expected output:**
```
========== CYCLE 1 STARTING ==========
Running health check...
Phase 1: SCRAPING
Phase 2: SITE GENERATION
Phase 3: EMAIL CAMPAIGNS
========== CYCLE 1 COMPLETED ==========
```

#### Test 3: Conductor (Continuous Autopilot)

**Run for 15 minutes (3 cycles @ 5 min intervals):**
```bash
python conductor.py --mode continuous --interval 300
```

**Press Ctrl+C to stop gracefully.**

## 🔄 Full Integration Test

Run the entire pipeline end-to-end:

### 1. Start All Services

**Terminal 1 - Redis:**
```bash
redis-server
```

**Terminal 2 - FastAPI:**
```bash
cd backend
python start.py
```

**Terminal 3 - Celery Worker:**
```bash
cd backend
python start_worker.py
```

**Terminal 4 - Celery Beat:**
```bash
cd backend
python start_beat.py
```

**Terminal 5 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 6 - Conductor (optional):**
```bash
cd backend
python conductor.py --mode continuous --interval 300
```

### 2. Manual End-to-End Test

**Step 1: Scrape leads**
```bash
# Via API
curl -X POST "http://localhost:8000/api/v1/coverage/scrape" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"location": "Test City", "category": "cafe"}'
```

**Step 2: Qualify leads**
- Check in admin dashboard: http://localhost:3000/businesses
- Should see new businesses with "qualified" status

**Step 3: Generate site**
```bash
# Via API
curl -X POST "http://localhost:8000/api/v1/sites/generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"business_id": "YOUR_BUSINESS_ID"}'
```

**Step 4: Check site**
- View in admin dashboard: http://localhost:3000/sites
- Should see new site with HTML content

**Step 5: Create campaign**
```bash
# Via API
curl -X POST "http://localhost:8000/api/v1/campaigns" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "YOUR_SITE_ID",
    "recipient_email": "test@example.com",
    "send_immediately": false
  }'
```

**Step 6: Check campaign**
- View in admin dashboard: http://localhost:3000/campaigns
- Should see new campaign ready to send

## 📊 Monitoring During Tests

### Check Celery Status
```bash
# Active tasks
celery -A celery_app inspect active

# Scheduled tasks
celery -A celery_app inspect scheduled

# Registered tasks
celery -A celery_app inspect registered

# Worker stats
celery -A celery_app inspect stats
```

### Check Logs
```bash
# Conductor logs
tail -f backend/conductor.log

# API logs (in terminal where start.py is running)

# Celery logs (in terminal where start_worker.py is running)
```

### Check Database
```bash
# Using psql
psql $DATABASE_URL

# Check counts
SELECT 'businesses', COUNT(*) FROM businesses
UNION ALL
SELECT 'sites', COUNT(*) FROM generated_sites
UNION ALL
SELECT 'campaigns', COUNT(*) FROM campaigns
UNION ALL
SELECT 'customers', COUNT(*) FROM customers;
```

## 🐛 Troubleshooting

### Issue: Redis connection failed
```bash
# Check if Redis is running
redis-cli ping

# Windows: Start Redis
# Download from: https://github.com/microsoftarchive/redis/releases

# Or use WSL
wsl redis-server
```

### Issue: Database connection failed
```bash
# Verify DATABASE_URL in .env
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

### Issue: Claude API errors
```bash
# Check API key
echo $ANTHROPIC_API_KEY

# Check rate limits
# Claude has rate limits - wait a bit between tests
```

### Issue: Frontend can't connect to API
```bash
# Check CORS in backend/api/main.py
# Should allow http://localhost:3000

# Check VITE_API_URL in frontend/.env
cat frontend/.env
```

### Issue: Celery tasks not running
```bash
# Check worker is running
celery -A celery_app inspect active

# Check task routing
celery -A celery_app inspect registered

# Restart worker
# Ctrl+C in worker terminal, then:
python start_worker.py
```

## ✅ Success Checklist

Before moving to VPS, verify:

- [ ] **Phase 1**: API starts, auth works, docs accessible
- [ ] **Phase 2**: Can scrape and qualify leads
- [ ] **Phase 3**: Can generate websites (test with 1-2 sites)
- [ ] **Phase 4**: Can create and queue campaigns
- [ ] **Phase 5**: Can create checkout sessions
- [ ] **Phase 6**: Frontend loads, all pages work, can login
- [ ] **Phase 7**: Celery workers process tasks
- [ ] **Phase 7**: Conductor runs complete cycle
- [ ] **Integration**: Full pipeline from scrape → site → campaign works
- [ ] **Monitoring**: Health checks return healthy status
- [ ] **Database**: All tables created and populated
- [ ] **Redis**: Can connect and store data
- [ ] **Logs**: No critical errors in any service

## 📝 Performance Notes

### Expected Local Performance

- **Scraping**: ~30 seconds per territory (API rate limits)
- **Site Generation**: ~2-5 minutes per site (Claude API calls)
- **Campaign Creation**: ~30 seconds (includes AI email generation)
- **Campaign Sending**: Instant (queue) to seconds (actual send)

### Resource Usage

- **RAM**: ~500MB (API + Celery + Redis)
- **CPU**: Low when idle, spikes during AI generation
- **Network**: Outbound only (to APIs)
- **Disk**: Minimal (~100MB for logs and temp files)

## 🎯 Next Steps

Once all tests pass locally:

1. **Document any issues** found and fixed
2. **Note API rate limits** encountered
3. **Estimate costs** based on usage (Claude API, Outscraper, etc.)
4. **Plan VPS specs** based on local performance
5. **Prepare deployment configs** for production

---

**Ready for VPS deployment when all tests pass!** ✅
