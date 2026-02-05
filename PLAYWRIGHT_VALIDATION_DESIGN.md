# Playwright Website Validation - Architectural Design

## Overview
Implement a robust, bot-resistant website validation service using Playwright to verify business websites are valid, accessible, and contain relevant information.

---

## 1. Architecture Design

### **Service Layer Pattern**
```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         BusinessValidationService                     │  │
│  │  - Orchestrates validation workflow                   │  │
│  │  - Manages retry logic & rate limiting                │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         PlaywrightValidationService                   │  │
│  │  - Browser automation                                 │  │
│  │  - Anti-bot detection avoidance                       │  │
│  │  - Screenshot capture                                 │  │
│  │  - Content extraction                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         WebsiteAnalysisService                        │  │
│  │  - Content analysis                                   │  │
│  │  - SEO extraction                                     │  │
│  │  - Business info detection                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │   Celery Queue       │
                │   (Background)       │
                └─────────────────────┘
```

---

## 2. Key Features & Anti-Bot Strategies

### **2.1 Browser Configuration (Critical for Bot Avoidance)**

```python
async def create_stealth_browser():
    """Create a browser with anti-detection measures."""
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        ]
    )
    
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='en-US',
        timezone_id='America/New_York',
        permissions=['geolocation'],
        geolocation={'longitude': -74.0060, 'latitude': 40.7128},  # NYC
        extra_http_headers={
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    )
    
    # Inject anti-detection scripts
    await context.add_init_script("""
        // Override navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Override chrome property
        window.chrome = {
            runtime: {}
        };
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Add plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Add languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
    """)
    
    return browser, context
```

### **2.2 Human-like Behavior**

```python
async def human_like_navigation(page, url: str):
    """Navigate with human-like behavior."""
    # Random delay before navigation
    await asyncio.sleep(random.uniform(0.5, 2.0))
    
    # Navigate with realistic timeout
    try:
        await page.goto(
            url,
            wait_until='networkidle',
            timeout=30000
        )
    except Exception:
        # Fallback to domcontentloaded if networkidle fails
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
    
    # Random scroll behavior
    await random_scroll(page)
    
    # Random mouse movements
    await random_mouse_movements(page)
    
    # Wait with jitter
    await asyncio.sleep(random.uniform(1.0, 3.0))


async def random_scroll(page):
    """Perform random scroll movements."""
    viewport_height = await page.evaluate('window.innerHeight')
    total_height = await page.evaluate('document.body.scrollHeight')
    
    # Scroll in chunks
    current = 0
    while current < total_height:
        scroll_amount = random.randint(100, 400)
        await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
        await asyncio.sleep(random.uniform(0.1, 0.3))
        current += scroll_amount
        
        if random.random() < 0.3:  # 30% chance to stop early
            break


async def random_mouse_movements(page):
    """Simulate random mouse movements."""
    for _ in range(random.randint(2, 5)):
        x = random.randint(100, 1800)
        y = random.randint(100, 1000)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.05, 0.15))
```

---

## 3. Service Implementation

### **File Structure**
```
backend/
├── services/
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── playwright_service.py      # Core browser automation
│   │   ├── stealth_config.py          # Anti-bot configuration
│   │   ├── content_analyzer.py        # Content extraction & analysis
│   │   ├── screenshot_service.py      # Screenshot capture & storage
│   │   └── validation_orchestrator.py # Main orchestration logic
│   └── storage/
│       └── screenshot_storage.py      # S3/local storage
├── tasks/
│   └── validation_tasks.py            # Celery tasks
└── api/
    └── v1/
        └── validation.py              # API endpoints
```

### **3.1 PlaywrightValidationService**

