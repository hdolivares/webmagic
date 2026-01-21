"""
SMS Sender Service - Multi-Provider SMS Sending.

Supports Twilio (primary) with extensible architecture for additional providers.
Mirrors the email_sender.py architecture for consistency.

Author: WebMagic Team
Date: January 21, 2026
"""
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import logging
from datetime import datetime

from core.config import get_settings
from core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)
settings = get_settings()


class SMSProvider(ABC):
    """Abstract base class for SMS providers."""
    
    @abstractmethod
    async def send_sms(
        self,
        to_phone: str,
        body: str,
        from_phone: Optional[str] = None,
        status_callback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send SMS and return message details.
        
        Args:
            to_phone: Recipient phone in E.164 format
            body: SMS message content
            from_phone: Optional sender phone number
            status_callback: Optional webhook URL for delivery status
        
        Returns:
            Dict with message details (message_id, status, cost, etc.)
        """
        pass


class TwilioSMSProvider(SMSProvider):
    """Twilio SMS provider implementation."""
    
    def __init__(self):
        """Initialize Twilio client."""
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_phone = settings.TWILIO_PHONE_NUMBER
        
        if not self.account_sid or not self.auth_token:
            raise ValueError(
                "Twilio credentials not configured. "
                "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env"
            )
        
        if not self.from_phone:
            raise ValueError(
                "Twilio phone number not configured. "
                "Set TWILIO_PHONE_NUMBER in .env"
            )
        
        # Lazy import Twilio (only when needed)
        try:
            from twilio.rest import Client
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("Twilio SMS client initialized successfully")
        except ImportError:
            raise ImportError(
                "Twilio SDK not installed. Run: pip install twilio"
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize Twilio client: {str(e)}")
    
    async def send_sms(
        self,
        to_phone: str,
        body: str,
        from_phone: Optional[str] = None,
        status_callback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send SMS via Twilio.
        
        Args:
            to_phone: Recipient phone in E.164 format (e.g., +12345678900)
            body: SMS message content (max 1600 chars)
            from_phone: Optional sender phone (defaults to configured number)
            status_callback: Optional webhook URL for delivery tracking
        
        Returns:
            Dict with Twilio message details
        
        Raises:
            ExternalAPIException: If SMS sending fails
        """
        try:
            # Validate phone format
            if not to_phone.startswith('+'):
                raise ExternalAPIException(
                    f"Phone must be in E.164 format (e.g., +12345678900): {to_phone}"
                )
            
            # Prepare message parameters
            message_params = {
                "body": body,
                "from_": from_phone or self.from_phone,
                "to": to_phone
            }
            
            # Add status callback if provided
            if status_callback:
                message_params["status_callback"] = status_callback
            
            # Send message
            logger.info(f"Sending SMS to {to_phone} (length: {len(body)} chars)")
            message = self.client.messages.create(**message_params)
            
            # Calculate cost (Twilio provides this after sending)
            cost = float(message.price) if message.price else None
            
            # Prepare response
            response = {
                "provider": "twilio",
                "message_id": message.sid,
                "status": message.status,
                "to": message.to,
                "from": message.from_,
                "body": body,
                "segments": message.num_segments,
                "cost": cost,
                "cost_unit": message.price_unit,
                "sent_at": message.date_created.isoformat() if message.date_created else None,
                "error_code": message.error_code,
                "error_message": message.error_message
            }
            
            logger.info(
                f"SMS sent successfully: {message.sid} "
                f"(segments: {message.num_segments}, cost: {cost})"
            )
            
            return response
        
        except Exception as e:
            # Import Twilio exceptions
            try:
                from twilio.base.exceptions import TwilioRestException
                
                if isinstance(e, TwilioRestException):
                    error_msg = f"Twilio error {e.code}: {e.msg}"
                    logger.error(f"Failed to send SMS to {to_phone}: {error_msg}")
                    raise ExternalAPIException(error_msg)
            except ImportError:
                pass
            
            # Generic error
            error_msg = f"SMS send failed: {str(e)}"
            logger.error(f"Failed to send SMS to {to_phone}: {error_msg}")
            raise ExternalAPIException(error_msg)


class SMSSender:
    """
    SMS sender that auto-selects configured provider.
    
    Currently supports:
    - Twilio (primary)
    
    Future providers:
    - MessageBird
    - AWS SNS
    - Vonage (Nexmo)
    """
    
    def __init__(self, provider: Optional[str] = None):
        """
        Initialize SMS sender with configured provider.
        
        Args:
            provider: Optional provider name (defaults to settings.SMS_PROVIDER)
        """
        self.provider_name = provider or settings.SMS_PROVIDER
        self.provider = self._init_provider()
    
    def _init_provider(self) -> SMSProvider:
        """
        Initialize the configured SMS provider.
        
        Returns:
            SMSProvider instance
        
        Raises:
            ValueError: If provider is not configured or invalid
        """
        if self.provider_name.lower() == "twilio":
            try:
                return TwilioSMSProvider()
            except Exception as e:
                logger.error(f"Failed to initialize Twilio: {e}")
                raise ValueError(f"Twilio initialization failed: {e}")
        
        # Future providers can be added here
        # elif self.provider_name.lower() == "messagebird":
        #     return MessageBirdSMSProvider()
        
        raise ValueError(
            f"Invalid SMS provider: {self.provider_name}. "
            "Supported providers: twilio"
        )
    
    async def send(
        self,
        to_phone: str,
        body: str,
        from_phone: Optional[str] = None,
        status_callback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send SMS via configured provider.
        
        Args:
            to_phone: Recipient phone in E.164 format
            body: SMS message content
            from_phone: Optional sender phone
            status_callback: Optional webhook URL
        
        Returns:
            Dict with message details
        
        Raises:
            ExternalAPIException: If sending fails
        """
        return await self.provider.send_sms(
            to_phone=to_phone,
            body=body,
            from_phone=from_phone,
            status_callback=status_callback
        )
    
    async def send_with_retry(
        self,
        to_phone: str,
        body: str,
        max_retries: int = 3,
        from_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send SMS with automatic retry on failure.
        
        Args:
            to_phone: Recipient phone
            body: SMS content
            max_retries: Maximum retry attempts
            from_phone: Optional sender phone
        
        Returns:
            Dict with message details
        
        Raises:
            ExternalAPIException: If all retries fail
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await self.send(
                    to_phone=to_phone,
                    body=body,
                    from_phone=from_phone
                )
            except ExternalAPIException as e:
                last_error = e
                logger.warning(
                    f"SMS send attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                
                if attempt < max_retries - 1:
                    # Wait before retry (exponential backoff)
                    import asyncio
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    await asyncio.sleep(wait_time)
        
        # All retries failed
        raise ExternalAPIException(
            f"SMS failed after {max_retries} attempts: {last_error}"
        )

