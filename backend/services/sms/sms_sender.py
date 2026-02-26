"""
SMS Sender Service.

Provider-agnostic SMS sending with retry logic and comprehensive error handling.
Supported providers: telnyx, labsmobile.

Author: WebMagic Team
Date: January 21, 2026
Updated: February 2026 - Added LabsMobile provider
"""
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import logging
import asyncio
import httpx

from core.config import get_settings
from core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)
settings = get_settings()

# Telnyx API configuration (kept for backward compatibility / rollback)
TELNYX_API_URL = "https://api.telnyx.com/v2/messages"


class SMSProvider(ABC):
    """
    Abstract base class for SMS providers.

    Each provider must implement send_sms() and declare webhook_status_path
    so the campaign helper can build the correct delivery callback URL
    without hard-coding provider names outside this module.
    """

    # Path on our own API that this provider will call for status callbacks.
    # Override in each concrete provider.
    webhook_status_path: str = ""

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


class TelnyxSMSProvider(SMSProvider):
    """Telnyx SMS provider implementation using raw requests."""

    webhook_status_path: str = "/api/v1/webhooks/telnyx/status"

    def __init__(self):
        """Initialize Telnyx client with API key."""
        self.api_key = settings.TELNYX_API_KEY
        self.from_phone = settings.TELNYX_PHONE_NUMBER
        self.messaging_profile_id = settings.TELNYX_MESSAGING_PROFILE_ID
        
        if not self.api_key:
            raise ValueError(
                "Telnyx API key not configured. "
                "Set TELNYX_API_KEY in .env"
            )
        
        if not self.from_phone:
            raise ValueError(
                "Telnyx phone number not configured. "
                "Set TELNYX_PHONE_NUMBER in .env"
            )
        
        logger.info("Telnyx SMS client initialized successfully")
    
    async def send_sms(
        self,
        to_phone: str,
        body: str,
        from_phone: Optional[str] = None,
        status_callback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send SMS via Telnyx API.
        
        Args:
            to_phone: Recipient phone in E.164 format (e.g., +12345678900)
            body: SMS message content (max 1600 chars)
            from_phone: Optional sender phone (defaults to configured number)
            status_callback: Optional webhook URL for delivery tracking
        
        Returns:
            Dict with Telnyx message details
        
        Raises:
            ExternalAPIException: If SMS sending fails
        """
        try:
            # Validate phone format
            if not to_phone.startswith('+'):
                raise ExternalAPIException(
                    f"Phone must be in E.164 format (e.g., +12345678900): {to_phone}"
                )
            
            # Prepare request payload
            payload = {
                "from": from_phone or self.from_phone,
                "to": to_phone,
                "text": body,
            }
            
            # Add messaging profile if configured
            if self.messaging_profile_id:
                payload["messaging_profile_id"] = self.messaging_profile_id
            
            # Add webhook URL if provided
            if status_callback:
                payload["webhook_url"] = status_callback
            
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            logger.info(f"Sending SMS to {to_phone} (length: {len(body)} chars)")
            
            # Send request using httpx (async)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    TELNYX_API_URL,
                    headers=headers,
                    json=payload
                )
                
                data = response.json()
                
                # Check for errors
                if response.status_code not in (200, 201, 202):
                    error_detail = data.get("errors", [{}])[0]
                    error_code = error_detail.get("code", "unknown")
                    error_msg = error_detail.get("detail", str(data))
                    
                    logger.error(
                        f"Telnyx API error {response.status_code}: {error_msg}"
                    )
                    raise ExternalAPIException(
                        f"Telnyx error {error_code}: {error_msg}"
                    )
                
                # Parse successful response
                message_data = data.get("data", {})
                message_id = message_data.get("id")
                
                # Telnyx returns parts count instead of segments
                parts = message_data.get("parts", 1)
                
                # Get initial status from 'to' array
                to_info = message_data.get("to", [{}])
                if isinstance(to_info, list) and len(to_info) > 0:
                    initial_status = to_info[0].get("status", "queued")
                else:
                    initial_status = "queued"
                
                # Prepare response (cost comes via webhook, not initial response)
                result = {
                    "provider": "telnyx",
                    "message_id": message_id,
                    "status": initial_status,
                    "to": to_phone,
                    "from": from_phone or self.from_phone,
                    "body": body,
                    "segments": parts,
                    "cost": None,  # Telnyx sends cost in webhook
                    "cost_unit": "USD",
                    "sent_at": message_data.get("created_at"),
                    "error_code": None,
                    "error_message": None
                }
                
                logger.info(
                    f"SMS sent successfully: {message_id} "
                    f"(parts: {parts}, status: {initial_status})"
                )
                
                return result
        
        except httpx.TimeoutException:
            error_msg = f"Telnyx API timeout sending SMS to {to_phone}"
            logger.error(error_msg)
            raise ExternalAPIException(error_msg)
        
        except httpx.RequestError as e:
            error_msg = f"Telnyx request error: {str(e)}"
            logger.error(error_msg)
            raise ExternalAPIException(error_msg)
        
        except ExternalAPIException:
            raise
        
        except Exception as e:
            error_msg = f"SMS send failed: {str(e)}"
            logger.error(f"Failed to send SMS to {to_phone}: {error_msg}")
            raise ExternalAPIException(error_msg)


class SMSSender:
    """
    SMS sender that auto-selects configured provider.

    Supported providers:
    - labsmobile (primary)
    - telnyx     (kept for rollback / testing)
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
        name = self.provider_name.lower()

        if name == "labsmobile":
            from services.sms.labsmobile_provider import LabsMobileSMSProvider
            try:
                return LabsMobileSMSProvider()
            except Exception as e:
                logger.error(f"Failed to initialize LabsMobile: {e}")
                raise ValueError(f"LabsMobile initialization failed: {e}")

        if name == "telnyx":
            try:
                return TelnyxSMSProvider()
            except Exception as e:
                logger.error(f"Failed to initialize Telnyx: {e}")
                raise ValueError(f"Telnyx initialization failed: {e}")

        raise ValueError(
            f"Invalid SMS provider: {self.provider_name}. "
            "Supported providers: labsmobile, telnyx"
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
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    await asyncio.sleep(wait_time)
        
        # All retries failed
        raise ExternalAPIException(
            f"SMS failed after {max_retries} attempts: {last_error}"
        )
