# WebMagic: Implementation Phases

## Step-by-Step Build Plan

This document provides a detailed, phased approach to building WebMagic from scratch.

---

## 📅 Overview Timeline

| Phase | Duration | Focus |
|-------|----------|-------|
| Phase 1 | 1 week | Foundation & Database |
| Phase 2 | 1-2 weeks | Hunter Module (Scraping) |
| Phase 3 | 2-3 weeks | Creative Engine (AI Agents) |
| Phase 4 | 1 week | Pitcher Module (Outreach) |
| Phase 5 | 1 week | Recurrente Payments |
| Phase 6 | 1-2 weeks | Admin Dashboard |
| Phase 7 | 1 week | Deployment & Testing |
| Phase 8 | Ongoing | Launch & Iteration |

**Total Estimated Time**: 8-12 weeks

---

## 🏗️ Phase 1: Foundation & Database (Week 1)

### Goals
- Set up development environment
- Create database schema
- Build core backend structure

### Tasks

#### 1.1 Project Setup
```bash
# Create project structure
mkdir -p webmagic/{backend,admin_dashboard,docs,scripts,tests}
cd webmagic

# Initialize Git
git init
echo "# WebMagic" > README.md

# Create Python virtual environment
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy[asyncio] asyncpg alembic pydantic-settings
pip install anthropic httpx python-jose[cryptography] passlib[bcrypt]
pip freeze > requirements.txt
```

#### 1.2 Core Module
- [ ] Create `core/config.py` - Settings management
- [ ] Create `core/database.py` - SQLAlchemy async setup
- [ ] Create `core/security.py` - Auth utilities
- [ ] Create `core/exceptions.py` - Custom exceptions

#### 1.3 Database Models
- [ ] Create `models/base.py` - Base model with UUID, timestamps
- [ ] Create `models/coverage.py` - CoverageGrid model
- [ ] Create `models/business.py` - Business model
- [ ] Create `models/site.py` - GeneratedSite model
- [ ] Create `models/campaign.py` - Campaign model
- [ ] Create `models/customer.py` - Customer, Subscription, Payment models
- [ ] Create `models/prompt_settings.py` - PromptSettings, PromptTemplate
- [ ] Create `models/user.py` - AdminUser model

#### 1.4 Database Migrations
```bash
# Initialize Alembic
alembic init migrations

# Edit alembic.ini and env.py for async

# Create initial migration
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

#### 1.5 Basic API Setup
- [ ] Create `api/main.py` - FastAPI app
- [ ] Create `api/deps.py` - Dependencies
- [ ] Create `api/v1/router.py` - Route aggregator
- [ ] Create `api/v1/auth.py` - Login endpoint

### Deliverables
- ✅ Running FastAPI server
- ✅ PostgreSQL with all tables created
- ✅ Basic authentication working
- ✅ Health check endpoint

### Verification
```bash
# Start server
uvicorn api.main:app --reload

# Test health
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# Test auth
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "password": "test123"}'
```

---

## 🔍 Phase 2: Hunter Module (Weeks 2-3)

### Goals
- Integrate Outscraper API
- Build lead filtering logic
- Create autopilot conductor

### Tasks

#### 2.1 Outscraper Integration
- [ ] Create `services/hunter/__init__.py`
- [ ] Create `services/hunter/scraper.py` - API client
- [ ] Test with sample queries
- [ ] Handle rate limits and errors

#### 2.2 Lead Filtering
- [ ] Create `services/hunter/filters.py` - Qualification logic
- [ ] Implement scoring algorithm
- [ ] Add chain detection (exclude McDonald's, etc.)
- [ ] Create unit tests

#### 2.3 Data Enrichment
- [ ] Create `services/hunter/enricher.py`
- [ ] Extract review highlights (basic, without AI yet)
- [ ] Normalize data format

#### 2.4 Autopilot Conductor
- [ ] Create `services/hunter/conductor.py`
- [ ] Implement target selection (priority-based)
- [ ] Track coverage status
- [ ] Handle retries and cooldowns

#### 2.5 Celery Tasks
- [ ] Create `tasks/celery_app.py` - Celery configuration
- [ ] Create `tasks/hunter_tasks.py`
- [ ] Implement `scrape_location` task
- [ ] Implement `run_autopilot_tick` task

#### 2.6 API Endpoints
- [ ] Create `api/v1/businesses.py` - CRUD endpoints
- [ ] Create `api/v1/coverage.py` - Coverage grid management
- [ ] Create `api/schemas/business.py` - Pydantic schemas

#### 2.7 Seed Data
- [ ] Create `scripts/seed_coverage_grid.py` - US cities
- [ ] Create `scripts/seed_industries.py` - Industry list

### Deliverables
- ✅ Scraping 50 businesses per query
- ✅ Filtering down to qualified leads
- ✅ Saving leads to database
- ✅ Celery tasks running

### Verification
```python
# Test scraper manually
from services.hunter.scraper import OutscraperClient

