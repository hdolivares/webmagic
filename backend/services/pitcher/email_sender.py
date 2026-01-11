"""
Email sender service with support for AWS SES and SendGrid.
"""
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import logging
from datetime import datetime

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
        try:
            import boto3
            self.client = boto3.client(
                'ses',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
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
        try:
            from sendgrid import SendGridAPIClient
            self.client = SendGridAPIClient(settings.SENDGRID_API_KEY)
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


class EmailSender:
    """
    Main email sender service.
    Routes to appropriate provider (SES or SendGrid).
    """
    
    def __init__(self, provider_name: Optional[str] = None):
        """
        Initialize email sender with specified provider.
        
        Args:
            provider_name: "ses" or "sendgrid" (defaults to settings.EMAIL_PROVIDER)
        """
        self.provider_name = provider_name or settings.EMAIL_PROVIDER
        self.provider = self._initialize_provider()
    
    def _initialize_provider(self) -> EmailProvider:
        """Initialize the email provider."""
        if self.provider_name == "ses":
            return SESEmailProvider()
        elif self.provider_name == "sendgrid":
            return SendGridEmailProvider()
        else:
            raise ValueError(f"Unknown email provider: {self.provider_name}")
    
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
