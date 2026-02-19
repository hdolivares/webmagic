"""
Domain Service

Business logic for custom domain management.
Handles DNS verification, domain validation, and lifecycle management.

Architecture:
- Modular functions with single responsibility
- Clean error handling
- Async/await for non-blocking operations
- Type hints for clarity

Author: WebMagic Team
Date: January 21, 2026
"""
import logging
import secrets
import string
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from models.site_models import Site, DomainVerificationRecord
from core.exceptions import (
    NotFoundError,
    ValidationError,
    ForbiddenError
)
from services.platform.nginx_provisioning import NginxProvisioningService

logger = logging.getLogger(__name__)


class DomainService:
    """Service for managing custom domains."""
    
    # ============================================
    # DOMAIN CONNECTION
    # ============================================
    
    @staticmethod
    async def request_domain_connection(
        db: AsyncSession,
        site_id: UUID,
        domain: str,
        verification_method: str = "dns_txt",
        user_id: Optional[UUID] = None
    ) -> DomainVerificationRecord:
        """
        Initiate custom domain connection.
        
        Steps:
        1. Validate site exists and user has permission
        2. Check if domain is already in use
        3. Create verification record
        4. Generate DNS instructions
        
        Args:
            db: Database session
            site_id: Site UUID
            domain: Domain to connect (e.g., www.example.com)
            verification_method: dns_txt or dns_cname
            user_id: User making the request
            
        Returns:
            DomainVerificationRecord with token and instructions
            
        Raises:
            NotFoundError: If site not found
            ForbiddenError: If user doesn't own site
            ValidationError: If domain already in use or invalid
        """
        # Get site
        result = await db.execute(
            select(Site).where(Site.id == site_id)
        )
        site = result.scalar_one_or_none()
        
        if not site:
            raise NotFoundError(f"Site {site_id} not found")
        
        # Check ownership (if user_id provided)
        if user_id and site.business_id:
            # TODO: Verify user owns this site's business
            pass
        
        # Check if domain already exists for another site
        existing = await DomainService._get_domain_by_name(db, domain)
        if existing and existing.site_id != site_id:
            raise ValidationError(
                f"Domain {domain} is already connected to another site"
            )
        
        # Check if site already has a domain
        site_domain = await DomainService._get_site_domain(db, site_id)
        if site_domain and site_domain.domain != domain:
            raise ValidationError(
                f"Site already has domain {site_domain.domain}. "
                "Remove it first before adding a new one."
            )
        
        # Generate verification token
        token = DomainService._generate_verification_token()
        
        # Create or update verification record
        if site_domain and site_domain.domain == domain:
            # Regenerate token for existing domain
            site_domain.verification_token = token
            site_domain.verification_method = verification_method
            site_domain.verified = False
            site_domain.verified_at = None
            site_domain.verification_attempts = 0
            site_domain.expires_at = datetime.utcnow() + timedelta(days=7)
            verification_record = site_domain
        else:
            verification_record = DomainVerificationRecord(
                site_id=site_id,
                domain=domain,
                verification_method=verification_method,
                verification_token=token,
                verified=False,
                verification_attempts=0,
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            db.add(verification_record)
        
        await db.commit()
        await db.refresh(verification_record)
        
        logger.info(
            f"Domain connection requested for site {site_id}: {domain}",
            extra={
                "site_id": str(site_id),
                "domain": domain,
                "method": verification_method
            }
        )
        
        return verification_record
    
    # ============================================
    # DOMAIN VERIFICATION
    # ============================================
    
    @staticmethod
    async def verify_domain(
        db: AsyncSession,
        site_id: UUID,
        domain: str
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Verify domain ownership via DNS check.
        
        Args:
            db: Database session
            site_id: Site UUID
            domain: Domain to verify
            
        Returns:
            Tuple of (verified: bool, dns_info: dict)
            
        Raises:
            NotFoundError: If verification record not found
        """
        # Get verification record
        record = await DomainService._get_domain_record(db, site_id, domain)
        if not record:
            raise NotFoundError(f"No verification record found for {domain}")
        
        # Check if already verified
        if record.verified:
            return True, {"message": "Domain already verified"}
        
        # Check if expired
        if record.is_expired:
            raise ValidationError("Verification token has expired. Request a new one.")
        
        # Increment attempts
        record.verification_attempts += 1
        record.last_check_at = datetime.utcnow()
        
        # Perform DNS verification
        verified, dns_info = await DomainService._check_dns_records(
            domain,
            record.verification_token,
            record.verification_method
        )
        
        # Update record
        record.dns_records = dns_info
        
        if verified:
            record.verified = True
            record.verified_at = datetime.utcnow()

            logger.info(
                f"Domain verified successfully: {domain}",
                extra={
                    "site_id": str(site_id),
                    "domain": domain,
                    "attempts": record.verification_attempts
                }
            )

            await db.commit()
            await db.refresh(record)

            # Auto-provision Nginx vhost + SSL now that ownership is confirmed.
            # Fetch the site slug needed for the web root path.
            site_result = await db.execute(select(Site).where(Site.id == site_id))
            site = site_result.scalar_one_or_none()
            if site and site.slug:
                provision_result = await NginxProvisioningService.provision(
                    domain=domain, slug=site.slug
                )
                logger.info(
                    f"[Domain] Provisioning result for {domain}: {provision_result}"
                )
            else:
                logger.warning(
                    f"[Domain] Could not provision {domain}: site slug not found "
                    f"for site_id={site_id}"
                )
        else:
            logger.warning(
                f"Domain verification failed: {domain}",
                extra={
                    "site_id": str(site_id),
                    "domain": domain,
                    "attempts": record.verification_attempts,
                    "dns_info": dns_info
                }
            )

            await db.commit()
            await db.refresh(record)

        return verified, dns_info
    
    # ============================================
    # DOMAIN STATUS
    # ============================================
    
    @staticmethod
    async def get_domain_status(
        db: AsyncSession,
        site_id: UUID
    ) -> Optional[DomainVerificationRecord]:
        """
        Get current domain status for a site.
        
        Args:
            db: Database session
            site_id: Site UUID
            
        Returns:
            DomainVerificationRecord or None if no domain
        """
        return await DomainService._get_site_domain(db, site_id)
    
    # ============================================
    # DOMAIN REMOVAL
    # ============================================
    
    @staticmethod
    async def remove_domain(
        db: AsyncSession,
        site_id: UUID,
        user_id: Optional[UUID] = None
    ) -> bool:
        """
        Remove custom domain from site.
        
        Args:
            db: Database session
            site_id: Site UUID
            user_id: User making the request
            
        Returns:
            True if successful
            
        Raises:
            NotFoundError: If no domain found
        """
        record = await DomainService._get_site_domain(db, site_id)
        if not record:
            raise NotFoundError("No custom domain found for this site")

        domain = record.domain
        was_verified = record.verified

        await db.delete(record)
        await db.commit()

        logger.info(
            f"Domain removed from site {site_id}: {domain}",
            extra={"site_id": str(site_id), "domain": domain}
        )

        # Remove Nginx vhost only if it was ever provisioned (i.e. verified).
        if was_verified:
            await NginxProvisioningService.deprovision(domain)

        return True
    
    # ============================================
    # DNS INSTRUCTIONS
    # ============================================
    
    @staticmethod
    def get_dns_instructions(
        domain: str,
        token: str,
        method: str
    ) -> Dict[str, Any]:
        """
        Generate DNS configuration instructions.
        
        Args:
            domain: Domain name
            token: Verification token
            method: Verification method (dns_txt or dns_cname)
            
        Returns:
            Dict with DNS record details and instructions
        """
        if method == "dns_txt":
            return {
                "record_type": "TXT",
                "host": f"_webmagic-verify.{domain}",
                "value": f"webmagic-verification={token}",
                "ttl": 3600,
                "instructions": (
                    f"Add a TXT record to your DNS:\n\n"
                    f"Host/Name: _webmagic-verify.{domain}\n"
                    f"Type: TXT\n"
                    f"Value: webmagic-verification={token}\n"
                    f"TTL: 3600 (1 hour)\n\n"
                    f"After adding the record, click 'Verify Domain'. "
                    f"DNS propagation can take up to 24 hours."
                )
            }
        else:  # dns_cname
            return {
                "record_type": "CNAME",
                "host": domain,
                "value": f"verify-{token[:16]}.sites.lavish.solutions",
                "ttl": 3600,
                "instructions": (
                    f"Add a CNAME record to your DNS:\n\n"
                    f"Host/Name: {domain}\n"
                    f"Type: CNAME\n"
                    f"Value: verify-{token[:16]}.sites.lavish.solutions\n"
                    f"TTL: 3600 (1 hour)\n\n"
                    f"After adding the record, click 'Verify Domain'. "
                    f"DNS propagation can take up to 24 hours."
                )
            }
    
    # ============================================
    # PRIVATE HELPER METHODS
    # ============================================
    
    @staticmethod
    async def _get_domain_by_name(
        db: AsyncSession,
        domain: str
    ) -> Optional[DomainVerificationRecord]:
        """Get domain verification record by domain name."""
        result = await db.execute(
            select(DomainVerificationRecord)
            .where(DomainVerificationRecord.domain == domain)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def _get_site_domain(
        db: AsyncSession,
        site_id: UUID
    ) -> Optional[DomainVerificationRecord]:
        """Get domain verification record for a site."""
        result = await db.execute(
            select(DomainVerificationRecord)
            .where(DomainVerificationRecord.site_id == site_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def _get_domain_record(
        db: AsyncSession,
        site_id: UUID,
        domain: str
    ) -> Optional[DomainVerificationRecord]:
        """Get specific domain record for site."""
        result = await db.execute(
            select(DomainVerificationRecord)
            .where(
                and_(
                    DomainVerificationRecord.site_id == site_id,
                    DomainVerificationRecord.domain == domain
                )
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    def _generate_verification_token(length: int = 32) -> str:
        """Generate a random verification token."""
        alphabet = string.ascii_lowercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    async def _check_dns_records(
        domain: str,
        token: str,
        method: str
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if DNS records are correctly configured.
        
        This is a placeholder implementation. In production, use dnspython.
        
        Args:
            domain: Domain to check
            token: Expected token
            method: Verification method
            
        Returns:
            Tuple of (verified: bool, dns_info: dict)
        """
        # TODO: Implement actual DNS checking with dnspython
        # For now, return mock response for development
        
        try:
            import dns.resolver
            
            if method == "dns_txt":
                # Check for TXT record
                try:
                    answers = dns.resolver.resolve(
                        f"_webmagic-verify.{domain}",
                        'TXT'
                    )
                    for rdata in answers:
                        txt_value = str(rdata).strip('"')
                        if f"webmagic-verification={token}" in txt_value:
                            return True, {
                                "found": True,
                                "record_type": "TXT",
                                "value": txt_value
                            }
                    return False, {
                        "found": True,
                        "record_type": "TXT",
                        "value": "Found TXT record but token mismatch",
                        "expected": f"webmagic-verification={token}"
                    }
                except dns.resolver.NXDOMAIN:
                    return False, {
                        "found": False,
                        "error": "DNS record not found",
                        "hint": "Make sure you've added the TXT record"
                    }
                except Exception as e:
                    logger.error(f"DNS TXT check failed: {e}")
                    return False, {
                        "found": False,
                        "error": str(e)
                    }
            
            else:  # dns_cname
                # Check for CNAME record
                try:
                    answers = dns.resolver.resolve(domain, 'CNAME')
                    for rdata in answers:
                        cname_value = str(rdata).rstrip('.')
                        expected = f"verify-{token[:16]}.sites.lavish.solutions"
                        if cname_value == expected:
                            return True, {
                                "found": True,
                                "record_type": "CNAME",
                                "value": cname_value
                            }
                    return False, {
                        "found": True,
                        "record_type": "CNAME",
                        "value": "Found CNAME but value mismatch",
                        "expected": expected
                    }
                except dns.resolver.NXDOMAIN:
                    return False, {
                        "found": False,
                        "error": "DNS record not found"
                    }
                except Exception as e:
                    logger.error(f"DNS CNAME check failed: {e}")
                    return False, {
                        "found": False,
                        "error": str(e)
                    }
        
        except ImportError:
            # dnspython not installed, return mock for development
            logger.warning("dnspython not installed, using mock DNS verification")
            return False, {
                "found": False,
                "error": "DNS verification not available (dnspython not installed)",
                "hint": "Install dnspython for DNS verification"
            }


def get_domain_service() -> DomainService:
    """Get domain service instance."""
    return DomainService()

