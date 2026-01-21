"""
Custom exception classes for WebMagic application.

Exception hierarchy follows HTTP status codes for API consistency.
"""
from typing import Optional


class WebMagicException(Exception):
    """Base exception for all WebMagic errors."""
    
    def __init__(self, message: str, status_code: int = 500):
        """
        Initialize exception.
        
        Args:
            message: Error message
            status_code: HTTP status code
        """
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# 400 Series - Client Errors


class ValidationError(WebMagicException):
    """
    Data validation error (HTTP 400).
    
    Used when request data fails validation.
    """
    
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class UnauthorizedError(WebMagicException):
    """
    Authentication error (HTTP 401).
    
    Used when credentials are invalid or missing.
    """
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class ForbiddenError(WebMagicException):
    """
    Authorization error (HTTP 403).
    
    Used when user lacks permission for action.
    """
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403)


class NotFoundError(WebMagicException):
    """
    Resource not found error (HTTP 404).
    
    Used when requested resource doesn't exist.
    """
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ConflictError(WebMagicException):
    """
    Conflict error (HTTP 409).
    
    Used when resource already exists or conflicts with current state.
    """
    
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=409)


# Legacy/Specific Error Classes (inherit from base classes above)


class DatabaseException(WebMagicException):
    """Database-related errors (HTTP 500)."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class AuthenticationException(UnauthorizedError):
    """Legacy authentication exception (use UnauthorizedError instead)."""
    pass


class ExternalAPIException(WebMagicException):
    """Errors from external APIs (HTTP 502)."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=502)


class GenerationException(WebMagicException):
    """Errors during website generation (HTTP 500)."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class PaymentException(WebMagicException):
    """Payment processing errors (HTTP 402)."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=402)


class ValidationException(ValidationError):
    """Legacy validation exception (use ValidationError instead)."""
    pass
