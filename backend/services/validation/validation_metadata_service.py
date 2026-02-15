"""
Validation Metadata Service.

Manages website validation history, discovery attempts, and audit trails.
Follows best practices: Single Responsibility, Immutability, Type Safety.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
import logging

from core.validation_enums import (
    ValidationState,
    ValidationRecommendation,
    URLSource,
    InvalidURLReason
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationHistoryEntry:
    """
    Single validation attempt record.
    
    Immutable record of a validation attempt for audit trail.
    """
    timestamp: str
    url: str
    verdict: str
    confidence: float
    reasoning: str
    recommendation: str
    invalid_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return asdict(self)
    
    @classmethod
    def from_validation_result(
        cls,
        url: str,
        result: Dict[str, Any]
    ) -> "ValidationHistoryEntry":
        """
        Create history entry from validation result.
        
        Args:
            url: URL that was validated
            result: Validation result dictionary
            
        Returns:
            ValidationHistoryEntry instance
        """
        return cls(
            timestamp=datetime.utcnow().isoformat(),
            url=url,
            verdict=result.get("verdict", "error"),
            confidence=result.get("confidence", 0.0),
            reasoning=result.get("reasoning", "No reasoning provided"),
            recommendation=result.get("recommendation", ""),
            invalid_reason=result.get("invalid_reason")
        )


@dataclass
class DiscoveryAttempt:
    """
    Single discovery attempt record.
    
    Tracks attempts to find a website URL via different methods.
    """
    method: str  # 'outscraper', 'scrapingdog', 'manual'
    attempted: bool
    timestamp: Optional[str] = None
    found_url: bool = False
    url_found: Optional[str] = None
    valid: bool = False
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class WebsiteMetadata:
    """
    Complete website metadata structure.
    
    Encapsulates all validation history, discovery attempts, and source tracking.
    Provides clean interface for metadata operations.
    """
    source: str = URLSource.NONE.value
    source_timestamp: Optional[str] = None
    validation_history: List[Dict[str, Any]] = field(default_factory=list)
    discovery_attempts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "source": self.source,
            "source_timestamp": self.source_timestamp,
            "validation_history": self.validation_history,
            "discovery_attempts": self.discovery_attempts,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebsiteMetadata":
        """
        Create metadata instance from dictionary.
        
        Args:
            data: Metadata dictionary (from JSONB field)
            
        Returns:
            WebsiteMetadata instance
        """
        if not data:
            return cls()
        
        return cls(
            source=data.get("source", URLSource.NONE.value),
            source_timestamp=data.get("source_timestamp"),
            validation_history=data.get("validation_history", []),
            discovery_attempts=data.get("discovery_attempts", {}),
            notes=data.get("notes")
        )


class ValidationMetadataService:
    """
    Service for managing validation metadata.
    
    Provides clean, testable interface for all metadata operations.
    Follows Single Responsibility Principle.
    """
    
    @staticmethod
    def create_initial_metadata(source: str = URLSource.NONE.value) -> Dict[str, Any]:
        """
        Create initial metadata for a new business.
        
        Args:
            source: Initial URL source
            
        Returns:
            Initial metadata dictionary
        """
        metadata = WebsiteMetadata(source=source)
        return metadata.to_dict()
    
    @staticmethod
    def add_validation_entry(
        current_metadata: Dict[str, Any],
        url: str,
        validation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add validation attempt to history.
        
        Args:
            current_metadata: Current metadata dictionary
            url: URL that was validated
            validation_result: Validation result from orchestrator
            
        Returns:
            Updated metadata dictionary
        """
        metadata = WebsiteMetadata.from_dict(current_metadata)
        
        # Create history entry
        entry = ValidationHistoryEntry.from_validation_result(url, validation_result)
        metadata.validation_history.append(entry.to_dict())
        
        logger.info(
            f"Added validation entry: {entry.verdict} "
            f"(confidence: {entry.confidence:.2f}) - {entry.reasoning}"
        )
        
        return metadata.to_dict()
    
    @staticmethod
    def update_url_source(
        current_metadata: Dict[str, Any],
        source: str,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update URL source information.
        
        Args:
            current_metadata: Current metadata dictionary
            source: New URL source
            url: Optional URL (for logging)
            
        Returns:
            Updated metadata dictionary
        """
        metadata = WebsiteMetadata.from_dict(current_metadata)
        
        metadata.source = source
        metadata.source_timestamp = datetime.utcnow().isoformat()
        
        logger.info(f"Updated URL source to: {source}" + (f" for URL: {url}" if url else ""))
        
        return metadata.to_dict()
    
    @staticmethod
    def record_discovery_attempt(
        current_metadata: Dict[str, Any],
        method: str,
        found_url: bool,
        url_found: Optional[str] = None,
        valid: bool = False,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a discovery attempt (Outscraper, ScrapingDog, etc).
        
        Args:
            current_metadata: Current metadata dictionary
            method: Discovery method ('outscraper', 'scrapingdog', 'manual')
            found_url: Whether a URL was found
            url_found: The URL that was found (if any)
            valid: Whether the URL was validated as valid
            notes: Additional notes
            
        Returns:
            Updated metadata dictionary
        """
        metadata = WebsiteMetadata.from_dict(current_metadata)
        
        attempt = DiscoveryAttempt(
            method=method,
            attempted=True,
            timestamp=datetime.utcnow().isoformat(),
            found_url=found_url,
            url_found=url_found,
            valid=valid,
            notes=notes
        )
        
        metadata.discovery_attempts[method] = attempt.to_dict()
        
        logger.info(
            f"Recorded {method} discovery: "
            f"found={found_url}, valid={valid}" +
            (f", url={url_found}" if url_found else "")
        )
        
        return metadata.to_dict()
    
    @staticmethod
    def get_discovery_attempt_count(metadata: Dict[str, Any]) -> int:
        """
        Get total number of discovery attempts.
        
        Args:
            metadata: Current metadata dictionary
            
        Returns:
            Number of discovery attempts
        """
        meta = WebsiteMetadata.from_dict(metadata)
        return len(meta.discovery_attempts)
    
    @staticmethod
    def has_attempted_method(metadata: Dict[str, Any], method: str) -> bool:
        """
        Check if a discovery method has been attempted.
        
        Args:
            metadata: Current metadata dictionary
            method: Discovery method to check
            
        Returns:
            True if method has been attempted
        """
        meta = WebsiteMetadata.from_dict(metadata)
        attempt = meta.discovery_attempts.get(method, {})
        return attempt.get("attempted", False)
    
    @staticmethod
    def get_last_validation(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get the most recent validation entry.
        
        Args:
            metadata: Current metadata dictionary
            
        Returns:
            Most recent validation entry or None
        """
        meta = WebsiteMetadata.from_dict(metadata)
        if not meta.validation_history:
            return None
        return meta.validation_history[-1]
    
    @staticmethod
    def should_trigger_discovery(
        metadata: Dict[str, Any],
        max_attempts: int = 1
    ) -> bool:
        """
        Determine if ScrapingDog discovery should be triggered.
        
        Args:
            metadata: Current metadata dictionary
            max_attempts: Maximum discovery attempts allowed
            
        Returns:
            True if discovery should be triggered
        """
        meta = WebsiteMetadata.from_dict(metadata)
        
        # Check if already attempted ScrapingDog
        scrapingdog_attempt = meta.discovery_attempts.get("scrapingdog", {})
        if scrapingdog_attempt.get("attempted", False):
            logger.info("ScrapingDog already attempted, skipping")
            return False
        
        # Check total attempts
        attempt_count = len(meta.discovery_attempts)
        if attempt_count >= max_attempts:
            logger.info(f"Max discovery attempts ({max_attempts}) reached")
            return False
        
        return True
    
    @staticmethod
    def get_audit_summary(metadata: Dict[str, Any]) -> str:
        """
        Generate human-readable audit summary.
        
        Args:
            metadata: Current metadata dictionary
            
        Returns:
            Formatted audit summary string
        """
        meta = WebsiteMetadata.from_dict(metadata)
        
        lines = [
            f"URL Source: {meta.source}",
            f"Validation Attempts: {len(meta.validation_history)}",
            f"Discovery Attempts: {len(meta.discovery_attempts)}",
        ]
        
        if meta.validation_history:
            last = meta.validation_history[-1]
            lines.append(
                f"Last Validation: {last.get('verdict')} "
                f"({last.get('confidence', 0):.1%} confidence)"
            )
        
        if meta.discovery_attempts:
            for method, attempt in meta.discovery_attempts.items():
                lines.append(
                    f"  {method.title()}: "
                    f"found={attempt.get('found_url')}, "
                    f"valid={attempt.get('valid')}"
                )
        
        return "\n".join(lines)
