# WebMagic - Dependencies & Installation Guide

Complete list of all dependencies required to run WebMagic locally.

---

## Backend Dependencies (Python 3.12+)

### Install Command
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### Core Dependencies

#### Web Framework
- `fastapi==0.109.0` - Modern, fast web framework
- `uvicorn[standard]==0.27.0` - ASGI server
- `python-multipart==0.0.6` - Form/file uploads

#### Database
- `sqlalchemy[asyncio]==2.0.25` - ORM with async support
- `asyncpg==0.29.0` - PostgreSQL async driver
- `alembic==1.13.1` - Database migrations

#### Configuration & Validation
- `pydantic==2.5.3` - Data validation
- `pydantic-settings==2.1.0` - Settings management
- `python-dotenv==1.0.0` - Environment variables
- `email-validator==2.3.0` - Email validation (required by pydantic)

#### Authentication & Security
- `python-jose[cryptography]==3.3.0` - JWT tokens
- `passlib[bcrypt]==1.7.4` - Password hashing
- `bcrypt==4.1.2` - Bcrypt algorithm

#### HTTP Client
- `httpx==0.26.0` - Async HTTP client

#### AI/LLM
- `anthropic==0.75.0` - Claude AI API client

#### Task Queue
- `celery==5.3.6` - Distributed task queue
- `redis==5.0.1` - Message broker & result backend

#### Email Services
- `boto3==1.34.28` - AWS SDK (for SES)
- `sendgrid==6.11.0` - SendGrid API

#### Web Scraping
- `outscraper==6.0.0` - Google Maps scraper
- `playwright==1.41.2` - Browser automation

#### Utilities
- `python-slugify==8.0.1` - URL slug generation
- `pytz==2024.1` - Timezone handling

#### Development Tools
- `pytest==7.4.4` - Testing framework
- `pytest-asyncio==0.23.3` - Async testing
- `black==24.1.1` - Code formatter
- `flake8==7.0.0` - Code linter

---

## Frontend Dependencies (Node.js 18+)

### Install Command
```bash
cd frontend
npm install
```

### Core Dependencies

#### React Framework
- `react@^18.2.0` - UI library
- `react-dom@^18.2.0` - React DOM renderer
- `react-router-dom@^6.20.0` - Routing

#### State Management & Data Fetching
- `@tanstack/react-query@^5.14.2` - Server state management
- `axios@^1.6.2` - HTTP client
- `zustand@^4.4.7` - Client state management

#### UI Components & Utilities
- `recharts@^2.10.3` - Charts and graphs
- `date-fns@^3.0.0` - Date formatting
- `lucide-react@^0.294.0` - Icon library

### Development Dependencies

#### TypeScript
- `typescript@^5.2.2` - TypeScript compiler
- `@types/react@^18.2.43` - React type definitions
- `@types/react-dom@^18.2.17` - React DOM types

#### Build Tools
- `vite@^5.0.8` - Build tool & dev server
- `@vitejs/plugin-react@^4.2.1` - React plugin for Vite

#### CSS/Styling
- `tailwindcss@^3.3.6` - Utility-first CSS framework
- `postcss@^8.4.32` - CSS processor
- `autoprefixer@^10.4.16` - CSS autoprefixer

#### Code Quality
- `eslint@^8.55.0` - JavaScript linter
- `@typescript-eslint/eslint-plugin@^6.14.0` - TypeScript ESLint plugin
- `@typescript-eslint/parser@^6.14.0` - TypeScript parser
- `eslint-plugin-react-hooks@^4.6.0` - React Hooks linting
- `eslint-plugin-react-refresh@^0.4.5` - React Fast Refresh linting

---

## External Services Required

### Database
- **Supabase PostgreSQL** (or any PostgreSQL 14+)
  - Connection pooler support (port 6543)
  - asyncpg driver compatibility
  - Required tables created via MCP or migrations

### Redis (Optional - for background tasks)
- **Redis 6+**
  - Used by Celery for task queue
  - Only needed for automation features
  - Can run locally or use cloud service

### API Keys (Add to backend/.env)

#### Required for Core Features
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:6543/db

# Security
SECRET_KEY=your-secret-key-here

# AI Agent
ANTHROPIC_API_KEY=your-anthropic-key

# Business Scraping
OUTSCRAPER_API_KEY=your-outscraper-key

# Payments
RECURRENTE_PUBLIC_KEY=your-public-key
RECURRENTE_SECRET_KEY=your-secret-key
```

#### Optional Services
```bash
# Email (choose one)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
# or
SENDGRID_API_KEY=your-sendgrid-key

# Redis (for background tasks)
REDIS_URL=redis://localhost:6379/0
```

---

## System Dependencies

### Windows
- Python 3.12+ ([python.org](https://www.python.org/downloads/))
- Node.js 18+ ([nodejs.org](https://nodejs.org/))
- Git ([git-scm.com](https://git-scm.com/))

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip nodejs npm git
```

### macOS
```bash
brew install python@3.12 node git
```

---

## Quick Start Installation

### 1. Clone & Setup Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp env.template .env
# Edit .env with your credentials
```

### 2. Setup Frontend
```bash
cd frontend
npm install
```

### 3. Start Services
```bash
# Terminal 1 - Backend
cd backend
venv\Scripts\activate
python start.py

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### 4. Access Application
- **Frontend**: http://localhost:3001/
- **Backend API**: http://localhost:8000/
- **API Docs**: http://localhost:8000/docs

### 5. Default Login
- **Email**: admin@webmagic.com
- **Password**: admin123

---

## Troubleshooting

### Backend Issues

**ModuleNotFoundError**
```bash
# Make sure venv is activated and dependencies installed
pip install -r requirements.txt
```

**Database Connection Error**
- Verify `DATABASE_URL` in `.env` starts with `postgresql+asyncpg://`
- Use session pooler (port 6543) for IPv4 networks
- Check Supabase project is active

**Import Errors**
```bash
# Reinstall with latest versions
pip install --upgrade -r requirements.txt
```

### Frontend Issues

**Module not found**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Port already in use**
- Frontend uses port 3001 by default (configurable in vite.config.ts)
- Backend uses port 8000 by default (configurable in start.py)

---

## Production Deployment

### Additional Requirements
- Nginx or similar reverse proxy
- SSL certificates (Let's Encrypt recommended)
- Process manager (systemd, PM2, or supervisord)
- Environment-specific .env files
- Database backup strategy

See `docs/BLUEPRINT_07_DEPLOYMENT.md` for detailed production setup.

---

## Keeping Dependencies Updated

### Check for Updates
```bash
# Backend
pip list --outdated

# Frontend
npm outdated
```

### Update All (use with caution)
```bash
# Backend
pip install --upgrade -r requirements.txt

# Frontend
npm update
```

### Security Updates
```bash
# Backend
pip install --upgrade pip
pip-audit  # Install with: pip install pip-audit

# Frontend
npm audit
npm audit fix
```

---

## Version Compatibility

- **Python**: 3.12+ (tested on 3.12.3)
- **Node.js**: 18+ (tested on 18.x and 20.x)
- **PostgreSQL**: 14+ (Supabase compatible)
- **Redis**: 6+ (optional)

---

For more information, see:
- `QUICKSTART.md` - Quick setup guide
- `LOCAL_TESTING.md` - Testing all features
- `docs/` - Detailed architecture and deployment guides
