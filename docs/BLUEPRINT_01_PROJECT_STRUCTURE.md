# WebMagic: Project Structure

## Complete File & Folder Organization

This document details every file and folder in the WebMagic project with estimated line counts and responsibilities.

---

## 📁 Root Directory

```
webmagic/
├── 📂 backend/               # Python FastAPI application
├── 📂 admin_dashboard/       # Next.js admin interface
├── 📂 generated_sites/       # Output directory for generated websites
├── 📂 migrations/            # Alembic database migrations
├── 📂 docs/                  # Blueprint & documentation
├── 📂 tests/                 # Test suites
├── 📂 scripts/               # Utility scripts
├── docker-compose.yml        # Local development setup
├── docker-compose.prod.yml   # Production setup
├── requirements.txt          # Python dependencies
├── pyproject.toml           # Python project config
├── .env.example             # Environment template
├── .gitignore
└── README.md
```

---

## 📂 Backend Structure

```
backend/
├── 📂 core/                          # Core application setup
│   ├── __init__.py
│   ├── config.py                     # (~200 lines)
│   │   └── Settings class, env loading, validation
│   │
│   ├── database.py                   # (~150 lines)
│   │   └── SQLAlchemy engine, session factory, deps
│   │
│   ├── security.py                   # (~300 lines)
│   │   └── Password hashing, JWT tokens, API key validation
│   │
│   ├── exceptions.py                 # (~100 lines)
│   │   └── Custom exception classes
│   │
│   └── constants.py                  # (~80 lines)
│       └── Enums, status codes, magic strings
│
├── 📂 models/                        # SQLAlchemy ORM models
│   ├── __init__.py                   # Export all models
│   ├── base.py                       # (~50 lines)
│   │   └── Base class with common fields (id, timestamps)
│   │
│   ├── coverage.py                   # (~150 lines)
│   │   └── CoverageGrid model
│   │
│   ├── business.py                   # (~250 lines)
│   │   └── Business model (the leads)
│   │
│   ├── site.py                       # (~200 lines)
│   │   └── GeneratedSite model
│   │
│   ├── campaign.py                   # (~200 lines)
│   │   └── Campaign, EmailLog models
│   │
│   ├── customer.py                   # (~250 lines)
│   │   └── Customer, Subscription models
│   │
│   ├── prompt_settings.py            # (~300 lines)
│   │   └── PromptTemplate, PromptVersion, AgentConfig
│   │
│   ├── analytics.py                  # (~200 lines)
│   │   └── MetricSnapshot, ConversionEvent
│   │
│   └── user.py                       # (~150 lines)
│       └── AdminUser model (dashboard access)
│
├── 📂 services/                      # Business logic layer
│   ├── __init__.py
│   │
│   ├── 📂 hunter/                    # Scraping module
│   │   ├── __init__.py
│   │   ├── scraper.py                # (~400 lines)
│   │   │   └── OutscraperClient, search methods
│   │   │
│   │   ├── filters.py                # (~250 lines)
│   │   │   └── LeadQualifier, scoring logic
│   │   │
│   │   ├── enricher.py               # (~200 lines)
│   │   │   └── ReviewAnalyzer, data enhancement
│   │   │
│   │   └── conductor.py              # (~300 lines)
│   │       └── AutopilotConductor, grid traversal
│   │
│   ├── 📂 creative/                  # AI generation module
│   │   ├── __init__.py
│   │   ├── orchestrator.py           # (~350 lines)
│   │   │   └── CreativePipeline, agent coordination
│   │   │
│   │   ├── 📂 agents/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # (~150 lines)
│   │   │   │   └── BaseAgent class, common methods
│   │   │   │
│   │   │   ├── analyst.py            # (~400 lines)
│   │   │   │   └── AnalystAgent - extracts brand DNA
│   │   │   │
│   │   │   ├── concept.py            # (~400 lines)
│   │   │   │   └── ConceptAgent - invents brand personality
│   │   │   │
│   │   │   ├── director.py           # (~500 lines)
│   │   │   │   └── ArtDirectorAgent - design brief
│   │   │   │
│   │   │   └── architect.py          # (~500 lines)
│   │   │       └── ArchitectAgent - writes code
│   │   │
│   │   ├── 📂 prompts/
│   │   │   ├── __init__.py
│   │   │   ├── loader.py             # (~200 lines)
│   │   │   │   └── PromptLoader - fetches from DB
│   │   │   │
│   │   │   └── builder.py            # (~250 lines)
│   │   │       └── PromptBuilder - template rendering
│   │   │
│   │   └── 📂 validators/
│   │       ├── __init__.py
│   │       ├── html_validator.py     # (~150 lines)
│   │       └── design_validator.py   # (~150 lines)
│   │
│   ├── 📂 pitcher/                   # Outreach module
│   │   ├── __init__.py
│   │   ├── screenshot.py             # (~250 lines)
│   │   │   └── ScreenshotService - Playwright integration
│   │   │
│   │   ├── email_composer.py         # (~300 lines)
│   │   │   └── EmailComposer - personalized emails
│   │   │
│   │   ├── email_sender.py           # (~250 lines)
│   │   │   └── EmailSender - SES/SendGrid
│   │   │
│   │   └── scheduler.py              # (~200 lines)
│   │       └── SendScheduler - timing, rate limits
│   │
│   ├── 📂 platform/                  # Site hosting module
│   │   ├── __init__.py
│   │   ├── deployer.py               # (~300 lines)
│   │   │   └── SiteDeployer - file system ops
│   │   │
│   │   ├── domain_manager.py         # (~250 lines)
│   │   │   └── DomainManager - subdomain/custom domains
│   │   │
│   │   └── asset_manager.py          # (~200 lines)
│   │       └── AssetManager - images, files
│   │
│   ├── 📂 payments/                  # Recurrente integration
│   │   ├── __init__.py
│   │   ├── client.py                 # (~300 lines)
│   │   │   └── RecurrenteClient - API wrapper
│   │   │
│   │   ├── checkout.py               # (~250 lines)
│   │   │   └── CheckoutService - session creation
│   │   │
│   │   ├── subscriptions.py          # (~300 lines)
│   │   │   └── SubscriptionService - recurring billing
│   │   │
│   │   ├── webhooks.py               # (~350 lines)
│   │   │   └── WebhookHandler - event processing
│   │   │
│   │   └── refunds.py                # (~150 lines)
│   │       └── RefundService - same-day refunds
│   │
│   └── 📂 concierge/                 # Maintenance module
│       ├── __init__.py
│       ├── ticket_handler.py         # (~300 lines)
│       │   └── TicketProcessor - support requests
│       │
│       └── site_updater.py           # (~350 lines)
│           └── SiteUpdater - AI-powered edits
│
├── 📂 api/                           # FastAPI routes
│   ├── __init__.py
│   ├── main.py                       # (~100 lines)
│   │   └── FastAPI app initialization
│   │
│   ├── deps.py                       # (~100 lines)
│   │   └── Dependency injection
│   │
│   ├── 📂 v1/
│   │   ├── __init__.py
│   │   ├── router.py                 # (~50 lines)
│   │   │   └── Route aggregator
│   │   │
│   │   ├── auth.py                   # (~200 lines)
│   │   │   └── Login, logout, token refresh
│   │   │
│   │   ├── businesses.py             # (~300 lines)
│   │   │   └── CRUD for businesses
│   │   │
│   │   ├── sites.py                  # (~300 lines)
│   │   │   └── Site management endpoints
│   │   │
│   │   ├── campaigns.py              # (~250 lines)
│   │   │   └── Campaign endpoints
│   │   │
│   │   ├── payments.py               # (~300 lines)
│   │   │   └── Webhook receiver, checkout
│   │   │
│   │   ├── settings.py               # (~250 lines)
│   │   │   └── Prompt settings CRUD
│   │   │
│   │   ├── coverage.py               # (~200 lines)
│   │   │   └── Coverage grid management
│   │   │
│   │   └── analytics.py              # (~200 lines)
│   │       └── Stats and metrics
│   │
│   └── 📂 schemas/
│       ├── __init__.py
│       ├── common.py                 # (~100 lines)
│       ├── business.py               # (~200 lines)
│       ├── site.py                   # (~150 lines)
│       ├── campaign.py               # (~150 lines)
│       ├── settings.py               # (~150 lines)
│       └── analytics.py              # (~100 lines)
│
├── 📂 tasks/                         # Celery async tasks
│   ├── __init__.py
│   ├── celery_app.py                 # (~100 lines)
│   │   └── Celery configuration
│   │
│   ├── hunter_tasks.py               # (~250 lines)
│   │   └── scrape_location, process_leads
│   │
│   ├── creative_tasks.py             # (~300 lines)
│   │   └── generate_site, generate_screenshots
│   │
│   ├── pitcher_tasks.py              # (~250 lines)
│   │   └── send_campaign, send_email
│   │
│   ├── payment_tasks.py              # (~200 lines)
│   │   └── process_payment, handle_subscription
│   │
│   └── maintenance_tasks.py          # (~200 lines)
│       └── cleanup, analytics_snapshot
│
└── 📂 utils/                         # Shared utilities
    ├── __init__.py
    ├── slugify.py                    # (~50 lines)
    ├── validators.py                 # (~150 lines)
    ├── formatters.py                 # (~100 lines)
    ├── logger.py                     # (~100 lines)
    └── retry.py                      # (~80 lines)
```

