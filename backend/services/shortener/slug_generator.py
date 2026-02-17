"""
Slug Generator - Creates short, URL-safe slugs for the URL shortener.

Uses base62 encoding (a-zA-Z0-9) for compact, URL-safe identifiers.
6 characters = 62^6 = 56.8 billion combinations.
"""
import secrets
import string

# Base62 character set (URL-safe, no special characters)
BASE62_CHARS = string.ascii_letters + string.digits  # a-zA-Z0-9


def generate_slug(length: int = 6) -> str:
    """
    Generate a random base62 slug.

    Args:
        length: Number of characters (default 6).
                6 chars = 56.8B combos, 7 = 3.5T, 8 = 218T.

    Returns:
        Random base62 string (e.g., 'a1B2c3').
    """
    return "".join(secrets.choice(BASE62_CHARS) for _ in range(length))
