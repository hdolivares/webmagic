"""
Preview System API Endpoints

Endpoints for viewing and comparing site edit previews.

Author: WebMagic Team
Date: January 21, 2026
"""
from typing import Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.deps import get_db
from models.site_models import Site, SiteVersion, EditRequest
from services.site_service import get_site_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/preview",
    tags=["preview"],
    responses={
        404: {"description": "Preview not found"}
    }
)


# ============================================================================
# PREVIEW ENDPOINTS
# ============================================================================

@router.get(
    "/{site_slug}/preview/{version_id}",
    response_class=HTMLResponse,
    summary="View preview version",
    description="""
    View a preview version of a site.
    
    This endpoint serves the HTML content of a preview version
    with preview controls for approval/rejection.
    """
)
async def view_preview(
    site_slug: str,
    version_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    """
    View a site preview.
    
    Args:
        site_slug: Site slug
        version_id: Preview version ID
        db: Database session
    
    Returns:
        HTML response with preview
    """
    try:
        # Get site
        site_query = select(Site).where(Site.slug == site_slug)
        result = await db.execute(site_query)
        site = result.scalar_one_or_none()
        
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site {site_slug} not found"
            )
        
        # Get preview version
        version_query = select(SiteVersion).where(
            SiteVersion.id == version_id,
            SiteVersion.site_id == site.id,
            SiteVersion.is_preview == True
        )
        result = await db.execute(version_query)
        version = result.scalar_one_or_none()
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preview version {version_id} not found"
            )
        
        # Get associated edit request for context
        edit_request_query = select(EditRequest).where(
            EditRequest.preview_version_id == version_id
        )
        result = await db.execute(edit_request_query)
        edit_request = result.scalar_one_or_none()
        
        # Build preview HTML with controls
        preview_html = _build_preview_with_controls(
            content_html=version.html_content,
            content_css=version.css_content,
            content_js=version.js_content,
            site=site,
            version=version,
            edit_request=edit_request
        )
        
        return HTMLResponse(content=preview_html)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving preview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while loading the preview"
        )


@router.get(
    "/{site_slug}/compare/{version_id}",
    response_class=HTMLResponse,
    summary="Compare preview with current",
    description="""
    View side-by-side comparison of current site and preview.
    
    Shows both versions in an iframe layout for easy comparison.
    """
)
async def compare_preview(
    site_slug: str,
    version_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    """
    Compare preview with current version.
    
    Args:
        site_slug: Site slug
        version_id: Preview version ID
        db: Database session
    
    Returns:
        HTML response with comparison view
    """
    try:
        # Get site
        site_query = select(Site).where(Site.slug == site_slug)
        result = await db.execute(site_query)
        site = result.scalar_one_or_none()
        
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site {site_slug} not found"
            )
        
        # Get current and preview versions
        if not site.current_version_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site has no current version"
            )
        
        current_query = select(SiteVersion).where(
            SiteVersion.id == site.current_version_id
        )
        result = await db.execute(current_query)
        current_version = result.scalar_one()
        
        preview_query = select(SiteVersion).where(
            SiteVersion.id == version_id
        )
        result = await db.execute(preview_query)
        preview_version = result.scalar_one_or_none()
        
        if not preview_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preview version {version_id} not found"
            )
        
        # Get edit request for context
        edit_request_query = select(EditRequest).where(
            EditRequest.preview_version_id == version_id
        )
        result = await db.execute(edit_request_query)
        edit_request = result.scalar_one_or_none()
        
        # Build comparison HTML
        comparison_html = _build_comparison_view(
            site=site,
            current_version=current_version,
            preview_version=preview_version,
            edit_request=edit_request
        )
        
        return HTMLResponse(content=comparison_html)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving comparison: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while loading the comparison"
        )


