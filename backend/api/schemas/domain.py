"""
Domain Management Schemas

Pydantic schemas for custom domain management API.
Handles validation for domain connection, verification, and removal.

Author: WebMagic Team
Date: January 21, 2026
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import re


class DomainConnectRequest(BaseModel):
    """Request to connect a custom domain."""
    
    domain: str = Field(
        ...,
        min_length=4,
        max_length=255,
        description="Custom domain to connect (e.g., www.example.com)"
    )
    
    verification_method: Optional[str] = Field(
        "dns_txt",
        description="Verification method: dns_txt or dns_cname"
    )
    
    @validator('domain')
    def validate_domain_format(cls, v):
        """Validate domain format."""
        # Remove protocol if present
        v = v.lower().strip()
        v = v.replace('http://', '').replace('https://', '').replace('www.', '')
        
        # Basic domain validation
        domain_pattern = r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$'
        if not re.match(domain_pattern, v):
            raise ValueError('Invalid domain format. Use format: example.com')
        
        # Add www. prefix
        return f"www.{v}"
    
    @validator('verification_method')
    def validate_verification_method(cls, v):
        """Validate verification method."""
        allowed = ['dns_txt', 'dns_cname']
        if v not in allowed:
            raise ValueError(f'Verification method must be one of: {", ".join(allowed)}')
        return v


class DNSRecordInfo(BaseModel):
    """DNS record information for customer."""
    
    record_type: str = Field(..., description="DNS record type (TXT or CNAME)")
    host: str = Field(..., description="DNS record host/name")
    value: str = Field(..., description="DNS record value")
    ttl: int = Field(3600, description="TTL in seconds")


class DomainConnectResponse(BaseModel):
    """Response after requesting domain connection."""
    
    id: UUID
    domain: str
    verification_method: str
    verification_token: str
    dns_records: DNSRecordInfo
    instructions: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class DomainVerifyRequest(BaseModel):
    """Request to verify domain ownership."""
    
    domain: str = Field(..., description="Domain to verify")


class DomainVerifyResponse(BaseModel):
    """Response after domain verification attempt."""
    
    verified: bool
    domain: str
    ssl_status: Optional[str] = None
    estimated_time: Optional[str] = None
    message: str
    dns_found: Optional[Dict[str, Any]] = None


class DomainStatusResponse(BaseModel):
    """Domain status information."""
    
    id: UUID
    domain: str
    verification_status: str
    verified: bool
    verified_at: Optional[datetime] = None
    ssl_status: Optional[str] = None
    ssl_expires: Optional[datetime] = None
    last_checked: Optional[datetime] = None
    verification_attempts: int
    dns_records: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class DomainDisconnectResponse(BaseModel):
    """Response after disconnecting domain."""
    
    success: bool
    message: str
    default_url: str


class DomainListResponse(BaseModel):
    """List of domains for a site."""
    
    domains: list[DomainStatusResponse]
    total: int
    default_url: str

