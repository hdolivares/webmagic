"""
Text formatting utilities.

Shared helpers for consistent display (e.g. business names in emails and checkout).
"""


def title_case(name: str) -> str:
    """
    Capitalize first letter of every word, rest lowercase.
    Fixes ALL CAPS business names for better readability.

    Examples:
        "A-1 PLUMBING CO." -> "A-1 Plumbing Co."
        "MARSHALL CAMPBELL & CO." -> "Marshall Campbell & Co."
    """
    if not name or not name.strip():
        return name or ""
    return " ".join(
        (w[0:1].upper() + w[1:].lower()) for w in name.strip().split()
    ).strip()