@router.get(
    "/{site_slug}/raw/{version_id}",
    response_class=HTMLResponse,
    summary="View raw preview HTML",
    description="""
    Get raw HTML of preview version without controls.
    
    Useful for embedding in iframes or comparison views.
    """
)
async def view_raw_preview(
    site_slug: str,
    version_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    """
    View raw preview HTML.
    
    Args:
        site_slug: Site slug
        version_id: Preview version ID
        db: Database session
    
    Returns:
        Raw HTML response
    """
    try:
        # Get version
        version_query = select(SiteVersion).where(
            SiteVersion.id == version_id
        )
        result = await db.execute(version_query)
        version = result.scalar_one_or_none()
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version_id} not found"
            )
        
        # Build complete HTML with inline CSS/JS
        complete_html = _build_complete_html(
            html=version.html_content,
            css=version.css_content,
            js=version.js_content
        )
        
        return HTMLResponse(content=complete_html)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving raw preview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while loading the preview"
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _build_preview_with_controls(
    content_html: str,
    content_css: Optional[str],
    content_js: Optional[str],
    site: Site,
    version: SiteVersion,
    edit_request: Optional[EditRequest]
) -> str:
    """
    Build preview HTML with approval/rejection controls.
    
    Args:
        content_html: Site HTML content
        content_css: Site CSS content
        content_css: Site JS content
        site: Site instance
        version: SiteVersion instance
        edit_request: Associated EditRequest if any
    
    Returns:
        Complete HTML with controls
    """
    # Build preview controls bar
    controls_html = f"""
    <div id="preview-controls" style="
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        z-index: 10000;
        font-family: system-ui, -apple-system, sans-serif;
    ">
        <div style="max-width: 1200px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between;">
            <div>
                <h3 style="margin: 0 0 0.5rem 0; font-size: 1.25rem; font-weight: 600;">
                    Preview: {site.site_title or site.slug}
                </h3>
                {f'<p style="margin: 0; opacity: 0.9; font-size: 0.875rem;">{edit_request.request_text}</p>' if edit_request else ''}
            </div>
            <div style="display: flex; gap: 1rem;">
                {f'''
                <button onclick="approveChanges()" style="
                    background: #10b981;
                    color: white;
                    border: none;
                    padding: 0.75rem 1.5rem;
                    border-radius: 0.5rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                " onmouseover="this.style.background='#059669'" onmouseout="this.style.background='#10b981'">
                    ✓ Approve Changes
                </button>
                <button onclick="rejectChanges()" style="
                    background: rgba(255,255,255,0.2);
                    color: white;
                    border: 2px solid white;
                    padding: 0.75rem 1.5rem;
                    border-radius: 0.5rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                " onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.2)'">
                    ✗ Reject
                </button>
                <a href="/preview/{site.slug}/compare/{version.id}" style="
                    background: rgba(255,255,255,0.1);
                    color: white;
                    border: 1px solid rgba(255,255,255,0.3);
                    padding: 0.75rem 1.5rem;
                    border-radius: 0.5rem;
                    text-decoration: none;
                    font-weight: 600;
                    transition: all 0.2s;
                " onmouseover="this.style.background='rgba(255,255,255,0.2)'" onmouseout="this.style.background='rgba(255,255,255,0.1)'">
                    Compare Versions
                </a>
                ''' if edit_request else ''}
            </div>
        </div>
    </div>
    <div style="height: 100px;"></div>
    """
    
    # Build complete HTML
    complete_html = _build_complete_html(content_html, content_css, content_js)
    
    # Inject controls before </body>
    if "</body>" in complete_html:
        complete_html = complete_html.replace("</body>", f"{controls_html}</body>")
    else:
        complete_html = controls_html + complete_html
    
    # Add JavaScript for approval/rejection
    if edit_request:
        script = f"""
        <script>
        function approveChanges() {{
            if (confirm('Approve these changes? They will be applied to your live site.')) {{
                fetch('/api/v1/sites/{site.id}/edits/{edit_request.id}/approve', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ approved: true, feedback: 'Approved from preview' }})
                }})
                .then(res => res.json())
                .then(data => {{
                    alert('Changes approved! Your site will be updated shortly.');
                    window.location.href = '/sites/{site.slug}';
                }})
                .catch(err => alert('Error approving changes: ' + err));
            }}
        }}
        
        function rejectChanges() {{
            const reason = prompt('Please tell us why you\'re rejecting these changes:');
            if (reason) {{
                fetch('/api/v1/sites/{site.id}/edits/{edit_request.id}/reject', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ approved: false, feedback: reason }})
                }})
                .then(res => res.json())
                .then(data => {{
                    alert('Changes rejected. You can submit a new request with different instructions.');
                    window.location.href = '/sites/{site.slug}';
                }})
                .catch(err => alert('Error rejecting changes: ' + err));
            }}
        }}
        </script>
        """
        complete_html = complete_html.replace("</body>", f"{script}</body>")
    
    return complete_html


