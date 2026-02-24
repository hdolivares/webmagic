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
from core.text_utils import title_case
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
    
    async def send_subscription_activated_email(
        self,
        to_email: str,
        customer_name: str,
        site_title: str,
        site_url: str,
        next_billing_date: Any
    ) -> bool:
        """Send subscription activation confirmation."""
        try:
            portal_url = f"{settings.FRONTEND_URL}/dashboard"
            
            html_content = self.templates.render_subscription_activated_email(
                customer_name=customer_name,
                site_title=site_title,
                site_url=site_url,
                next_billing_date=str(next_billing_date),
                portal_url=portal_url
            )
            
            return await self._send_email(
                to_email=to_email,
                subject=f"🎉 Subscription Activated! - {site_title}",
                html_content=html_content
            )
        except Exception as e:
            logger.error(f"Failed to send subscription activated email: {e}")
            return False
    
    async def send_subscription_payment_failed_email(
        self,
        to_email: str,
        customer_name: str,
        site_title: str,
        grace_period_ends: Any,
        payment_url: str
    ) -> bool:
        """Send payment failure notification."""
        try:
            html_content = self.templates.render_subscription_payment_failed_email(
                customer_name=customer_name,
                site_title=site_title,
                grace_period_ends=str(grace_period_ends),
                payment_url=payment_url
            )
            
            return await self._send_email(
                to_email=to_email,
                subject=f"⚠️ Payment Failed - Update Payment Method",
                html_content=html_content
            )
        except Exception as e:
            logger.error(f"Failed to send payment failed email: {e}")
            return False
    
    async def send_subscription_cancelled_email(
        self,
        to_email: str,
        customer_name: str,
        site_title: str,
        immediate: bool,
        ends_at: Any
    ) -> bool:
        """Send subscription cancellation confirmation."""
        try:
            portal_url = f"{settings.FRONTEND_URL}/dashboard"
            
            html_content = self.templates.render_subscription_cancelled_email(
                customer_name=customer_name,
                site_title=site_title,
                immediate=immediate,
                ends_at=str(ends_at) if ends_at else None,
                portal_url=portal_url
            )
            
            return await self._send_email(
                to_email=to_email,
                subject=f"Subscription Cancelled - {site_title}",
                html_content=html_content
            )
        except Exception as e:
            logger.error(f"Failed to send cancellation email: {e}")
            return False
    
    async def send_purchase_confirmation_email(
        self,
        to_email: str,
        customer_name: str,
        site_title: str,
        site_url: str,
        purchase_amount: float,
        transaction_id: str,
        site_password: Optional[str] = None
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
            site_password: Temporary password for new customers (optional)
        
        Returns:
            True if sent successfully
        """
        try:
            portal_url = f"{settings.FRONTEND_URL}/dashboard"
            
            html_content = self.templates.render_purchase_confirmation_email(
                customer_email=to_email,
                customer_name=customer_name,
                site_title=site_title,
                site_url=site_url,
                purchase_amount=purchase_amount,
                transaction_id=transaction_id,
                portal_url=portal_url,
                site_password=site_password  # Pass to template
            )
            
            return await self._send_email(
                to_email=to_email,
                subject=f"🎉 Your Website is Ready! - {site_title}",
                html_content=html_content
            )
        
        except Exception as e:
            logger.error(f"Failed to send purchase confirmation to {to_email}: {e}")
            return False
    
    async def send_abandoned_cart_email(
        self,
        to_email: str,
        customer_name: str,
        site_slug: str,
        checkout_url: str,
        discount_code: str,
        purchase_amount: float,
        monthly_amount: float,
        business_name: Optional[str] = None,
    ) -> bool:
        """
        Send abandoned cart recovery email with 10% discount.
        
        Args:
            to_email: Customer email
            customer_name: Customer's name
            site_slug: Slug of the site they started purchasing
            checkout_url: Recurrente checkout URL to complete purchase
            discount_code: 10% discount code
            purchase_amount: Original one-time amount
            monthly_amount: Monthly subscription amount
            business_name: Optional business name for subject (uses title case)
        
        Returns:
            True if sent successfully
        """
        try:
            site_preview_url = f"{settings.FRONTEND_URL}/site-preview/{site_slug}"
            # Abandoned cart: $49.70 off the first (setup) payment = 10% of total first bill ($400 + $97)
            discount_amount = 49.70
            total_first_bill = purchase_amount + monthly_amount  # e.g. 400 + 97 = 497
            first_payment_after_discount = round(purchase_amount - discount_amount, 2)  # e.g. 350.30
            # Subject: use business name (title-cased) instead of slug when available
            display_name = (business_name or site_slug).strip()
            subject_display = title_case(display_name) if display_name else "Your Website"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Complete Your Website Purchase - 10% Off!</title>
            </head>
            <body style="margin: 0; padding: 0; background-color: #f4f4f7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
                <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin: 0; padding: 20px 0;">
                    <tr>
                        <td align="center">
                            <table role="presentation" cellpadding="0" cellspacing="0" width="600" style="background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden;">
                                
                                <!-- Header -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                                        <h1 style="margin: 0; color: white; font-size: 32px; font-weight: 700;">💼 Don't Miss Out!</h1>
                                        <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.9); font-size: 18px;">Your website is waiting</p>
                                    </td>
                                </tr>
                                
                                <!-- Body -->
                                <tr>
                                    <td style="padding: 40px 30px;">
                                        <p style="margin: 0 0 20px; font-size: 16px; line-height: 1.6; color: #374151;">
                                            Hi <strong>{customer_name}</strong>,
                                        </p>
                                        
                                        <p style="margin: 0 0 20px; font-size: 16px; line-height: 1.6; color: #374151;">
                                            We noticed you started the checkout process for your professional website but didn't complete it. 
                                            We understand – sometimes life gets in the way!
                                        </p>
                                        
                                        <!-- Special Offer Box -->
                                        <div style="background: #f0fdf4; border-left: 4px solid #10b981; padding: 20px; margin: 30px 0; border-radius: 8px;">
                                            <h2 style="margin: 0 0 15px; font-size: 24px; color: #065f46;">🎁 10% Off Your Total First Bill – Just for You!</h2>
                                            <p style="margin: 0 0 10px; font-size: 16px; color: #065f46;">
                                                Use the code below at checkout for <strong>${discount_amount:.2f} off</strong> your first payment. 
                                                That's 10% off your total first bill (setup + first month). You'll pay <strong>${first_payment_after_discount:.2f}</strong> today, then ${monthly_amount:.2f}/month — one code, one click.
                                            </p>
                                            <div style="background: white; padding: 15px; border-radius: 6px; margin-top: 15px;">
                                                <p style="margin: 0 0 5px; font-size: 14px; color: #6b7280;">Your discount code:</p>
                                                <p style="margin: 0; font-size: 28px; font-weight: 700; color: #10b981; letter-spacing: 2px;">{discount_code}</p>
                                            </div>
                                        </div>
                                        
                                        <!-- Pricing -->
                                        <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 25px 0;">
                                            <table width="100%" cellpadding="8" cellspacing="0">
                                                <tr>
                                                    <td style="font-size: 15px; color: #6b7280;">Total first bill (setup + first month):</td>
                                                    <td align="right" style="font-size: 15px; color: #9ca3af; text-decoration: line-through;">${total_first_bill:.2f}</td>
                                                </tr>
                                                <tr>
                                                    <td style="font-size: 15px; color: #6b7280;">Your discount (10% off):</td>
                                                    <td align="right" style="font-size: 15px; color: #10b981;">−${discount_amount:.2f}</td>
                                                </tr>
                                                <tr>
                                                    <td style="font-size: 18px; color: #111827; font-weight: 600;">Your total payment today:</td>
                                                    <td align="right" style="font-size: 22px; color: #10b981; font-weight: 700;">${(total_first_bill - discount_amount):.2f}</td>
                                                </tr>
                                                <tr>
                                                    <td colspan="2" style="font-size: 13px; color: #6b7280; padding-top: 6px; padding-bottom: 4px;">Breakdown: initial payment ${first_payment_after_discount:.2f} + first month ${monthly_amount:.2f} = ${(total_first_bill - discount_amount):.2f}</td>
                                                </tr>
                                                <tr>
                                                    <td style="font-size: 14px; color: #6b7280; padding-top: 10px; border-top: 1px solid #e5e7eb;">Then monthly:</td>
                                                    <td align="right" style="font-size: 14px; color: #374151; padding-top: 10px; border-top: 1px solid #e5e7eb;">${monthly_amount:.2f}/month</td>
                                                </tr>
                                            </table>
                                        </div>
                                        
                                        <!-- What's Included -->
                                        <div style="margin: 30px 0;">
                                            <h3 style="margin: 0 0 15px; font-size: 18px; color: #111827;">What you get:</h3>
                                            <ul style="margin: 0; padding: 0; list-style: none;">
                                                <li style="margin: 0 0 10px; padding-left: 30px; position: relative; font-size: 15px; color: #374151;">
                                                    <span style="position: absolute; left: 0;">✅</span>
                                                    Professional AI-generated website ready to launch
                                                </li>
                                                <li style="margin: 0 0 10px; padding-left: 30px; position: relative; font-size: 15px; color: #374151;">
                                                    <span style="position: absolute; left: 0;">✅</span>
                                                    Unlimited AI-powered customization and updates
                                                </li>
                                                <li style="margin: 0 0 10px; padding-left: 30px; position: relative; font-size: 15px; color: #374151;">
                                                    <span style="position: absolute; left: 0;">✅</span>
                                                    Custom domain support included
                                                </li>
                                                <li style="margin: 0 0 10px; padding-left: 30px; position: relative; font-size: 15px; color: #374151;">
                                                    <span style="position: absolute; left: 0;">✅</span>
                                                    SSL certificate & 24/7 hosting
                                                </li>
                                                <li style="margin: 0 0 10px; padding-left: 30px; position: relative; font-size: 15px; color: #374151;">
                                                    <span style="position: absolute; left: 0;">✅</span>
                                                    Dedicated support team
                                                </li>
                                            </ul>
                                        </div>
                                        
                                        <!-- CTA Button -->
                                        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin: 35px 0;">
                                            <tr>
                                                <td align="center">
                                                    <a href="{checkout_url}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 18px 50px; border-radius: 8px; font-size: 18px; font-weight: 600; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.4);">
                                                        Complete Your Purchase Now →
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <p style="margin: 30px 0 0; font-size: 14px; line-height: 1.6; color: #6b7280; text-align: center;">
                                            <a href="{site_preview_url}" style="color: #667eea; text-decoration: none;">Preview your website again</a> · 
                                            Questions? Just reply to this email!
                                        </p>
                                    </td>
                                </tr>
                                
                                <!-- Footer -->
                                <tr>
                                    <td style="background: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                                        <p style="margin: 0 0 10px; font-size: 14px; color: #6b7280;">
                                            This discount expires in <strong>24 hours</strong>. Don't miss out!
                                        </p>
                                        <p style="margin: 0; font-size: 12px; color: #9ca3af;">
                                            © 2026 WebMagic by Lavish Solutions. All rights reserved.
                                        </p>
                                    </td>
                                </tr>
                                
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """
            
            return await self._send_email(
                to_email=to_email,
                subject=f"💼 Complete Your Purchase - Get 10% Off! ({subject_display})",
                html_content=html_content
            )
        
        except Exception as e:
            logger.error(f"Failed to send abandoned cart email to {to_email}: {e}")
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
            elif provider == "brevo":
                return await self._send_via_brevo(
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
    
    async def _send_via_brevo(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str]
    ) -> bool:
        """Send email via Brevo (formerly Sendinblue)."""
        try:
            import sib_api_v3_sdk
            from sib_api_v3_sdk.rest import ApiException
            
            # Configure API key
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = settings.BREVO_API_KEY
            
            # Create API instance
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )
            
            # Create email
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": to_email}],
                sender={"name": self.from_name, "email": self.from_email},
                subject=subject,
                html_content=html_content
            )
            
            if text_content:
                send_smtp_email.text_content = text_content
            
            # Send email
            response = api_instance.send_transac_email(send_smtp_email)
            
            logger.info(f"Brevo email sent to {to_email}: {response.message_id}")
            return True
        
        except ApiException as e:
            logger.error(f"Brevo API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Brevo error: {e}")
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


    async def send_new_ticket_admin_notification(
        self,
        admin_email: str,
        ticket_number: str,
        customer_name: str,
        customer_email: str,
        category: str,
        priority: str,
        subject: str,
        description: str,
        admin_link: str,
    ) -> bool:
        """Notify admin when a new support ticket is created."""
        try:
            html_content = self.templates.render_new_ticket_admin_notification(
                ticket_number=ticket_number,
                customer_name=customer_name,
                customer_email=customer_email,
                category=category,
                priority=priority,
                subject=subject,
                description=description,
                admin_link=admin_link,
            )
            return await self._send_email(
                to_email=admin_email,
                subject=f"[{priority.upper()}] New Ticket {ticket_number}: {subject}",
                html_content=html_content,
            )
        except Exception as e:
            logger.error(f"Failed to send new-ticket admin notification: {e}")
            return False

    async def send_ticket_reply_to_customer(
        self,
        customer_email: str,
        customer_name: str,
        ticket_number: str,
        subject: str,
        reply_message: str,
        portal_link: str,
        is_ai_reply: bool = False,
    ) -> bool:
        """Email customer when staff or AI has replied to their ticket."""
        try:
            html_content = self.templates.render_ticket_reply_to_customer(
                customer_name=customer_name,
                ticket_number=ticket_number,
                subject=subject,
                reply_message=reply_message,
                portal_link=portal_link,
                is_ai_reply=is_ai_reply,
            )
            sender_label = "AI Assistant" if is_ai_reply else "Support Team"
            return await self._send_email(
                to_email=customer_email,
                subject=f"Re: [{ticket_number}] {subject} — {sender_label} Reply",
                html_content=html_content,
            )
        except Exception as e:
            logger.error(f"Failed to send ticket reply email to customer {customer_email}: {e}")
            return False

    async def send_customer_reply_admin_notification(
        self,
        admin_email: str,
        ticket_number: str,
        customer_name: str,
        customer_email: str,
        subject: str,
        reply_message: str,
        admin_link: str,
    ) -> bool:
        """Notify admin when a customer replies to an existing ticket."""
        try:
            html_content = self.templates.render_customer_reply_admin_notification(
                ticket_number=ticket_number,
                customer_name=customer_name,
                customer_email=customer_email,
                subject=subject,
                reply_message=reply_message,
                admin_link=admin_link,
            )
            return await self._send_email(
                to_email=admin_email,
                subject=f"[Customer Reply] {ticket_number}: {subject}",
                html_content=html_content,
            )
        except Exception as e:
            logger.error(f"Failed to send customer-reply admin notification: {e}")
            return False


def get_email_service() -> EmailService:
    """Get email service instance."""
    return EmailService()
