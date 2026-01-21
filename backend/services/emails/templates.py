"""
Email Templates

Beautiful, responsive HTML email templates for customer communications.

All templates use inline CSS for maximum email client compatibility.

Author: WebMagic Team
Date: January 21, 2026
"""
from typing import Dict, Any


class EmailTemplates:
    """Email template renderer with inline CSS."""
    
    def __init__(self):
        """Initialize template renderer."""
        self.brand_color = "#6366f1"  # Indigo
        self.brand_color_dark = "#4f46e5"
        self.success_color = "#10b981"  # Green
        self.text_color = "#1f2937"  # Gray 800
        self.text_light = "#6b7280"  # Gray 500
        self.bg_light = "#f9fafb"  # Gray 50
    
    def render_welcome_email(
        self,
        customer_name: str,
        verification_url: str
    ) -> str:
        """Render welcome email with verification link."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to WebMagic!</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: {self.bg_light};">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {self.bg_light}; padding: 40px 20px;">
        <tr>
            <td align="center">
                <!-- Main Container -->
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    
                    <!-- Header with gradient -->
                    <tr>
                        <td style="background: linear-gradient(135deg, {self.brand_color} 0%, {self.brand_color_dark} 100%); padding: 40px 40px 60px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: bold;">
                                Welcome to WebMagic! 🎉
                            </h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <p style="margin: 0 0 20px; color: {self.text_color}; font-size: 16px; line-height: 1.6;">
                                Hi <strong>{customer_name}</strong>,
                            </p>
                            
                            <p style="margin: 0 0 20px; color: {self.text_color}; font-size: 16px; line-height: 1.6;">
                                Thank you for joining WebMagic! We're excited to help you create and manage your professional website.
                            </p>
                            
                            <p style="margin: 0 0 30px; color: {self.text_color}; font-size: 16px; line-height: 1.6;">
                                To get started, please verify your email address by clicking the button below:
                            </p>
                            
                            <!-- CTA Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding: 10px 0 30px;">
                                        <a href="{verification_url}" style="display: inline-block; background-color: {self.brand_color}; color: #ffffff; text-decoration: none; padding: 16px 32px; border-radius: 8px; font-size: 16px; font-weight: 600; box-shadow: 0 2px 4px rgba(99, 102, 241, 0.4);">
                                            Verify Email Address
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin: 0 0 20px; color: {self.text_light}; font-size: 14px; line-height: 1.6;">
                                Or copy and paste this link into your browser:<br>
                                <a href="{verification_url}" style="color: {self.brand_color}; word-break: break-all;">{verification_url}</a>
                            </p>
                            
                            <!-- What's Next Section -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {self.bg_light}; border-radius: 8px; padding: 20px; margin-top: 30px;">
                                <tr>
                                    <td>
                                        <h3 style="margin: 0 0 15px; color: {self.text_color}; font-size: 18px; font-weight: 600;">
                                            What's Next?
                                        </h3>
                                        <ul style="margin: 0; padding-left: 20px; color: {self.text_color}; font-size: 15px; line-height: 1.8;">
                                            <li>Verify your email address</li>
                                            <li>Complete your profile</li>
                                            <li>Browse available websites</li>
                                            <li>Purchase your perfect site</li>
                                        </ul>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin: 30px 0 0; color: {self.text_color}; font-size: 16px; line-height: 1.6;">
                                If you have any questions, we're here to help!
                            </p>
                            
                            <p style="margin: 10px 0 0; color: {self.text_color}; font-size: 16px; line-height: 1.6;">
                                Best regards,<br>
                                <strong>The WebMagic Team</strong>
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: {self.bg_light}; padding: 30px 40px; text-align: center; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0 0 10px; color: {self.text_light}; font-size: 14px;">
                                This email was sent to you because you created an account at WebMagic.
                            </p>
                            <p style="margin: 0; color: {self.text_light}; font-size: 14px;">
                                &copy; 2026 WebMagic. All rights reserved.
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
    
    def render_verification_email(
        self,
        customer_name: str,
        verification_url: str
    ) -> str:
        """Render email verification reminder."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: {self.bg_light};">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {self.bg_light}; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    
                    <tr>
                        <td style="background-color: {self.brand_color}; padding: 40px; text-align: center; border-radius: 12px 12px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: bold;">
                                Verify Your Email Address
                            </h1>
                        </td>
                    </tr>
                    
                    <tr>
                        <td style="padding: 40px;">
                            <p style="margin: 0 0 20px; color: {self.text_color}; font-size: 16px; line-height: 1.6;">
                                Hi <strong>{customer_name}</strong>,
                            </p>
                            
                            <p style="margin: 0 0 30px; color: {self.text_color}; font-size: 16px; line-height: 1.6;">
                                Please verify your email address to unlock all features of your WebMagic account.
                            </p>
                            
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding: 10px 0 30px;">
                                        <a href="{verification_url}" style="display: inline-block; background-color: {self.brand_color}; color: #ffffff; text-decoration: none; padding: 16px 32px; border-radius: 8px; font-size: 16px; font-weight: 600;">
                                            Verify Email
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin: 0; color: {self.text_light}; font-size: 14px; line-height: 1.6;">
                                Or copy this link:<br>
                                <a href="{verification_url}" style="color: {self.brand_color}; word-break: break-all;">{verification_url}</a>
                            </p>
                        </td>
                    </tr>
                    
                    <tr>
                        <td style="background-color: {self.bg_light}; padding: 20px 40px; text-align: center;">
                            <p style="margin: 0; color: {self.text_light}; font-size: 14px;">
                                &copy; 2026 WebMagic
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
    
    def render_password_reset_email(
        self,
        customer_name: str,
        reset_url: str
    ) -> str:
        """Render password reset email."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: {self.bg_light};">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {self.bg_light}; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    
                    <tr>
                        <td style="background-color: #ef4444; padding: 40px; text-align: center; border-radius: 12px 12px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: bold;">
                                Password Reset Request
                            </h1>
                        </td>
                    </tr>
                    
                    <tr>
                        <td style="padding: 40px;">
                            <p style="margin: 0 0 20px; color: {self.text_color}; font-size: 16px; line-height: 1.6;">
                                Hi <strong>{customer_name}</strong>,
                            </p>
                            
                            <p style="margin: 0 0 20px; color: {self.text_color}; font-size: 16px; line-height: 1.6;">
                                We received a request to reset your password. Click the button below to create a new password:
                            </p>
                            
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding: 10px 0 30px;">
                                        <a href="{reset_url}" style="display: inline-block; background-color: #ef4444; color: #ffffff; text-decoration: none; padding: 16px 32px; border-radius: 8px; font-size: 16px; font-weight: 600;">
                                            Reset Password
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin: 0 0 20px; color: {self.text_light}; font-size: 14px; line-height: 1.6;">
                                Or copy and paste this link:<br>
                                <a href="{reset_url}" style="color: #ef4444; word-break: break-all;">{reset_url}</a>
                            </p>
                            
                            <!-- Security Notice -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; margin-top: 20px;">
                                <tr>
                                    <td>
                                        <p style="margin: 0; color: {self.text_color}; font-size: 14px; line-height: 1.6; font-weight: 600;">
                                            ⚠️ Security Notice
                                        </p>
                                        <p style="margin: 10px 0 0; color: {self.text_color}; font-size: 14px; line-height: 1.6;">
                                            This link will expire in <strong>1 hour</strong>. If you didn't request a password reset, please ignore this email or contact support if you're concerned about your account security.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <tr>
                        <td style="background-color: {self.bg_light}; padding: 20px 40px; text-align: center;">
                            <p style="margin: 0; color: {self.text_light}; font-size: 14px;">
                                &copy; 2026 WebMagic
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
    
    def render_purchase_confirmation_email(
        self,
        customer_name: str,
        site_title: str,
        site_url: str,
        purchase_amount: float,
        transaction_id: str,
        portal_url: str
    ) -> str:
        """Render purchase confirmation email."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Website is Ready!</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: {self.bg_light};">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {self.bg_light}; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    
                    <!-- Success Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, {self.success_color} 0%, #059669 100%); padding: 40px; text-align: center;">
                            <div style="font-size: 48px; margin-bottom: 10px;">🎉</div>
                            <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: bold;">
                                Your Website is Ready!
                            </h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <p style="margin: 0 0 20px; color: {self.text_color}; font-size: 16px; line-height: 1.6;">
                                Hi <strong>{customer_name}</strong>,
                            </p>
                            
                            <p style="margin: 0 0 30px; color: {self.text_color}; font-size: 16px; line-height: 1.6;">
                                Congratulations! Your website purchase is complete and your site is now live. 🚀
                            </p>
                            
                            <!-- Site Info Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {self.bg_light}; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                                <tr>
                                    <td>
                                        <h3 style="margin: 0 0 15px; color: {self.text_color}; font-size: 18px; font-weight: 600;">
                                            Your Website
                                        </h3>
                                        <p style="margin: 0 0 10px; color: {self.text_color}; font-size: 15px;">
                                            <strong>Site:</strong> {site_title}
                                        </p>
                                        <p style="margin: 0; color: {self.brand_color}; font-size: 15px;">
                                            <a href="{site_url}" style="color: {self.brand_color}; text-decoration: none; font-weight: 600;">{site_url}</a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Purchase Details -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; margin-bottom: 30px;">
                                <tr style="background-color: {self.bg_light};">
                                    <td colspan="2" style="padding: 15px; border-bottom: 1px solid #e5e7eb;">
                                        <h3 style="margin: 0; color: {self.text_color}; font-size: 16px; font-weight: 600;">
                                            Purchase Details
                                        </h3>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb; color: {self.text_light}; font-size: 14px;">
                                        Amount Paid
                                    </td>
                                    <td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb; color: {self.text_color}; font-size: 14px; font-weight: 600; text-align: right;">
                                        ${purchase_amount:.2f}
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 15px; color: {self.text_light}; font-size: 14px;">
                                        Transaction ID
                                    </td>
                                    <td style="padding: 12px 15px; color: {self.text_color}; font-size: 14px; font-family: monospace; text-align: right;">
                                        {transaction_id}
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- CTA Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding: 10px 0 30px;">
                                        <a href="{portal_url}" style="display: inline-block; background-color: {self.brand_color}; color: #ffffff; text-decoration: none; padding: 16px 32px; border-radius: 8px; font-size: 16px; font-weight: 600; box-shadow: 0 2px 4px rgba(99, 102, 241, 0.4);">
                                            Access Your Dashboard
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Next Steps -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #eff6ff; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                                <tr>
                                    <td>
                                        <h3 style="margin: 0 0 15px; color: {self.text_color}; font-size: 18px; font-weight: 600;">
                                            Next Steps
                                        </h3>
                                        <ol style="margin: 0; padding-left: 20px; color: {self.text_color}; font-size: 15px; line-height: 1.8;">
                                            <li>Visit your live website</li>
                                            <li>Activate monthly subscription ($95/month)</li>
                                            <li>Request AI-powered edits</li>
                                            <li>Connect your custom domain</li>
                                        </ol>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin: 0 0 10px; color: {self.text_color}; font-size: 16px; line-height: 1.6;">
                                Thank you for choosing WebMagic!
                            </p>
                            
                            <p style="margin: 0; color: {self.text_color}; font-size: 16px; line-height: 1.6;">
                                Best regards,<br>
                                <strong>The WebMagic Team</strong>
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: {self.bg_light}; padding: 30px 40px; text-align: center; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0 0 10px; color: {self.text_light}; font-size: 14px;">
                                Need help? Contact us at support@webmagic.com
                            </p>
                            <p style="margin: 0; color: {self.text_light}; font-size: 14px;">
                                &copy; 2026 WebMagic. All rights reserved.
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

    def render_subscription_activated_email(
        self,
        customer_name: str,
        site_title: str,
        site_url: str,
        next_billing_date: str,
        portal_url: str
    ) -> str:
        """Render subscription activation confirmation email."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Subscription Activated!</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, ''Segoe UI'', Roboto, ''Helvetica Neue'', Arial, sans-serif; background-color: {self.bg_light};">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {self.bg_light}; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px;">
                    <tr>
                        <td style="background: linear-gradient(135deg, {self.success_color} 0%, #059669 100%); padding: 40px; text-align: center;">
                            <div style="font-size: 48px; margin-bottom: 10px;">🎉</div>
                            <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: bold;">Subscription Activated!</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px;">
                            <p style="margin: 0 0 20px; color: {self.text_color}; font-size: 16px;">Hi <strong>{customer_name}</strong>,</p>
                            <p style="margin: 0 0 30px; color: {self.text_color}; font-size: 16px;">Your monthly subscription is now active. Your website has full access to all premium features.</p>
                            <p style="margin: 0; color: {self.text_color};">Next Billing: {next_billing_date}</p>
                            <p style="margin: 20px 0;"><a href="{portal_url}" style="background-color: {self.brand_color}; color: #ffffff; padding: 16px 32px; text-decoration: none; border-radius: 8px;">Access Dashboard</a></p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