def _build_comparison_view(
    site: Site,
    current_version: SiteVersion,
    preview_version: SiteVersion,
    edit_request: Optional[EditRequest]
) -> str:
    """Build side-by-side comparison view."""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Compare: {site.site_title or site.slug}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: system-ui, -apple-system, sans-serif; }}
            
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 1.5rem;
                text-align: center;
            }}
            
            .header h1 {{ font-size: 1.5rem; margin-bottom: 0.5rem; }}
            .header p {{ opacity: 0.9; }}
            
            .controls {{
                background: #f3f4f6;
                padding: 1rem;
                text-align: center;
                border-bottom: 1px solid #e5e7eb;
            }}
            
            .controls button {{
                margin: 0 0.5rem;
                padding: 0.75rem 1.5rem;
                border: none;
                border-radius: 0.5rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
            }}
            
            .btn-approve {{
                background: #10b981;
                color: white;
            }}
            
            .btn-approve:hover {{ background: #059669; }}
            
            .btn-reject {{
                background: #ef4444;
                color: white;
            }}
            
            .btn-reject:hover {{ background: #dc2626; }}
            
            .comparison {{
                display: flex;
                height: calc(100vh - 160px);
            }}
            
            .pane {{
                flex: 1;
                display: flex;
                flex-direction: column;
                border-right: 1px solid #e5e7eb;
            }}
            
            .pane:last-child {{ border-right: none; }}
            
            .pane-header {{
                background: #f9fafb;
                padding: 1rem;
                border-bottom: 2px solid #e5e7eb;
                font-weight: 600;
                text-align: center;
            }}
            
            .pane-current {{ color: #6b7280; }}
            .pane-preview {{ color: #8b5cf6; }}
            
            .pane iframe {{
                flex: 1;
                border: none;
                width: 100%;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Compare Versions: {site.site_title or site.slug}</h1>
            {f'<p>{edit_request.request_text}</p>' if edit_request else ''}
        </div>
        
        {f'''
        <div class="controls">
            <button class="btn-approve" onclick="approveChanges()">
                ✓ Approve Preview
            </button>
            <button class="btn-reject" onclick="rejectChanges()">
                ✗ Reject Changes
            </button>
        </div>
        ''' if edit_request and edit_request.status == 'ready_for_review' else ''}
        
        <div class="comparison">
            <div class="pane">
                <div class="pane-header pane-current">
                    Current Version
                </div>
                <iframe src="/preview/{site.slug}/raw/{current_version.id}" title="Current Version"></iframe>
            </div>
            
            <div class="pane">
                <div class="pane-header pane-preview">
                    Preview (New Changes)
                </div>
                <iframe src="/preview/{site.slug}/raw/{preview_version.id}" title="Preview Version"></iframe>
            </div>
        </div>
        
        {f'''
        <script>
        function approveChanges() {{
            if (confirm('Approve these changes? They will be applied to your live site.')) {{
                fetch('/api/v1/sites/{site.id}/edits/{edit_request.id}/approve', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ approved: true, feedback: 'Approved from comparison view' }})
                }})
                .then(res => res.json())
                .then(data => {{
                    alert('Changes approved! Your site will be updated shortly.');
                    window.location.href = '/sites/{site.slug}';
                }})
                .catch(err => alert('Error: ' + err));
            }}
        }}
        
        function rejectChanges() {{
            const reason = prompt('Please tell us why you\'re rejecting these changes:');
            if (reason) {{
                fetch('/api/v1/sites/{site.id}/edits/{edit_request.id}/reject', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ approved: false, feedback: reason }})
                }})
                .then(res => res.json())
                .then(data => {{
                    alert('Changes rejected. You can submit a new request.');
                    window.location.href = '/sites/{site.slug}';
                }})
                .catch(err => alert('Error: ' + err));
            }}
        }}
        </script>
        ''' if edit_request else ''}
    </body>
    </html>
    """


def _build_complete_html(
    html: str,
    css: Optional[str],
    js: Optional[str]
) -> str:
    """Build complete HTML with inline CSS and JS."""
    # If HTML is already complete, just add CSS/JS
    if "<!DOCTYPE" in html or "<html" in html:
        # Inject CSS before </head> if present
        if css and "</head>" in html:
            html = html.replace("</head>", f"<style>{css}</style></head>")
        
        # Inject JS before </body> if present
        if js and "</body>" in html:
            html = html.replace("</body>", f"<script>{js}</script></body>")
        
        return html
    
    # Build from scratch
    css_tag = f"<style>{css}</style>" if css else ""
    js_tag = f"<script>{js}</script>" if js else ""
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {css_tag}
    </head>
    <body>
        {html}
        {js_tag}
    </body>
    </html>
    """