---

## 📂 Admin Dashboard Structure

```
admin_dashboard/
├── 📂 src/
│   ├── 📂 app/                       # Next.js App Router
│   │   ├── layout.tsx                # Root layout with providers
│   │   ├── page.tsx                  # Dashboard home
│   │   ├── globals.css               # Global styles
│   │   │
│   │   ├── 📂 (auth)/                # Auth route group
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   └── layout.tsx
│   │   │
│   │   ├── 📂 (dashboard)/           # Main app route group
│   │   │   ├── layout.tsx            # Dashboard shell
│   │   │   │
│   │   │   ├── 📂 businesses/
│   │   │   │   ├── page.tsx          # List view
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx      # Detail view
│   │   │   │
│   │   │   ├── 📂 sites/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx
│   │   │   │
│   │   │   ├── 📂 campaigns/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx
│   │   │   │
│   │   │   ├── 📂 customers/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx
│   │   │   │
│   │   │   ├── 📂 coverage/
│   │   │   │   └── page.tsx          # Coverage map
│   │   │   │
│   │   │   ├── 📂 analytics/
│   │   │   │   └── page.tsx          # Charts & metrics
│   │   │   │
│   │   │   └── 📂 settings/
│   │   │       ├── page.tsx          # General settings
│   │   │       │
│   │   │       └── 📂 prompts/       # Prompt management
│   │   │           ├── page.tsx      # List all agents
│   │   │           └── [agentId]/
│   │   │               └── page.tsx  # Edit agent prompts
│   │   │
│   │   └── 📂 api/                   # API routes (optional)
│   │       └── health/
│   │           └── route.ts
│   │
│   ├── 📂 components/
│   │   ├── 📂 ui/                    # Shadcn components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── input.tsx
│   │   │   ├── select.tsx
│   │   │   ├── table.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── toast.tsx
│   │   │   └── ... (other primitives)
│   │   │
│   │   ├── 📂 layout/
│   │   │   ├── sidebar.tsx
│   │   │   ├── header.tsx
│   │   │   ├── nav-item.tsx
│   │   │   └── theme-toggle.tsx
│   │   │
│   │   ├── 📂 forms/
│   │   │   ├── prompt-editor.tsx     # Rich text for prompts
│   │   │   ├── business-form.tsx
│   │   │   └── settings-form.tsx
│   │   │
│   │   ├── 📂 data-display/
│   │   │   ├── data-table.tsx        # Generic data table
│   │   │   ├── stat-card.tsx
│   │   │   ├── status-badge.tsx
│   │   │   └── site-preview.tsx      # iframe preview
│   │   │
│   │   └── 📂 charts/
│   │       ├── conversion-chart.tsx
│   │       ├── revenue-chart.tsx
│   │       └── coverage-map.tsx
│   │
│   ├── 📂 lib/
│   │   ├── api.ts                    # API client
│   │   ├── utils.ts                  # Helpers
│   │   ├── auth.ts                   # Auth helpers
│   │   └── constants.ts
│   │
│   ├── 📂 hooks/
│   │   ├── use-businesses.ts
│   │   ├── use-sites.ts
│   │   ├── use-prompts.ts
│   │   └── use-analytics.ts
│   │
│   ├── 📂 types/
│   │   ├── business.ts
│   │   ├── site.ts
│   │   ├── campaign.ts
│   │   └── settings.ts
│   │
│   └── 📂 styles/
│       ├── variables.css             # CSS custom properties
│       └── components.css            # Semantic classes
│
├── public/
│   └── ... (static assets)
│
├── tailwind.config.ts
├── next.config.js
├── package.json
└── tsconfig.json
```

