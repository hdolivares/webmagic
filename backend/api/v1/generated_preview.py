"""
Generated Sites Preview API

Serves HTML content for generated sites (from generated_sites table).
This is a PUBLIC endpoint that serves the actual website HTML.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging

from core.config import get_settings
from core.database import get_db
from models.site import GeneratedSite
from models.site_models import Site, SiteVersion
import re

router = APIRouter(tags=["generated-preview"])
logger = logging.getLogger(__name__)
_settings = get_settings()


@router.get(
    "/{subdomain}/img/{filename}",
    summary="Serve AI-generated site image",
    description="PUBLIC — serves a Nano Banana image saved for a specific generated site.",
)
async def serve_site_image(subdomain: str, filename: str) -> FileResponse:
    """
    Serve pre-generated images (hero.jpg, about.jpg, services.jpg) for a site.
    Images are saved at SITES_BASE_PATH/{subdomain}/img/{filename} during generation.
    """
    # Sanitise filename — only allow alphanumeric, hyphens, underscores, dots
    safe_name = re.sub(r"[^a-zA-Z0-9_\-.]", "", filename)
    if not safe_name or safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    img_path = Path(_settings.SITES_BASE_PATH) / subdomain / "img" / safe_name

    if not img_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image not found: {subdomain}/img/{safe_name}",
        )

    media_type = "image/jpeg" if safe_name.lower().endswith(".jpg") else "image/png"
    return FileResponse(
        path=str(img_path),
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get(
    "/{subdomain}",
    response_class=HTMLResponse,
    summary="View generated site",
    description="""
    **PUBLIC ENDPOINT** - Serves the HTML content of a generated site.
    
    This endpoint is called when accessing:
    `https://sites.lavish.solutions/{subdomain}`
    
    Returns the full HTML content with inline CSS and JavaScript.
    """
)
async def view_generated_site(
    subdomain: str,
    db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    """
    Serve site HTML content (from generated_sites OR sites table).
    
    Handles both:
    1. Generated sites (from generated_sites table) - like 'marshall-campbell-co-cpas-la'
    2. Purchase preview sites (from sites table) - like 'test-cpa-site'
    
    Args:
        subdomain: Site subdomain/slug
        db: Database session
    
    Returns:
        HTMLResponse with complete site HTML
    """
    try:
        # First, try generated_sites table (most common case)
        gen_query = select(GeneratedSite).where(GeneratedSite.subdomain == subdomain)
        gen_result = await db.execute(gen_query)
        gen_site = gen_result.scalar_one_or_none()
        
        if gen_site:
            # Handle generated site
            return await _serve_generated_site(db, gen_site, subdomain)
        
        # If not found, try sites table (purchase preview sites)
        site_query = select(Site).where(Site.slug == subdomain)
        site_result = await db.execute(site_query)
        purchase_site = site_result.scalar_one_or_none()
        
        if purchase_site:
            # Handle purchase preview site
            return await _serve_purchase_site(db, purchase_site, subdomain)
        
        # Not found in either table
        logger.warning(f"Site not found in any table: {subdomain}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {subdomain}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving site {subdomain}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while loading the site"
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _serve_generated_site(
    db: AsyncSession,
    site: GeneratedSite,
    subdomain: str
) -> HTMLResponse:
    """Serve a site from generated_sites table."""
    # Check if site has content
    if not site.html_content:
        logger.warning(f"Site {subdomain} has no HTML content (status: {site.status})")
        
        if site.status == "generating":
            return HTMLResponse(content=_build_generating_page(site.subdomain))
        elif site.status == "failed":
            return HTMLResponse(content=_build_error_page(subdomain, "Site generation failed"))
        else:
            return HTMLResponse(content=_build_error_page(subdomain, "Site content not available"))
    
    # Check if this site has been purchased (check sites table by business_id)
    is_owned = False
    if site.business_id:
        purchase_query = select(Site).where(
            Site.business_id == site.business_id,
            Site.status == 'owned'
        )
        purchase_result = await db.execute(purchase_query)
        purchased_site = purchase_result.scalar_one_or_none()
        is_owned = purchased_site is not None
        
        if is_owned:
            logger.info(f"Generated site {subdomain} is owned (purchase: {purchased_site.slug})")
    
    # Get HTML content
    html_content = site.html_content
    
    if is_owned:
        # Remove claim bar entirely for purchased sites
        html_content = _remove_claim_bar(html_content)
        logger.info(f"Removed claim bar from owned generated site: {subdomain}")
    else:
        # Read custom pricing stored during manual site creation (if any).
        one_time_price, monthly_price = _extract_site_pricing(site)

        # Always strip and re-inject claim bar so style fixes apply to existing sites
        html_content = _remove_claim_bar(html_content)
        html_content = _inject_canonical_claim_bar(
            html_content, subdomain,
            one_time_price=one_time_price,
            monthly_price=monthly_price,
        )
    
    # Inject <base> tag so relative image paths (img/hero.jpg) resolve correctly.
    # The page is served at /{subdomain} (no trailing slash), so without the base
    # tag relative URLs would resolve to the site root instead of /{subdomain}/.
    html_content = _inject_base_tag(html_content, subdomain)

    # Build complete HTML
    complete_html = _build_complete_html(
        html=html_content,
        css=site.css_content,
        js=site.js_content
    )
    
    logger.info(f"Serving generated site: {subdomain} (status: {site.status}, owned: {is_owned})")
    return HTMLResponse(content=complete_html)


async def _serve_purchase_site(
    db: AsyncSession,
    site: Site,
    slug: str
) -> HTMLResponse:
    """Serve a site from sites table (purchase preview sites)."""
    # Get current version
    if not site.current_version_id:
        logger.warning(f"Purchase site {slug} has no current version")
        return HTMLResponse(content=_build_error_page(slug, "Site content not available"))
    
    version_query = select(SiteVersion).where(SiteVersion.id == site.current_version_id)
    version_result = await db.execute(version_query)
    version = version_result.scalar_one_or_none()
    
    if not version or not version.html_content:
        logger.warning(f"Purchase site {slug} version has no HTML content")
        return HTMLResponse(content=_build_error_page(slug, "Site content not available"))
    
    # Get HTML content
    html_content = version.html_content
    
    # Remove claim bar if site is owned, otherwise re-inject canonical version
    is_owned = site.status == 'owned'
    if is_owned:
        html_content = _remove_claim_bar(html_content)
        logger.info(f"Removed claim bar from owned purchase site: {slug}")
    else:
        html_content = _remove_claim_bar(html_content)
        html_content = _inject_canonical_claim_bar(html_content, slug)
    
    # Build complete HTML
    complete_html = _build_complete_html(
        html=html_content,
        css=version.css_content,
        js=version.js_content
    )
    
    logger.info(f"Serving purchase site: {slug} (status: {site.status})")
    return HTMLResponse(content=complete_html)


def _extract_site_pricing(site) -> tuple:
    """
    Return (one_time_price, monthly_price) for a GeneratedSite.

    Reads from the site's business raw_data.manual_input when available;
    falls back to the historical defaults ($497 / $97) for scraped sites.
    """
    # GeneratedSite has a business_id but we can read raw_data from the
    # business inline if it's been eagerly loaded.  Since we don't want an
    # extra DB round-trip here, we store the pricing directly on the
    # GeneratedSite.design_brief JSON at creation time (see sites.py).
    # For backward-compat we also accept the values coming from the
    # site's own design_brief (populated by the generation task).
    _DEFAULT_ONE_TIME = 497.0
    _DEFAULT_MONTHLY  = 97.0

    try:
        brief = site.design_brief or {}
        pricing = brief.get("pricing") or {}
        one_time = float(pricing.get("one_time_price") or _DEFAULT_ONE_TIME)
        monthly  = float(pricing.get("monthly_price")  or _DEFAULT_MONTHLY)
        return one_time, monthly
    except Exception:
        return _DEFAULT_ONE_TIME, _DEFAULT_MONTHLY


def _inject_canonical_claim_bar(
    html: str,
    slug: str,
    one_time_price: float = 497.0,
    monthly_price: float = 97.0,
) -> str:
    """
    Inject the canonical, always-up-to-date claim bar into site HTML.

    Called at serve time so styling fixes apply immediately to ALL existing
    sites without a DB migration. The JS is in a separate <script> block —
    no inline onclick — to avoid any quote-escaping issues.

    Args:
        one_time_price: Total first-month charge (setup fee + first month).
        monthly_price:  Recurring monthly subscription price.
    """
    from core.config import get_settings
    api_url = get_settings().API_URL
    checkout_url = f"{api_url}/api/v1/sites/{slug}/purchase"

    # Format prices cleanly — no trailing .00 for whole numbers.
    def _fmt(v: float) -> str:
        return f"{v:,.0f}" if v == int(v) else f"{v:,.2f}"

    one_time_display = _fmt(one_time_price)
    monthly_display  = _fmt(monthly_price)

    claim_label = f"Claim for ${one_time_display}"

    # All JS lives in this script block. No inline onclick anywhere.
    claim_script = f"""<script>