client = OutscraperClient()
results = await client.search_businesses(
    query="Plumbers",
    city="Austin",
    state="TX",
    limit=10
)
print(f"Found {len(results)} businesses")

# Check filtering
from services.hunter.filters import LeadQualifier
qualifier = LeadQualifier()
qualified = qualifier.filter_batch(results)
print(f"Qualified: {len(qualified)}")
```

---

## 🎨 Phase 3: Creative Engine (Weeks 4-6)

### Goals
- Build all 4 AI agents
- Create prompt management system
- Generate first websites

### Tasks

#### 3.1 Base Agent
- [ ] Create `services/creative/__init__.py`
- [ ] Create `services/creative/agents/__init__.py`
- [ ] Create `services/creative/agents/base.py` - Claude client

#### 3.2 Prompt Loader
- [ ] Create `services/creative/prompts/__init__.py`
- [ ] Create `services/creative/prompts/loader.py`
- [ ] Create `services/creative/prompts/builder.py`
- [ ] Seed initial prompts in database

#### 3.3 Analyst Agent
- [ ] Create `services/creative/agents/analyst.py`
- [ ] Implement review analysis
- [ ] Extract brand archetype
- [ ] Generate review highlights

**Test:**
```python
analyst = AnalystAgent(prompt_loader)
result = await analyst.analyze({
    "name": "Joe's Pizza",
    "category": "Restaurant",
    "rating": 4.8,
    "review_count": 150,
    "reviews_data": [...]
})
print(result["review_highlight"])
print(result["brand_archetype"])
```

#### 3.4 Concept Agent
- [ ] Create `services/creative/agents/concept.py`
- [ ] Generate 3 brand concepts
- [ ] Select best concept
- [ ] Output Creative DNA

#### 3.5 Art Director Agent
- [ ] Create `services/creative/agents/director.py`
- [ ] Generate typography choices
- [ ] Generate color palette
- [ ] Define loader, hero, interactions
- [ ] Output Design Brief

**Test:**
```python
director = ArtDirectorAgent(prompt_loader)
brief = await director.create_brief(business, creative_dna)
print(brief["vibe"])
print(brief["typography"])
print(brief["colors"])
```

#### 3.6 Architect Agent
- [ ] Create `services/creative/agents/architect.py`
- [ ] Generate HTML with Tailwind
- [ ] Include GSAP animations
- [ ] Add responsive design
- [ ] Include "Claim" bar

#### 3.7 Pipeline Orchestrator
- [ ] Create `services/creative/orchestrator.py`
- [ ] Chain all 4 agents
- [ ] Handle errors gracefully
- [ ] Log all outputs for debugging

#### 3.8 Celery Tasks
- [ ] Create `tasks/creative_tasks.py`
- [ ] Implement `generate_site_for_business`
- [ ] Implement `take_screenshots`

#### 3.9 API Endpoints
- [ ] Create `api/v1/sites.py` - Site management
- [ ] Create `api/v1/settings.py` - Prompt settings
- [ ] Create `api/schemas/site.py`
- [ ] Create `api/schemas/settings.py`

### Deliverables
- ✅ Full pipeline generating HTML
- ✅ Creative DNA stored in database
- ✅ Prompt settings editable via API
- ✅ 10 test sites generated

### Verification
```python
# Generate a site
from services.creative.orchestrator import CreativePipeline

pipeline = CreativePipeline(db)
result = await pipeline.generate({
    "name": "Tony's Auto Repair",
    "category": "Auto Repair",
    "rating": 4.8,
    "city": "Austin",
    "state": "TX"
})

print(f"Success: {result.success}")
print(f"HTML length: {len(result.html_content)}")
print(f"Vibe: {result.design_brief.get('vibe')}")

# Save to file and open in browser
with open("test_site.html", "w") as f:
    f.write(result.html_content)
