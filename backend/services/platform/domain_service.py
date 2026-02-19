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
import os
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
from services.platform.nginx_provisioning import NginxProvisioningService, SERVER_IP

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
        method: str,
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Two-phase DNS verification:

        Phase 1 — Ownership check
            Verify the TXT (or CNAME) record that proves the customer controls the domain.

        Phase 2 — A-record check
            Verify that the bare domain's A record resolves to this server's public IP
            (SERVER_IP). This ensures Nginx can serve the domain AND certbot can issue
            an SSL certificate via the HTTP-01 ACME challenge.

        Both phases must pass for the overall verification to succeed.

        Returns:
            (verified: bool, dns_info: dict)
            dns_info always contains:
                ownership  – result dict for phase 1
                a_record   – result dict for phase 2 (or {"checked": False} if phase 1 failed)
                error      – machine-readable failure reason, if any
        """
        try:
            import dns.resolver
        except ImportError:
            logger.warning("dnspython not installed — DNS verification unavailable")
            return False, {
                "ownership": {"checked": False},
                "a_record": {"checked": False},
                "error": "dns_library_unavailable",
            }

        bare = domain.removeprefix("www.")

        # ── Phase 1: Ownership record ────────────────────────────────────────
        ownership_ok, ownership_info = DomainService._check_ownership_record(
            domain=domain,
            token=token,
            method=method,
            resolver=dns.resolver,
        )

        if not ownership_ok:
            return False, {
                "ownership": ownership_info,
                "a_record": {"checked": False},
                "error": "ownership_failed",
            }

        # ── Phase 2: A record must point to our server ───────────────────────
        a_ok, a_info = DomainService._check_a_record(
            bare_domain=bare,
            expected_ip=SERVER_IP,
            resolver=dns.resolver,
        )

        if not a_ok:
            return False, {
                "ownership": ownership_info,
                "a_record": a_info,
                "error": "a_record_not_pointing_to_server",
            }

        return True, {
            "ownership": ownership_info,
            "a_record": a_info,
        }

    # ── DNS sub-checks ────────────────────────────────────────────────────────

    @staticmethod
    def _check_ownership_record(
        domain: str,
        token: str,
        method: str,
        resolver,
    ) -> tuple[bool, Dict[str, Any]]:
        """Check TXT or CNAME ownership record synchronously."""
        if method == "dns_txt":
            txt_host = f"_webmagic-verify.{domain}"
            try:
                answers = resolver.resolve(txt_host, "TXT")
                expected = f"webmagic-verification={token}"
                for rdata in answers:
                    txt_value = str(rdata).strip('"')
                    if expected in txt_value:
                        return True, {
                            "checked": True,
                            "found": True,
                            "record_type": "TXT",
                            "value": txt_value,
                        }
                return False, {
                    "checked": True,
                    "found": True,
                    "record_type": "TXT",
                    "error": "token_mismatch",
                    "hint": f"Found a TXT record at {txt_host} but the value does not match. "
                            f"Make sure you copied the value exactly.",
                }
            except resolver.NXDOMAIN:
                return False, {
                    "checked": True,
                    "found": False,
                    "record_type": "TXT",
                    "error": "record_not_found",
                    "hint": f"No TXT record found at {txt_host}. "
                            "Add the TXT record and wait for DNS propagation (up to 24 hours).",
                }
            except Exception as exc:
                logger.error(f"DNS TXT check error for {domain}: {exc}")
                return False, {
                    "checked": True,
                    "found": False,
                    "record_type": "TXT",
                    "error": "lookup_error",
                    "hint": str(exc),
                }
        else:  # dns_cname
            expected_cname = f"verify-{token[:16]}.sites.lavish.solutions"
            try:
                answers = resolver.resolve(domain, "CNAME")
                for rdata in answers:
                    cname_value = str(rdata).rstrip(".")
                    if cname_value == expected_cname:
                        return True, {
                            "checked": True,
                            "found": True,
                            "record_type": "CNAME",
                            "value": cname_value,
                        }
                return False, {
                    "checked": True,
                    "found": True,
                    "record_type": "CNAME",
                    "error": "cname_mismatch",
                    "hint": "Found a CNAME record but the value does not match.",
                }
            except resolver.NXDOMAIN:
                return False, {
                    "checked": True,
                    "found": False,
                    "record_type": "CNAME",
                    "error": "record_not_found",
                    "hint": "No CNAME record found. Add the CNAME record and wait for propagation.",
                }
            except Exception as exc:
                logger.error(f"DNS CNAME check error for {domain}: {exc}")
                return False, {
                    "checked": True,
                    "found": False,
                    "record_type": "CNAME",
                    "error": "lookup_error",
                    "hint": str(exc),
                }

    @staticmethod
    def _check_a_record(
        bare_domain: str,
        expected_ip: str,
        resolver,
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Verify that the bare domain's A record resolves to expected_ip.
        We only check the bare domain (not www) since certbot needs it to reach
        this server for the HTTP-01 ACME challenge.
        """
        try:
            answers = resolver.resolve(bare_domain, "A")
            found_ips = [str(r) for r in answers]
            if expected_ip in found_ips:
                return True, {
                    "checked": True,
                    "found": True,
                    "record_type": "A",
                    "value": found_ips,
                }
            return False, {
                "checked": True,
                "found": True,
                "record_type": "A",
                "resolved_ips": found_ips,
                "expected_ip": expected_ip,
                "error": "ip_mismatch",
                "hint": (
                    f"Your domain resolves to {', '.join(found_ips)} instead of "
                    f"{expected_ip}. Update your A record to point to {expected_ip}. "
                    "If you are using Cloudflare, make sure the proxy (orange cloud) "
                    "is turned OFF (grey cloud) so the IP is visible."
                ),
            }
        except Exception as exc:
            logger.error(f"DNS A-record check error for {bare_domain}: {exc}")
            return False, {
                "checked": True,
                "found": False,
                "record_type": "A",
                "expected_ip": expected_ip,
                "error": "record_not_found",
                "hint": (
                    f"No A record found for {bare_domain}. "
                    f"Add an A record pointing to {expected_ip}."
                ),
            }


def get_domain_service() -> DomainService:
    """Get domain service instance."""
    return DomainService()

