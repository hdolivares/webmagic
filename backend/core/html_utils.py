"""
HTML utility helpers shared across the codebase.
"""
import re


def strip_claim_bar(html: str) -> str:
    """
    Remove all WebMagic claim-bar markup (HTML, CSS, JS) from a full HTML document.

    The architect always injects the claim bar into generated HTML before saving to
    the database.  Any code path that deploys HTML to disk for an *owned* site, or
    that feeds HTML to the site-edit AI pipeline, must strip it first so the bar
    doesn't appear on live sites and doesn't confuse the LLM.
    """
    if not html or "webmagic-claim" not in html.lower():
        return html

    # 1. Remove the claim-bar <div> (with optional preceding HTML comment)
    patterns = [
        r'<!--\s*WebMagic Claim Bar[^-]*-->\s*<div\s+id=["\']webmagic-claim-bar["\'][^>]*>.*?</div>',
        r'<div\s+id=["\']webmagic-claim-bar["\'][^>]*>.*?</div>',
        r'<div[^>]*id=["\']?claim[^>]*>.*?</div>',
    ]
    for pattern in patterns:
        html = re.sub(pattern, "", html, flags=re.DOTALL | re.IGNORECASE)

    # 2. Remove claim-bar JS block
    html = re.sub(
        r"//\s*WebMagic Claim Bar Handler.*?\}\)\(\);",
        "",
        html,
        flags=re.DOTALL,
    )

    # 3. Remove claim-bar CSS block (inside a <style> tag or standalone CSS file)
    html = re.sub(
        r"/\*\s*WebMagic Claim Bar Styles\s*\*/.*?(?=/\*|</style>|$)",
        "",
        html,
        flags=re.DOTALL,
    )

    return html


def strip_claim_bar_css(css: str) -> str:
    """Remove the claim-bar CSS block from a standalone CSS string."""
    if not css or "WebMagic Claim Bar" not in css:
        return css
    return re.sub(
        r"/\*\s*WebMagic Claim Bar Styles\s*\*/.*?(?=/\*|$)",
        "",
        css,
        flags=re.DOTALL,
    )
