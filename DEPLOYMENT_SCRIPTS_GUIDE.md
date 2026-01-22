# WebMagic Deployment Scripts Guide

## Overview

This guide documents the reusable deployment scripts created for WebMagic. These scripts automate common deployment tasks and service management operations.

## Available Scripts

All scripts are located in the `/var/www/webmagic/scripts/` directory on the VPS and are executable.

### 1. Stop Services (`stop_services.sh`)

**Purpose:** Stops all WebMagic backend services.

**Usage:**
```bash
bash /var/www/webmagic/scripts/stop_services.sh
```

**What it does:**
- Stops webmagic-api
- Stops webmagic-celery worker
- Stops webmagic-celery-beat
- Shows status confirmation

---

### 2. Start Services (`start_services.sh`)

**Purpose:** Starts all WebMagic backend services and verifies health.

**Usage:**
```bash
bash /var/www/webmagic/scripts/start_services.sh
```

**What it does:**
- Starts webmagic-api
- Starts webmagic-celery worker
- Starts webmagic-celery-beat
- Waits 5 seconds for initialization
- Checks service status
- Verifies API health endpoint
- Reports any recent errors

---

### 3. Restart Services (`restart_services.sh`)

**Purpose:** Restarts all WebMagic backend services (stop + start).

**Usage:**
```bash
bash /var/www/webmagic/scripts/restart_services.sh
```

**What it does:**
- Stops all services
- Waits 2 seconds
- Starts all services
- Waits 5 seconds for initialization
- Shows final status

**When to use:** After code changes that don't require frontend rebuild (backend-only changes).

---

### 4. Rebuild Frontend (`rebuild_frontend.sh`)

**Purpose:** Rebuilds the production frontend bundle.

**Usage:**
```bash
bash /var/www/webmagic/scripts/rebuild_frontend.sh
```

**What it does:**
- Changes to frontend directory
- Installs/updates npm dependencies
- Runs production build (`npm run build`)
- Shows build output and statistics
- Lists build artifacts

**When to use:** After frontend code changes.

---

### 5. Complete Deployment (`deploy.sh`)

**Purpose:** Full deployment pipeline - pulls code, updates dependencies, rebuilds frontend, and restarts services.

**Usage:**
```bash
bash /var/www/webmagic/scripts/deploy.sh
```

**What it does:**
1. Pulls latest code from Git (`git pull origin main`)
2. Updates Python dependencies (`pip install -r requirements.txt`)
3. Rebuilds frontend (calls `rebuild_frontend.sh`)
4. Restarts all services (calls `restart_services.sh`)

**When to use:** For complete deployments after pushing changes to the main branch.

---

## Common Deployment Scenarios

### Scenario 1: Backend Code Changes Only
```bash
cd /var/www/webmagic
git pull origin main
bash scripts/restart_services.sh
```

### Scenario 2: Frontend Code Changes Only
```bash
cd /var/www/webmagic
git pull origin main
bash scripts/rebuild_frontend.sh
```

### Scenario 3: Both Backend & Frontend Changes
```bash
cd /var/www/webmagic
bash scripts/deploy.sh
```

### Scenario 4: Emergency Service Restart
```bash
bash /var/www/webmagic/scripts/restart_services.sh
```

### Scenario 5: Check Service Status
```bash
sudo supervisorctl status
```

---

## Service Management Commands

### Manual Service Control

**Check status:**
```bash
sudo supervisorctl status
```

**Restart individual service:**
```bash
sudo supervisorctl restart webmagic-api
sudo supervisorctl restart webmagic-celery
sudo supervisorctl restart webmagic-celery-beat
```

**Stop individual service:**
```bash
sudo supervisorctl stop webmagic-api
```

**Start individual service:**
```bash
sudo supervisorctl start webmagic-api
```

**View logs:**
```bash
tail -f /var/log/webmagic/api.log
tail -f /var/log/webmagic/api_error.log
tail -f /var/log/webmagic/celery.log
tail -f /var/log/webmagic/celery_error.log
```

---

## Troubleshooting

### Services Won't Start

1. Check error logs:
   ```bash
   tail -50 /var/log/webmagic/api_error.log
   tail -50 /var/log/webmagic/celery_error.log
   tail -50 /var/log/supervisor/supervisord.log
   ```

2. Verify Python environment:
   ```bash
   cd /var/www/webmagic/backend
   source .venv/bin/activate
   python -c "from api.main import app; print('API imports OK')"
   ```

3. Check database connection:
   ```bash
   cd /var/www/webmagic/backend
   source .venv/bin/activate
   python -c "from core.database import get_db; print('Database connection OK')"
   ```

### Frontend Build Fails

1. Check Node.js version:
   ```bash
   node --version  # Should be v18+
   npm --version
   ```

2. Clear npm cache and rebuild:
   ```bash
   cd /var/www/webmagic/frontend
   rm -rf node_modules package-lock.json
   npm install
   npm run build
   ```

3. Check TypeScript errors:
   ```bash
   cd /var/www/webmagic/frontend
   npm run tsc
   ```

### Git Pull Conflicts

```bash
cd /var/www/webmagic
git status
git stash  # Save local changes
git pull origin main
git stash pop  # Reapply local changes if needed
```

---

## Best Practices

1. **Always review changes before deployment:**
   ```bash
   cd /var/www/webmagic
   git fetch origin
   git log HEAD..origin/main --oneline
   ```

2. **Test in development first** before deploying to production.

3. **Monitor logs after deployment:**
   ```bash
   tail -f /var/log/webmagic/api_error.log &
   tail -f /var/log/webmagic/celery_error.log &
   ```

4. **Keep backups** of critical files like `.env` before making changes.

5. **Use the `deploy.sh` script** for standard deployments to ensure consistency.

---

## Environment Variables

Critical environment files (never commit these to Git):
- `/var/www/webmagic/backend/.env` - Backend configuration
- Contains sensitive data: API keys, database credentials, Twilio credentials

To update environment variables:
1. Edit the `.env` file directly on the VPS
2. Restart services: `bash scripts/restart_services.sh`

---

## Recent Deployments

### January 21, 2026
- **Fixed:** `CoverageGrid.category` attribute errors (replaced with `industry_category`)
- **Fixed:** Webhooks module import conflicts
- **Added:** Reusable deployment scripts
- **Added:** Twilio SMS integration with compliance features
- **Status:** All services running successfully

---

## Support

For issues or questions:
1. Check service logs first
2. Review error messages in supervisorctl status
3. Verify environment variables are correctly set
4. Ensure all dependencies are installed

---

**Last Updated:** January 21, 2026  
**Platform:** WebMagic VPS (web.lavish.solutions)  
**Services:** FastAPI, Celery, React + Vite, Nginx, PostgreSQL, Redis