(function() {{
  function wmClaim() {{
    if (document.getElementById('wm-claim-modal')) return;
    var overlay = document.createElement('div');
    overlay.id = 'wm-claim-modal';
    overlay.style.cssText = 'position:fixed;inset:0;z-index:10001;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.65);font-family:system-ui,sans-serif;';
    overlay.innerHTML = [
      '<div style="background:#fff;border-radius:16px;padding:40px;max-width:480px;width:90%;position:relative;">',
        '<button id="wm-close-btn" style="position:absolute;top:14px;right:16px;background:none;border:none;font-size:26px;cursor:pointer;color:#999;line-height:1;">&times;</button>',
        '<h2 style="margin:0 0 8px;font-size:24px;color:#1e3a5f;font-weight:700;">Claim Your Website</h2>',
        '<p style="color:#666;margin:0 0 24px;font-size:15px;">Enter your details and we will contact you within 24 hours.</p>',
        '<form id="wm-claim-form" style="display:flex;flex-direction:column;gap:12px;">',
          '<input type="email" id="wm-email" placeholder="Your email address *" required style="padding:14px 16px;border:2px solid #e2e8f0;border-radius:8px;font-size:15px;outline:none;">',
          '<input type="text"  id="wm-name"  placeholder="Your full name *"      required style="padding:14px 16px;border:2px solid #e2e8f0;border-radius:8px;font-size:15px;outline:none;">',
          '<button type="submit" style="background:#7c3aed;color:#fff;border:none;padding:16px;border-radius:8px;font-size:16px;font-weight:700;cursor:pointer;">{claim_label}</button>',
        '</form>',
        '<p id="wm-msg" style="margin:12px 0 0;font-size:13px;color:#10b981;display:none;"></p>',
      '</div>'
    ].join('');
    document.body.appendChild(overlay);
    document.getElementById('wm-close-btn').addEventListener('click', function() {{ overlay.remove(); }});
    overlay.addEventListener('click', function(e) {{ if (e.target === overlay) overlay.remove(); }});
    document.getElementById('wm-claim-form').addEventListener('submit', async function(e) {{
      e.preventDefault();
      var btn = this.querySelector('button[type=submit]');
      btn.disabled = true; btn.textContent = 'Processing...';
      try {{
        var resp = await fetch('{checkout_url}', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{ customer_email: document.getElementById('wm-email').value, customer_name: document.getElementById('wm-name').value }})
        }});
        var data = await resp.json();
        if (data.checkout_url) {{ window.location.href = data.checkout_url; }}
        else {{
          var errMsg = Array.isArray(data.detail) ? data.detail.map(function(e){{ return e.msg || JSON.stringify(e); }}).join(', ') : (data.detail || 'Something went wrong. Please try again.');
          document.getElementById('wm-msg').style.display='block'; document.getElementById('wm-msg').style.color='#ef4444'; document.getElementById('wm-msg').textContent = errMsg; btn.disabled=false; btn.textContent='{claim_label}';
        }}
      }} catch(err) {{ document.getElementById('wm-msg').style.display='block'; document.getElementById('wm-msg').style.color='#ef4444'; document.getElementById('wm-msg').textContent='Network error. Please try again.'; btn.disabled=false; btn.textContent='{claim_label}'; }}
    }});
  }}
  window.wmClaim = wmClaim;
}})();
</script>"""

    claim_bar_html = f"""{claim_script}
