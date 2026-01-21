"""
Customer Authentication Service

Handles customer user registration, login, email verification,
and password reset for the customer portal.

Author: WebMagic Team
Date: January 21, 2026
"""
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext

from models.site_models import CustomerUser, Site
from core.exceptions import UnauthorizedError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CustomerAuthService:
    """Service for customer authentication operations."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
        
        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password to verify against
        
        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        Generate a random token for email verification or password reset.
        
        Args:
            length: Length of token in bytes
        
        Returns:
            URL-safe token string
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    async def create_customer_user(
        db: AsyncSession,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        site_id: Optional[UUID] = None
    ) -> CustomerUser:
        """
        Create a new customer user account.
        
        Args:
            db: Database session
            email: Customer email
            password: Plain text password
            full_name: Optional full name
            phone: Optional phone number
            site_id: Optional site ID to associate
        
        Returns:
            Created CustomerUser instance
        
        Raises:
            ValidationError: If email already exists
        """
        # Check if email exists
        result = await db.execute(
            select(CustomerUser).where(CustomerUser.email == email.lower())
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ValidationError("Email already registered")
        
        # Create user
        user = CustomerUser(
            email=email.lower(),
            password_hash=CustomerAuthService.hash_password(password),
            full_name=full_name,
            phone=phone,
            site_id=site_id,
            email_verification_token=CustomerAuthService.generate_token(),
            is_active=True
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Created customer user: {email}")
        return user
    
    @staticmethod
    async def authenticate_customer(
        db: AsyncSession,
        email: str,
        password: str
    ) -> Tuple[CustomerUser, bool]:
        """
        Authenticate a customer user.
        
        Args:
            db: Database session
            email: Customer email
            password: Plain text password
        
        Returns:
            Tuple of (CustomerUser, email_verified)
        
        Raises:
            UnauthorizedError: If credentials are invalid
        """
        # Get user
        result = await db.execute(
            select(CustomerUser).where(CustomerUser.email == email.lower())
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UnauthorizedError("Invalid email or password")
        
        if not user.is_active:
            raise UnauthorizedError("Account is inactive")
        
        # Verify password
        if not CustomerAuthService.verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")
        
        # Update last login
        user.update_last_login()
        await db.commit()
        
        logger.info(f"Customer authenticated: {email}")
        return user, user.email_verified
    
    @staticmethod
    async def verify_email(
        db: AsyncSession,
        token: str
    ) -> CustomerUser:
        """
        Verify a customer's email address.
        
        Args:
            db: Database session
            token: Email verification token
        
        Returns:
            Verified CustomerUser instance
        
        Raises:
            NotFoundError: If token is invalid
        """
        result = await db.execute(
            select(CustomerUser).where(
                CustomerUser.email_verification_token == token
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError("Invalid verification token")
        
        if user.email_verified:
            return user  # Already verified
        
        # Mark as verified
        user.email_verified = True
        user.email_verified_at = datetime.utcnow()
        user.email_verification_token = None
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Email verified for customer: {user.email}")
        return user
    
    @staticmethod
    async def resend_verification_email(
        db: AsyncSession,
        email: str
    ) -> CustomerUser:
        """
        Resend verification email (generates new token).
        
        Args:
            db: Database session
            email: Customer email
        
        Returns:
            CustomerUser instance with new token
        
        Raises:
            NotFoundError: If user doesn't exist
            ValidationError: If already verified
        """
        result = await db.execute(
            select(CustomerUser).where(CustomerUser.email == email.lower())
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError("User not found")
        
        if user.email_verified:
            raise ValidationError("Email already verified")
        
        # Generate new token
        user.email_verification_token = CustomerAuthService.generate_token()
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Resent verification email to: {email}")
        return user
    
    @staticmethod
    async def request_password_reset(
        db: AsyncSession,
        email: str
    ) -> CustomerUser:
        """
        Request a password reset (generates token).
        
        Args:
            db: Database session
            email: Customer email
        
        Returns:
            CustomerUser instance with reset token
        
        Raises:
            NotFoundError: If user doesn't exist
        """
        result = await db.execute(
            select(CustomerUser).where(CustomerUser.email == email.lower())
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Don't reveal that email doesn't exist
            logger.warning(f"Password reset requested for non-existent email: {email}")
            raise NotFoundError("If the email exists, a reset link will be sent")
        
        # Generate reset token (expires in 1 hour)
        user.password_reset_token = CustomerAuthService.generate_token()
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Password reset requested for: {email}")
        return user
    
    @staticmethod
    async def reset_password(
        db: AsyncSession,
        token: str,
        new_password: str
    ) -> CustomerUser:
        """
        Reset password using a reset token.
        
        Args:
            db: Database session
            token: Password reset token
            new_password: New plain text password
        
        Returns:
            CustomerUser instance with updated password
        
        Raises:
            NotFoundError: If token is invalid
            ValidationError: If token is expired
        """
        result = await db.execute(
            select(CustomerUser).where(
                CustomerUser.password_reset_token == token
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError("Invalid reset token")
        
        # Check if token is expired
        if not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
            raise ValidationError("Reset token has expired")
        
        # Update password
        user.password_hash = CustomerAuthService.hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Password reset for customer: {user.email}")
        return user
    
    @staticmethod
    async def change_password(
        db: AsyncSession,
        user_id: UUID,
        current_password: str,
        new_password: str
    ) -> CustomerUser:
        """
        Change password for a logged-in user.
        
        Args:
            db: Database session
            user_id: Customer user ID
            current_password: Current plain text password
            new_password: New plain text password
        
        Returns:
            CustomerUser instance with updated password
        
        Raises:
            NotFoundError: If user doesn't exist
            UnauthorizedError: If current password is wrong
        """
        result = await db.execute(
            select(CustomerUser).where(CustomerUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError("User not found")
        
        # Verify current password
        if not CustomerAuthService.verify_password(current_password, user.password_hash):
            raise UnauthorizedError("Current password is incorrect")
        
        # Update password
        user.password_hash = CustomerAuthService.hash_password(new_password)
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Password changed for customer: {user.email}")
        return user
    
    @staticmethod
    async def get_customer_by_id(
        db: AsyncSession,
        user_id: UUID
    ) -> CustomerUser:
        """
        Get customer user by ID.
        
        Args:
            db: Database session
            user_id: Customer user ID
        
        Returns:
            CustomerUser instance
        
        Raises:
            NotFoundError: If user doesn't exist
        """
        result = await db.execute(
            select(CustomerUser).where(CustomerUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError("User not found")
        
        return user
    
    @staticmethod
    async def get_customer_by_email(
        db: AsyncSession,
        email: str
    ) -> Optional[CustomerUser]:
        """
        Get customer user by email.
        
        Args:
            db: Database session
            email: Customer email
        
        Returns:
            CustomerUser instance or None
        """
        result = await db.execute(
            select(CustomerUser).where(CustomerUser.email == email.lower())
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_customer_profile(
        db: AsyncSession,
        user_id: UUID,
        full_name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> CustomerUser:
        """
        Update customer profile.
        
        Args:
            db: Database session
            user_id: Customer user ID
            full_name: Optional new full name
            phone: Optional new phone
        
        Returns:
            Updated CustomerUser instance
        
        Raises:
            NotFoundError: If user doesn't exist
        """
        user = await CustomerAuthService.get_customer_by_id(db, user_id)
        
        if full_name is not None:
            user.full_name = full_name
        if phone is not None:
            user.phone = phone
        
        user.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Profile updated for customer: {user.email}")
        return user
