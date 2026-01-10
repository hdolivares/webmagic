# WebMagic: Software Blueprint

## Master Document Index

This blueprint is organized into multiple documents for better maintainability:

| Document | Description |
|----------|-------------|
| [BLUEPRINT_00_OVERVIEW.md](./BLUEPRINT_00_OVERVIEW.md) | This file - Overview & Architecture |
| [BLUEPRINT_01_PROJECT_STRUCTURE.md](./BLUEPRINT_01_PROJECT_STRUCTURE.md) | Complete file/folder structure |
| [BLUEPRINT_02_DATABASE_SCHEMA.md](./BLUEPRINT_02_DATABASE_SCHEMA.md) | PostgreSQL tables & relationships |
| [BLUEPRINT_03_BACKEND_MODULES.md](./BLUEPRINT_03_BACKEND_MODULES.md) | Python backend module specs |
| [BLUEPRINT_04_AI_AGENTS.md](./BLUEPRINT_04_AI_AGENTS.md) | AI agent pipeline & prompts |
| [BLUEPRINT_05_PAYMENTS_RECURRENTE.md](./BLUEPRINT_05_PAYMENTS_RECURRENTE.md) | Recurrente integration guide |
| [BLUEPRINT_06_FRONTEND_ADMIN.md](./BLUEPRINT_06_FRONTEND_ADMIN.md) | Admin dashboard specs |
| [BLUEPRINT_07_DEPLOYMENT.md](./BLUEPRINT_07_DEPLOYMENT.md) | Server & deployment config |
| [BLUEPRINT_08_IMPLEMENTATION_PHASES.md](./BLUEPRINT_08_IMPLEMENTATION_PHASES.md) | Step-by-step build plan |

---

## 🎯 Executive Summary

**WebMagic** is an autonomous "Agency-in-a-Box" system that:

1. **Hunts**: Scrapes Google My Business for businesses without websites
2. **Creates**: Uses AI agents to generate personalized, award-winning websites
3. **Pitches**: Sends automated cold emails with live website previews
4. **Converts**: Handles payments via Recurrente (Guatemala-focused)
5. **Maintains**: AI-powered support ticket handling for site updates

---

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WEBMAGIC ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │   HUNTER    │───▶│  CREATIVE   │───▶│   PITCHER   │───▶│  PLATFORM   │   │
│  │  (Scraper)  │    │  (AI Gen)   │    │  (Outreach) │    │  (Hosting)  │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   │
│         │                 │                  │                  │           │
│         ▼                 ▼                  ▼                  ▼           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         POSTGRESQL DATABASE                          │   │
│  │  coverage_grid | businesses | campaigns | sites | prompt_settings   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                 │                  │                  │           │
│         ▼                 ▼                  ▼                  ▼           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                           REDIS (Celery)                             │   │
│  │                     Task Queue & Caching Layer                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         ADMIN DASHBOARD                              │   │
│  │   Prompt Settings | Coverage Map | Analytics | Manual Overrides      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Tech Stack

### Backend
| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.11+ | Core application logic |
| Framework | FastAPI | REST API & async support |
| Database | PostgreSQL | Primary data store |
| Cache/Queue | Redis | Celery broker & caching |
| Task Queue | Celery | Async job processing |
| ORM | SQLAlchemy 2.0 | Database abstraction |
| Migrations | Alembic | Schema versioning |

### AI & External Services
| Service | Purpose |
|---------|---------|
| Claude 3.5 Sonnet (Anthropic) | Website generation & analysis |
| Outscraper API | Google My Business data |
| Amazon SES / SendGrid | Email delivery |
| Playwright | Screenshot generation |

### Frontend (Admin Dashboard)
| Component | Technology |
|-----------|------------|
| Framework | Next.js 14+ (App Router) |
| UI Library | Shadcn/UI + Tailwind CSS |
| State | TanStack Query |
| Charts | Recharts |

### Hosting & Infrastructure
| Component | Technology |
|-----------|------------|
| Server | Ubuntu 22.04 LTS (Hetzner/DigitalOcean) |
| Web Server | Nginx (reverse proxy + static sites) |
| Process Manager | Supervisor / systemd |
| SSL | Let's Encrypt (Certbot) |

### Payments
| Provider | Region | Purpose |
|----------|--------|---------|
| Recurrente | Guatemala/LATAM | Primary payment processor |

---

## 🎨 Design Principles

### 1. Modular Architecture
- Each module handles ONE domain (Hunter, Creative, Pitcher, etc.)
- Clear interfaces between modules
- Easy to test, maintain, and scale independently

### 2. Clean Code Standards
- **Max file size**: ~2,000 lines (hard limit: 5,000)
- **Max function size**: ~50 lines
- **Single Responsibility**: One function = one task
- **Meaningful names**: `generate_brand_concept()` not `process()`

### 3. Semantic CSS
```css
/* ✅ Good - Semantic, themeable */
.card-primary { background: var(--surface-primary); }
.text-heading { color: var(--text-primary); }
.btn-action { background: var(--accent-primary); }

/* ❌ Bad - Hard-coded, non-semantic */
.blue-card { background: #3b82f6; }
.header-text { color: #1f2937; }
```

### 4. Configuration-Driven
- Prompts stored in database, editable via admin UI
- No code changes needed for prompt iterations
- A/B testing support for different prompt versions

### 5. Security First
- API keys in environment variables only
- Webhook signature validation
- Rate limiting on all endpoints
- Input sanitization everywhere

---

## 📈 Key Metrics to Track

| Metric | Description |
|--------|-------------|
| Leads Generated | Businesses scraped per day/week |
| Sites Created | Websites generated |
| Email Open Rate | Outreach effectiveness |
| Click Rate | Preview link engagement |
| Conversion Rate | Purchases / Emails sent |
| MRR | Monthly recurring revenue |
| Churn Rate | Subscription cancellations |
| Cost per Lead | API costs / Leads |
| ROI per Campaign | Revenue / Campaign cost |

---

## 🚀 Quick Start Guide

After reading all blueprint documents:

1. **Phase 1**: Set up development environment
2. **Phase 2**: Build database schema & models
3. **Phase 3**: Implement Hunter module (scraping)
4. **Phase 4**: Build Creative engine (AI agents)
5. **Phase 5**: Create Pitcher module (outreach)
6. **Phase 6**: Integrate Recurrente payments
7. **Phase 7**: Build Admin Dashboard
8. **Phase 8**: Deploy & configure Nginx
9. **Phase 9**: Testing & launch

See [BLUEPRINT_08_IMPLEMENTATION_PHASES.md](./BLUEPRINT_08_IMPLEMENTATION_PHASES.md) for detailed steps.

---

## 📝 Document Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-09 | 1.0.0 | Initial blueprint creation |
