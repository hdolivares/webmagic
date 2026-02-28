"""
Site file export utilities.

Handles two concerns:
  1. Writing the text files (index.html, styles.css, script.js) to the same
     directory on disk where site images already live, so the folder is a
     self-contained snapshot of the site.
  2. Assembling an in-memory ZIP archive containing the text files and any
     images already saved to disk, ready to stream as a browser download.

These are pure utility functions with no database access — the caller is
responsible for fetching the site record and passing the content in.
"""
import io
import logging
import zipfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Filenames written to disk and included in the ZIP.
_TEXT_FILES: dict[str, str] = {
    "index.html": "html",
    "styles.css": "css",
    "script.js":  "js",
}


def write_site_files(
    subdomain: str,
    html: Optional[str],
    css: Optional[str],
    js: Optional[str],
    sites_base_path: str,
) -> Path:
    """
    Write index.html, styles.css, and script.js into the site's directory.

    The directory ``{sites_base_path}/{subdomain}/`` is created if it doesn't
    exist yet.  Files are only written when the source string is non-empty so
    a site with no CSS (e.g. inline-only) won't produce an empty styles.css.

    Returns the Path of the site directory.
    """
    site_dir = Path(sites_base_path) / subdomain
    site_dir.mkdir(parents=True, exist_ok=True)

    content_map = {"index.html": html, "styles.css": css, "script.js": js}
    for filename, content in content_map.items():
        if content:
            file_path = site_dir / filename
            file_path.write_text(content, encoding="utf-8")
            logger.info("Wrote %s (%d bytes)", file_path, len(content))
        else:
            logger.debug("Skipped %s — no content provided", filename)

    return site_dir


def build_site_zip(
    subdomain: str,
    html: Optional[str],
    css: Optional[str],
    js: Optional[str],
    sites_base_path: str,
) -> bytes:
    """
    Build an in-memory ZIP archive containing all site assets.

    Archive layout::

        index.html
        styles.css          (omitted if empty)
        script.js           (omitted if empty)
        img/hero.jpg        (from disk, if present)
        img/about.jpg       (from disk, if present)
        img/services.jpg    (from disk, if present)

    Images are read from ``{sites_base_path}/{subdomain}/img/``.  Any image
    file present in that directory is included, so future image names are
    handled automatically.

    Returns the raw ZIP bytes ready to stream as an HTTP response.
    """
    buffer = io.BytesIO()
    img_dir = Path(sites_base_path) / subdomain / "img"

    content_map = {"index.html": html, "styles.css": css, "script.js": js}

    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, content in content_map.items():
            if content:
                zf.writestr(filename, content.encode("utf-8"))

        if img_dir.exists():
            for img_path in sorted(img_dir.iterdir()):
                if img_path.is_file():
                    zf.write(img_path, arcname=f"img/{img_path.name}")
                    logger.debug("Added image to ZIP: %s", img_path.name)

    zip_bytes = buffer.getvalue()
    logger.info(
        "Built ZIP for %r: %d bytes (%d entries)",
        subdomain,
        len(zip_bytes),
        len(content_map),
    )
    return zip_bytes
