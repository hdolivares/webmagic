"""
URL Prescreener - Fast validation checks before Playwright.

Detects obvious invalid URLs to avoid expensive browser automation:
- File documents (PDF, DOC, TXT, XLS, etc.)
- File storage (Google Drive, Dropbox, OneDrive)
- IP addresses and localhost
- Malformed URLs
- Shortened URLs that need expansion

This is the first stage in the validation pipeline - fail fast, fail cheap.
"""
import logging
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import socket

logger = logging.getLogger(__name__)


class URLPrescreener:
    """
    Fast pre-screening of URLs before expensive Playwright validation.
    
    Design principles:
    - Fail fast: Catch obvious invalids in milliseconds
    - No API calls: Pure logic, no external dependencies
    - Clear reasoning: Every rejection has an explanation
    """
    
    # File extensions that are not websites
    FILE_EXTENSIONS = {
        # Documents
        '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt',
        # Spreadsheets
        '.xls', '.xlsx', '.csv', '.ods',
        # Presentations
        '.ppt', '.pptx', '.odp',
        # Archives
        '.zip', '.rar', '.7z', '.tar', '.gz',
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
        # Media
        '.mp4', '.avi', '.mov', '.mp3', '.wav',
        # Other
        '.exe', '.dmg', '.apk',
    }
    
    # Domains that are file storage (not business websites)
    FILE_STORAGE_DOMAINS = {
        'drive.google.com',
        'docs.google.com',
        'dropbox.com',
        'onedrive.live.com',
        '1drv.ms',
        'box.com',
        'icloud.com',
        'mediafire.com',
        'mega.nz',
        'wetransfer.com',
    }
    
    # URL shorteners (need expansion, should be pre-processed)
    URL_SHORTENERS = {
        'bit.ly',
        'tinyurl.com',
        't.co',
        'goo.gl',
        'ow.ly',
        'is.gd',
        'buff.ly',
        'adf.ly',
    }
    
    def prescreen_url(self, url: str) -> Dict[str, Any]:
        """
        Pre-screen a URL for obvious issues.
        
        Args:
            url: URL to check
            
        Returns:
            {
                "should_validate": bool,
                "skip_reason": str or None,
                "recommendation": "skip_playwright" | "proceed" | "expand_url"
            }
        """
        if not url or not url.strip():
            return {
                "should_validate": False,
                "skip_reason": "Empty or null URL",
                "recommendation": "skip_playwright"
            }
        
        url = url.strip()
        
        # Check 1: File extensions
        file_check = self._check_file_extension(url)
        if not file_check["is_valid"]:
            return {
                "should_validate": False,
                "skip_reason": file_check["reason"],
                "recommendation": "skip_playwright"
            }
        
        # Check 2: File storage domains
        storage_check = self._check_file_storage(url)
        if not storage_check["is_valid"]:
            return {
                "should_validate": False,
                "skip_reason": storage_check["reason"],
                "recommendation": "skip_playwright"
            }
        
        # Check 3: URL shorteners (warn but don't block)
        shortener_check = self._check_url_shortener(url)
        if not shortener_check["is_valid"]:
            logger.warning(f"URL shortener detected: {url}")
            return {
                "should_validate": False,
                "skip_reason": shortener_check["reason"],
                "recommendation": "expand_url"
            }
        
        # Check 4: IP addresses / localhost
        ip_check = self._check_ip_or_localhost(url)
        if not ip_check["is_valid"]:
            return {
                "should_validate": False,
                "skip_reason": ip_check["reason"],
                "recommendation": "skip_playwright"
            }
        
        # Check 5: Malformed URL
        format_check = self._check_url_format(url)
        if not format_check["is_valid"]:
            return {
                "should_validate": False,
                "skip_reason": format_check["reason"],
                "recommendation": "skip_playwright"
            }
        
        # All checks passed
        return {
            "should_validate": True,
            "skip_reason": None,
            "recommendation": "proceed"
        }
    
    def _check_file_extension(self, url: str) -> Dict[str, Any]:
        """Check if URL points to a file document."""
        url_lower = url.lower()
        
        for ext in self.FILE_EXTENSIONS:
            if url_lower.endswith(ext):
                return {
                    "is_valid": False,
                    "reason": f"File document ({ext}), not a website"
                }
            
            # Check for extension in path (before query params)
            if ext in url_lower.split('?')[0]:
                # Make sure it's actually the extension (not just in domain name)
                path = urlparse(url_lower).path
                if path.endswith(ext):
                    return {
                        "is_valid": False,
                        "reason": f"File document ({ext}), not a website"
                    }
        
        return {"is_valid": True, "reason": None}
    
    def _check_file_storage(self, url: str) -> Dict[str, Any]:
        """Check if URL is a file storage service."""
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            
            for storage_domain in self.FILE_STORAGE_DOMAINS:
                if storage_domain in domain:
                    return {
                        "is_valid": False,
                        "reason": f"File storage service ({storage_domain}), not a business website"
                    }
            
            return {"is_valid": True, "reason": None}
            
        except Exception as e:
            logger.warning(f"Error parsing URL for storage check: {url} - {e}")
            return {"is_valid": True, "reason": None}
    
    def _check_url_shortener(self, url: str) -> Dict[str, Any]:
        """Check if URL is a URL shortener."""
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc.replace('www.', '')
            
            if domain in self.URL_SHORTENERS:
                return {
                    "is_valid": False,
                    "reason": f"URL shortener ({domain}), needs expansion"
                }
            
            return {"is_valid": True, "reason": None}
            
        except Exception as e:
            logger.warning(f"Error parsing URL for shortener check: {url} - {e}")
            return {"is_valid": True, "reason": None}
    
    def _check_ip_or_localhost(self, url: str) -> Dict[str, Any]:
        """Check if URL uses IP address or localhost."""
        try:
            parsed = urlparse(url.lower())
            host = parsed.netloc.split(':')[0]  # Remove port if present
            
            # Check for localhost variants
            if host in ['localhost', '127.0.0.1', '0.0.0.0']:
                return {
                    "is_valid": False,
                    "reason": "Localhost/loopback address, not a public website"
                }
            
            # Check if it's an IP address
            try:
                socket.inet_aton(host)
                return {
                    "is_valid": False,
                    "reason": "IP address instead of domain name"
                }
            except socket.error:
                # Not an IP address, that's good
                pass
            
            return {"is_valid": True, "reason": None}
            
        except Exception as e:
            logger.warning(f"Error checking IP/localhost: {url} - {e}")
            return {"is_valid": True, "reason": None}
    
    def _check_url_format(self, url: str) -> Dict[str, Any]:
        """Check if URL is properly formatted."""
        try:
            parsed = urlparse(url)
            
            # Must have a scheme
            if not parsed.scheme:
                return {
                    "is_valid": False,
                    "reason": "Missing URL scheme (http/https)"
                }
            
            # Scheme must be http or https
            if parsed.scheme not in ['http', 'https']:
                return {
                    "is_valid": False,
                    "reason": f"Invalid URL scheme: {parsed.scheme}"
                }
            
            # Must have a domain
            if not parsed.netloc:
                return {
                    "is_valid": False,
                    "reason": "Missing domain name"
                }
            
            # Domain must have at least one dot (TLD)
            if '.' not in parsed.netloc:
                return {
                    "is_valid": False,
                    "reason": "Invalid domain format (no TLD)"
                }
            
            return {"is_valid": True, "reason": None}
            
        except Exception as e:
            logger.error(f"Error parsing URL format: {url} - {e}")
            return {
                "is_valid": False,
                "reason": f"Malformed URL: {str(e)}"
            }