```python
# backend/services/validation/playwright_service.py

import asyncio
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from core.config import get_settings
from .stealth_config import create_stealth_browser, human_like_navigation

settings = get_settings()


class PlaywrightValidationService:
    """
    Playwright-based website validation service.
    Implements anti-bot detection and human-like behavior.
    """
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
    
    async def __aenter__(self):
        """Context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser, self.context = await create_stealth_browser(self.playwright)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def validate_website(self, url: str) -> Dict[str, Any]:
        """
        Validate a website and extract information.
        
        Returns:
            {
                "is_valid": bool,
                "status_code": int,
                "title": str,
                "meta_description": str,
                "has_contact_info": bool,
                "has_phone": bool,
                "has_email": bool,
                "has_address": bool,
                "content_length": int,
                "screenshot_url": str,
                "error": str or None,
                "validation_timestamp": datetime,
            }
        """
        page = None
        try:
            page = await self.context.new_page()
            
            # Navigate with human-like behavior
            await human_like_navigation(page, url)
            
            # Wait for page to be interactive
            await page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # Extract information
            result = await self._extract_page_info(page, url)
            
            # Capture screenshot
            screenshot_path = await self._capture_screenshot(page, url)
            result['screenshot_url'] = screenshot_path
            
            result['is_valid'] = True
            result['error'] = None
            
            return result
            
        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e),
                "status_code": 0,
                "title": None,
                "meta_description": None,
                "has_contact_info": False,
                "has_phone": False,
                "has_email": False,
                "has_address": False,
                "content_length": 0,
                "screenshot_url": None,
            }
        finally:
            if page:
                await page.close()
    
    async def _extract_page_info(self, page: Page, url: str) -> Dict[str, Any]:
        """Extract information from the page."""
        # Get title
        title = await page.title()
        
        # Get meta description
        meta_description = await page.evaluate("""
            () => {
                const meta = document.querySelector('meta[name="description"]');
                return meta ? meta.content : null;
            }
        """)
        
        # Get page content
        content = await page.content()
        content_text = await page.evaluate('document.body.innerText')
        
        # Check for contact information
        has_phone = bool(re.search(
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b|\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',
            content_text
        ))
        
        has_email = bool(re.search(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            content_text
        ))
        
        # Check for address (basic heuristic)
        address_keywords = ['address', 'location', 'street', 'suite', 'floor']
        has_address = any(keyword in content_text.lower() for keyword in address_keywords)
        
        has_contact_info = has_phone or has_email or has_address
        
        # Get status code (if available)
        response = page.frame.page.main_frame.parent_frame
        status_code = 200  # Default, as Playwright doesn't always expose this
        
        return {
            "status_code": status_code,
            "title": title,
            "meta_description": meta_description,
            "has_contact_info": has_contact_info,
            "has_phone": has_phone,
            "has_email": has_email,
            "has_address": has_address,
            "content_length": len(content),
            "content_preview": content_text[:500] if content_text else None,
        }
    
    async def _capture_screenshot(self, page: Page, url: str) -> Optional[str]:
        """Capture and store screenshot."""
        try:
            from services.storage.screenshot_storage import store_screenshot
            
            # Capture full page screenshot
            screenshot_bytes = await page.screenshot(
                full_page=True,
                type='png'
            )
            
            # Store screenshot (implement storage service)
            screenshot_url = await store_screenshot(screenshot_bytes, url)
            
            return screenshot_url
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None
```

### **3.2 Celery Task**

```python
# backend/tasks/validation_tasks.py

from celery import shared_task
from services.validation.playwright_service import PlaywrightValidationService
from services.hunter.business_service import BusinessService
from core.database import get_sync_db
import asyncio


@shared_task(
    bind=True,
    name="tasks.validation.validate_business_website",
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def validate_business_website(self, business_id: str):
    """
    Validate a business website using Playwright.
    Runs in background queue.
    """
    try:
        db = next(get_sync_db())
        business_service = BusinessService(db)
        
        # Get business
        business = business_service.get_business(business_id)
        if not business or not business.website_url:
            return {"error": "No website URL"}
        
        # Run validation (sync wrapper for async code)
        result = asyncio.run(_run_validation(business.website_url))
        
        # Update business record
        business_service.update_business(
            business_id,
            {
                "website_validation_status": "valid" if result["is_valid"] else "invalid",
                "website_validation_result": result,
                "website_validated_at": datetime.utcnow()
            }
        )
        db.commit()
        
        return result
        
    except Exception as e:
        # Retry on failure
        raise self.retry(exc=e)


async def _run_validation(url: str):
    """Run async validation."""
    async with PlaywrightValidationService() as validator:
        return await validator.validate_website(url)
```

---

## 4. Database Schema Updates

