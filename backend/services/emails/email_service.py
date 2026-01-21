"""
Email Service

Handles email sending with template rendering and multiple provider support.

Providers:
- SendGrid (primary)
- AWS SES (fallback)
- SMTP (development)

Author: WebMagic Team
Date: January 21, 2026
"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from core.config import get_settings
from .templates import EmailTemplates

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    """
    Email service with template support and provider abstraction.
    """
    
    def __init__(self):
        """Initialize email service."""
        self.templates = EmailTemplates()
        self.from_email = settings.EMAIL_FROM
        self.from_name = settings.EMAIL_FROM_NAME
    
    async def send_welcome_email(
        self,
        to_email: str,
        customer_name: str,
        verification_token: str
    ) -> bool:
        """
        Send welcome email with verification link.
        
        Args:
            to_email: Customer email address
            customer_name: Customer's name
            verification_token: Email verification token
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
            
            html_content = self.templates.render_welcome_email(
                customer_name=customer_name,
                verification_url=verification_url
            )
            
            return await self._send_email(
                to_email=to_email,
                subject="Welcome to WebMagic! 🎉 Verify Your Email",
                html_content=html_content
            )
        
        except Exception as e:
            logger.error(f"Failed to send welcome email to {to_email}: {e}")
            return False
    
    async def send_verification_email(
        self,
        to_email: str,
        customer_name: str,
        verification_token: str
    ) -> bool:
        """
        Send email verification link.
        
        Args:
            to_email: Customer email address
            customer_name: Customer's name
            verification_token: Email verification token
        
        Returns:
            True if sent successfully
        """
        try:
            verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
            
            html_content = self.templates.render_verification_email(
                customer_name=customer_name,
                verification_url=verification_url
            )
            
            return await self._send_email(
                to_email=to_email,
                subject="Verify Your Email Address",
                html_content=html_content
            )
        
        except Exception as e:
            logger.error(f"Failed to send verification email to {to_email}: {e}")
            return False
    
    async def send_password_reset_email(
        self,
        to_email: str,
        customer_name: str,
        reset_token: str
    ) -> bool:
        """
        Send password reset email.
        
        Args:
            to_email: Customer email address
            customer_name: Customer's name
            reset_token: Password reset token
        
        Returns:
            True if sent successfully
        """
        try:
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
            
            html_content = self.templates.render_password_reset_email(
                customer_name=customer_name,
                reset_url=reset_url
            )
            
            return await self._send_email(
                to_email=to_email,
                subject="Reset Your Password",
                html_content=html_content
            )
        
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {e}")
            return False
    
    async def send_purchase_confirmation_email(
        self,
        to_email: str,
        customer_name: str,
        site_title: str,
        site_url: str,
        purchase_amount: float,
        transaction_id: str
    ) -> bool:
        """
        Send purchase confirmation email.
        
        Args:
            to_email: Customer email address
            customer_name: Customer's name
            site_title: Title of purchased site
            site_url: URL of the site
            purchase_amount: Amount paid
            transaction_id: Transaction ID
        
        Returns:
            True if sent successfully
        """
        try:
            portal_url = f"{settings.FRONTEND_URL}/dashboard"
            
            html_content = self.templates.render_purchase_confirmation_email(
                customer_name=customer_name,
                site_title=site_title,
                site_url=site_url,
                purchase_amount=purchase_amount,
                transaction_id=transaction_id,
                portal_url=portal_url
            )
            
            return await self._send_email(
                to_email=to_email,
                subject=f"🎉 Your Website is Ready! - {site_title}",
                html_content=html_content
            )
        
        except Exception as e:
            logger.error(f"Failed to send purchase confirmation to {to_email}: {e}")
            return False
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send email using configured provider.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text fallback
        
        Returns:
            True if sent successfully
        """
        provider = settings.EMAIL_PROVIDER.lower()
        
        try:
            if provider == "sendgrid":
                return await self._send_via_sendgrid(
                    to_email, subject, html_content, text_content
                )
            elif provider == "ses":
                return await self._send_via_ses(
                    to_email, subject, html_content, text_content
                )
            elif provider == "smtp":
                return await self._send_via_smtp(
                    to_email, subject, html_content, text_content
                )
            else:
                logger.warning(f"Unknown email provider: {provider}, using console fallback")
                return await self._send_via_console(
                    to_email, subject, html_content
                )
        
        except Exception as e:
            logger.error(f"Failed to send email via {provider}: {e}")
            # Try console fallback in development
            if settings.DEBUG:
                return await self._send_via_console(to_email, subject, html_content)
            return False
    
    async def _send_via_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str]
    ) -> bool:
        """Send email via SendGrid."""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Content
            
            message = Mail(
                from_email=(self.from_email, self.from_name),
                to_emails=to_email,
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            if text_content:
                message.add_content(Content("text/plain", text_content))
            
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            
            logger.info(f"SendGrid email sent to {to_email}: {response.status_code}")
            return response.status_code in [200, 201, 202]
        
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            raise
    
    async def _send_via_ses(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str]
    ) -> bool:
        """Send email via AWS SES."""
        try:
            import boto3
            
            ses = boto3.client(
                'ses',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            
            email_body = {'Html': {'Data': html_content, 'Charset': 'UTF-8'}}
            if text_content:
                email_body['Text'] = {'Data': text_content, 'Charset': 'UTF-8'}
            
            response = ses.send_email(
                Source=f"{self.from_name} <{self.from_email}>",
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': email_body
                }
            )
            
            logger.info(f"SES email sent to {to_email}: {response['MessageId']}")
            return True
        
        except Exception as e:
            logger.error(f"SES error: {e}")
            raise
    
    async def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str]
    ) -> bool:
        """Send email via SMTP (development)."""
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"SMTP email sent to {to_email}")
            return True
        
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            raise
    
    async def _send_via_console(
        self,
        to_email: str,
        subject: str,
        html_content: str
    ) -> bool:
        """Console output for development (no actual email sent)."""
        logger.info("=" * 80)
        logger.info("EMAIL (Console Output - Development Mode)")
        logger.info("=" * 80)
        logger.info(f"To: {to_email}")
        logger.info(f"From: {self.from_name} <{self.from_email}>")
        logger.info(f"Subject: {subject}")
        logger.info("-" * 80)
        logger.info(f"HTML Content Length: {len(html_content)} chars")
        logger.info("=" * 80)
        
        # Save to file for preview
        if settings.DEBUG:
            output_dir = Path(__file__).parent / "email_preview"
            output_dir.mkdir(exist_ok=True)
            
            from datetime import datetime
            filename = f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            output_file = output_dir / filename
            
            output_file.write_text(html_content, encoding='utf-8')
            logger.info(f"Email preview saved: {output_file}")
        
        return True


def get_email_service() -> EmailService:
    """Get email service instance."""
    return EmailService()
