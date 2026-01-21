"""
Customer JWT Authentication

Handles JWT token generation, verification, and authentication
middleware for customer portal access.

Security Features:
- HS256 algorithm
- Token expiration (24 hours)
- Secure token generation
- HTTP-only cookie support

Author: WebMagic Team
Date: January 21, 2026
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.database import get_db
from core.exceptions import UnauthorizedError
from models.site_models import CustomerUser
from services.customer_auth_service import CustomerAuthService

logger = logging.getLogger(__name__)
settings = get_settings()

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# HTTP Bearer scheme for Authorization header
security = HTTPBearer(auto_error=False)


def create_customer_access_token(
    customer_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token for a customer.
    
    Args:
        customer_id: Customer user ID (UUID as string)
        email: Customer email
        expires_delta: Optional expiration time delta
    
    Returns:
        Encoded JWT token string
    
    Example:
        >>> token = create_customer_access_token("uuid", "user@example.com")
        >>> # Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    expire = datetime.utcnow() + expires_delta
    
    # Token payload
    to_encode = {
        "sub": customer_id,  # Subject (customer ID)
        "email": email,
        "type": "customer",  # Distinguish from admin tokens
        "exp": expire,  # Expiration time
        "iat": datetime.utcnow(),  # Issued at
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=ALGORITHM
    )
    
    logger.debug(f"Created access token for customer: {email}")
    return encoded_jwt


def verify_customer_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a customer JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    
    Raises:
        UnauthorizedError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        
        # Verify token type
        if payload.get("type") != "customer":
            raise UnauthorizedError("Invalid token type")
        
        # Verify required fields
        if not payload.get("sub") or not payload.get("email"):
            raise UnauthorizedError("Invalid token payload")
        
        return payload
    
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise UnauthorizedError("Could not validate credentials")


async def get_current_customer(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> CustomerUser:
    """
    Get current authenticated customer from JWT token.
    
    This is a FastAPI dependency that extracts and validates the JWT token
    from the Authorization header, then retrieves the customer from database.
    
    Args:
        credentials: HTTP Bearer credentials from request header
        db: Database session
    
    Returns:
        Authenticated CustomerUser instance
    
    Raises:
        HTTPException 401: If token is missing, invalid, or customer not found
    
    Usage:
        @router.get("/me")
        async def get_profile(customer: CustomerUser = Depends(get_current_customer)):
            return {"email": customer.email}
    """
    # Check if credentials provided
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Verify token
        payload = verify_customer_token(credentials.credentials)
        customer_id: str = payload.get("sub")
        
        if not customer_id:
            raise UnauthorizedError("Invalid token")
        
        # Get customer from database
        customer = await CustomerAuthService.get_customer_by_id(
            db=db,
            user_id=customer_id
        )
        
        if not customer:
            raise UnauthorizedError("Customer not found")
        
        if not customer.is_active:
            raise UnauthorizedError("Customer account is inactive")
        
        return customer
    
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_customer(
    current_customer: CustomerUser = Depends(get_current_customer)
) -> CustomerUser:
    """
    Get current active customer (email verified).
    
    Adds an additional check that email is verified.
    Use this for routes that require verified email.
    
    Args:
        current_customer: Customer from get_current_customer dependency
    
    Returns:
        Verified CustomerUser instance
    
    Raises:
        HTTPException 403: If email is not verified
    
    Usage:
        @router.post("/site/request-edit")
        async def request_edit(
            customer: CustomerUser = Depends(get_current_active_customer)
        ):
            # Only verified customers can request edits
            pass
    """
    if not current_customer.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email to access this feature.",
        )
    
    return current_customer


async def get_optional_customer(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[CustomerUser]:
    """
    Get current customer if authenticated, None otherwise.
    
    Useful for routes that work both authenticated and unauthenticated.
    
    Args:
        credentials: HTTP Bearer credentials (optional)
        db: Database session
    
    Returns:
        CustomerUser if authenticated, None otherwise
    
    Usage:
        @router.get("/site/{slug}")
        async def view_site(
            slug: str,
            customer: Optional[CustomerUser] = Depends(get_optional_customer)
        ):
            # Show different content based on authentication
            if customer:
                return {"message": "Welcome back", "user": customer.email}
            return {"message": "Welcome guest"}
    """
    if not credentials:
        return None
    
    try:
        payload = verify_customer_token(credentials.credentials)
        customer_id: str = payload.get("sub")
        
        if not customer_id:
            return None
        
        customer = await CustomerAuthService.get_customer_by_id(
            db=db,
            user_id=customer_id
        )
        
        return customer if customer and customer.is_active else None
    
    except Exception:
        return None


def create_customer_refresh_token(
    customer_id: str,
    email: str
) -> str:
    """
    Create a refresh token for extending sessions.
    
    Refresh tokens have longer expiration (7 days) and can be used
    to obtain new access tokens without re-authentication.
    
    Args:
        customer_id: Customer user ID
        email: Customer email
    
    Returns:
        Encoded refresh token
    """
    expires_delta = timedelta(days=7)
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": customer_id,
        "email": email,
        "type": "customer_refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=ALGORITHM
    )
    
    logger.debug(f"Created refresh token for customer: {email}")
    return encoded_jwt


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a refresh token.
    
    Args:
        token: Refresh token string
    
    Returns:
        Decoded token payload
    
    Raises:
        UnauthorizedError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        
        if payload.get("type") != "customer_refresh":
            raise UnauthorizedError("Invalid token type")
        
        return payload
    
    except JWTError as e:
        logger.warning(f"Refresh token verification failed: {e}")
        raise UnauthorizedError("Invalid refresh token")