<!-- WebMagic Claim Bar - Official -->
<div id="webmagic-claim-bar" style="position:fixed;bottom:0;left:0;right:0;z-index:9999;">
  <div style="background:linear-gradient(135deg,#1e40af 0%,#7c3aed 100%);padding:12px 20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;box-shadow:0 -4px 20px rgba(0,0,0,0.25);">
    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
      <span style="font-size:20px;line-height:1;flex-shrink:0;">&#x1f3e2;</span>
      <div>
        <p style="margin:0;font-weight:700;font-size:15px;color:#ffffff;text-shadow:0 1px 3px rgba(0,0,0,0.4);font-family:system-ui,sans-serif;line-height:1.4;">Is this your business?</p>
        <p style="margin:0;font-size:13px;color:#e0e7ff;text-shadow:0 1px 2px rgba(0,0,0,0.3);font-family:system-ui,sans-serif;line-height:1.4;">Claim this website for only <strong style="color:#ffffff;font-weight:700;">${one_time_display}</strong> &middot; Then just ${monthly_display}/month for hosting, maintenance &amp; updates</p>
        <a href="https://web.lavish.solutions/how-it-works" target="_blank" rel="noopener noreferrer" style="color:#bfdbfe;font-size:12px;text-decoration:underline;margin-top:3px;display:inline-block;font-family:system-ui,sans-serif;">See what&#39;s included &rarr;</a>
      </div>
    </div>
    <button onclick="wmClaim()" style="background:#fbbf24;color:#1e3a5f;border:none;padding:12px 28px;border-radius:8px;font-weight:700;font-size:14px;cursor:pointer;text-transform:uppercase;letter-spacing:0.5px;font-family:system-ui,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,0.2);flex-shrink:0;">
      CLAIM FOR ${one_time_display}
    </button>
  </div>