```

---

## 📧 Phase 4: Pitcher Module (Week 7)

### Goals
- Generate screenshots
- Compose personalized emails
- Send via SES/SendGrid

### Tasks

#### 4.1 Screenshot Service
- [ ] Create `services/pitcher/__init__.py`
- [ ] Create `services/pitcher/screenshot.py`
- [ ] Install Playwright
- [ ] Capture desktop (1440px) and mobile (390px)
- [ ] Save to screenshots directory

#### 4.2 Email Composer
- [ ] Create `services/pitcher/email_composer.py`
- [ ] Use review highlight in email
- [ ] Generate compelling subject line
- [ ] Include site preview link

#### 4.3 Email Sender
- [ ] Create `services/pitcher/email_sender.py`
- [ ] Implement SES integration
- [ ] Implement SendGrid as fallback
- [ ] Handle bounces and complaints

#### 4.4 Send Scheduler
- [ ] Create `services/pitcher/scheduler.py`
- [ ] Implement rate limiting (max 50/hour)
- [ ] Spread sends throughout day
- [ ] Handle timezone considerations

#### 4.5 Celery Tasks
- [ ] Create `tasks/pitcher_tasks.py`
- [ ] Implement `take_screenshots`
- [ ] Implement `send_campaign`
- [ ] Implement `process_email_queue`

#### 4.6 API Endpoints
- [ ] Create `api/v1/campaigns.py`
- [ ] Create `api/schemas/campaign.py`

### Deliverables
- ✅ Screenshots generating automatically
- ✅ Emails composing with personalization
- ✅ Test emails sending successfully
- ✅ Campaign tracking in database

### Verification
```python
# Take screenshots
from services.pitcher.screenshot import ScreenshotService

service = ScreenshotService()
screenshots = await service.capture(
    html_path="/var/www/sites/test/index.html",
    output_dir="/var/www/screenshots",
    subdomain="test"
)
print(screenshots["desktop"])
print(screenshots["mobile"])

# Send test email
from services.pitcher.email_sender import EmailSender

sender = EmailSender()
result = await sender.send(
    to="test@example.com",
    subject="Test Email",
    body="This is a test"
)
print(result["message_id"])
```

---

## 💳 Phase 5: Recurrente Payments (Week 8)

### Goals
- Integrate Recurrente API
- Handle webhooks
- Complete purchase flow

### Tasks

#### 5.1 Recurrente Client
- [ ] Create `services/payments/__init__.py`
- [ ] Create `services/payments/client.py`
- [ ] Test connection with API

#### 5.2 Checkout Service
- [ ] Create `services/payments/checkout.py`
- [ ] Create checkout with setup + subscription
- [ ] Handle success/cancel URLs
- [ ] Store checkout metadata

#### 5.3 Subscription Service
- [ ] Create `services/payments/subscriptions.py`
- [ ] Get subscription status
- [ ] Cancel subscription

#### 5.4 Webhook Handler
- [ ] Create `services/payments/webhooks.py`
- [ ] Handle `payment_intent.succeeded`
- [ ] Handle `payment_intent.failed`
- [ ] Handle `subscription.cancel`
- [ ] Handle `subscription.past_due`

#### 5.5 Refund Service
- [ ] Create `services/payments/refunds.py`
- [ ] Implement same-day refund

#### 5.6 API Endpoints
- [ ] Create `api/v1/payments.py`
- [ ] Webhook endpoint
- [ ] Create checkout endpoint
- [ ] Status check endpoint

#### 5.7 Mock Webhook Script
- [ ] Create `scripts/mock_webhook.py`
- [ ] Test all event types locally

#### 5.8 Post-Purchase Flow
- [ ] Create `tasks/payment_tasks.py`
- [ ] Deploy site to production subdomain
- [ ] Send welcome email
- [ ] Update all statuses

### Deliverables
- ✅ Checkout sessions creating
- ✅ Webhooks processing correctly
- ✅ Customers created on purchase
- ✅ Sites deployed after payment

### Verification
```python
# Create checkout
from services.payments.checkout import CheckoutService, CheckoutConfig

