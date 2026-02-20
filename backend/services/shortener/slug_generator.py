"""
Slug Generator - Creates short, URL-safe slugs for the URL shortener.

Two slug strategies:
  1. generate_slug()           — pure random base62 (legacy / generic use)
  2. generate_business_slug()  — 4-letter name prefix + 3-char random suffix
                                  e.g. "Redwood Plumbing" → "redwx7k"
                                       "CAMP Clinic"      → "camp3mn"

Business-slug format makes URLs less spammy (a real prefix instead of
pure noise) while the 3-char suffix keeps enough entropy that a business
with many locations / retries still gets unique slugs.

Entropy of business slug suffix: 36^3 = 46 656 combinations per prefix.
"""
import re
import secrets
import string

# Base62 character set (URL-safe, no special characters)
BASE62_CHARS = string.ascii_letters + string.digits  # a-zA-Z0-9

# Lowercase-only charset for business slug (easier to read / type)
_LOWER_ALPHA = string.ascii_lowercase
_LOWER_ALPHANUM = string.ascii_lowercase + string.digits


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


def generate_business_slug(
    business_name: str,
    prefix_len: int = 4,
    suffix_len: int = 3,
) -> str:
    """
    Generate a human-readable slug using the business name as a prefix.

    Strategy:
      1. Strip all non-letter characters from the name (keep a-z only).
      2. Take the first `prefix_len` letters (lowercase).
      3. Pad with random lowercase letters if the name is shorter.
      4. Append `suffix_len` random lowercase alphanumeric characters.

    Examples:
        "Redwood Plumbing Service" → "redw" + "x7k" = "redwx7k"
        "CAMP Clinic - Los Angeles" → "camp" + "3mn" = "camp3mn"
        "A & M Plumbing"           → "ampl" + "9bz" = "ampl9bz"

    Args:
        business_name: Raw business name (any case, any characters).
        prefix_len:    How many name letters to use (default 4).
        suffix_len:    How many random chars to append (default 3).

    Returns:
        A lowercase string of length (prefix_len + suffix_len).
    """
    # Keep only letters, lowercase
    letters_only = re.sub(r"[^a-zA-Z]", "", business_name).lower()

    # Take up to prefix_len; pad with random lowercase letters if too short
    prefix = letters_only[:prefix_len]
    while len(prefix) < prefix_len:
        prefix += secrets.choice(_LOWER_ALPHA)

    suffix = "".join(secrets.choice(_LOWER_ALPHANUM) for _ in range(suffix_len))
    return prefix + suffix
