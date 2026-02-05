"""
Stealth browser configuration for Playwright.
Implements anti-bot detection measures.
"""
import random
import asyncio
from typing import Tuple
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import logging

logger = logging.getLogger(__name__)


# User agents pool for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


async def create_stealth_browser(playwright) -> Tuple[Browser, BrowserContext]:
    """
    Create a browser with anti-detection measures.
    
    Implements multiple stealth techniques:
    - Custom browser arguments
    - Spoofed navigator properties
    - Realistic viewport and locale
    - Injected anti-detection scripts
    
    Returns:
        Tuple of (Browser, BrowserContext)
    """
    # Launch browser with stealth args
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--disable-infobars',
            '--window-size=1920,1080',
            '--start-maximized',
        ]
    )
    
    # Random user agent from pool
    user_agent = random.choice(USER_AGENTS)
    
    # Create context with realistic settings
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent=user_agent,
        locale='en-US',
        timezone_id='America/New_York',
        permissions=['geolocation'],
        geolocation={'longitude': -74.0060, 'latitude': 40.7128},  # NYC coordinates
        color_scheme='light',
        extra_http_headers={
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
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
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Add plugins to appear more realistic
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                },
                {
                    0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                    description: "Portable Document Format",
                    filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                    length: 1,
                    name: "Chrome PDF Viewer"
                },
                {
                    0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable"},
                    1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable"},
                    description: "",
                    filename: "internal-nacl-plugin",
                    length: 2,
                    name: "Native Client"
                }
            ]
        });
        
        // Add languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Override platform
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32'
        });
        
        // Override hardwareConcurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8
        });
        
        // Override deviceMemory
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8
        });
    """)
    
    logger.info(f"Created stealth browser with user agent: {user_agent[:50]}...")
    
    return browser, context


async def human_like_navigation(page: Page, url: str, wait_until: str = 'networkidle'):
    """
    Navigate to URL with human-like behavior.
    
    Args:
        page: Playwright page object
        url: URL to navigate to
        wait_until: Load state to wait for ('networkidle', 'domcontentloaded', 'load')
    """
    # Random delay before navigation (simulate thinking time)
    await asyncio.sleep(random.uniform(0.5, 2.0))
    
    try:
        # Try networkidle first
        await page.goto(
            url,
            wait_until=wait_until,
            timeout=30000
        )
    except Exception as e:
        logger.warning(f"Navigation with {wait_until} failed, falling back to domcontentloaded: {e}")
        try:
            # Fallback to domcontentloaded
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        except Exception as e2:
            logger.error(f"Navigation failed completely: {e2}")
            raise
    
    # Wait for page to be interactive
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    # Random scroll behavior
    await random_scroll(page)
    
    # Random mouse movements
    await random_mouse_movements(page)
    
    # Final wait with jitter
    await asyncio.sleep(random.uniform(1.0, 2.0))


async def random_scroll(page: Page):
    """
    Perform random scroll movements to appear human-like.
    """
    try:
        viewport_height = await page.evaluate('window.innerHeight')
        total_height = await page.evaluate('document.body.scrollHeight')
        
        # Don't scroll if page is shorter than viewport
        if total_height <= viewport_height:
            return
        
        # Scroll in chunks
        current = 0
        max_scroll = min(total_height, viewport_height * 3)  # Don't scroll entire page
        
        while current < max_scroll:
            scroll_amount = random.randint(100, 400)
            await page.evaluate(f'window.scrollBy({{top: {scroll_amount}, behavior: "smooth"}})')
            await asyncio.sleep(random.uniform(0.1, 0.3))
            current += scroll_amount
            
            # 30% chance to stop early
            if random.random() < 0.3:
                break
        
        # Scroll back to top
        await page.evaluate('window.scrollTo({top: 0, behavior: "smooth"})')
        await asyncio.sleep(random.uniform(0.3, 0.6))
        
    except Exception as e:
        logger.debug(f"Random scroll failed (non-critical): {e}")


async def random_mouse_movements(page: Page):
    """
    Simulate random mouse movements.
    """
    try:
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1800)
            y = random.randint(100, 1000)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.05, 0.15))
    except Exception as e:
        logger.debug(f"Random mouse movements failed (non-critical): {e}")


async def wait_for_stable_page(page: Page, timeout: int = 5000):
    """
    Wait for page to be stable (no network activity).
    Useful after navigation completes.
    """
    try:
        await page.wait_for_load_state('networkidle', timeout=timeout)
    except Exception:
        # If networkidle fails, just wait a bit
        await asyncio.sleep(2.0)

