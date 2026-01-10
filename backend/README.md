# WebMagic Backend

Python FastAPI backend for the WebMagic autonomous website generation system.

## Setup

### 1. Create Virtual Environment

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `env.template` to `.env` and fill in your credentials:

```bash
cp env.template .env
# Edit .env with your actual values
```

**Required Configuration:**
- `DATABASE_URL`: Your Supabase PostgreSQL connection string
- `SECRET_KEY`: Generate with `openssl rand -hex 32`
- `ANTHROPIC_API_KEY`: Get from https://console.anthropic.com
- `OUTSCRAPER_API_KEY`: Get from https://app.outscraper.com
- `RECURRENTE_PUBLIC_KEY` & `RECURRENTE_SECRET_KEY`: Get from Recurrente dashboard

### 4. Run the Application

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Project Structure

```
backend/
├── api/              # FastAPI routes
│   ├── main.py       # Application entry point
│   ├── v1/           # API version 1 routes
│   └── schemas/      # Pydantic schemas
│
├── core/             # Core functionality
│   ├── config.py     # Settings management
│   ├── database.py   # Database connection
│   ├── security.py   # Auth utilities
│   └── exceptions.py # Custom exceptions
│
├── models/           # SQLAlchemy models
│   ├── base.py       # Base model
│   ├── user.py       # Admin users
│   └── business.py   # Business leads
│
├── services/         # Business logic
│   ├── hunter/       # Scraping module
│   ├── creative/     # AI generation
│   ├── pitcher/      # Email outreach
│   ├── payments/     # Recurrente integration
│   └── platform/     # Site hosting
│
└── tasks/            # Celery async tasks
```

## Development

### Run Tests

```bash
pytest
```

### Format Code

```bash
black .
flake8 .
```

### Database Migrations

The database schema is already created in Supabase. To make changes:

1. Modify models in `models/`
2. Create migration via Supabase dashboard or MCP
3. Apply migration

## API Endpoints

### Health Check
```bash
GET /health
```

### Authentication
```bash
POST /api/v1/auth/login
```

### Businesses
```bash
GET /api/v1/businesses
GET /api/v1/businesses/{id}
POST /api/v1/businesses
```

*More endpoints coming in future phases...*

## Next Steps

- [ ] Phase 2: Build Hunter module (scraping)
- [ ] Phase 3: Build Creative Engine (AI agents)
- [ ] Phase 4: Build Pitcher module (outreach)
- [ ] Phase 5: Integrate Recurrente payments
- [ ] Phase 6: Build Admin Dashboard

See `docs/BLUEPRINT_08_IMPLEMENTATION_PHASES.md` for full implementation plan.
