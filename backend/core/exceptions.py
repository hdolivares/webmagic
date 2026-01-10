"""
Custom exception classes for WebMagic application.
"""


class WebMagicException(Exception):
    """Base exception for all WebMagic errors."""
    pass


class DatabaseException(WebMagicException):
    """Database-related errors."""
    pass


class AuthenticationException(WebMagicException):
    """Authentication and authorization errors."""
    pass


class ExternalAPIException(WebMagicException):
    """Errors from external APIs (Outscraper, Anthropic, etc.)."""
    pass


class GenerationException(WebMagicException):
    """Errors during website generation."""
    pass


class PaymentException(WebMagicException):
    """Payment processing errors."""
    pass


class ValidationException(WebMagicException):
    """Data validation errors."""
    pass
