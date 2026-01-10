# WebMagic: Deployment & Infrastructure

## Server Configuration & Deployment Guide

This document covers server setup, Nginx configuration, and deployment procedures.

---

## 🖥️ Server Requirements

### Recommended Specifications

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 4 vCPU | 8 vCPU |
| **RAM** | 8 GB | 16 GB |
| **Storage** | 100 GB SSD | 200 GB NVMe |
| **Bandwidth** | 1 TB/mo | Unmetered |
| **OS** | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Recommended Providers

| Provider | Plan | Estimated Cost |
|----------|------|----------------|
| Hetzner | CPX41 | ~$20/mo |
| DigitalOcean | Premium Intel 8GB | ~$56/mo |
| Linode | Dedicated 8GB | ~$72/mo |

---

## 🏗️ Directory Structure (Server)

```
/
├── var/
│   └── www/
│       ├── webmagic/                 # Main application
│       │   ├── backend/              # Python backend
│       │   ├── admin_dashboard/      # Next.js frontend
│       │   └── .env                  # Environment variables
│       │
│       ├── sites/                    # Generated websites
│       │   ├── plumber-joe/
│       │   │   └── index.html
│       │   ├── tonys-pizza/
│       │   │   └── index.html
│       │   └── ...
│       │
│       └── screenshots/              # Site screenshots
│           ├── plumber-joe_desktop.png
│           └── plumber-joe_mobile.png
│
├── etc/
│   ├── nginx/
│   │   ├── sites-available/
│   │   │   ├── webmagic-api
│   │   │   ├── webmagic-admin
│   │   │   └── webmagic-sites
│   │   └── sites-enabled/
│   │
│   └── supervisor/
│       └── conf.d/
│           ├── webmagic-api.conf
│           └── webmagic-celery.conf
│
└── home/
    └── webmagic/
        └── logs/
            ├── api.log
            ├── celery.log
            └── nginx/
```

---

## 🔧 Initial Server Setup

### 1. Create User & Basic Setup

```bash
#!/bin/bash
# scripts/server_setup.sh

# Create application user
sudo adduser --disabled-password --gecos "" webmagic
sudo usermod -aG sudo webmagic

# Update system
sudo apt update && sudo apt upgrade -y

# Install essentials
sudo apt install -y \
    build-essential \
    git \
    curl \
    wget \
    vim \
    htop \
    ufw \
    fail2ban

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable

# Setup fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 2. Install Dependencies

```bash
#!/bin/bash
# scripts/install_deps.sh

# Python 3.11
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# PostgreSQL 15
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-15

# Redis
sudo apt install -y redis-server
sudo systemctl enable redis-server

# Nginx
sudo apt install -y nginx
sudo systemctl enable nginx

# Supervisor
sudo apt install -y supervisor
sudo systemctl enable supervisor

# Playwright dependencies
sudo apt install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2
```

### 3. Setup PostgreSQL

```bash
#!/bin/bash
# scripts/setup_postgres.sh

# Create database and user
sudo -u postgres psql << EOF
CREATE USER webmagic WITH PASSWORD 'your_secure_password';
CREATE DATABASE webmagic OWNER webmagic;
GRANT ALL PRIVILEGES ON DATABASE webmagic TO webmagic;
\c webmagic
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOF

echo "PostgreSQL configured"
```

---

## 🌐 Nginx Configuration

### API Server (FastAPI)

```nginx
# /etc/nginx/sites-available/webmagic-api