---

## 📂 Other Directories

### Tests
```
tests/
├── 📂 unit/
│   ├── 📂 services/
│   │   ├── test_hunter.py
│   │   ├── test_creative.py
│   │   └── test_payments.py
│   └── 📂 models/
│       └── test_business.py
│
├── 📂 integration/
│   ├── test_api_endpoints.py
│   ├── test_celery_tasks.py
│   └── test_recurrente.py
│
├── 📂 e2e/
│   └── test_full_pipeline.py
│
├── conftest.py                # Fixtures
└── pytest.ini
```

### Scripts
```
scripts/
├── seed_coverage_grid.py     # Populate US cities
├── seed_industries.py        # Industry categories
├── test_outscraper.py        # Manual API test
├── test_recurrente.py        # Payment test
├── backup_db.sh              # Database backup
└── deploy.sh                 # Deployment script
```

### Migrations
```
migrations/
├── env.py
├── script.py.mako
├── alembic.ini
└── 📂 versions/
    ├── 001_initial_schema.py
    ├── 002_add_prompt_settings.py
    └── ...
```

---

## 📏 Line Count Summary

| Module | Estimated Lines |
|--------|-----------------|
| Core | ~800 |
| Models | ~1,750 |
| Services (Hunter) | ~1,150 |
| Services (Creative) | ~2,650 |
| Services (Pitcher) | ~1,000 |
| Services (Platform) | ~750 |
| Services (Payments) | ~1,350 |
| Services (Concierge) | ~650 |
| API Routes | ~1,850 |
| API Schemas | ~850 |
| Celery Tasks | ~1,300 |
| Utils | ~480 |
| **Backend Total** | **~14,580** |
| Admin Dashboard | ~8,000 (estimated) |
| **Grand Total** | **~22,580** |

All files stay well under the 2,000 line target, with the largest files (~500 lines) being the AI agents.
