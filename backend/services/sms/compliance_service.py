"""
SMS Compliance Service - TCPA & Best Practices Enforcement.

This service ensures we comply with US TCPA regulations and SMS best practices:
- Immediate opt-out honoring (STOP keyword)
- Business hours enforcement
- Opt-out list management
- Do-not-disturb periods
- Consent tracking

Author: WebMagic Team
Date: January 21, 2026
"""
import logging
from typing import Optional, Tuple
from datetime import datetime, time, timedelta
from uuid import UUID
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.sms_opt_out import SMSOptOut
from core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class SMSComplianceService:
    """
    Enforces SMS compliance and best practices.
    
    Key responsibilities:
    1. Check if recipient has opted out
    2. Validate business hours
    3. Process STOP requests
    4. Track opt-out history
    """
    
    # STOP keywords (case-insensitive)
    STOP_KEYWORDS = [
        "stop", "stopall", "unsubscribe", "cancel", "end", "quit",
        "stopit", "no", "remove", "optout", "opt-out", "opt out"
    ]
    
    # Business hours (local time)
    BUSINESS_HOURS_START = time(9, 0)   # 9:00 AM
    BUSINESS_HOURS_END = time(21, 0)    # 9:00 PM
    
    def __init__(self, db: AsyncSession):
        """Initialize compliance service with database session."""
        self.db = db
    
    # ========================================================================
    # OPT-OUT CHECKING
    # ========================================================================
    
    async def is_opted_out(self, phone_number: str) -> bool:
        """
        Check if a phone number has opted out.
        
        Args:
            phone_number: Phone in E.164 format (e.g., +12345678900)
        
        Returns:
            True if opted out, False if allowed to send
        """
        phone_number = self._normalize_phone(phone_number)
        
        result = await self.db.execute(
            select(SMSOptOut).where(SMSOptOut.phone_number == phone_number)
        )
        opt_out = result.scalar_one_or_none()
        
        if opt_out:
            logger.info(f"Phone {phone_number} is opted out (source: {opt_out.source})")
            return True
        
        return False
    
    async def check_can_send(
        self,
        phone_number: str,
        timezone_str: str = "America/Chicago"
    ) -> Tuple[bool, Optional[str]]:
        """
        Comprehensive check if we can send SMS to this number.
        
        Args:
            phone_number: Phone in E.164 format
            timezone_str: Recipient's timezone for business hours check
        
        Returns:
            Tuple of (can_send, reason_if_not)
        """
        phone_number = self._normalize_phone(phone_number)
        
        # Check 1: Opted out?
        if await self.is_opted_out(phone_number):
            return (False, "Recipient has opted out")
        
        # Check 2: Business hours?
        if not self._is_business_hours(timezone_str):
            return (False, "Outside business hours (9 AM - 9 PM local time)")
        
        # All checks passed
        return (True, None)
    
    # ========================================================================
    # OPT-OUT MANAGEMENT
    # ========================================================================
    
    async def add_opt_out(
        self,
        phone_number: str,
        source: str,
        campaign_id: Optional[UUID] = None,
        notes: Optional[str] = None
    ) -> SMSOptOut:
        """
        Add a phone number to the opt-out list.
        
        Args:
            phone_number: Phone in E.164 format
            source: How they opted out (reply_stop, manual, complaint, admin)
            campaign_id: Campaign they opted out from (if applicable)
            notes: Optional notes
        
        Returns:
            SMSOptOut instance
        """
        phone_number = self._normalize_phone(phone_number)
        
        # Check if already opted out
        existing = await self.db.execute(
            select(SMSOptOut).where(SMSOptOut.phone_number == phone_number)
        )
        if existing.scalar_one_or_none():
            logger.info(f"Phone {phone_number} already opted out")
            return existing.scalar_one()
        
        # Create opt-out record
        opt_out = SMSOptOut(
            phone_number=phone_number,
            opted_out_at=datetime.utcnow(),
            source=source,
            campaign_id=campaign_id,
            notes=notes
        )
        
        self.db.add(opt_out)
        await self.db.commit()
        await self.db.refresh(opt_out)
        
        logger.info(f"Added opt-out: {phone_number} (source: {source})")
        return opt_out
    
    async def remove_opt_out(self, phone_number: str) -> bool:
        """
        Remove a phone number from opt-out list.
        
        This should only be used if the recipient explicitly re-consents.
        Use with extreme caution - violating TCPA can result in fines.
        
        Args:
            phone_number: Phone in E.164 format
        
        Returns:
            True if removed, False if not found
        """
        phone_number = self._normalize_phone(phone_number)
        
        result = await self.db.execute(
            select(SMSOptOut).where(SMSOptOut.phone_number == phone_number)
        )
        opt_out = result.scalar_one_or_none()
        
        if not opt_out:
            return False
        
        await self.db.delete(opt_out)
        await self.db.commit()
        
        logger.warning(
            f"Removed opt-out for {phone_number} - ensure explicit re-consent was obtained!"
        )
        return True
    
    # ========================================================================
    # REPLY PROCESSING
    # ========================================================================
    
    def is_stop_keyword(self, message: str) -> bool:
        """
        Check if a message contains a STOP keyword.
        
        Args:
            message: The SMS reply text
        
        Returns:
            True if contains STOP keyword
        """
        message_lower = message.strip().lower()
        
        # Check exact match first
        if message_lower in self.STOP_KEYWORDS:
            return True
        
        # Check if any stop keyword is in the message
        for keyword in self.STOP_KEYWORDS:
            if keyword in message_lower:
                return True
        
        return False
    
    async def process_reply(
        self,
        phone_number: str,
        reply_message: str,
        campaign_id: Optional[UUID] = None
    ) -> Tuple[str, bool]:
        """
        Process an SMS reply and handle STOP requests.
        
        Args:
            phone_number: Phone that replied
            reply_message: The message content
            campaign_id: Campaign being replied to
        
        Returns:
            Tuple of (action_taken, is_opt_out)
            action_taken: "opt_out", "reply", or "none"
        """
        phone_number = self._normalize_phone(phone_number)
        
        # Check if it's a STOP request
        if self.is_stop_keyword(reply_message):
            await self.add_opt_out(
                phone_number=phone_number,
                source="reply_stop",
                campaign_id=campaign_id,
                notes=f"Reply: {reply_message[:100]}"
            )
            logger.info(f"Processed STOP request from {phone_number}")
            return ("opt_out", True)
        
        # Not a STOP request - just a regular reply
        logger.info(f"Received reply from {phone_number}: {reply_message[:50]}...")
        return ("reply", False)
    
    # ========================================================================
    # BUSINESS HOURS
    # ========================================================================
    
    def _is_business_hours(self, timezone_str: str = "America/Chicago") -> bool:
        """
        Check if current time is within business hours (9 AM - 9 PM local time).
        
        Args:
            timezone_str: Timezone string (e.g., "America/Chicago")
        
        Returns:
            True if within business hours
        """
        try:
            tz = pytz.timezone(timezone_str)
            local_time = datetime.now(tz).time()
            
            return self.BUSINESS_HOURS_START <= local_time <= self.BUSINESS_HOURS_END
        
        except Exception as e:
            logger.error(f"Error checking business hours: {e}")
            # Default to allowing send if we can't check
            return True
    
    def get_next_send_time(self, timezone_str: str = "America/Chicago") -> datetime:
        """
        Get the next valid time to send SMS (within business hours).
        
        Args:
            timezone_str: Recipient's timezone
        
        Returns:
            Next valid datetime to send
        """
        try:
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
            current_time = now.time()
            
            # If before business hours, send at start time today
            if current_time < self.BUSINESS_HOURS_START:
                return now.replace(
                    hour=self.BUSINESS_HOURS_START.hour,
                    minute=self.BUSINESS_HOURS_START.minute,
                    second=0
                )
            
            # If after business hours, send at start time tomorrow
            if current_time > self.BUSINESS_HOURS_END:
                tomorrow = now.replace(hour=self.BUSINESS_HOURS_START.hour, minute=0, second=0)
                tomorrow = tomorrow + timedelta(days=1)
                return tomorrow
            
            # Currently in business hours
            return now
        
        except Exception as e:
            logger.error(f"Error calculating next send time: {e}")
            return datetime.utcnow()
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def _normalize_phone(self, phone_number: str) -> str:
        """
        Normalize phone number to E.164 format.
        
        Args:
            phone_number: Phone in any format
        
        Returns:
            Phone in E.164 format (e.g., +12345678900)
        
        Raises:
            ValidationError: If phone format is invalid
        """
        # Remove all non-digits
        digits = ''.join(c for c in phone_number if c.isdigit())
        
        # Validate length
        if len(digits) == 10:
            # US number without country code
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):
            # US number with country code
            return f"+{digits}"
        elif len(digits) > 11:
            # International number (assume already has country code)
            return f"+{digits}"
        else:
            raise ValidationError(f"Invalid phone number format: {phone_number}")
    
    def validate_phone_format(self, phone_number: str) -> bool:
        """
        Validate phone number format without raising exception.
        
        Args:
            phone_number: Phone to validate
        
        Returns:
            True if valid
        """
        try:
            self._normalize_phone(phone_number)
            return True
        except ValidationError:
            return False