</div>
<style>
  #webmagic-claim-bar p, #webmagic-claim-bar a, #webmagic-claim-bar span {{ color: inherit; }}
  #webmagic-claim-bar > div > div:first-child > div > p:first-child {{ color: #ffffff !important; }}
  #webmagic-claim-bar > div > div:first-child > div > p:last-of-type {{ color: #e0e7ff !important; }}
  #webmagic-claim-bar > div > div:first-child > div > a {{ color: #bfdbfe !important; }}
  #webmagic-claim-bar button[onclick] {{ background: #fbbf24 !important; color: #1e3a5f !important; }}
  #webmagic-claim-bar button[onclick]:hover {{ background: #f59e0b !important; transform: scale(1.03); }}
  @media (max-width: 640px) {{
    #webmagic-claim-bar > div {{ flex-direction: column; text-align: center; }}
    #webmagic-claim-bar button[onclick] {{ width: 100%; }}
  }}
</style>"""

    if "</body>" in html.lower():
        body_pos = html.lower().rfind("</body>")
        return html[:body_pos] + claim_bar_html + "\n" + html[body_pos:]
    return html + claim_bar_html


def _inject_base_tag(html: str, subdomain: str) -> str:
    """
    Inject a <base href="/{subdomain}/"> into the <head> so that relative
    image paths like img/hero.jpg resolve to /{subdomain}/img/hero.jpg.

    Without this, a page served at /{subdomain} (no trailing slash) would
    resolve img/hero.jpg to /img/hero.jpg — the site root, not the subdomain.
    """
    base_tag = f'<base href="/{subdomain}/">'
    if '<base ' in html:
        return html  # already has a base tag, don't double-inject
    if '<head>' in html:
        return html.replace('<head>', f'<head>\n    {base_tag}', 1)
    if '<HEAD>' in html:
        return html.replace('<HEAD>', f'<HEAD>\n    {base_tag}', 1)
    return html


def _remove_claim_bar(html: str) -> str:
    """
    Remove the WebMagic claim bar from HTML.
    
    Removes the claim bar that was injected during site generation.
    This is called when a site has been purchased (status='owned').
    
    Args:
        html: HTML content with claim bar
    
    Returns:
        HTML content without claim bar
    """
    # Remove the claim bar div and all its content
    # Pattern matches the entire claim bar div with id="webmagic-claim-bar"
    patterns = [
        # Official claim bar (with comment)
        r'<!-- WebMagic Claim Bar(?:\s*-\s*Official)?\s*-->.*?<div\s+id=["\']webmagic-claim-bar["\'][^>]*>.*?</div>',
        # Just the div without comment
        r'<div\s+id=["\']webmagic-claim-bar["\'][^>]*>.*?</div>',
        # Alternative patterns the LLM might have generated
        r'<div[^>]*id=["\']?claim[^>]*>.*?</div>',
    ]
    
    for pattern in patterns:
        html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove claim bar JavaScript handler if present
    claim_js_pattern = r'//\s*WebMagic Claim Bar Handler.*?}\)\(\);'
    html = re.sub(claim_js_pattern, '', html, flags=re.DOTALL)
    
    # Remove claim bar CSS if present
    claim_css_pattern = r'/\*\s*WebMagic Claim Bar Styles\s*\*/.*?(?=(/\*|</style>|$))'
    html = re.sub(claim_css_pattern, '', html, flags=re.DOTALL)
    
    return html


def _build_complete_html(
    html: str,
    css: Optional[str] = None,
    js: Optional[str] = None
) -> str:
    """
    Build complete HTML document with inline CSS and JS.
    
    Args:
        html: HTML content
        css: CSS content (optional)
        js: JavaScript content (optional)
    
    Returns:
        Complete HTML document
    """
    # If HTML already contains <!DOCTYPE html>, inject CSS and JS into it
    if html.strip().lower().startswith('<!doctype html>'):
        import re
        # Strip external <link rel="stylesheet"> and <script src="..."> refs that
        # would 404 — the content is already inlined below.
        html = re.sub(r'<link\b[^>]*\brel=["\']stylesheet["\'][^>]*>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'<script\b[^>]*\bsrc=["\'][^"\']+["\'][^>]*>\s*</script>', '', html, flags=re.IGNORECASE)
        # Also strip favicon links since we don't host them
        html = re.sub(r'<link\b[^>]*\brel=["\'](?:icon|shortcut icon|apple-touch-icon)["\'][^>]*>', '', html, flags=re.IGNORECASE)

        # Find the closing </head> tag and inject CSS before it
        if css and '</head>' in html:
            html = html.replace('</head>', f'<style>{css}</style>\n</head>', 1)
        
        # Find the closing </body> tag and inject JS before it
        if js and '</body>' in html:
            html = html.replace('</body>', f'<script>{js}</script>\n</body>', 1)
        
        return html
    
    # Otherwise, wrap with CSS and JS
    style_tag = f"<style>{css}</style>" if css else ""
    script_tag = f"<script>{js}</script>" if js else ""
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {style_tag}
</head>
<body>
    {html}
    {script_tag}
</body>
</html>"""


