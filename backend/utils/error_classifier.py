"""
Shared error classification utility for Celery tasks.

Used by generation, validation, and scraping tasks to produce a consistent
error_category alongside a human-readable message, so the frontend can
render actionable error banners instead of raw exception strings.
"""


def classify_error(exc: Exception) -> tuple[str, str]:
    """
    Return (error_category, human_readable_message) for any generation or
    validation exception.

    Categories
    ----------
    credits_exhausted  Anthropic API returned "credit balance is too low"
    data_error         Business data has missing/invalid fields
    api_error          External API failure (not credits-related)
    timeout            Operation timed out
    unknown            Anything else
    """
    msg = str(exc)
    lower = msg.lower()

    if "credit balance is too low" in lower or ("credits" in lower and "too low" in lower):
        return "credits_exhausted", (
            "Anthropic API credits exhausted. Add credits at "
            "console.anthropic.com/settings/billing to resume."
        )
    if any(phrase in lower for phrase in [
        "not supported between instances of 'nonetype'",
        "nonetype",
        "attributeerror",
        "keyerror",
        "typeerror",
        "valueerror",
    ]):
        return "data_error", f"Business data issue: {msg[:300]}"
    if any(phrase in lower for phrase in ["timeout", "timed out", "read timeout"]):
        return "timeout", f"Operation timed out: {msg[:300]}"
    if any(phrase in lower for phrase in [
        "api failed", "claude api", "gemini", "openai", "external api",
        "http", "connection", "status code", "anthropic",
    ]):
        return "api_error", f"External API error: {msg[:300]}"
    return "unknown", msg[:400]
