"""
Generated Sites Preview API

Serves HTML content for generated sites (from generated_sites table).
This is a PUBLIC endpoint that serves the actual website HTML.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging

from core.database import get_db
from models.site import GeneratedSite
from models.site_models import Site, SiteVersion
import re

router = APIRouter(tags=["generated-preview"])
logger = logging.getLogger(__name__)


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
        # Always strip and re-inject claim bar so style fixes apply to existing sites
        html_content = _remove_claim_bar(html_content)
        html_content = _inject_canonical_claim_bar(html_content, subdomain)
    
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


def _inject_canonical_claim_bar(html: str, slug: str) -> str:
    """
    Inject the canonical, always-up-to-date claim bar into site HTML.

    Called at serve time (not generation time) so styling fixes apply
    immediately to ALL existing sites without a DB migration.
    Uses explicit colors and `all: unset` on every text element so the
    site's own CSS can never override the claim bar's text color.
    """
    from core.config import get_settings
    api_url = get_settings().API_URL
    checkout_url = f"{api_url}/api/v1/sites/{slug}/purchase"

    claim_bar_html = f'''
<!-- WebMagic Claim Bar - Official -->
<div id="webmagic-claim-bar" style="position:fixed;bottom:0;left:0;right:0;z-index:9999;all:initial;display:block;">
  <div style="all:unset;display:flex;background:linear-gradient(135deg,#1e40af 0%,#7c3aed 100%);padding:12px 20px;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;box-shadow:0 -4px 20px rgba(0,0,0,0.25);">
    <div style="all:unset;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
      <span style="all:unset;font-size:20px;line-height:1;">🏢</span>
      <div style="all:unset;display:block;">
        <p style="all:unset;display:block;margin:0;font-weight:700;font-size:15px;color:#ffffff!important;text-shadow:0 1px 3px rgba(0,0,0,0.4);font-family:system-ui,sans-serif;line-height:1.4;">Is this your business?</p>
        <p style="all:unset;display:block;margin:0;font-size:13px;color:#e0e7ff!important;text-shadow:0 1px 2px rgba(0,0,0,0.3);font-family:system-ui,sans-serif;line-height:1.4;">Claim this website for only <strong style="color:#ffffff!important;font-weight:700;">$497</strong> &middot; Then just $97/month for hosting, maintenance &amp; updates</p>
        <a href="https://web.lavish.solutions/how-it-works" target="_blank" rel="noopener noreferrer" style="all:unset;display:inline-block;color:#bfdbfe!important;font-size:12px;text-decoration:underline;margin-top:3px;font-family:system-ui,sans-serif;cursor:pointer;">See what&#39;s included &rarr;</a>
      </div>
    </div>
    <button id="webmagic-claim-btn"
      onclick="(function(){{var m=document.createElement('div');m.id='webmagic-claim-modal';m.style='position:fixed;inset:0;z-index:10000;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.6);';m.innerHTML='<div style=\\'background:#fff;border-radius:16px;padding:40px;max-width:480px;width:90%;position:relative;\\'>  <button onclick=\\'this.closest(\\\"#webmagic-claim-modal\\\").remove()\\' style=\\'position:absolute;top:16px;right:16px;background:none;border:none;font-size:24px;cursor:pointer;color:#666;\\'>&times;</button>  <h2 style=\\'margin:0 0 8px;font-size:24px;color:#1e3a5f;\\'>Claim Your Website</h2>  <p style=\\'color:#666;margin:0 0 24px;\\'>Enter your details and we will contact you within 24 hours.</p>  <form id=\\'webmagic-claim-form\\' style=\\'display:flex;flex-direction:column;gap:12px;\\'>    <input type=\\'email\\' id=\\'claim-email\\' placeholder=\\'Your email address *\\' required style=\\'padding:14px 16px;border:2px solid #e2e8f0;border-radius:8px;font-size:15px;\\'>    <input type=\\'text\\' id=\\'claim-name\\' placeholder=\\'Your full name *\\' required style=\\'padding:14px 16px;border:2px solid #e2e8f0;border-radius:8px;font-size:15px;\\'>    <button type=\\'submit\\' style=\\'background:#7c3aed;color:#fff;border:none;padding:16px;border-radius:8px;font-size:16px;font-weight:700;cursor:pointer;\\'>Claim for $497</button>  </form></div>';document.body.appendChild(m);document.getElementById('webmagic-claim-form').addEventListener('submit',async function(e){{e.preventDefault();var email=document.getElementById('claim-email').value;var name=document.getElementById('claim-name').value;try{{var r=await fetch('{checkout_url}',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email:email,name:name}})}});var d=await r.json();if(d.checkout_url){{window.location.href=d.checkout_url;}}else{{alert('Something went wrong. Please try again.');}};}}catch(err){{alert('Something went wrong. Please try again.');}}}});}})()"
      style="all:unset;display:inline-block;background:#fbbf24;color:#1e3a5f!important;padding:12px 28px;border-radius:8px;font-weight:700;font-size:14px;cursor:pointer;text-transform:uppercase;letter-spacing:0.5px;font-family:system-ui,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,0.2);">
      CLAIM FOR $497
    </button>
  </div>
</div>
'''

    if "</body>" in html.lower():
        body_pos = html.lower().rfind("</body>")
        return html[:body_pos] + claim_bar_html + "\n" + html[body_pos:]
    return html + claim_bar_html


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

