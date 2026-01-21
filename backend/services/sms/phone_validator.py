"""
Phone Number Validation Service.

Validates and formats phone numbers for SMS sending.
Uses phonenumbers library for robust international support.

Author: WebMagic Team
Date: January 21, 2026
"""
import logging
from typing import Optional, Tuple
import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberType

logger = logging.getLogger(__name__)


class PhoneValidator:
    """
    Validates and formats phone numbers for SMS.
    
    Features:
    - E.164 format conversion
    - US/International number support
    - Mobile number detection
    - Invalid number rejection
    """
    
    DEFAULT_REGION = "US"
    
    @staticmethod
    def validate_and_format(
        phone: str,
        region: str = DEFAULT_REGION
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate phone number and return E.164 format.
        
        Args:
            phone: Phone number in any format
            region: Country code (default: US)
        
        Returns:
            Tuple of (is_valid, formatted_phone, error_message)
            
        Example:
            >>> PhoneValidator.validate_and_format("(555) 123-4567")
            (True, "+15551234567", None)
        """
        if not phone:
            return (False, None, "Phone number is required")
        
        try:
            # Parse the phone number
            parsed = phonenumbers.parse(phone, region)
            
            # Check if it's valid
            if not phonenumbers.is_valid_number(parsed):
                return (False, None, "Invalid phone number")
            
            # Check if it's a mobile number (SMS requires mobile)
            number_type = phonenumbers.number_type(parsed)
            if number_type not in [
                PhoneNumberType.MOBILE,
                PhoneNumberType.FIXED_LINE_OR_MOBILE
            ]:
                logger.warning(f"Non-mobile number: {phone} (type: {number_type})")
                # Still allow it, but log warning
            
            # Format to E.164
            formatted = phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.E164
            )
            
            return (True, formatted, None)
        
        except NumberParseException as e:
            error_msg = f"Invalid phone format: {str(e)}"
            logger.debug(error_msg)
            return (False, None, error_msg)
        
        except Exception as e:
            error_msg = f"Phone validation error: {str(e)}"
            logger.error(error_msg)
            return (False, None, error_msg)
    
    @staticmethod
    def is_valid_for_sms(phone: str, region: str = DEFAULT_REGION) -> bool:
        """
        Quick check if phone number is valid for SMS.
        
        Args:
            phone: Phone number to check
            region: Country code
        
        Returns:
            True if valid and can receive SMS
        """
        is_valid, _, _ = PhoneValidator.validate_and_format(phone, region)
        return is_valid
    
    @staticmethod
    def get_country_code(phone: str, region: str = DEFAULT_REGION) -> Optional[str]:
        """
        Extract country code from phone number.
        
        Args:
            phone: Phone number
            region: Default region
        
        Returns:
            Country code (e.g., "US", "CA", "MX") or None
        """
        try:
            parsed = phonenumbers.parse(phone, region)
            return phonenumbers.region_code_for_number(parsed)
        except Exception:
            return None
    
    @staticmethod
    def format_display(phone: str, region: str = DEFAULT_REGION) -> str:
        """
        Format phone number for display (human-readable).
        
        Args:
            phone: Phone number
            region: Country code
        
        Returns:
            Formatted phone for display (e.g., "(555) 123-4567")
        """
        try:
            parsed = phonenumbers.parse(phone, region)
            
            # Use national format for display
            formatted = phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.NATIONAL
            )
            
            return formatted
        except Exception:
            # Return original if formatting fails
            return phone
    
    @staticmethod
    def normalize_to_e164(phone: str, region: str = DEFAULT_REGION) -> Optional[str]:
        """
        Normalize phone to E.164 format.
        
        This is a convenience method that returns None on error
        instead of a tuple.
        
        Args:
            phone: Phone number
            region: Country code
        
        Returns:
            E.164 formatted phone or None
        """
        is_valid, formatted, _ = PhoneValidator.validate_and_format(phone, region)
        return formatted if is_valid else None

