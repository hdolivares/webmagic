# WebMagic Setup Guide

## What We've Built So Far

✅ **Database**: 13 tables created in Supabase
✅ **Backend Structure**: Modular Python/FastAPI architecture  
✅ **Core Modules**: Config, database, security, exceptions
✅ **Authentication**: JWT-based login system
✅ **API Foundation**: Health check, auth endpoints

## Prerequisites

- Python 3.11+
- Supabase account (already set up)
- API keys for: Anthropic, Outscraper, Recurrente

## Quick Start

### 1. Install Python Dependencies

```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the `backend/` directory with your credentials:

```bash
# Copy the template
cp env.template .env
```

**Required values to fill in `.env`:**

```env
# Database - Get from your Supabase project settings
DATABASE_URL=postgresql+asyncpg://postgres.YOUR_PROJECT_ID:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# Security - Generate a secure key
SECRET_KEY=YOUR_SECRET_KEY_HERE

# AI API Key
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Scraping API Key  
OUTSCRAPER_API_KEY=your-outscraper-key

# Payment Gateway
RECURRENTE_PUBLIC_KEY=your-recurrente-public-key
RECURRENTE_SECRET_KEY=your-recurrente-secret-key
```

**To generate a SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**To get your Supabase DATABASE_URL:**
1. Go to your Supabase project
2. Click "Settings" → "Database"
3. Under "Connection string" → "URI" → Toggle "Display connection pooler"
4. Copy the connection string
5. Replace `postgresql://` with `postgresql+asyncpg://`
6. Replace `[YOUR-PASSWORD]` with your actual password

### 3. Start the API Server

```bash
python start.py
```

Or alternatively:
```bash
uvicorn api.main:app --reload
```

The API will start on **http://localhost:8000**

### 4. Test the API

Open a new terminal and run:

```bash
cd backend
python test_api.py
```

Or visit the interactive API docs:
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 5. Test Login

**Default admin credentials:**
- Email: `admin@webmagic.com`
- Password: `admin123`

Try logging in via the API docs or using curl:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@webmagic.com","password":"admin123"}'
```

## Project Structure

```
webmagic/
├── backend/                    # Python FastAPI backend
│   ├── api/                   # API routes
│   │   ├── main.py           # FastAPI app
│   │   ├── deps.py           # Dependencies (auth)
│   │   ├── v1/               # API v1
│   │   │   ├── auth.py       # Auth endpoints ✅
│   │   │   └── router.py     # Route aggregator
│   │   └── schemas/          # Pydantic schemas
│   │       └── auth.py       # Auth schemas
│   │
│   ├── core/                  # Core functionality
│   │   ├── config.py         # Settings ✅
│   │   ├── database.py       # DB connection ✅
│   │   ├── security.py       # Auth utils ✅
│   │   └── exceptions.py     # Custom exceptions ✅
│   │
│   ├── models/               # SQLAlchemy models
│   │   ├── base.py          # Base model ✅
│   │   ├── user.py          # Admin user ✅
│   │   └── business.py      # Business leads ✅
│   │
│   ├── services/            # Business logic (next phase)
│   ├── tasks/              # Celery tasks (next phase)
│   ├── requirements.txt    # Dependencies
│   ├── env.template        # Environment template
│   └── start.py           # Dev server script
│
└── docs/                   # Blueprint documentation
    ├── BLUEPRINT_00_OVERVIEW.md
    ├── BLUEPRINT_01_PROJECT_STRUCTURE.md
    ├── BLUEPRINT_02_DATABASE_SCHEMA.md
    └── ... (8 blueprint files)
```

## Database Tables (Supabase)

✅ **13 tables created:**
1. `admin_users` - Dashboard access
2. `coverage_grid` - Scraping conquest map
3. `businesses` - Lead storage
4. `generated_sites` - Generated websites
5. `campaigns` - Email outreach tracking
6. `customers` - Paying clients
7. `subscriptions` - Recurring billing
8. `payments` - Payment records
9. `prompt_templates` - Master AI prompts
10. `prompt_settings` - Editable prompt sections
11. `support_tickets` - Customer requests
12. `analytics_snapshots` - Daily metrics
13. `activity_log` - Audit trail

## Next Steps

### Phase 2: Hunter Module (Scraping)
- [ ] Outscraper integration
- [ ] Coverage grid management
- [ ] Business qualification logic
- [ ] Lead scraping endpoints

### Phase 3: Creative Engine (AI Agents)
- [ ] Analyst agent (business analysis)
- [ ] Concept agent (brand personality)
- [ ] Art Director agent (design brief)
- [ ] Architect agent (HTML/CSS generation)
- [ ] Prompt management UI

### Phase 4: Pitcher Module (Email Outreach)
- [ ] Email template generation
- [ ] AWS SES / SendGrid integration
- [ ] Campaign management
- [ ] Tracking pixel & link tracking

### Phase 5: Payments (Recurrente)
- [ ] Checkout session creation
- [ ] Webhook handling
- [ ] Subscription management
- [ ] Customer portal

### Phase 6: Admin Dashboard (Frontend)
- [ ] Vue.js/React admin UI
- [ ] Business management
- [ ] Site preview & editing
- [ ] Analytics dashboard
- [ ] Prompt settings editor

## Troubleshooting

### Database Connection Issues

If you see `could not connect to server`:
1. Check your Supabase connection string
2. Make sure you're using the connection pooler URL
3. Verify your database password is correct

### Import Errors

If you see `ModuleNotFoundError`:
```bash
# Make sure you're in the backend directory
cd backend

# Activate virtual environment
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Authentication Issues

If login fails:
1. Check the seed data was inserted correctly
2. Verify the password hash in the database
3. The default password is `admin123`

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Available endpoints:
- `GET /health` - Health check
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Get current user (requires auth)
- `POST /api/v1/auth/logout` - Logout

## Ready to Continue?

Once you've tested the API successfully, we can move to:
1. **Phase 2** - Build the Hunter (scraping) module
2. **Phase 3** - Build the Creative Engine (AI agents)
3. Or any other phase you'd like to prioritize!

Let me know what you'd like to build next! 🚀
