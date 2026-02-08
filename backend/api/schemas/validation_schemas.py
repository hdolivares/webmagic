"""
Pydantic schemas for website validation.

Structured data models for validation requests, responses, and results.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, Literal
from datetime import datetime


# --- LLM Validation Structures ---

class MatchSignals(BaseModel):
    """Cross-reference match signals from LLM analysis."""
    phone_match: bool = Field(description="Business phone found on website")
    address_match: bool = Field(description="Business address found on website")
    name_match: bool = Field(description="Business name found on website")
    is_directory: bool = Field(description="Website is a member directory")
    is_aggregator: bool = Field(description="Website is an aggregator/review site")


class LLMValidationResult(BaseModel):
    """Result from LLM validation stage."""
    verdict: Literal["valid", "invalid", "missing", "error"] = Field(
        description="Final LLM verdict"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score (0.0-1.0)"
    )
    reasoning: str = Field(
        description="Explanation for the verdict"
    )
    recommendation: Literal[
        "keep_url",
        "clear_url_and_mark_missing",
        "mark_invalid_keep_url"
    ] = Field(description="Action to take")
    match_signals: MatchSignals = Field(
        description="Cross-reference match indicators"
    )
    llm_model: str = Field(description="LLM model used")
    llm_tokens: int = Field(description="Total tokens consumed")
    llm_raw_response: Optional[str] = Field(
        None,
        description="Raw LLM response for debugging"
    )


# --- Pipeline Stage Results ---

class PrescreenResult(BaseModel):
    """Result from URL prescreening stage."""
    should_validate: bool = Field(
        description="Whether to proceed to Playwright"
    )
    skip_reason: Optional[str] = Field(
        None,
        description="Reason for skipping (if should_validate=False)"
    )
    recommendation: Literal[
        "skip_playwright",
        "proceed",
        "expand_url"
    ] = Field(description="Next action")


class PlaywrightResult(BaseModel):
    """Result from Playwright content extraction."""
    success: bool = Field(description="Whether extraction succeeded")
    final_url: str = Field(description="URL after redirects")
    content: Dict[str, Any] = Field(
        description="Extracted content (title, phones, emails, etc.)"
    )
    quality_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Content quality score"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if failed"
    )
    screenshot_base64: Optional[str] = Field(
        None,
        description="Screenshot (if captured)"
    )


class ValidationStages(BaseModel):
    """Results from all pipeline stages."""
    prescreen: Optional[PrescreenResult] = None
    playwright: Optional[PlaywrightResult] = None
    llm: Optional[LLMValidationResult] = None


# --- Complete Validation Result ---

class ValidationMetadata(BaseModel):
    """Metadata about validation execution."""
    timestamp: datetime = Field(description="When validation ran")
    total_duration_ms: int = Field(description="Total pipeline duration")
    pipeline_version: str = Field(description="Pipeline version")


class CompleteValidationResult(BaseModel):
    """
    Complete validation result from orchestrator.
    
    This is the final structure returned by ValidationOrchestrator
    and stored in Business.website_validation_result.
    """
    is_valid: bool = Field(description="Overall validity (True = valid)")
    verdict: Literal["valid", "invalid", "missing", "error"] = Field(
        description="Final verdict from pipeline"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in verdict"
    )
    reasoning: str = Field(description="Human-readable explanation")
    recommendation: str = Field(
        description="Recommended action (keep_url, clear_url, etc.)"
    )
    stages: ValidationStages = Field(
        description="Results from each pipeline stage"
    )
    metadata: ValidationMetadata = Field(description="Execution metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "is_valid": False,
                "verdict": "missing",
                "confidence": 0.95,
                "reasoning": "This is a Canton Chamber of Commerce member directory listing, not the business's actual website.",
                "recommendation": "clear_url_and_mark_missing",
                "stages": {
                    "prescreen": {
                        "should_validate": True,
                        "skip_reason": None,
                        "recommendation": "proceed"
                    },
                    "playwright": {
                        "success": True,
                        "final_url": "https://business.cantonchamber.org/member/dx-plumbing",
                        "content": {
                            "title": "DX Plumbing - Chamber Member",
                            "phones": [],
                            "emails": []
                        }
                    },
                    "llm": {
                        "verdict": "missing",
                        "confidence": 0.95,
                        "reasoning": "Chamber directory page, not business website",
                        "recommendation": "clear_url_and_mark_missing",
                        "match_signals": {
                            "phone_match": False,
                            "address_match": False,
                            "name_match": True,
                            "is_directory": True,
                            "is_aggregator": False
                        },
                        "llm_model": "claude-3-5-sonnet-20241022",
                        "llm_tokens": 1500
                    }
                },
                "metadata": {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "total_duration_ms": 8500,
                    "pipeline_version": "1.0.0"
                }
            }
        }


# --- API Request/Response Models ---

class ValidateWebsiteRequest(BaseModel):
    """Request to validate a specific website."""
    business_id: str = Field(description="Business UUID")
    force: bool = Field(
        default=False,
        description="Force revalidation even if recently validated"
    )


class ValidateWebsiteResponse(BaseModel):
    """Response from validation request."""
    business_id: str
    status: Literal["queued", "processing", "completed", "error"]
    task_id: Optional[str] = Field(
        None,
        description="Celery task ID (if queued)"
    )
    result: Optional[CompleteValidationResult] = Field(
        None,
        description="Validation result (if completed)"
    )


class BatchValidateRequest(BaseModel):
    """Request to validate multiple businesses."""
    business_ids: list[str] = Field(description="List of business UUIDs")
    force: bool = Field(default=False, description="Force revalidation")


class BatchValidateResponse(BaseModel):
    """Response from batch validation request."""
    total: int = Field(description="Total businesses requested")
    queued: int = Field(description="Number successfully queued")
    tasks: list[Dict[str, str]] = Field(
        description="List of {business_id, task_id}"
    )
