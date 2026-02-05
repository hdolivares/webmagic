# Playwright Setup Instructions

## System Dependencies Installation

Playwright requires specific system dependencies to run headless browsers. Due to package name changes in Ubuntu 24.04 (Noble), we need to manually install compatible versions.

### Option 1: Manual Dependency Installation (Recommended for Ubuntu 24.04+)

```bash
# Install compatible system libraries
apt-get update
apt-get install -y \
    libasound2t64 \
    libatk-bridge2.0-0t64 \
    libatk1.0-0t64 \
    libatspi2.0-0t64 \
    libcairo2 \
    libcups2t64 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0t64 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2

# Install Chromium browser for Playwright
cd /var/www/webmagic/backend
source .venv/bin/activate
playwright install chromium
```

### Option 2: Docker Deployment (Recommended for Production)

Use the official Playwright Docker image which has all dependencies pre-installed:

```bash
# Update docker-compose.yml to use Playwright base image
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

# Your existing Dockerfile instructions...
```

### Option 3: Use Playwright Install Script (For older Ubuntu versions)

```bash
# This works on Ubuntu 20.04/22.04 but has issues on 24.04
playwright install-deps chromium
playwright install chromium
```

## Testing the Installation

After installing dependencies, test the validation service:

```bash
cd /var/www/webmagic/backend
source .venv/bin/activate
python scripts/test_playwright_validation.py
```

Expected output:
```
🚀 Testing Playwright Validation Service...

✅ Service initialized successfully

🔍 Validating: https://example.com

📊 Validation Result:
============================================================
  ✓ Is Valid: True
  ✓ Title: Example Domain
  ✓ Status Code: 200
  ✓ Load Time: 1234ms
  ✓ Quality Score: 45/100
  ✓ Has Contact Info: False
  ✓ Word Count: 124
  ✓ Is Placeholder: False

📝 Content Preview:
  Example Domain This domain is for use in illustrative examples...

============================================================

✅ Test completed successfully!
```

## Enabling Validation Queue

Once Playwright is working, enable the validation queue in Celery:

```bash
# Update supervisor config to include validation queue
supervisorctl stop webmagic-celery
nano /etc/supervisor/conf.d/webmagic.conf

# Update celery command to include validation queue:
command=/var/www/webmagic/backend/.venv/bin/celery -A celery_app worker -Q celery,generation,scraping,campaigns,monitoring,validation --loglevel=info

supervisorctl reread
supervisorctl update
supervisorctl start webmagic-celery
```

## API Usage

### Trigger Validation for Single Business

```bash
curl -X POST "https://web.lavish.solutions/api/v1/validation/businesses/{business_id}/validate" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Batch Validation

```bash
curl -X POST "https://web.lavish.solutions/api/v1/validation/businesses/batch-validate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "business_ids": ["uuid1", "uuid2", "uuid3"]
  }'
```

### Check Validation Status

```bash
curl "https://web.lavish.solutions/api/v1/validation/businesses/{business_id}/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### View Statistics

```bash
curl "https://web.lavish.solutions/api/v1/validation/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Troubleshooting

### Error: "Host system is missing dependencies"

This means Playwright browser dependencies are not installed. Follow Option 1 or Option 2 above.

### Error: "Browser executable not found"

Run `playwright install chromium` to download the Chromium browser.

### Error: "Permission denied"

Ensure the virtual environment is activated and you have permissions to install packages.

### Validation Times Out

Increase the timeout in the validation service or check your network connectivity to the target website.

## Performance Considerations

- **Concurrent Validations**: Default is 3 concurrent validations per worker. Adjust based on server resources.
- **Memory Usage**: Each browser instance uses ~100-300MB RAM. Plan accordingly.
- **CPU Usage**: Rendering pages is CPU-intensive. Consider dedicated workers for validation tasks.
- **Rate Limiting**: Be respectful of target websites. Add delays between validations if needed.

## Security Best Practices

1. **Isolate Validation Workers**: Run validation tasks in separate workers/containers
2. **Resource Limits**: Set memory and CPU limits to prevent resource exhaustion
3. **Timeout Configuration**: Always use timeouts to prevent hanging tasks
4. **Network Security**: Consider running validations in a sandboxed environment
5. **User Agent Rotation**: The service rotates user agents automatically

## Next Steps

1. Install system dependencies using Option 1 or Option 2
2. Test the validation service
3. Enable the validation queue in Celery
4. Trigger validation for test businesses
5. Monitor validation results in the database
6. Optionally: Set up S3 for screenshot storage