service = CheckoutService()
result = await service.create_website_checkout(
    CheckoutConfig(
        business_name="Tony's Auto Repair",
        site_id="test-site-id",
        customer_email="tony@example.com"
    )
)
print(result["checkout_url"])
# Open URL in browser and complete test payment
```

---

## 🖥️ Phase 6: Admin Dashboard (Weeks 9-10)

### Goals
- Build Next.js dashboard
- Implement all management pages
- Create prompt editor

### Tasks

#### 6.1 Project Setup
```bash
cd admin_dashboard
npx create-next-app@latest . --typescript --tailwind --app
npm install @tanstack/react-query lucide-react recharts
```

#### 6.2 Design System
- [ ] Create `styles/variables.css`
- [ ] Create `styles/components.css`
- [ ] Set up dark mode support

#### 6.3 Layout Components
- [ ] Create `components/layout/sidebar.tsx`
- [ ] Create `components/layout/header.tsx`
- [ ] Create dashboard layout

#### 6.4 Dashboard Home
- [ ] Create stat cards
- [ ] Create conversion funnel chart
- [ ] Create recent activity feed

#### 6.5 Businesses Page
- [ ] List view with filtering
- [ ] Detail view
- [ ] Status management

#### 6.6 Sites Page
- [ ] List view with previews
- [ ] Detail view with iframe preview
- [ ] Regeneration trigger

#### 6.7 Campaigns Page
- [ ] List view with status
- [ ] Email content preview
- [ ] Analytics (opens, clicks)

#### 6.8 Customers Page
- [ ] List view
- [ ] Subscription management
- [ ] Payment history

#### 6.9 Coverage Map Page
- [ ] US map visualization
- [ ] City/industry matrix
- [ ] Priority adjustment

#### 6.10 Prompt Settings Page
- [ ] Agent selection
- [ ] Section editor (rich text)
- [ ] Version history
- [ ] Test button

#### 6.11 Analytics Page
- [ ] Conversion charts
- [ ] Revenue metrics
- [ ] Cost analysis

### Deliverables
- ✅ Full admin dashboard running
- ✅ All pages functional
- ✅ Prompt editing working
- ✅ Dark mode toggle

### Verification
- Navigate through all pages
- Edit a prompt section
- View site preview
- Check responsive design

---

## 🚀 Phase 7: Deployment & Testing (Week 11)

### Goals
- Deploy to production server
- Configure Nginx
- Run end-to-end tests

### Tasks

#### 7.1 Server Setup
- [ ] Provision server (Hetzner/DO)
- [ ] Run setup scripts
- [ ] Install all dependencies

#### 7.2 Database Setup
- [ ] Create PostgreSQL database
- [ ] Run migrations
- [ ] Seed initial data

#### 7.3 Nginx Configuration
- [ ] Configure API reverse proxy
- [ ] Configure admin dashboard
- [ ] Configure wildcard subdomain for sites

#### 7.4 SSL Certificates
- [ ] Install Certbot
- [ ] Generate certificates
- [ ] Configure auto-renewal

#### 7.5 Process Management
- [ ] Configure Supervisor
- [ ] Start all services
- [ ] Verify auto-restart

#### 7.6 DNS Configuration
- [ ] Point api.webmagic.com to server
- [ ] Point admin.webmagic.com to server
- [ ] Configure *.sites.webmagic.com wildcard

#### 7.7 Recurrente Configuration
- [ ] Add production webhook URL
- [ ] Test live payment (refund immediately)

#### 7.8 Monitoring
- [ ] Set up log rotation
- [ ] Configure basic alerting
- [ ] Test health checks

#### 7.9 End-to-End Testing
- [ ] Full pipeline test (scrape → generate → email → payment)
- [ ] Verify site deployment
- [ ] Check email delivery
- [ ] Confirm webhook processing

### Deliverables
- ✅ Production server running
- ✅ All endpoints accessible via HTTPS
- ✅ Sites serving on subdomains
- ✅ Payments processing correctly

---

## 🎯 Phase 8: Launch & Iteration (Week 12+)

### Goals
- Launch autopilot
- Monitor performance
- Iterate on prompts

### Tasks

#### 8.1 Initial Launch
- [ ] Seed coverage grid (top 50 US cities)
- [ ] Start with 5 industries
- [ ] Run autopilot at low volume (10 leads/day)

#### 8.2 Monitor & Adjust
- [ ] Track email open rates
- [ ] Track click rates
- [ ] Monitor site quality

#### 8.3 Prompt Iteration
- [ ] A/B test subject lines
- [ ] Improve design vibe selection
- [ ] Refine review highlight extraction

#### 8.4 Scale Up
- [ ] Increase to 50 leads/day
- [ ] Add more industries
- [ ] Expand to more cities

### Success Metrics

| Metric | Target (Month 1) | Target (Month 3) |
|--------|------------------|------------------|
| Leads/day | 50 | 200 |
| Sites generated | 1,000 | 5,000 |
| Email open rate | 30% | 35% |
| Click rate | 5% | 8% |
| Conversion rate | 0.5% | 1% |
| Revenue | $3,000 | $15,000 |

---

## ✅ Pre-Launch Checklist

### Technical
- [ ] All endpoints tested
- [ ] Error handling complete
- [ ] Rate limiting configured
- [ ] Logging comprehensive
- [ ] Backups automated

### Legal
- [ ] CAN-SPAM compliance (unsubscribe link)
- [ ] Terms of service drafted
- [ ] Privacy policy drafted

### Business
- [ ] Recurrente account approved
- [ ] Email sender reputation warmed
- [ ] Support email configured

### Monitoring
- [ ] Uptime monitoring (UptimeRobot)
- [ ] Error alerting configured
- [ ] Payment failure alerts

---

## 🎉 Launch Day

```bash
# Start autopilot
ssh webmagic@server

# Verify all services running
sudo supervisorctl status

# Start first autopilot run
cd /var/www/webmagic/backend
source .venv/bin/activate
python -c "from tasks.hunter_tasks import run_autopilot_tick; run_autopilot_tick.delay()"

# Monitor logs
tail -f /home/webmagic/logs/api.log
tail -f /home/webmagic/logs/celery.log
```

**🚀 WebMagic is live!**
