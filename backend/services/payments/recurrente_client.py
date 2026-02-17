"""
Recurrente API client wrapper.
Handles authentication, requests, and error handling.
"""
from typing import Dict, Any, Optional
import httpx
import logging
import hashlib
import hmac

from core.config import get_settings
from core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)
settings = get_settings()


class RecurrenteClient:
    """
    Recurrente API client.
    Documentation: https://recurrente.com/docs
    """
    
    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize Recurrente client.
        
        Args:
            public_key: Recurrente public key (defaults to settings)
            secret_key: Recurrente secret key (defaults to settings)
            base_url: API base URL (defaults to settings)
        """
        self.public_key = public_key or settings.RECURRENTE_PUBLIC_KEY
        self.secret_key = secret_key or settings.RECURRENTE_SECRET_KEY
        self.base_url = (base_url or settings.RECURRENTE_BASE_URL).rstrip("/")
        self.webhook_secret = settings.RECURRENTE_WEBHOOK_SECRET
        
        logger.info(f"Recurrente client initialized: {self.base_url}")
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated API request.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/checkouts")
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data
            
        Raises:
            ExternalAPIException: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        # Build headers with authentication
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.secret_key}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=headers,
                    timeout=30.0
                )
                
                # Log request
                logger.info(f"Recurrente {method} {url}: status={response.status_code}")
                logger.debug(f"Recurrente response body: {response.text[:500]}")
                
                # Handle response
                if response.status_code >= 400:
                    error_msg = f"Recurrente API error: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg += f" - {error_data}"
                    except:
                        error_msg += f" - {response.text}"
                    
                    logger.error(error_msg)
                    raise ExternalAPIException(error_msg)
                
                # Parse JSON response
                try:
                    return response.json()
                except ValueError as e:
                    logger.error(f"Recurrente returned non-JSON response: status={response.status_code}, body={response.text[:500]}")
                    raise ExternalAPIException(f"Recurrente returned invalid JSON: {str(e)}")
                
        except httpx.RequestError as e:
            logger.error(f"Recurrente request failed: {str(e)}")
            raise ExternalAPIException(f"Recurrente request failed: {str(e)}")
    
    # Checkouts
    
    async def create_checkout(
        self,
        description: str,
        price_cents: int,
        currency: str = "GTQ",
        recurrence_type: str = "once",
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a checkout session.
        
        Args:
            description: Product/service description
            price_cents: Price in cents
            currency: Currency code (GTQ, USD, etc.)
            recurrence_type: "once" or "subscription"
            success_url: Redirect URL after successful payment
            cancel_url: Redirect URL if user cancels
            user_email: Pre-fill customer email
            user_name: Pre-fill customer name
            metadata: Custom metadata
            
        Returns:
            Checkout data with checkout_url
        """
        data = {
            "description": description,
            "price": price_cents,
            "currency": currency,
            "recurrence_type": recurrence_type
        }
        
        if success_url:
            data["success_url"] = success_url
        if cancel_url:
            data["cancel_url"] = cancel_url
        if user_email:
            data["user_email"] = user_email
        if user_name:
            data["user_name"] = user_name
        if metadata:
            data["metadata"] = metadata
        
        response = await self._request("POST", "/checkouts", data=data)
        
        logger.info(f"Created checkout: {response.get('id')}")
        return response
    
    async def get_checkout(self, checkout_id: str) -> Dict[str, Any]:
        """
        Get checkout details.
        
        Args:
            checkout_id: Checkout ID
            
        Returns:
            Checkout data
        """
        return await self._request("GET", f"/checkouts/{checkout_id}")
    
    # Users (Customers)
    
    async def create_user(
        self,
        email: str,
        name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a user (customer).
        
        Args:
            email: User email
            name: User full name
            phone: User phone number
            
        Returns:
            User data
        """
        data = {"email": email}
        if name:
            data["name"] = name
        if phone:
            data["phone"] = phone
        
        response = await self._request("POST", "/users", data=data)
        
        logger.info(f"Created user: {response.get('id')}")
        return response
    
    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user details."""
        return await self._request("GET", f"/users/{user_id}")
    
    async def list_users(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List users."""
        params = {"limit": limit, "offset": offset}
        return await self._request("GET", "/users", params=params)
    
    # Subscriptions
    
    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription details."""
        return await self._request("GET", f"/subscriptions/{subscription_id}")
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Subscription ID
            reason: Cancellation reason
            
        Returns:
            Updated subscription data
        """
        data = {}
        if reason:
            data["reason"] = reason
        
        response = await self._request(
            "POST",
            f"/subscriptions/{subscription_id}/cancel",
            data=data
        )
        
        logger.info(f"Cancelled subscription: {subscription_id}")
        return response
    
    async def pause_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Pause a subscription."""
        response = await self._request(
            "POST",
            f"/subscriptions/{subscription_id}/pause"
        )
        logger.info(f"Paused subscription: {subscription_id}")
        return response
    
    async def resume_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Resume a paused subscription."""
        response = await self._request(
            "POST",
            f"/subscriptions/{subscription_id}/resume"
        )
        logger.info(f"Resumed subscription: {subscription_id}")
        return response
    
    # Refunds
    
    async def create_refund(
        self,
        payment_id: str,
        amount_cents: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a refund.
        
        Args:
            payment_id: Payment ID to refund
            amount_cents: Amount to refund (None for full refund)
            reason: Refund reason
            
        Returns:
            Refund data
        """
        data = {"payment_id": payment_id}
        if amount_cents:
            data["amount"] = amount_cents
        if reason:
            data["reason"] = reason
        
        response = await self._request("POST", "/refunds", data=data)
        
        logger.info(f"Created refund for payment: {payment_id}")
        return response
    
    async def get_refund(self, refund_id: str) -> Dict[str, Any]:
        """Get refund details."""
        return await self._request("GET", f"/refunds/{refund_id}")
    
    # Webhook verification
    
    def verify_webhook_signature(
        self,
        payload: str,
        signature: str
    ) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: Raw webhook payload (JSON string)
            signature: Signature from X-Recurrente-Signature header
            
        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return True
        
        # Compute HMAC signature
        computed_signature = hmac.new(
            self.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        is_valid = hmac.compare_digest(computed_signature, signature)
        
        if not is_valid:
            logger.warning(f"Invalid webhook signature: {signature}")
        
        return is_valid
