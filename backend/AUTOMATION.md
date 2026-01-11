# WebMagic Automation System

Complete guide to WebMagic's autopilot orchestration and background task processing.

## 🤖 Overview

The automation system coordinates the entire WebMagic pipeline:

1. **Scraping** - Automated territory scraping and lead qualification
2. **Generation** - AI-powered website creation
3. **Campaigns** - Email outreach and tracking
4. **Monitoring** - Health checks and alerts

## 🏗️ Architecture

### Components

- **Conductor** - Main orchestration script (`conductor.py`)
- **Celery** - Distributed task queue
- **Redis** - Message broker and result backend
- **Tasks** - Modular task definitions
  - `tasks/scraping.py` - Scraping automation
  - `tasks/generation.py` - Site generation automation
  - `tasks/campaigns.py` - Campaign automation
  - `tasks/monitoring.py` - Health checks and alerts

### Task Queues

- `scraping` - Territory scraping tasks
- `generation` - Site generation tasks
- `campaigns` - Email sending tasks
- `monitoring` - Health checks and monitoring

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (if not running)
redis-server
```

### Option 1: Use Conductor (Recommended)

The conductor script orchestrates everything in a single process:

```bash
# Run once (manual trigger)
python conductor.py --mode once

# Run continuously (autopilot)
python conductor.py --mode continuous --interval 300

# Check pipeline status
python conductor.py --status
```

### Option 2: Use Celery Directly

For distributed processing across multiple machines:

```bash
# Terminal 1: Start Celery worker
python start_worker.py

# Terminal 2: Start Celery Beat scheduler (for periodic tasks)
python start_beat.py

# Terminal 3: Start FastAPI
python start.py
```

## 📋 Tasks

### Scraping Tasks

#### `scrape_territory(grid_id)`
Scrape a specific territory grid.
- Max retries: 3
- Retry delay: 5 minutes
- Cooldown: 30 days after success

#### `scrape_pending_territories()`
**Scheduled**: Every 6 hours
- Finds pending grids not on cooldown
- Queues up to 10 territories per run

#### `qualify_new_leads()`
Qualify recently scraped businesses.
- Processes up to 100 businesses per run
- Applies qualification filters

#### `cleanup_expired_cooldowns()`
**Scheduled**: Daily at 3 AM
- Resets expired territory cooldowns to pending

### Generation Tasks

#### `generate_site_for_business(business_id)`
Generate a website for a specific business.
- Max retries: 2
- Retry delay: 10 minutes
- Uses multi-agent AI pipeline

#### `generate_pending_sites()`
**Scheduled**: Every hour
- Finds qualified businesses without sites
- Queues up to 5 generations per run

#### `publish_completed_sites()`
Publish completed sites to production.
- Processes up to 10 sites per run

#### `retry_failed_generations()`
Retry failed site generations.
- Retries up to 3 failed sites per run

### Campaign Tasks

#### `send_campaign(campaign_id)`
Send a specific campaign email.
- Max retries: 3
- Retry delay: 5 minutes
- Includes tracking pixel and links

#### `create_campaign_for_site(site_id)`
Create and queue a campaign for a published site.
- Generates AI-powered email content
- Creates tracking pixel

#### `send_pending_campaigns()`
**Scheduled**: Every 30 minutes
- Sends up to 20 campaigns per run
- Respects rate limits

#### `create_campaigns_for_new_sites()`
Create campaigns for newly published sites.
- Processes up to 10 sites per run

#### `retry_failed_campaigns()`
Retry failed campaign sends.
- Retries up to 5 campaigns per run

### Monitoring Tasks

#### `health_check()`
**Scheduled**: Every 5 minutes
- Checks database connectivity
- Collects pipeline metrics
- Detects stuck tasks

#### `cleanup_stuck_tasks()`
Clean up tasks stuck in processing.
- Timeout: 2 hours
- Resets stuck grids/sites/campaigns

#### `generate_daily_report()`
Generate daily performance report.
- Businesses scraped
- Sites generated
- Campaigns sent
- Revenue collected

#### `alert_on_failures()`
Send alerts if failure rates are too high.
- Site generation failures > 50%
- Campaign failures > 30%

## 📅 Periodic Schedule

| Task | Schedule | Queue | Purpose |
|------|----------|-------|---------|
| `scrape_pending_territories` | Every 6 hours | scraping | Scrape new territories |
| `generate_pending_sites` | Every hour | generation | Generate sites |
| `send_pending_campaigns` | Every 30 min | campaigns | Send emails |
| `cleanup_expired_cooldowns` | Daily 3 AM | scraping | Reset cooldowns |
| `health_check` | Every 5 min | monitoring | System health |

## 🎛️ Configuration

### Celery Settings (`celery_app.py`)

```python
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