upstream webmagic_api {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name api.webmagic.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.webmagic.com;
    
    # SSL (managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/api.webmagic.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.webmagic.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /home/webmagic/logs/nginx/api_access.log;
    error_log /home/webmagic/logs/nginx/api_error.log;
    
    # API routes
    location / {
        proxy_pass http://webmagic_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check
    location /health {
        proxy_pass http://webmagic_api/health;
        access_log off;
    }
}
```

### Admin Dashboard (Next.js)

```nginx
# /etc/nginx/sites-available/webmagic-admin

upstream webmagic_admin {
    server 127.0.0.1:3000;
    keepalive 32;
}

server {
    listen 80;
    server_name admin.webmagic.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name admin.webmagic.com;
    
    ssl_certificate /etc/letsencrypt/live/admin.webmagic.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/admin.webmagic.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    
    access_log /home/webmagic/logs/nginx/admin_access.log;
    error_log /home/webmagic/logs/nginx/admin_error.log;
    
    location / {
        proxy_pass http://webmagic_admin;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Static assets caching
    location /_next/static {
        proxy_pass http://webmagic_admin;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }
}
```

### Generated Sites (Wildcard Subdomain)

```nginx
# /etc/nginx/sites-available/webmagic-sites

server {
    listen 80;
    server_name ~^(?<subdomain>.+)\.sites\.webmagic\.com$;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ~^(?<subdomain>.+)\.sites\.webmagic\.com$;
    
    # Wildcard SSL certificate
    ssl_certificate /etc/letsencrypt/live/sites.webmagic.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sites.webmagic.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    
    # Root directory based on subdomain
    root /var/www/sites/$subdomain;
    index index.html;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Caching for static assets
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
    
    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Error pages
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
    
    # Logging (minimal for performance)
    access_log off;
    error_log /home/webmagic/logs/nginx/sites_error.log error;
}
```

### Enable Sites

```bash
sudo ln -s /etc/nginx/sites-available/webmagic-api /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/webmagic-admin /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/webmagic-sites /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔐 SSL Certificates

### Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Generate Certificates

```bash
# Main domains
sudo certbot --nginx -d api.webmagic.com
sudo certbot --nginx -d admin.webmagic.com

# Wildcard for generated sites (requires DNS challenge)
sudo certbot certonly --manual --preferred-challenges dns \
    -d "*.sites.webmagic.com" \
    -d "sites.webmagic.com"
```

### Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Cron job (already configured by certbot)
cat /etc/cron.d/certbot
```

---

## ⚙️ Process Management (Supervisor)

### FastAPI Backend

```ini
# /etc/supervisor/conf.d/webmagic-api.conf

[program:webmagic-api]
directory=/var/www/webmagic/backend
command=/var/www/webmagic/backend/.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 4
user=webmagic
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/home/webmagic/logs/api_error.log
stdout_logfile=/home/webmagic/logs/api.log
environment=
    PATH="/var/www/webmagic/backend/.venv/bin",
    PYTHONPATH="/var/www/webmagic/backend"
```

### Celery Worker

```ini
# /etc/supervisor/conf.d/webmagic-celery.conf

[program:webmagic-celery]
directory=/var/www/webmagic/backend
command=/var/www/webmagic/backend/.venv/bin/celery -A tasks.celery_app worker --loglevel=info --concurrency=4
user=webmagic
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/home/webmagic/logs/celery_error.log
stdout_logfile=/home/webmagic/logs/celery.log
environment=
    PATH="/var/www/webmagic/backend/.venv/bin",
    PYTHONPATH="/var/www/webmagic/backend"

[program:webmagic-celery-beat]
directory=/var/www/webmagic/backend
command=/var/www/webmagic/backend/.venv/bin/celery -A tasks.celery_app beat --loglevel=info
user=webmagic
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/home/webmagic/logs/celery_beat_error.log
stdout_logfile=/home/webmagic/logs/celery_beat.log
```

### Reload Supervisor

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status
```

---

## 🚀 Deployment Script

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

echo "🚀 Starting WebMagic deployment..."

# Variables
APP_DIR="/var/www/webmagic"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/admin_dashboard"
BRANCH="${1:-main}"

# Pull latest code
echo "📥 Pulling latest code..."
cd $APP_DIR
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH

# Backend deployment
echo "🐍 Deploying backend..."
cd $BACKEND_DIR
source .venv/bin/activate
pip install -r requirements.txt --quiet
alembic upgrade head
deactivate

# Frontend deployment
echo "⚛️ Building frontend..."
cd $FRONTEND_DIR
npm ci --silent
npm run build

# Restart services
echo "🔄 Restarting services..."
sudo supervisorctl restart webmagic-api
sudo supervisorctl restart webmagic-celery
sudo supervisorctl restart webmagic-celery-beat

# Reload Next.js (if using PM2)
pm2 reload webmagic-admin --update-env

# Clear caches
echo "🧹 Clearing caches..."
redis-cli FLUSHDB

# Health check
echo "🏥 Running health checks..."
sleep 5
curl -sf https://api.webmagic.com/health || echo "API health check failed!"
curl -sf https://admin.webmagic.com || echo "Admin health check failed!"

echo "✅ Deployment complete!"
```

---

## 📊 Monitoring

### Basic Monitoring with Prometheus + Grafana

```yaml
# docker-compose.monitoring.yml (optional)

version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      
  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=secure_password
```

### Log Rotation

```bash
# /etc/logrotate.d/webmagic

/home/webmagic/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 644 webmagic webmagic
    postrotate
        supervisorctl restart webmagic-api webmagic-celery
    endscript
}
```

---

## 🔒 Security Checklist

- [ ] UFW firewall enabled (only 22, 80, 443 open)
- [ ] Fail2ban configured
- [ ] SSH key-only authentication
- [ ] PostgreSQL not exposed to internet
- [ ] Redis password protected
- [ ] All secrets in environment variables
- [ ] HTTPS everywhere
- [ ] Security headers configured
- [ ] Regular security updates

---

## 📋 Maintenance Commands

```bash
# View logs
sudo tail -f /home/webmagic/logs/api.log
sudo tail -f /home/webmagic/logs/celery.log

# Restart services
sudo supervisorctl restart all

# Check service status
sudo supervisorctl status

# Database backup
pg_dump -U webmagic webmagic > backup_$(date +%Y%m%d).sql

# View Celery tasks
celery -A tasks.celery_app inspect active

# Clear Redis cache
redis-cli FLUSHDB
```