def _build_generating_page(subdomain: str) -> str:
    """Build a friendly "generating" page."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Site Generating...</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
        }}
        .spinner {{
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 1.5rem;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
    </style>
    <script>
        // Refresh page every 10 seconds to check if generation is complete
        setTimeout(() => {{
            window.location.reload();
        }}, 10000);
    </script>
</head>
<body>
    <div class="container">
        <div class="spinner"></div>
        <h1>✨ Website Generating...</h1>
        <p>Your AI-generated website is being created.</p>
        <p style="font-size: 0.9rem; margin-top: 1rem;">This page will auto-refresh when ready.</p>
    </div>
</body>
</html>"""


def _build_error_page(subdomain: str, message: str) -> str:
    """Build a friendly error page."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Site Not Available</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            background: #f7fafc;
            color: #2d3748;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
            max-width: 500px;
        }}
        h1 {{
            font-size: 4rem;
            margin: 0 0 1rem;
        }}
        h2 {{
            font-size: 1.5rem;
            margin-bottom: 1rem;
            color: #4a5568;
        }}
        p {{
            color: #718096;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚧</h1>
        <h2>Site Not Available</h2>
        <p>{message}</p>
        <p style="font-size: 0.9rem; margin-top: 1.5rem;">
            Site: <code>{subdomain}</code>
        </p>
    </div>
</body>
</html>"""

