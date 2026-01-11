"""
Email sender service with support for AWS SES, SendGrid, and Brevo.
"""
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import logging
from datetime import datetime
import httpx

from core.config import get_settings
from core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailProvider(ABC):
    """Abstract base class for email providers."""
    
    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email and return message details."""
        pass


class SESEmailProvider(EmailProvider):
    """AWS SES email provider."""
    
    def __init__(self):
        """Initialize SES provider. Client creation is deferred until first send."""
        self.client = None
        self._initialized = False
    
    def _check_credentials(self):
        """Initialize SES client before sending. Raises error if not configured."""
        if self._initialized:
            return
        
        try:
            import boto3
            if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
                raise ValueError("AWS credentials not configured")
            
            self.client = boto3.client(
                'ses',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            self._initialized = True
            logger.info("AWS SES client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize SES: {str(e)}")
            raise ExternalAPIException(f"SES initialization failed: {str(e)}")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email via AWS SES."""
        try:
            # Check credentials before sending
            self._check_credentials()
            
            from_addr = from_email or settings.EMAIL_FROM
            
            # Build message
            message = {
                'Subject': {'Data': subject},
                'Body': {}
            }
            
            if body_html:
                message['Body']['Html'] = {'Data': body_html}
            
            message['Body']['Text'] = {'Data': body_text}
            
            # Send via SES
            response = self.client.send_email(
                Source=from_addr,
                Destination={'ToAddresses': [to_email]},
                Message=message,
                ReplyToAddresses=[reply_to or from_addr]
            )
            
            message_id = response['MessageId']
            
            logger.info(f"Email sent via SES: {message_id} to {to_email}")
            
            return {
                "provider": "ses",
                "message_id": message_id,
                "status": "sent",
                "sent_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"SES send failed: {str(e)}")
            raise ExternalAPIException(f"Failed to send email via SES: {str(e)}")


class SendGridEmailProvider(EmailProvider):
    """SendGrid email provider."""
    
    def __init__(self):
        """Initialize SendGrid provider. Client creation is deferred until first send."""
        self.client = None
        self._initialized = False
    
    def _check_credentials(self):
        """Initialize SendGrid client before sending. Raises error if not configured."""
        if self._initialized:
            return
        
        try:
            if not settings.SENDGRID_API_KEY:
                raise ValueError("SENDGRID_API_KEY not configured")
            
            from sendgrid import SendGridAPIClient
            self.client = SendGridAPIClient(settings.SENDGRID_API_KEY)
            self._initialized = True
            logger.info("SendGrid client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize SendGrid: {str(e)}")
            raise ExternalAPIException(f"SendGrid initialization failed: {str(e)}")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email via SendGrid."""
        try:
            # Check credentials before sending
            self._check_credentials()
            
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            from_addr = from_email or settings.EMAIL_FROM
            
            # Build message
            message = Mail(
                from_email=Email(from_addr),
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", body_text)
            )
            
            if body_html:
                from sendgrid.helpers.mail import HtmlContent
                message.add_content(HtmlContent(body_html))
            
            if reply_to:
                from sendgrid.helpers.mail import ReplyTo
                message.reply_to = ReplyTo(reply_to)
            
            # Send via SendGrid
            response = self.client.send(message)
            
            message_id = response.headers.get('X-Message-Id', '')
            
            logger.info(f"Email sent via SendGrid: {message_id} to {to_email}")
            
            return {
                "provider": "sendgrid",
                "message_id": message_id,
                "status": "sent",
                "sent_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"SendGrid send failed: {str(e)}")
            raise ExternalAPIException(f"Failed to send email via SendGrid: {str(e)}")


class BrevoEmailProvider(EmailProvider):
    """Brevo (formerly Sendinblue) email provider."""
    
    def __init__(self):
        """Initialize Brevo provider. API key check is deferred until first send."""
        self.api_key = settings.BREVO_API_KEY
        self.api_url = "https://api.brevo.com/v3/smtp/email"
        self._initialized = False
    
    def _check_credentials(self):
        """Check credentials before sending. Raises error if not configured."""
        if self._initialized:
            return
        
        if not self.api_key:
            raise ExternalAPIException(
                "BREVO_API_KEY not configured. "
                "Get your API key from https://app.brevo.com/ → Settings → SMTP & API → API Keys"
            )
        self._initialized = True
        logger.info("Brevo credentials verified")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email via Brevo API."""
        try:
            # Check credentials before sending
            self._check_credentials()
            
            from_addr = from_email or settings.EMAIL_FROM
            
            # Extract name from email if format is "Name <email@domain.com>"
            from_name = settings.APP_NAME
            if "<" in from_addr:
                from_name, from_addr = from_addr.split("<")
                from_name = from_name.strip()
                from_addr = from_addr.strip(">").strip()
            
            # Build request payload
            payload = {
                "sender": {
                    "name": from_name,
                    "email": from_addr
                },
                "to": [
                    {"email": to_email}
                ],
                "subject": subject,
                "textContent": body_text
            }
            
            # Add HTML content if provided
            if body_html:
                payload["htmlContent"] = body_html
            
            # Add reply-to if provided
            if reply_to:
                payload["replyTo"] = {"email": reply_to}
            
            # Send via Brevo API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers={
                        "api-key": self.api_key,
                        "Content-Type": "application/json",
                        "accept": "application/json"
                    },
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
            
            message_id = result.get("messageId", "")
            
            logger.info(f"Email sent via Brevo: {message_id} to {to_email}")
            
            return {
                "provider": "brevo",
                "message_id": message_id,
                "status": "sent",
                "sent_at": datetime.utcnow().isoformat()
            }
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"Brevo HTTP error: {e.response.status_code} - {error_detail}")
            raise ExternalAPIException(f"Brevo API error: {error_detail}")
        except Exception as e:
            logger.error(f"Brevo send failed: {str(e)}")
            raise ExternalAPIException(f"Failed to send email via Brevo: {str(e)}")