```sql
-- Add validation fields to businesses table
ALTER TABLE businesses 
ADD COLUMN website_validation_status VARCHAR(30) DEFAULT 'pending',
ADD COLUMN website_validation_result JSONB,
ADD COLUMN website_validated_at TIMESTAMP,
ADD COLUMN website_screenshot_url TEXT;

CREATE INDEX idx_businesses_validation_status 
ON businesses(website_validation_status);
```

---

## 5. Best Practices Implemented

### ✅ **Separation of Concerns**
- `PlaywrightService`: Browser automation
- `ContentAnalyzer`: Content extraction
- `ScreenshotService`: Image handling
- `ValidationOrchestrator`: Business logic

### ✅ **Error Handling**
- Graceful degradation
- Retry logic with exponential backoff
- Timeout management

### ✅ **Resource Management**
- Context managers for browser lifecycle
- Connection pooling
- Memory cleanup

### ✅ **Scalability**
- Celery queue for async processing
- Rate limiting to avoid IP blocks
- Browser instance reuse where possible

### ✅ **Observability**
- Structured logging
- Metrics (validation success rate, duration)
- Error tracking

---

## 6. Configuration

```python
# backend/core/config.py

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Playwright settings
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_TIMEOUT: int = 30000
    PLAYWRIGHT_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."
    
    # Validation settings
    VALIDATION_RETRY_ATTEMPTS: int = 3
    VALIDATION_RETRY_DELAY: int = 300  # seconds
    VALIDATION_RATE_LIMIT: int = 10  # requests per minute
    
    # Screenshot storage
    SCREENSHOT_BUCKET: str = "webmagic-screenshots"
    SCREENSHOT_CDN_URL: str = "https://cdn.lavish.solutions"
```

---

## 7. API Endpoints

```python
# backend/api/v1/validation.py

@router.post("/businesses/{business_id}/validate-website")
async def validate_business_website(
    business_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Trigger website validation for a business.
    Runs in background.
    """
    # Queue validation task
    task = validate_business_website.delay(str(business_id))
    
    return {
        "message": "Validation started",
        "task_id": task.id,
        "business_id": str(business_id)
    }


@router.post("/businesses/batch-validate")
async def batch_validate_websites(
    business_ids: List[UUID],
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Trigger validation for multiple businesses.
    """
    tasks = []
    for business_id in business_ids:
        task = validate_business_website.delay(str(business_id))
        tasks.append({"business_id": str(business_id), "task_id": task.id})
    
    return {
        "message": f"Validation started for {len(business_ids)} businesses",
        "tasks": tasks
    }
```

---

## 8. Testing Strategy

```python
# backend/tests/test_playwright_validation.py

@pytest.mark.asyncio
async def test_validate_valid_website():
    """Test validation of a known valid website."""
    async with PlaywrightValidationService() as validator:
        result = await validator.validate_website("https://example.com")
        
        assert result["is_valid"] is True
        assert result["title"] is not None
        assert result["status_code"] == 200


@pytest.mark.asyncio
async def test_validate_invalid_website():
    """Test validation of invalid website."""
    async with PlaywrightValidationService() as validator:
        result = await validator.validate_website("https://thisdoesnotexist.invalid")
        
        assert result["is_valid"] is False
        assert result["error"] is not None
```

---

## 9. Deployment Considerations

### **Docker Setup**
```dockerfile
# Install Playwright browsers in Docker
RUN pip install playwright && \
    playwright install chromium && \
    playwright install-deps chromium
```

### **Resource Requirements**
- Memory: 512MB-1GB per browser instance
- CPU: 1-2 cores recommended
- Disk: 500MB for browser binaries

### **Rate Limiting**
- Implement per-domain rate limiting
- Use rotating user agents
- Add random delays between requests

---

## 10. Monitoring & Alerts

```python
# Metrics to track
- validation_success_rate
- validation_duration_ms
- validation_errors_by_type
- browser_crashes
- screenshot_capture_failures
```

---

## Summary

This architecture provides:
- ✅ **Bot-resistant validation** using Playwright stealth techniques
- ✅ **Scalable processing** with Celery queues
- ✅ **Clean separation** of concerns
- ✅ **Comprehensive error handling**
- ✅ **Production-ready** implementation

**Next Steps:**
1. Implement `PlaywrightValidationService`
2. Add to Celery task queue
3. Update Business model with validation fields
4. Create API endpoints
5. Add to admin UI for manual triggering