task_time_limit = 3600  # 1 hour max
task_soft_time_limit = 3300  # 55 minutes soft limit
worker_prefetch_multiplier = 1  # One task at a time
```

### Environment Variables

```bash
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## 🔧 Conductor CLI

### Commands

```bash
# Run single cycle
python conductor.py --mode once

# Run continuous autopilot (5 min intervals)
python conductor.py --mode continuous --interval 300

# Run continuous autopilot (1 hour intervals)
python conductor.py --mode continuous --interval 3600

# Show pipeline status
python conductor.py --status
```

### Conductor Cycle

Each cycle runs:

1. **Health Check** - Verify system health
2. **Cleanup** - Clean up stuck tasks
3. **Scraping Phase**
   - Clean up cooldowns
   - Scrape territories
   - Qualify leads
4. **Generation Phase**
   - Retry failures
   - Generate sites
   - Publish sites
5. **Campaign Phase**
   - Create campaigns
   - Retry failures
   - Send emails
6. **Status Report** - Log pipeline metrics

## 📊 Monitoring

### Logs

```bash
# Conductor logs
tail -f conductor.log

# Celery worker logs
tail -f celery_worker.log

# Celery beat logs
tail -f celery_beat.log
```

### Health Status

```bash
# Check pipeline status
python conductor.py --status

# Check Celery workers
celery -A celery_app inspect active

# Check scheduled tasks
celery -A celery_app inspect scheduled
```

### Metrics

The conductor tracks:
- Pending territories
- Total/qualified businesses
- Sites (generating/completed/published)
- Campaigns (sent/opened)
- Total customers

## 🚨 Error Handling

### Automatic Retries

All tasks have built-in retry logic:
- **Scraping**: 3 retries, 5 min delay
- **Generation**: 2 retries, 10 min delay
- **Campaigns**: 3 retries, 5 min delay

### Stuck Task Cleanup

Tasks stuck > 2 hours are automatically:
- Coverage grids → Reset to pending
- Site generations → Marked as failed
- Campaigns → Reset to draft

### Failure Alerts

Alerts triggered when:
- Site generation failures > 50%
- Campaign send failures > 30%

## 🔄 Task Flow

```
┌─────────────────┐
│ Scrape Territory│
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Qualify Leads  │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Generate Site   │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Publish Site   │
└────────┬────────┘
         │
         v
┌─────────────────┐
│Create Campaign  │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Send Email     │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Track Opens    │
└─────────────────┘
```

## 💡 Best Practices

1. **Start Small** - Use `conductor.py --mode once` to test
2. **Monitor Logs** - Watch `conductor.log` for issues
3. **Adjust Intervals** - Tune cycle intervals based on load
4. **Scale Horizontally** - Add more Celery workers as needed
5. **Use Queues** - Route tasks to specialized workers

## 📈 Scaling

### Single Machine

```bash
# Run conductor in autopilot
python conductor.py --mode continuous
```

### Multiple Workers

```bash
# Worker 1: Scraping only
celery -A celery_app worker -Q scraping -n scraper@%h

# Worker 2: Generation only
celery -A celery_app worker -Q generation -n generator@%h

# Worker 3: Campaigns only
celery -A celery_app worker -Q campaigns -n mailer@%h

# Beat scheduler
celery -A celery_app beat
```

## 🐛 Troubleshooting

### Tasks not running

```bash
# Check Redis connection
redis-cli ping

# Check Celery workers
celery -A celery_app inspect active

# Check task routing
celery -A celery_app inspect registered
```

### High failure rates

```bash
# Check task errors
celery -A celery_app events

# Review logs
tail -f conductor.log

# Check health
python conductor.py --status
```

---

Built for **WebMagic** - Agency automation at scale 🚀
