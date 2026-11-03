# WebMagic

**Web design and development on autopilot.**

WebMagic finds local businesses that don't have a website, generates a custom landing page for each one with a multi-agent LLM pipeline, reaches out to the owner by SMS or email with a live preview, and handles checkout, subscriptions, custom domains, and post-sale support. It covers the whole cycle from lead to paying customer with little manual work.

> **Status:** this is a portfolio project. It ran in production in 2026 and is not currently deployed. The code is here to read and run locally.

---

## How it works

```mermaid
flowchart LR
    A[Hunter<br/>Google Maps scraping] --> B[Validation<br/>does a real website exist?]
    B -->|no website| C[Creative pipeline<br/>multi-agent site generation]
    C --> D[Pitcher<br/>SMS / email outreach]
    D --> E[Checkout<br/>Recurrente payments]
    E --> F[Customer portal<br/>domains, edits, support]
```

1. **Hunter: lead discovery.** Claude plans a geographic search strategy for a city and category, splitting a metro area into zones ordered by population. Each zone is scraped from Google Maps through [Outscraper](https://outscraper.com/). Every business is geo-validated, scored for data quality, de-duplicated, and stored along with its coverage progress.
2. **Validation: is there already a website?** A multi-stage pipeline: a fast URL prescreen, then a Playwright headless-browser fetch, then an LLM that cross-references the page content against the business's name, phone, and address. When no website is listed, an LLM reviews Google results (via ScrapingDog) to look for one. Only businesses confirmed to have no site go on to generation.
3. **Creative: site generation.** A chain of specialized Claude agents:
   - **Analyst**: reads the business data and reviews, and extracts the brand archetype, emotional triggers, and differentiators.
   - **Concept**: produces brand personality and "creative DNA".
   - **Art Director**: writes a design brief covering vibe, typography, an industry-aware color palette, and motion.
   - **Architect**: generates a complete responsive single-page site in HTML, CSS, and JS.

   Hero and section images come from Google Gemini. Prompts are stored in the database and can be edited from the admin UI. A manual site builder runs the same pipeline from a free-form description, starting with an extra **Interpreter** agent.
4. **Pitcher: outreach.** Personalized SMS (LabsMobile, or Telnyx) and email (Brevo, SES, or SendGrid) campaigns, each linking to the business's live preview through a short link. The messaging layer handles opt-outs and compliance, business hours, cost budgets, and a two-way SMS inbox.
5. **Monetization and after the sale.** Checkout and recurring subscriptions run on [Recurrente](https://recurrente.com/), with abandoned-cart recovery coupons. Customers get a portal where they can connect a custom domain (DNS verification, then automatic nginx and Let's Encrypt provisioning), request edits in plain language (applied by an **Editor** agent, with versioned previews), and open support tickets.

Celery Beat runs the whole loop on a schedule: scrape, generate, create campaigns, send, sync SMS, and recover abandoned carts.

## Tech stack

| Layer | Technology |
|---|---|
| API | Python 3.12, FastAPI, SQLAlchemy 2 (async) + asyncpg, Pydantic v2 |
| Background jobs | Celery + Redis (separate queues for scraping, validation, discovery, generation, campaigns, monitoring) |
| Database | PostgreSQL |
| AI | Anthropic Claude (agents, validation, strategy), Google Gemini (images) |
| Scraping / browsing | Outscraper, ScrapingDog, Playwright |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand |
| Integrations | Recurrente (payments), LabsMobile / Telnyx (SMS), Brevo / SES / SendGrid (email) |

## Repository layout

```
backend/
  api/            FastAPI app (main.py), routers in api/v1/, Pydantic schemas
  core/           settings, database, auth/JWT, webhook verification, rate limiting
  models/         SQLAlchemy models
  services/
    hunter/       scraping, geo strategies, coverage, data quality
    validation/   prescreen -> Playwright -> LLM website validation
    discovery/    LLM-assisted website discovery
    creative/     agent pipeline, image generation, site export
    pitcher/      email/SMS campaigns and tracking
    sms/          providers, compliance, conversations
    payments/     Recurrente client, checkout, subscriptions, webhooks
    platform/     custom domains, nginx provisioning
  tasks/          Celery tasks; schedule in celery_app.py
  migrations/     historical SQL migrations (from the original deployment)
  scripts/        init_db, create_admin, seed data
  tests/
frontend/
  src/pages/      admin dashboard (businesses, coverage, campaigns, sites, messages, settings, ...)
                  customer portal (my sites, domains, edit requests, tickets) and public pages
infra/nginx/      example nginx config for serving the SPA, API, and generated sites
```

## Running locally

### Prerequisites

- Python 3.12, Node.js 20+, PostgreSQL 14+, Redis 6+
- API keys. Required: **Anthropic** and **Outscraper**. Optional, depending on the features you use: Gemini, ScrapingDog, Recurrente, LabsMobile or Telnyx, and an email provider.

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

cp env.template .env             # then fill in DATABASE_URL, SECRET_KEY and your API keys
```

Create the schema, seed the defaults, and create your admin account:

```bash
python -m scripts.init_db                 # create tables from the SQLAlchemy models
python -m scripts.seed_system_settings    # AI provider/model settings
python -m scripts.seed_prompt_templates   # agent prompt templates
python -m scripts.seed_us_cities          # optional: coverage grid of US cities
python -m scripts.create_admin you@example.com --name "Your Name"   # prompts for a password
```

Start the API, worker, and scheduler, each in its own terminal:

```bash
python start.py          # API on http://localhost:8000 (/docs when DEBUG=true)
python start_worker.py   # Celery worker (all queues)
python start_beat.py     # Celery Beat scheduler, needed only for autopilot
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev              # http://localhost:3000, proxies /api to :8000
```

On Windows, `start_all.bat` opens the API, worker, beat, and frontend together.

### Tests

```bash
cd backend && pytest
```

## Configuration

All configuration comes from environment variables. [`backend/env.template`](backend/env.template) documents each one. The important ones:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/db` |
| `SECRET_KEY` | JWT signing key: at least 32 random characters (`openssl rand -hex 32`). The app refuses to start with a weak value. |
| `DEBUG` | `true` turns on `/docs`, localhost CORS, and verbose errors. Keep it `false` anywhere public. |
| `ANTHROPIC_API_KEY`, `OUTSCRAPER_API_KEY` | Required |
| `FRONTEND_URL`, `API_URL`, `SITES_BASE_URL` | Public URLs, used for CORS, links in outreach, and webhook callbacks |
| `RECURRENTE_WEBHOOK_SECRET` | Svix signing secret. Payment webhooks are rejected without it. |
| `LABSMOBILE_WEBHOOK_TOKEN` / `TELNYX_PUBLIC_KEY` | Authenticate SMS webhooks. Unauthenticated callbacks are rejected. |

Frontend build-time variables, all optional: `VITE_API_URL`, `VITE_SITES_BASE_URL`, `VITE_PORTAL_URL`, `VITE_CONTACT_EMAIL`, `VITE_SERVER_IP`, `VITE_SMS_SENDER_NUMBER`.

## Security

- **Auth.** Admin and customer JWTs are separate token types, signed with HS256 and validated on every request. Passwords are hashed with bcrypt. Password-reset tokens are stored only as SHA-256 hashes and expire after one hour. Login attempts return a single generic error, so they don't reveal which accounts exist.
- **Rate limiting.** Login, registration, password reset, and verification resend are rate-limited per client IP. Behind a proxy, run uvicorn with `--proxy-headers` so the real client IP is used.
- **Webhooks fail closed.** Recurrente webhooks are verified with Svix HMAC signatures and a timestamp tolerance. Telnyx webhooks are verified with Ed25519 signatures. LabsMobile callbacks require a shared secret token. When a secret isn't configured, every request is rejected.
- **Untrusted URLs.** Scraped URLs are prescreened, and hostnames that resolve to private or internal addresses are rejected before any fetch (SSRF). Redirect targets are restricted to the deployment's own hosts.
- **System commands.** nginx and certbot run through `exec` with argument lists, never a shell. Domains are validated again just before provisioning.
- **Known trade-off.** The example nginx config serves generated sites on the same origin as the portal, so the visual site editor can inspect them, and auth tokens live in `localStorage`. All site HTML comes from the app's own generation pipeline. If you accept arbitrary customer HTML, serve sites from a separate origin or move auth to HttpOnly cookies.

Found a vulnerability? Please open a private [security advisory](../../security/advisories/new) instead of a public issue.