class EmailSender:
    """
    Main email sender service.
    Routes to appropriate provider (SES, SendGrid, or Brevo).
    """
    
    def __init__(self, provider_name: Optional[str] = None):
        """
        Initialize email sender with specified provider.
        Provider initialization is deferred until first send.
        
        Args:
            provider_name: "ses", "sendgrid", or "brevo" (defaults to settings.EMAIL_PROVIDER)
        """
        self.provider_name = provider_name or settings.EMAIL_PROVIDER
        self._provider = None  # Lazy-loaded
    
    @property
    def provider(self) -> EmailProvider:
        """Lazy-load email provider only when needed."""
        if self._provider is None:
            self._provider = self._initialize_provider()
        return self._provider
    
    def _initialize_provider(self) -> EmailProvider:
        """Initialize the email provider."""
        if self.provider_name == "ses":
            return SESEmailProvider()
        elif self.provider_name == "sendgrid":
            return SendGridEmailProvider()
        elif self.provider_name == "brevo":
            return BrevoEmailProvider()
        else:
            raise ValueError(f"Unknown email provider: {self.provider_name}. Must be 'ses', 'sendgrid', or 'brevo'.")
    
    async def send_campaign_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        tracking_pixel: Optional[str] = None,
        tracking_links: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send campaign email with tracking.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            tracking_pixel: URL for tracking pixel (optional)
            tracking_links: Dict of original_url -> tracked_url (optional)
            
        Returns:
            Send result with message_id
        """
        # Add tracking pixel to HTML if provided
        if body_html and tracking_pixel:
            body_html += f'\n<img src="{tracking_pixel}" width="1" height="1" alt="" />'
        
        # Replace links with tracking links if provided
        if body_html and tracking_links:
            for original_url, tracked_url in tracking_links.items():
                body_html = body_html.replace(original_url, tracked_url)
                body_text = body_text.replace(original_url, tracked_url)
        
        # Send email
        result = await self.provider.send_email(
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html
        )
        
        return result
    
    async def send_test_email(
        self,
        to_email: str,
        subject: str = "Test Email from WebMagic"
    ) -> Dict[str, Any]:
        """
        Send a test email to verify configuration.
        
        Args:
            to_email: Test recipient email
            subject: Test subject line
            
        Returns:
            Send result
        """
        body_text = """This is a test email from WebMagic.

If you're receiving this, your email configuration is working correctly!

Provider: {provider}
Sent at: {timestamp}
""".format(
            provider=self.provider_name,
            timestamp=datetime.utcnow().isoformat()
        )
        
        body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2>Test Email from WebMagic</h2>
    <p>If you're receiving this, your email configuration is working correctly!</p>
    <ul>
        <li><strong>Provider:</strong> {self.provider_name}</li>
        <li><strong>Sent at:</strong> {datetime.utcnow().isoformat()}</li>
    </ul>
</body>
</html>
"""
        
        return await self.provider.send_email(
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html
        )
    
    def generate_html_from_text(self, text_body: str) -> str:
        """
        Convert plain text email to simple HTML.
        
        Args:
            text_body: Plain text email body
            
        Returns:
            HTML version
        """
        # Simple conversion: paragraphs and line breaks
        paragraphs = text_body.split('\n\n')
        html_paragraphs = [f'<p>{p.replace(chr(10), "<br>")}</p>' for p in paragraphs]
        
        html = f"""
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
             line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    {''.join(html_paragraphs)}
</body>
</html>
"""
        return html.strip()
