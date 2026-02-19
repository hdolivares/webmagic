"""
HTML utility helpers shared across the codebase.
"""
import re

# ── Markers that identify where claim-bar content starts ──────────────────────
# Checked in order; the earliest one found in the document wins.
_CLAIM_MARKERS = [
    "webmagic claim bar",   # comment: <!-- WebMagic Claim Bar ... -->
    "webmagic-claim-bar",   # outer wrapper div id
    "webmagic-claim",       # any other claim element
]

# Standalone button that survives when the outer wrapper was already removed
_CLAIM_BTN_RE = re.compile(
    r"<button[^>]+id=[\"']webmagic-claim-btn[\"'][^>]*>.*?</button>",
    re.DOTALL | re.IGNORECASE,
)

# Orphaned </div>s that appear between page content and </body> after stripping
_ORPHAN_DIVS_BEFORE_BODY_RE = re.compile(
    r"(\s*</div>){1,5}(\s*</body>)",
    re.IGNORECASE,
)

# Claim-bar JavaScript block
_CLAIM_JS_RE = re.compile(
    r"//\s*WebMagic Claim Bar Handler.*?\}\)\(\);",
    re.DOTALL,
)

# Claim-bar CSS block (in <style> tags or standalone CSS files)
_CLAIM_CSS_RE = re.compile(
    r"/\*\s*WebMagic Claim Bar Styles\s*\*/.*?(?=/\*|</style>|$)",
    re.DOTALL,
)


def strip_claim_bar(html: str) -> str:
    """
    Remove all WebMagic claim-bar markup from a full HTML document.

    Strategy
    --------
    Regex-matching *nested* HTML is fundamentally unreliable — a non-greedy
    ``.*?</div>`` always stops at the first closing tag, leaving sibling divs
    and child buttons behind.

    Instead we:

    1. **Anchor search** — find the first occurrence of any claim-bar marker
       string (case-insensitive), walk backwards to the nearest ``<`` to get
       the true start of the HTML element/comment, then truncate the document
       from that point and re-append ``</body>\\n</html>`` cleanly.

    2. **Fallback button removal** — explicitly remove ``<button id="webmagic-
       claim-btn">`` in case the outer wrapper was already stripped in a
       previous pass but the button survived.

    3. **Orphan div cleanup** — remove stray ``</div>`` tags that appear
       directly before ``</body>`` after partial stripping.

    4. **JS / CSS removal** — strip the claim-bar script block and CSS block.
    """
    if not html:
        return html

    lower = html.lower()

    # ── 1. Anchor-based truncation ─────────────────────────────────────────
    for marker in _CLAIM_MARKERS:
        idx = lower.find(marker)
        if idx < 0:
            continue

        # Walk back to the start of the enclosing HTML tag / comment
        tag_start = html.rfind("<", 0, idx)
        if tag_start < 0:
            tag_start = idx

        before = html[:tag_start].rstrip()
        html = before + "\n</body>\n</html>"
        lower = html.lower()
        break  # stop after first match — one truncation is enough

    # ── 2. Fallback: remove standalone claim button ────────────────────────
    html = _CLAIM_BTN_RE.sub("", html)

    # ── 3. Remove orphaned closing divs now sitting before </body> ─────────
    html = _ORPHAN_DIVS_BEFORE_BODY_RE.sub(r"\2", html)

    # ── 4. Remove claim-bar JavaScript block ───────────────────────────────
    html = _CLAIM_JS_RE.sub("", html)

    # ── 5. Remove claim-bar CSS block (inside <style> tags) ────────────────
    html = _CLAIM_CSS_RE.sub("", html)

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
