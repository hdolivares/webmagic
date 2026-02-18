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
from models.site_models import Site
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
    Serve generated site HTML content.
    
    Args:
        subdomain: Site subdomain/slug (e.g., 'mayfair-plumbers-1770254203251-83b6e7b8')
        db: Database session
    
    Returns:
        HTMLResponse with complete site HTML
    """
    try:
        # Query generated_sites table
        query = select(GeneratedSite).where(
            GeneratedSite.subdomain == subdomain
        )
        result = await db.execute(query)
        site = result.scalar_one_or_none()
        
        if not site:
            logger.warning(f"Generated site not found: {subdomain}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site not found: {subdomain}"
            )
        
        # Check if site has content
        if not site.html_content:
            logger.warning(f"Site {subdomain} has no HTML content (status: {site.status})")
            
            # Return a friendly message if site is still generating
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
                logger.info(f"Site {subdomain} is owned (purchase record: {purchased_site.slug})")
        
        # Get HTML content
        html_content = site.html_content
        
        # Remove claim bar if site is owned
        if is_owned:
            html_content = _remove_claim_bar(html_content)
            logger.info(f"Removed claim bar from owned site: {subdomain}")
        
        # Build complete HTML with inline CSS and JS
        complete_html = _build_complete_html(
            html=html_content,
            css=site.css_content,
            js=site.js_content
        )
        
        logger.info(f"Serving generated site: {subdomain} (status: {site.status}, owned: {is_owned})")
        return HTMLResponse(content=complete_html)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving generated site {subdomain}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while loading the site"
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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

