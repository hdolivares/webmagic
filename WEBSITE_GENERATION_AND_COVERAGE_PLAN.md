# Website Generation & Coverage Enhancement Implementation Plan

**Date:** February 4, 2026  
**Version:** 1.0  
**Status:** Planning Phase

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current System Analysis](#current-system-analysis)
3. [Requirements & Goals](#requirements--goals)
4. [Architecture Design](#architecture-design)
5. [Database Schema Enhancements](#database-schema-enhancements)
6. [Backend Services](#backend-services)
7. [Frontend Enhancements](#frontend-enhancements)
8. [Implementation Roadmap](#implementation-roadmap)
9. [Testing Strategy](#testing-strategy)

---

## 🎯 Executive Summary

This plan outlines a comprehensive enhancement to the webmagic scraping and website generation system to:

1. **Automate website generation** for businesses without websites
2. **Validate and verify website URLs** (detect PDFs, broken links, missing URLs)
3. **Enhance coverage reporting** with detailed per-zone statistics
4. **Implement comprehensive filtering** for business data

### Key Principles

- **Modular Design**: Each service has a single responsibility
- **Fail-Safe**: Validation gates prevent bad data from entering the system
- **Scalable**: Background task queues handle intensive operations
- **Observable**: Comprehensive logging and metrics at every stage

---

## 🔍 Current System Analysis

### What Works Well ✅

1. **Scraping Pipeline**
   - Successfully scrapes businesses from Outscraper
   - Normalizes data into consistent format
   - Tracks coverage in `coverage_grid` table

2. **Website Generation**
   - Full AI pipeline exists (`Analyst` → `Concept` → `Director` → `Architect`)
   - Can generate beautiful, professional websites
   - Celery background tasks for async processing

3. **Data Storage**
   - Stores raw Outscraper data in `raw_data` JSONB field
   - Tracks `website_status` and `contact_status`
   - Links businesses to coverage grids

### What's Missing ❌

1. **No Automatic Website Generation**
   - Businesses without websites are saved but not processed
   - `site_count` never increments
   - Manual intervention required for each business

2. **No Website URL Validation**
   - Invalid URLs (PDFs, images, broken links) saved as-is
   - No detection of missing websites in Google web results
   - No cross-referencing or verification

3. **Limited Coverage Reporting**
   - Per-zone statistics not displayed on frontend
   - No breakdown of qualified vs raw businesses
   - No visibility into website generation status

4. **No Advanced Filtering**
   - Can't filter businesses by website status
   - Can't filter by category, location, rating combination
   - No saved filter presets

---

## 📝 Requirements & Goals

### Functional Requirements

#### FR-1: Automated Website Detection & Generation
- **FR-1.1**: Detect businesses without `website_url` after scraping
- **FR-1.2**: Check Google web results for hidden website URLs
- **FR-1.3**: Validate existing website URLs (active, not PDF, not broken)
- **FR-1.4**: Queue businesses without valid websites for generation
- **FR-1.5**: Track generation status and increment `site_count`

#### FR-2: Website URL Validation
- **FR-2.1**: Detect invalid URL formats (PDFs, images, weird protocols)
- **FR-2.2**: Check if website is accessible (HTTP 200 response)
- **FR-2.3**: Detect placeholder/template websites
- **FR-2.4**: Cross-reference with Google web results
- **FR-2.5**: Store validation results for audit trail

#### FR-3: Enhanced Coverage Reporting
- **FR-3.1**: Display per-zone statistics on coverage page
- **FR-3.2**: Show breakdown: raw businesses, qualified, websites found, websites generated
- **FR-3.3**: Make statistics persistent (not just temporary `scrapeResult`)
- **FR-3.4**: Show zone-by-zone progress and completion status
- **FR-3.5**: Display validation failures and issues

#### FR-4: Advanced Business Filtering
- **FR-4.1**: Filter by website status (none, invalid, generated, existing)
- **FR-4.2**: Filter by location (country, state, city, zip code)
- **FR-4.3**: Filter by business attributes (category, rating, review count)
- **FR-4.4**: Combine multiple filters (AND/OR logic)
- **FR-4.5**: Save and load filter presets

### Non-Functional Requirements

- **NFR-1**: Website validation should complete in < 5 seconds per business
- **NFR-2**: Website generation queue should not exceed 1000 pending tasks
- **NFR-3**: Coverage page should load in < 2 seconds
- **NFR-4**: All background tasks should have retry logic with exponential backoff
- **NFR-5**: System should log all validation failures for debugging

---

## 🏗️ Architecture Design

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      SCRAPING WORKFLOW                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  HunterService   │ (scrapes businesses)
                    └────────┬─────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │   OutscraperClient           │
              │   - google_maps_search()     │
              │   - get_web_results()  [NEW] │
              └──────────┬───────────────────┘
                         │
                         ▼
              ┌──────────────────────────────┐
              │   BusinessService            │
              │   - create_or_update()       │
              └──────────┬───────────────────┘
                         │
                         ▼
           ┌─────────────────────────────────────────┐
           │   WebsiteValidationService [NEW]        │
           │   - validate_url()                      │
           │   - check_accessibility()               │
           │   - detect_web_results()                │
           │   - classify_url_type()                 │
           └───────────┬─────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
   [Valid Website]         [No Valid Website]
          │                         │
          │                         ▼
          │              ┌──────────────────────────┐
          │              │  WebsiteGenerationQueue  │
          │              │  (Celery Background)     │
          │              └────────┬─────────────────┘
          │                       │
          │                       ▼
          │              ┌──────────────────────────┐
          │              │  CreativeOrchestrator    │
          │              │  - generate_website()    │
          │              └────────┬─────────────────┘
          │                       │
          │                       ▼
          │              ┌──────────────────────────┐
          │              │  Update business record  │
          │              │  website_status="generated"
          │              └──────────────────────────┘
          │
          └────────────────────┬────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Update coverage_grid│
                    │  - increment site_count
                    │  - increment lead_count
                    │  - track metrics     │
                    └──────────────────────┘
```

### Service Architecture (Modular Design)

#### 1. **WebsiteValidationService** [NEW]
**Location**: `backend/services/hunter/website_validation_service.py`  
**Responsibility**: Validate and classify website URLs

```python
class WebsiteValidationService:
    """
    Validates business website URLs and detects issues.
    
    Responsibilities:
    - Check URL format and accessibility
    - Detect invalid URLs (PDFs, images, broken links)
    - Cross-reference with Google web results
    - Classify URL quality (excellent, good, poor, none, invalid)
    """
    
    async def validate_business_website(business_data: Dict) -> ValidationResult
    async def check_url_accessibility(url: str) -> AccessibilityResult
    async def detect_url_type(url: str) -> URLType
    async def fetch_google_web_results(place_id: str) -> List[str]
```

**Key Methods**:
- `validate_business_website()`: Main entry point
- `check_url_accessibility()`: HTTP HEAD request to check if URL is alive
- `detect_url_type()`: Classify URL (html, pdf, image, redirect, invalid)
- `fetch_google_web_results()`: Get web results from Outscraper or scrape directly

**Validation Logic**:
```python
ValidationResult:
  - status: "valid" | "invalid" | "missing" | "needs_generation"
  - url: str (original or discovered URL)
  - url_type: "html" | "pdf" | "image" | "redirect" | "invalid"
  - accessibility: "accessible" | "inaccessible" | "timeout"
  - web_results: List[str] (URLs from Google web results)
  - issues: List[str] (detected problems)
  - recommendation: "keep" | "replace" | "generate"
```

#### 2. **WebsiteGenerationQueueService** [NEW]
**Location**: `backend/services/hunter/website_generation_queue_service.py`  
**Responsibility**: Queue businesses for website generation

```python
class WebsiteGenerationQueueService:
    """
    Manages the queue of businesses needing website generation.
    
    Responsibilities:
    - Add businesses to generation queue
    - Track queue status and priority
    - Prevent duplicate queue entries
    - Monitor generation progress
    """
    
    async def queue_for_generation(business_id: UUID, priority: int)
    async def get_queue_status() -> QueueStatus
    async def mark_generation_started(business_id: UUID)
    async def mark_generation_completed(business_id: UUID)
```

#### 3. **CoverageReportingService** [NEW]
**Location**: `backend/services/hunter/coverage_reporting_service.py`  
**Responsibility**: Generate coverage statistics and reports

```python
class CoverageReportingService:
    """
    Generates comprehensive coverage reports and statistics.
    
    Responsibilities:
    - Aggregate coverage metrics by zone
    - Calculate qualification rates
    - Track website generation progress
    - Generate per-zone breakdowns
    """
    
    async def get_zone_statistics(zone_id: str) -> ZoneStats
    async def get_strategy_overview(strategy_id: UUID) -> StrategyOverview
    async def get_coverage_breakdown(filters: Dict) -> CoverageBreakdown
```

#### 4. **BusinessFilterService** [NEW]
**Location**: `backend/services/business_filter_service.py`  
**Responsibility**: Advanced filtering of businesses

```python
class BusinessFilterService:
    """
    Advanced filtering and querying of business data.
    
    Responsibilities:
    - Build complex filter queries
    - Support AND/OR combinations
    - Save and load filter presets
    - Export filtered results
    """
    
    async def filter_businesses(filters: FilterCriteria) -> List[Business]
    async def save_filter_preset(name: str, filters: Dict)
    async def load_filter_preset(name: str) -> FilterCriteria
```

---

## 🗄️ Database Schema Enhancements

### Modified Tables

#### 1. `businesses` table (modifications)

**Add new columns:**
```sql
-- Website validation
ALTER TABLE businesses ADD COLUMN website_validation_status VARCHAR(30);
-- Values: 'pending', 'valid', 'invalid', 'missing', 'timeout'

ALTER TABLE businesses ADD COLUMN website_validation_result JSONB;
-- Stores full ValidationResult from WebsiteValidationService

ALTER TABLE businesses ADD COLUMN website_validated_at TIMESTAMP;

ALTER TABLE businesses ADD COLUMN discovered_urls JSONB;
-- Stores URLs found in Google web results that weren't in 'site' field

-- Generation queue tracking
ALTER TABLE businesses ADD COLUMN generation_queued_at TIMESTAMP;
ALTER TABLE businesses ADD COLUMN generation_started_at TIMESTAMP;
ALTER TABLE businesses ADD COLUMN generation_completed_at TIMESTAMP;
ALTER TABLE businesses ADD COLUMN generation_attempts INTEGER DEFAULT 0;

-- Add indexes for filtering
CREATE INDEX idx_businesses_website_validation_status 
  ON businesses(website_validation_status);
CREATE INDEX idx_businesses_generation_queued 
  ON businesses(generation_queued_at) 
  WHERE website_status = 'none';
```

#### 2. `coverage_grid` table (modifications)

**Add new columns for detailed metrics:**
```sql
-- Detailed scrape metrics
ALTER TABLE coverage_grid ADD COLUMN businesses_with_websites INTEGER DEFAULT 0;
ALTER TABLE coverage_grid ADD COLUMN businesses_without_websites INTEGER DEFAULT 0;
ALTER TABLE coverage_grid ADD COLUMN invalid_websites INTEGER DEFAULT 0;
ALTER TABLE coverage_grid ADD COLUMN websites_generated INTEGER DEFAULT 0;
ALTER TABLE coverage_grid ADD COLUMN generation_in_progress INTEGER DEFAULT 0;
ALTER TABLE coverage_grid ADD COLUMN generation_failed INTEGER DEFAULT 0;

-- Validation metrics
ALTER TABLE coverage_grid ADD COLUMN validation_completed_count INTEGER DEFAULT 0;
ALTER TABLE coverage_grid ADD COLUMN validation_pending_count INTEGER DEFAULT 0;

-- Zone performance
ALTER TABLE coverage_grid ADD COLUMN avg_qualification_score NUMERIC(5,2);
ALTER TABLE coverage_grid ADD COLUMN avg_rating NUMERIC(2,1);

-- Last scrape details (for persistent display)
ALTER TABLE coverage_grid ADD COLUMN last_scrape_details JSONB;
-- Stores: {
--   "raw_businesses": 50,
--   "qualified_leads": 35,
--   "new_businesses": 30,
--   "existing_businesses": 5,
--   "with_websites": 20,
--   "without_websites": 15,
--   "invalid_websites": 5
-- }
```

#### 3. `geo_strategies` table (modifications)

**Add strategy-level aggregated metrics:**
```sql
-- Strategy-wide metrics
ALTER TABLE geo_strategies ADD COLUMN total_businesses_scraped INTEGER DEFAULT 0;
ALTER TABLE geo_strategies ADD COLUMN total_with_websites INTEGER DEFAULT 0;
ALTER TABLE geo_strategies ADD COLUMN total_without_websites INTEGER DEFAULT 0;
ALTER TABLE geo_strategies ADD COLUMN total_websites_generated INTEGER DEFAULT 0;
ALTER TABLE geo_strategies ADD COLUMN avg_businesses_per_zone NUMERIC(6,2);
ALTER TABLE geo_strategies ADD COLUMN completion_rate NUMERIC(5,2);

-- Per-zone details stored in zones JSONB array - enhance structure:
-- zones: [
--   {
--     "zone_id": "la_downtown",
--     "lat": 34.0522,
--     "lon": -118.2437,
--     "radius_km": 2.5,
--     "priority": "high",
--     "status": "completed",
--     "businesses_found": 50,
--     "qualified_leads": 35,
--     "websites_generated": 15,  // NEW
--     "scraped_at": "2026-02-04T10:30:00Z"
--   }
-- ]
```

### New Tables

#### 1. `website_validations` [NEW]
**Purpose**: Audit trail of all website validation attempts

```sql
CREATE TABLE website_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    
    -- Validation input
    url_tested VARCHAR(500),
    
    -- Validation results
    status VARCHAR(30) NOT NULL,  -- valid, invalid, missing, timeout
    url_type VARCHAR(30),  -- html, pdf, image, redirect, invalid
    accessibility VARCHAR(30),  -- accessible, inaccessible, timeout
    http_status_code INTEGER,
    response_time_ms INTEGER,
    
    -- Issues found
    issues JSONB,  -- ["redirects_to_pdf", "certificate_error", etc.]
    
    -- Web results discovered
    web_results_urls JSONB,  -- URLs found in Google web results
    recommended_url VARCHAR(500),  -- Best URL if different from url_tested
    
    -- Metadata
    validation_method VARCHAR(50),  -- http_head, full_request, external_api
    validator_version VARCHAR(20),
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_website_validations_business_id (business_id),
    INDEX idx_website_validations_status (status),
    INDEX idx_website_validations_created_at (created_at)
);
```

#### 2. `business_filter_presets` [NEW]
**Purpose**: Save user-defined filter combinations

```sql
CREATE TABLE business_filter_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
    
    -- Preset details
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Filter criteria
    filters JSONB NOT NULL,
    -- Example: {
    --   "website_status": ["none", "invalid"],
    --   "rating_min": 4.0,
    --   "location": {"state": "CA"},
    --   "category": "plumbers"
    -- }
    
    -- Usage tracking
    last_used_at TIMESTAMP,
    use_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id, name),
    INDEX idx_filter_presets_user_id (user_id)
);
```

---

## 💻 Backend Services Implementation

### Service 1: WebsiteValidationService

**File**: `backend/services/hunter/website_validation_service.py`

```python
"""
Website URL Validation Service.

Validates business website URLs, detects issues, and discovers
alternative URLs from Google web results.
"""
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

from services.hunter.scraper import OutscraperClient

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of website validation."""
    status: str  # valid, invalid, missing, needs_generation
    url: Optional[str]
    url_type: Optional[str]  # html, pdf, image, redirect, invalid
    accessibility: str  # accessible, inaccessible, timeout
    http_status_code: Optional[int]
    response_time_ms: Optional[int]
    issues: List[str]
    web_results_urls: List[str]
    recommended_url: Optional[str]
    recommendation: str  # keep, replace, generate


class WebsiteValidationService:
    """
    Validates business website URLs.
    
    Key Features:
    - HTTP HEAD requests to check accessibility
    - Content-Type detection (HTML vs PDF vs image)
    - Google web results cross-reference
    - Invalid URL pattern detection
    - Timeout and error handling
    """
    
    # Invalid URL patterns
    INVALID_PATTERNS = [
        r'\.pdf$',
        r'\.jpg$',
        r'\.png$',
        r'\.gif$',
        r'^file://',
        r'^ftp://',
    ]
    
    # Suspicious domain patterns
    SUSPICIOUS_DOMAINS = [
        'facebook.com',
        'instagram.com',
        'linkedin.com',
        'twitter.com',
        'google.com',
        'maps.google.com',
    ]
    
    def __init__(self, outscraper_client: OutscraperClient):
        self.outscraper = outscraper_client
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5),
            headers={'User-Agent': 'WebMagic/1.0 (Website Validator)'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def validate_business_website(
        self,
        business_data: Dict[str, Any],
        check_web_results: bool = True
    ) -> ValidationResult:
        """
        Main validation entry point.
        
        Args:
            business_data: Business data dict with website_url, gmb_place_id
            check_web_results: Whether to check Google web results
            
        Returns:
            ValidationResult with all findings
        """
        url = business_data.get('website_url')
        place_id = business_data.get('gmb_place_id')
        
        issues = []
        web_results_urls = []
        
        # STEP 1: Check if URL exists
        if not url or url.strip() == '':
            logger.info(f"No website URL for business: {business_data.get('name')}")
            
            # Check web results for hidden URL
            if check_web_results and place_id:
                web_results_urls = await self.fetch_google_web_results(place_id)
                if web_results_urls:
                    issues.append("url_missing_but_found_in_web_results")
                    return ValidationResult(
                        status='missing',
                        url=None,
                        url_type=None,
                        accessibility='not_checked',
                        http_status_code=None,
                        response_time_ms=None,
                        issues=issues,
                        web_results_urls=web_results_urls,
                        recommended_url=web_results_urls[0],
                        recommendation='replace'
                    )
            
            return ValidationResult(
                status='missing',
                url=None,
                url_type=None,
                accessibility='not_checked',
                http_status_code=None,
                response_time_ms=None,
                issues=['no_url_provided'],
                web_results_urls=[],
                recommended_url=None,
                recommendation='generate'
            )
        
        # STEP 2: Validate URL format
        url_type = self._detect_url_type(url)
        if url_type in ['pdf', 'image']:
            issues.append(f"url_is_{url_type}")
            return ValidationResult(
                status='invalid',
                url=url,
                url_type=url_type,
                accessibility='not_checked',
                http_status_code=None,
                response_time_ms=None,
                issues=issues,
                web_results_urls=[],
                recommended_url=None,
                recommendation='generate'
            )
        
        # STEP 3: Check if URL is suspicious (social media, etc.)
        if self._is_suspicious_domain(url):
            issues.append('suspicious_domain')
        
        # STEP 4: Check accessibility
        accessibility_result = await self.check_url_accessibility(url)
        
        if accessibility_result['accessible']:
            # URL is valid and accessible
            return ValidationResult(
                status='valid',
                url=url,
                url_type=accessibility_result.get('content_type', 'html'),
                accessibility='accessible',
                http_status_code=accessibility_result['status_code'],
                response_time_ms=accessibility_result['response_time_ms'],
                issues=issues,
                web_results_urls=[],
                recommended_url=url,
                recommendation='keep'
            )
        else:
            # URL is inaccessible
            issues.append(accessibility_result.get('error', 'inaccessible'))
            
            # Check web results for alternative
            if check_web_results and place_id:
                web_results_urls = await self.fetch_google_web_results(place_id)
            
            return ValidationResult(
                status='invalid',
                url=url,
                url_type=url_type,
                accessibility=accessibility_result['accessibility'],
                http_status_code=accessibility_result.get('status_code'),
                response_time_ms=accessibility_result.get('response_time_ms'),
                issues=issues,
                web_results_urls=web_results_urls,
                recommended_url=web_results_urls[0] if web_results_urls else None,
                recommendation='replace' if web_results_urls else 'generate'
            )
    
    async def check_url_accessibility(self, url: str) -> Dict[str, Any]:
        """
        Check if URL is accessible via HTTP HEAD request.
        
        Returns:
            Dict with accessible, status_code, response_time_ms, error
        """
        start_time = datetime.utcnow()
        
        try:
            # Try HEAD request first (faster)
            async with self.session.head(url, allow_redirects=True) as response:
                response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                # Check status code
                if 200 <= response.status < 400:
                    content_type = response.headers.get('Content-Type', '')
                    return {
                        'accessible': True,
                        'status_code': response.status,
                        'response_time_ms': response_time_ms,
                        'content_type': self._parse_content_type(content_type),
                        'accessibility': 'accessible'
                    }
                else:
                    return {
                        'accessible': False,
                        'status_code': response.status,
                        'response_time_ms': response_time_ms,
                        'error': f'http_status_{response.status}',
                        'accessibility': 'inaccessible'
                    }
        
        except asyncio.TimeoutError:
            return {
                'accessible': False,
                'error': 'timeout',
                'accessibility': 'timeout'
            }
        except aiohttp.ClientError as e:
            return {
                'accessible': False,
                'error': f'client_error_{type(e).__name__}',
                'accessibility': 'inaccessible'
            }
        except Exception as e:
            logger.error(f"Unexpected error checking URL {url}: {str(e)}")
            return {
                'accessible': False,
                'error': 'unknown_error',
                'accessibility': 'inaccessible'
            }
    
    def _detect_url_type(self, url: str) -> str:
        """
        Detect URL type from extension or pattern.
        
        Returns:
            'html', 'pdf', 'image', 'redirect', 'invalid'
        """
        import re
        
        url_lower = url.lower()
        
        # Check for file extensions
        if url_lower.endswith('.pdf'):
            return 'pdf'
        elif url_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            return 'image'
        elif url_lower.endswith(('.zip', '.rar', '.tar', '.gz')):
            return 'archive'
        
        # Check for invalid protocols
        parsed = urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            return 'invalid'
        
        return 'html'
    
    def _is_suspicious_domain(self, url: str) -> bool:
        """Check if domain is suspicious (social media, etc.)."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        for suspicious in self.SUSPICIOUS_DOMAINS:
            if suspicious in domain:
                return True
        return False
    
    def _parse_content_type(self, content_type: str) -> str:
        """Parse Content-Type header to simple type."""
        if 'text/html' in content_type:
            return 'html'
        elif 'application/pdf' in content_type:
            return 'pdf'
        elif 'image/' in content_type:
            return 'image'
        else:
            return 'other'
    
    async def fetch_google_web_results(self, place_id: str) -> List[str]:
        """
        Fetch web results URLs for a business from Google.
        
        NOTE: Outscraper doesn't directly provide web results in the
        google_maps_search API. We may need to:
        1. Use a separate Outscraper endpoint if available
        2. Scrape Google Maps directly (risky)
        3. Use Google Custom Search API
        
        For now, returning empty list - to be implemented.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            List of discovered URLs
        """
        # TODO: Implement web results fetching
        # Options:
        # 1. Check if Outscraper provides this in raw_data
        # 2. Use Google Custom Search API
        # 3. Direct scraping (last resort)
        
        logger.warning("Web results fetching not yet implemented")
        return []
```

### Service 2: WebsiteGenerationQueueService

**File**: `backend/services/hunter/website_generation_queue_service.py`

```python
"""
Website Generation Queue Service.

Manages queueing businesses for website generation and tracks status.
"""
import logging
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from models.business import Business
from tasks.generation import generate_site_for_business

logger = logging.getLogger(__name__)


class WebsiteGenerationQueueService:
    """
    Manages the website generation queue.
    
    Responsibilities:
    - Queue businesses for generation
    - Prevent duplicate queue entries
    - Track generation status
    - Provide queue statistics
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def queue_for_generation(
        self,
        business_id: UUID,
        priority: int = 5
    ) -> Dict[str, any]:
        """
        Queue a business for website generation.
        
        Args:
            business_id: Business UUID
            priority: Task priority (1-10, higher = more important)
            
        Returns:
            Dict with status and task_id
        """
        # Check if business exists
        result = await self.db.execute(
            select(Business).where(Business.id == business_id)
        )
        business = result.scalar_one_or_none()
        
        if not business:
            return {'status': 'error', 'message': 'Business not found'}
        
        # Check if already queued or in progress
        if business.generation_queued_at and not business.generation_completed_at:
            logger.info(f"Business {business_id} already queued for generation")
            return {
                'status': 'already_queued',
                'queued_at': business.generation_queued_at
            }
        
        # Check if already has generated website
        if business.website_status == 'generated':
            logger.info(f"Business {business_id} already has generated website")
            return {
                'status': 'already_generated',
                'website_status': business.website_status
            }
        
        # Update business record
        business.generation_queued_at = datetime.utcnow()
        business.generation_attempts = (business.generation_attempts or 0) + 1
        business.website_status = 'queued'
        
        await self.db.commit()
        
        # Queue Celery task
        task = generate_site_for_business.apply_async(
            args=[str(business_id)],
            priority=priority
        )
        
        logger.info(f"Queued business {business_id} for generation (task: {task.id})")
        
        return {
            'status': 'queued',
            'business_id': str(business_id),
            'task_id': task.id,
            'priority': priority
        }
    
    async def queue_multiple(
        self,
        business_ids: List[UUID],
        priority: int = 5
    ) -> Dict[str, any]:
        """
        Queue multiple businesses for generation.
        
        Returns:
            Dict with queued count and task_ids
        """
        results = []
        for business_id in business_ids:
            result = await self.queue_for_generation(business_id, priority)
            results.append(result)
        
        queued_count = sum(1 for r in results if r['status'] == 'queued')
        
        return {
            'total': len(business_ids),
            'queued': queued_count,
            'results': results
        }
    
    async def get_queue_status(self) -> Dict[str, any]:
        """
        Get current queue status.
        
        Returns:
            Dict with queue statistics
        """
        # Count businesses in queue
        queued_result = await self.db.execute(
            select(Business).where(
                and_(
                    Business.website_status == 'queued',
                    Business.generation_completed_at.is_(None)
                )
            )
        )
        queued_count = len(queued_result.scalars().all())
        
        # Count in progress
        in_progress_result = await self.db.execute(
            select(Business).where(
                and_(
                    Business.website_status == 'generating',
                    Business.generation_completed_at.is_(None)
                )
            )
        )
        in_progress_count = len(in_progress_result.scalars().all())
        
        # Count completed today
        from datetime import date
        today_start = datetime.combine(date.today(), datetime.min.time())
        
        completed_result = await self.db.execute(
            select(Business).where(
                Business.generation_completed_at >= today_start
            )
        )
        completed_today_count = len(completed_result.scalars().all())
        
        return {
            'queued': queued_count,
            'in_progress': in_progress_count,
            'completed_today': completed_today_count
        }
```

### Service 3: CoverageReportingService

**File**: `backend/services/hunter/coverage_reporting_service.py`

```python
"""
Coverage Reporting Service.

Generates comprehensive coverage statistics and reports.
"""
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from models.coverage import CoverageGrid
from models.business import Business
from models.geo_strategy import GeoStrategy

logger = logging.getLogger(__name__)


class CoverageReportingService:
    """
    Generates coverage reports and statistics.
    
    Provides comprehensive breakdowns of scraping results,
    qualification rates, and website generation progress.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_zone_statistics(self, zone_id: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a specific zone.
        
        Returns:
            Dict with all zone metrics
        """
        # Get coverage entry
        result = await self.db.execute(
            select(CoverageGrid).where(CoverageGrid.zone_id == zone_id)
        )
        coverage = result.scalar_one_or_none()
        
        if not coverage:
            return {'error': 'Zone not found'}
        
        # Get businesses for this zone
        businesses_result = await self.db.execute(
            select(Business).where(Business.coverage_grid_id == coverage.id)
        )
        businesses = businesses_result.scalars().all()
        
        # Calculate statistics
        total_businesses = len(businesses)
        with_websites = sum(1 for b in businesses if b.website_url)
        without_websites = total_businesses - with_websites
        websites_generated = sum(
            1 for b in businesses 
            if b.website_status == 'generated'
        )
        generation_in_progress = sum(
            1 for b in businesses 
            if b.website_status in ['queued', 'generating']
        )
        
        return {
            'zone_id': zone_id,
            'coverage_id': str(coverage.id),
            'status': coverage.status,
            'total_businesses': total_businesses,
            'qualified_leads': coverage.qualified_count,
            'with_websites': with_websites,
            'without_websites': without_websites,
            'websites_generated': websites_generated,
            'generation_in_progress': generation_in_progress,
            'last_scraped_at': coverage.last_scraped_at,
            'last_scrape_details': coverage.last_scrape_details,
            'avg_rating': float(coverage.avg_rating) if coverage.avg_rating else None,
            'avg_qualification_score': float(coverage.avg_qualification_score) if coverage.avg_qualification_score else None
        }
    
    async def get_strategy_overview(self, strategy_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive overview of a geo-strategy.
        
        Returns:
            Dict with strategy-wide statistics
        """
        # Get strategy
        result = await self.db.execute(
            select(GeoStrategy).where(GeoStrategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            return {'error': 'Strategy not found'}
        
        # Get all coverage entries for this strategy
        coverage_result = await self.db.execute(
            select(CoverageGrid).where(
                and_(
                    CoverageGrid.city == strategy.city,
                    CoverageGrid.state == strategy.state,
                    CoverageGrid.industry == strategy.category
                )
            )
        )
        coverage_entries = coverage_result.scalars().all()
        
        # Aggregate statistics
        total_zones = len(strategy.zones)
        zones_completed = sum(1 for zone in strategy.zones if zone.get('status') == 'completed')
        zones_in_progress = sum(1 for zone in strategy.zones if zone.get('status') == 'in_progress')
        zones_pending = total_zones - zones_completed - zones_in_progress
        
        total_businesses = sum(c.lead_count for c in coverage_entries)
        total_qualified = sum(c.qualified_count for c in coverage_entries)
        total_with_websites = sum(c.businesses_with_websites or 0 for c in coverage_entries)
        total_without_websites = sum(c.businesses_without_websites or 0 for c in coverage_entries)
        total_websites_generated = sum(c.websites_generated or 0 for c in coverage_entries)
        
        # Per-zone breakdown
        zone_details = []
        for zone in strategy.zones:
            zone_id = zone.get('zone_id')
            zone_stats = await self.get_zone_statistics(zone_id)
            zone_details.append(zone_stats)
        
        return {
            'strategy_id': str(strategy_id),
            'city': strategy.city,
            'state': strategy.state,
            'category': strategy.category,
            'status': strategy.status,
            'zones': {
                'total': total_zones,
                'completed': zones_completed,
                'in_progress': zones_in_progress,
                'pending': zones_pending
            },
            'businesses': {
                'total': total_businesses,
                'qualified': total_qualified,
                'with_websites': total_with_websites,
                'without_websites': total_without_websites,
                'websites_generated': total_websites_generated,
                'generation_pending': total_without_websites - total_websites_generated
            },
            'zone_details': zone_details
        }
```

### Service 4: BusinessFilterService

**File**: `backend/services/business_filter_service.py`

```python
"""
Business Filter Service.

Advanced filtering and querying of business data with support for
complex filter combinations and saved presets.
"""
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from dataclasses import dataclass

from models.business import Business
from models.business_filter_preset import BusinessFilterPreset

logger = logging.getLogger(__name__)


@dataclass
class FilterCriteria:
    """Filter criteria for business queries."""
    # Website filters
    website_status: Optional[List[str]] = None  # ['none', 'generated', etc.]
    website_validation_status: Optional[List[str]] = None
    has_website: Optional[bool] = None
    
    # Location filters
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    zip_codes: Optional[List[str]] = None
    
    # Business attributes
    categories: Optional[List[str]] = None
    min_rating: Optional[float] = None
    max_rating: Optional[float] = None
    min_review_count: Optional[int] = None
    min_qualification_score: Optional[int] = None
    
    # Dates
    scraped_after: Optional[str] = None
    scraped_before: Optional[str] = None
    
    # Pagination
    limit: int = 50
    offset: int = 0
    
    # Sorting
    order_by: str = 'scraped_at'
    order_direction: str = 'desc'


class BusinessFilterService:
    """
    Advanced business filtering and querying.
    
    Supports complex filter combinations with AND/OR logic,
    saved filter presets, and efficient querying.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def filter_businesses(
        self,
        filters: FilterCriteria
    ) -> Dict[str, Any]:
        """
        Filter businesses based on criteria.
        
        Returns:
            Dict with businesses list and total count
        """
        # Build query
        query = select(Business)
        conditions = []
        
        # Website filters
        if filters.website_status:
            conditions.append(Business.website_status.in_(filters.website_status))
        
        if filters.website_validation_status:
            conditions.append(
                Business.website_validation_status.in_(filters.website_validation_status)
            )
        
        if filters.has_website is not None:
            if filters.has_website:
                conditions.append(Business.website_url.isnot(None))
            else:
                conditions.append(Business.website_url.is_(None))
        
        # Location filters
        if filters.country:
            conditions.append(Business.country == filters.country)
        if filters.state:
            conditions.append(Business.state == filters.state)
        if filters.city:
            conditions.append(Business.city == filters.city)
        if filters.zip_codes:
            conditions.append(Business.zip_code.in_(filters.zip_codes))
        
        # Business attributes
        if filters.categories:
            conditions.append(Business.category.in_(filters.categories))
        if filters.min_rating:
            conditions.append(Business.rating >= filters.min_rating)
        if filters.max_rating:
            conditions.append(Business.rating <= filters.max_rating)
        if filters.min_review_count:
            conditions.append(Business.review_count >= filters.min_review_count)
        if filters.min_qualification_score:
            conditions.append(
                Business.qualification_score >= filters.min_qualification_score
            )
        
        # Date filters
        if filters.scraped_after:
            conditions.append(Business.scraped_at >= filters.scraped_after)
        if filters.scraped_before:
            conditions.append(Business.scraped_at <= filters.scraped_before)
        
        # Apply conditions
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count()).select_from(Business)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        # Apply sorting
        if filters.order_direction == 'desc':
            query = query.order_by(getattr(Business, filters.order_by).desc())
        else:
            query = query.order_by(getattr(Business, filters.order_by).asc())
        
        # Apply pagination
        query = query.limit(filters.limit).offset(filters.offset)
        
        # Execute query
        result = await self.db.execute(query)
        businesses = result.scalars().all()
        
        return {
            'businesses': businesses,
            'total': total,
            'page': filters.offset // filters.limit + 1,
            'page_size': filters.limit,
            'pages': (total + filters.limit - 1) // filters.limit
        }
    
    async def save_filter_preset(
        self,
        user_id: UUID,
        name: str,
        filters: Dict[str, Any],
        description: Optional[str] = None
    ) -> BusinessFilterPreset:
        """
        Save a filter preset for reuse.
        """
        preset = BusinessFilterPreset(
            user_id=user_id,
            name=name,
            description=description,
            filters=filters
        )
        
        self.db.add(preset)
        await self.db.commit()
        await self.db.refresh(preset)
        
        logger.info(f"Saved filter preset: {name} for user {user_id}")
        
        return preset
    
    async def load_filter_preset(
        self,
        user_id: UUID,
        preset_name: str
    ) -> Optional[BusinessFilterPreset]:
        """
        Load a saved filter preset.
        """
        result = await self.db.execute(
            select(BusinessFilterPreset).where(
                and_(
                    BusinessFilterPreset.user_id == user_id,
                    BusinessFilterPreset.name == preset_name
                )
            )
        )
        preset = result.scalar_one_or_none()
        
        if preset:
            # Update usage tracking
            preset.last_used_at = datetime.utcnow()
            preset.use_count += 1
            await self.db.commit()
        
        return preset
    
    async def list_filter_presets(self, user_id: UUID) -> List[BusinessFilterPreset]:
        """
        List all filter presets for a user.
        """
        result = await self.db.execute(
            select(BusinessFilterPreset)
            .where(BusinessFilterPreset.user_id == user_id)
            .order_by(BusinessFilterPreset.last_used_at.desc())
        )
        return result.scalars().all()
```

---

## 🎨 Frontend Enhancements

### CSS Design System (Semantic Variables)

**File**: `frontend/src/styles/coverage-system.css`

```css
/* Coverage System CSS Variables */
:root {
  /* Colors - Status */
  --coverage-status-pending: #94a3b8;
  --coverage-status-in-progress: #3b82f6;
  --coverage-status-completed: #22c55e;
  --coverage-status-failed: #ef4444;
  
  /* Colors - Website Status */
  --website-status-none: #f59e0b;
  --website-status-valid: #22c55e;
  --website-status-invalid: #ef4444;
  --website-status-generating: #3b82f6;
  --website-status-generated: #8b5cf6;
  
  /* Spacing */
  --coverage-card-padding: 1.5rem;
  --coverage-card-gap: 1rem;
  --coverage-section-gap: 2rem;
  
  /* Typography */
  --coverage-heading-size: 1.5rem;
  --coverage-subheading-size: 1.125rem;
  --coverage-metric-value-size: 2rem;
  --coverage-metric-label-size: 0.875rem;
  
  /* Borders */
  --coverage-card-border-radius: 0.75rem;
  --coverage-badge-border-radius: 0.375rem;
  
  /* Shadows */
  --coverage-card-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
  --coverage-card-shadow-hover: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  
  /* Transitions */
  --coverage-transition-speed: 200ms;
}

/* Zone Statistics Card */
.zone-stats-card {
  background: white;
  border-radius: var(--coverage-card-border-radius);
  padding: var(--coverage-card-padding);
  box-shadow: var(--coverage-card-shadow);
  transition: box-shadow var(--coverage-transition-speed);
}

.zone-stats-card:hover {
  box-shadow: var(--coverage-card-shadow-hover);
}

.zone-stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--coverage-card-gap);
}

.zone-stats-title {
  font-size: var(--coverage-heading-size);
  font-weight: 600;
  color: #1e293b;
}

.zone-status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: var(--coverage-badge-border-radius);
  font-size: 0.875rem;
  font-weight: 500;
}

.zone-status-badge.pending {
  background: var(--coverage-status-pending);
  color: white;
}

.zone-status-badge.in-progress {
  background: var(--coverage-status-in-progress);
  color: white;
}

.zone-status-badge.completed {
  background: var(--coverage-status-completed);
  color: white;
}

/* Metrics Grid */
.zone-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--coverage-card-gap);
  margin-top: var(--coverage-card-gap);
}

.metric-card {
  background: #f8fafc;
  border-radius: var(--coverage-badge-border-radius);
  padding: 1rem;
  text-align: center;
}

.metric-value {
  font-size: var(--coverage-metric-value-size);
  font-weight: 700;
  color: #0f172a;
  line-height: 1;
}

.metric-label {
  font-size: var(--coverage-metric-label-size);
  color: #64748b;
  margin-top: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Website Status Colors */
.metric-card.website-none .metric-value {
  color: var(--website-status-none);
}

.metric-card.website-valid .metric-value {
  color: var(--website-status-valid);
}

.metric-card.website-invalid .metric-value {
  color: var(--website-status-invalid);
}

.metric-card.website-generating .metric-value {
  color: var(--website-status-generating);
}

.metric-card.website-generated .metric-value {
  color: var(--website-status-generated);
}

/* Breakdown Section */
.coverage-breakdown {
  margin-top: var(--coverage-section-gap);
}

.breakdown-title {
  font-size: var(--coverage-subheading-size);
  font-weight: 600;
  color: #1e293b;
  margin-bottom: var(--coverage-card-gap);
}

.breakdown-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.breakdown-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #f8fafc;
  border-radius: var(--coverage-badge-border-radius);
}

.breakdown-item-label {
  font-size: 0.9375rem;
  color: #475569;
}

.breakdown-item-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: #0f172a;
}

/* Progress Bar */
.coverage-progress {
  margin-top: var(--coverage-card-gap);
}

.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.progress-bar {
  height: 0.5rem;
  background: #e2e8f0;
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  transition: width var(--coverage-transition-speed) ease-in-out;
}
```

### React Components

#### Component 1: ZoneStatisticsCard

**File**: `frontend/src/components/coverage/ZoneStatisticsCard.tsx`

```typescript
import React from 'react';
import './coverage-system.css';

interface ZoneStatistics {
  zone_id: string;
  status: string;
  total_businesses: number;
  qualified_leads: number;
  with_websites: number;
  without_websites: number;
  websites_generated: number;
  generation_in_progress: number;
  last_scraped_at: string;
  avg_rating: number;
}

interface ZoneStatisticsCardProps {
  stats: ZoneStatistics;
  onGenerateWebsites?: (zoneId: string) => void;
}

export function ZoneStatisticsCard({ stats, onGenerateWebsites }: ZoneStatisticsCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'completed';
      case 'in_progress': return 'in-progress';
      default: return 'pending';
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const websiteGeneration Percentage = stats.without_websites > 0
    ? (stats.websites_generated / stats.without_websites) * 100
    : 0;

  return (
    <div className="zone-stats-card">
      {/* Header */}
      <div className="zone-stats-header">
        <h3 className="zone-stats-title">📍 {stats.zone_id}</h3>
        <span className={`zone-status-badge ${getStatusColor(stats.status)}`}>
          {stats.status}
        </span>
      </div>

      {/* Last Scraped */}
      <div className="zone-stats-meta">
        <span className="text-sm text-gray-600">
          Last scraped: {formatDate(stats.last_scraped_at)}
        </span>
      </div>

      {/* Main Metrics Grid */}
      <div className="zone-metrics-grid">
        <div className="metric-card">
          <div className="metric-value">{stats.total_businesses}</div>
          <div className="metric-label">Total Businesses</div>
        </div>

        <div className="metric-card">
          <div className="metric-value">{stats.qualified_leads}</div>
          <div className="metric-label">Qualified Leads</div>
        </div>

        <div className="metric-card website-valid">
          <div className="metric-value">{stats.with_websites}</div>
          <div className="metric-label">With Websites</div>
        </div>

        <div className="metric-card website-none">
          <div className="metric-value">{stats.without_websites}</div>
          <div className="metric-label">Without Websites</div>
        </div>

        <div className="metric-card website-generated">
          <div className="metric-value">{stats.websites_generated}</div>
          <div className="metric-label">Sites Generated</div>
        </div>

        <div className="metric-card website-generating">
          <div className="metric-value">{stats.generation_in_progress}</div>
          <div className="metric-label">In Progress</div>
        </div>

        {stats.avg_rating && (
          <div className="metric-card">
            <div className="metric-value">{stats.avg_rating.toFixed(1)} ⭐</div>
            <div className="metric-label">Avg Rating</div>
          </div>
        )}
      </div>

      {/* Website Generation Progress */}
      {stats.without_websites > 0 && (
        <div className="coverage-progress">
          <div className="progress-label">
            <span>Website Generation Progress</span>
            <span>{websiteGenerationPercentage.toFixed(0)}%</span>
          </div>
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${websiteGenerationPercentage}%` }}
            />
          </div>
        </div>
      )}

      {/* Action Button */}
      {stats.without_websites > stats.websites_generated && (
        <button
          onClick={() => onGenerateWebsites?.(stats.zone_id)}
          className="mt-4 w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
        >
          🎨 Generate {stats.without_websites - stats.websites_generated} Websites
        </button>
      )}
    </div>
  );
}
```

#### Component 2: CoverageBreakdownPanel

**File**: `frontend/src/components/coverage/CoverageBreakdownPanel.tsx`

```typescript
import React from 'react';
import './coverage-system.css';

interface CoverageBreakdown {
  total_businesses: number;
  qualified_leads: number;
  with_websites: number;
  without_websites: number;
  websites_generated: number;
  invalid_websites: number;
  generation_pending: number;
}

interface CoverageBreakdownPanelProps {
  breakdown: CoverageBreakdown;
}

export function CoverageBreakdownPanel({ breakdown }: CoverageBreakdownPanelProps) {
  const qualificationRate = breakdown.total_businesses > 0
    ? (breakdown.qualified_leads / breakdown.total_businesses) * 100
    : 0;

  const websiteRate = breakdown.total_businesses > 0
    ? (breakdown.with_websites / breakdown.total_businesses) * 100
    : 0;

  return (
    <div className="zone-stats-card">
      <h3 className="breakdown-title">📊 Coverage Breakdown</h3>

      <div className="breakdown-list">
        {/* Total Businesses */}
        <div className="breakdown-item">
          <span className="breakdown-item-label">📋 Total Businesses Scraped</span>
          <span className="breakdown-item-value">{breakdown.total_businesses}</span>
        </div>

        {/* Qualification */}
        <div className="breakdown-item">
          <span className="breakdown-item-label">
            ✅ Qualified Leads ({qualificationRate.toFixed(1)}%)
          </span>
          <span className="breakdown-item-value">{breakdown.qualified_leads}</span>
        </div>

        {/* Websites */}
        <div className="breakdown-item">
          <span className="breakdown-item-label">
            🌐 With Websites ({websiteRate.toFixed(1)}%)
          </span>
          <span className="breakdown-item-value">{breakdown.with_websites}</span>
        </div>

        <div className="breakdown-item">
          <span className="breakdown-item-label">🚫 Without Websites</span>
          <span className="breakdown-item-value">{breakdown.without_websites}</span>
        </div>

        {breakdown.invalid_websites > 0 && (
          <div className="breakdown-item">
            <span className="breakdown-item-label">⚠️ Invalid Websites (PDF, broken, etc.)</span>
            <span className="breakdown-item-value">{breakdown.invalid_websites}</span>
          </div>
        )}

        {/* Generation Status */}
        <div className="breakdown-item" style={{ background: '#f0fdf4', borderLeft: '4px solid #22c55e' }}>
          <span className="breakdown-item-label">✨ Websites Generated</span>
          <span className="breakdown-item-value" style={{ color: '#22c55e' }}>
            {breakdown.websites_generated}
          </span>
        </div>

        {breakdown.generation_pending > 0 && (
          <div className="breakdown-item" style={{ background: '#fef3c7', borderLeft: '4px solid #f59e0b' }}>
            <span className="breakdown-item-label">⏳ Generation Pending</span>
            <span className="breakdown-item-value" style={{ color: '#f59e0b' }}>
              {breakdown.generation_pending}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
```

#### Component 3: BusinessFilterPanel

**File**: `frontend/src/components/businesses/BusinessFilterPanel.tsx`

```typescript
import React, { useState } from 'react';

interface FilterCriteria {
  website_status: string[];
  has_website: boolean | null;
  state: string;
  city: string;
  min_rating: number | null;
  categories: string[];
}

interface BusinessFilterPanelProps {
  onFilterChange: (filters: FilterCriteria) => void;
  onSavePreset?: (name: string, filters: FilterCriteria) => void;
  savedPresets?: Array<{ name: string; filters: FilterCriteria }>;
}

export function BusinessFilterPanel({ 
  onFilterChange, 
  onSavePreset,
  savedPresets = []
}: BusinessFilterPanelProps) {
  const [filters, setFilters] = useState<FilterCriteria>({
    website_status: [],
    has_website: null,
    state: '',
    city: '',
    min_rating: null,
    categories: []
  });

  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [presetName, setPresetName] = useState('');

  const handleFilterChange = (key: keyof FilterCriteria, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleWebsiteStatusToggle = (status: string) => {
    const currentStatuses = filters.website_status;
    const newStatuses = currentStatuses.includes(status)
      ? currentStatuses.filter(s => s !== status)
      : [...currentStatuses, status];
    
    handleFilterChange('website_status', newStatuses);
  };

  const handleSavePreset = () => {
    if (presetName && onSavePreset) {
      onSavePreset(presetName, filters);
      setShowSaveDialog(false);
      setPresetName('');
    }
  };

  const handleLoadPreset = (preset: { name: string; filters: FilterCriteria }) => {
    setFilters(preset.filters);
    onFilterChange(preset.filters);
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">🔍 Filter Businesses</h3>
        <button
          onClick={() => setShowSaveDialog(true)}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          💾 Save Preset
        </button>
      </div>

      {/* Saved Presets */}
      {savedPresets.length > 0 && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Quick Presets
          </label>
          <div className="flex gap-2 flex-wrap">
            {savedPresets.map((preset) => (
              <button
                key={preset.name}
                onClick={() => handleLoadPreset(preset)}
                className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-full"
              >
                {preset.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Website Status Filter */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Website Status
        </label>
        <div className="flex flex-wrap gap-2">
          {[
            { value: 'none', label: '🚫 No Website', color: 'orange' },
            { value: 'invalid', label: '⚠️ Invalid', color: 'red' },
            { value: 'valid', label: '✅ Valid', color: 'green' },
            { value: 'generated', label: '✨ Generated', color: 'purple' }
          ].map(({ value, label, color }) => (
            <button
              key={value}
              onClick={() => handleWebsiteStatusToggle(value)}
              className={`px-4 py-2 rounded-lg border-2 transition-all ${
                filters.website_status.includes(value)
                  ? `bg-${color}-100 border-${color}-500 text-${color}-700`
                  : 'bg-white border-gray-300 text-gray-700 hover:border-gray-400'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Quick Filter: Businesses Without Websites */}
      <div className="mb-4">
        <button
          onClick={() => handleFilterChange('website_status', ['none', 'invalid'])}
          className="w-full px-4 py-3 bg-orange-50 border-2 border-orange-300 text-orange-700 rounded-lg hover:bg-orange-100 font-medium"
        >
          🎯 Show All Businesses Without Websites
        </button>
      </div>

      {/* Location Filters */}
      <div className="mb-4 grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            State
          </label>
          <input
            type="text"
            value={filters.state}
            onChange={(e) => handleFilterChange('state', e.target.value)}
            placeholder="CA, NY, TX..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            City
          </label>
          <input
            type="text"
            value={filters.city}
            onChange={(e) => handleFilterChange('city', e.target.value)}
            placeholder="Los Angeles..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Rating Filter */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Minimum Rating
        </label>
        <input
          type="number"
          min="0"
          max="5"
          step="0.1"
          value={filters.min_rating || ''}
          onChange={(e) => handleFilterChange('min_rating', parseFloat(e.target.value) || null)}
          placeholder="4.0"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Save Preset Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96">
            <h4 className="text-lg font-semibold mb-4">Save Filter Preset</h4>
            <input
              type="text"
              value={presetName}
              onChange={(e) => setPresetName(e.target.value)}
              placeholder="e.g., LA Plumbers Without Websites"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4"
            />
            <div className="flex gap-2">
              <button
                onClick={handleSavePreset}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Save
              </button>
              <button
                onClick={() => setShowSaveDialog(false)}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## 📅 Implementation Roadmap

### Phase 1: Foundation (Week 1)

**Goal**: Set up infrastructure for website validation and generation queue

**Tasks**:
1. **Database Migrations** (Day 1-2)
   - Create migration scripts for new columns in `businesses`, `coverage_grid`, `geo_strategies`
   - Create `website_validations` and `business_filter_presets` tables
   - Run migrations on production database
   - Verify schema changes

2. **WebsiteValidationService** (Day 3-4)
   - Implement URL accessibility checking
   - Implement URL type detection
   - Add validation logging
   - Write unit tests

3. **WebsiteGenerationQueueService** (Day 5)
   - Implement queue management
   - Add queue status tracking
   - Integrate with existing Celery tasks
   - Write unit tests

**Deliverables**:
- ✅ Database schema updated
- ✅ WebsiteValidationService fully functional
- ✅ Generation queue system operational
- ✅ Unit tests passing

---

### Phase 2: Integration (Week 2)

**Goal**: Integrate validation and generation into scraping workflow

**Tasks**:
1. **Modify HunterService** (Day 1-2)
   - Add validation step after business creation
   - Queue businesses without websites for generation
   - Update `coverage_grid` metrics
   - Add comprehensive logging

2. **Update BusinessService** (Day 2-3)
   - Add validation result storage
   - Track generation queue status
   - Handle validation failures gracefully

3. **Enhance CoverageService** (Day 3-4)
   - Update metrics tracking
   - Store last_scrape_details JSONB
   - Calculate aggregated statistics

4. **Testing & Debugging** (Day 5)
   - End-to-end testing of scraping → validation → generation flow
   - Fix bugs and edge cases
   - Performance optimization

**Deliverables**:
- ✅ Automated validation integrated
- ✅ Automated generation queuing
- ✅ Metrics accurately tracked
- ✅ Integration tests passing

---

### Phase 3: Reporting (Week 3)

**Goal**: Build comprehensive coverage reporting UI

**Tasks**:
1. **CoverageReportingService** (Day 1-2)
   - Implement zone statistics aggregation
   - Implement strategy overview
   - Add caching for performance

2. **Frontend Components** (Day 3-5)
   - Create `ZoneStatisticsCard` component
   - Create `CoverageBreakdownPanel` component
   - Update `IntelligentCampaignPanel` to show persistent stats
   - Style with semantic CSS variables

3. **API Endpoints** (Day 5)
   - Add `/coverage/zone-stats/:zone_id` endpoint
   - Add `/coverage/strategy-overview/:strategy_id` endpoint
   - Update existing endpoints to return new metrics

**Deliverables**:
- ✅ Zone statistics displayed on frontend
- ✅ Strategy overview with full breakdown
- ✅ Persistent scrape result display
- ✅ Beautiful, intuitive UI

---

### Phase 4: Filtering (Week 4)

**Goal**: Implement advanced business filtering

**Tasks**:
1. **BusinessFilterService** (Day 1-2)
   - Implement filter query building
   - Add filter preset management
   - Optimize query performance with indexes

2. **Frontend Filter UI** (Day 3-4)
   - Create `BusinessFilterPanel` component
   - Add quick filter buttons
   - Implement saved presets UI

3. **API Integration** (Day 4-5)
   - Add `/businesses/filter` endpoint
   - Add `/businesses/filter-presets` endpoints
   - Update business list page

**Deliverables**:
- ✅ Advanced filtering system operational
- ✅ Filter presets save/load functionality
- ✅ "Businesses without websites" quick filter
- ✅ Full business filtering UI

---

### Phase 5: Optimization & Polish (Week 5)

**Goal**: Performance optimization and edge case handling

**Tasks**:
1. **Performance Optimization** (Day 1-2)
   - Add database indexes for common queries
   - Implement caching for expensive aggregations
   - Optimize frontend rendering

2. **Edge Case Handling** (Day 3)
   - Handle timeout scenarios
   - Handle API rate limits
   - Handle validation failures gracefully

3. **Documentation** (Day 4)
   - Update API documentation
   - Write user guide for filtering
   - Document validation logic

4. **User Testing & Refinement** (Day 5)
   - Gather user feedback
   - Fix UI/UX issues
   - Final polish

**Deliverables**:
- ✅ System performs under load
- ✅ All edge cases handled
- ✅ Documentation complete
- ✅ System ready for production

---

## 🧪 Testing Strategy

### Unit Tests

**Backend Services**:
```python
# tests/services/test_website_validation_service.py

async def test_validate_url_with_valid_html():
    """Test validation of valid HTML website."""
    service = WebsiteValidationService(mock_outscraper)
    result = await service.validate_business_website({
        'website_url': 'https://example.com',
        'gmb_place_id': 'ChIJ...'
    })
    assert result.status == 'valid'
    assert result.recommendation == 'keep'

async def test_validate_url_with_pdf():
    """Test validation detects PDF URLs."""
    service = WebsiteValidationService(mock_outscraper)
    result = await service.validate_business_website({
        'website_url': 'https://example.com/file.pdf',
        'gmb_place_id': 'ChIJ...'
    })
    assert result.status == 'invalid'
    assert result.url_type == 'pdf'
    assert result.recommendation == 'generate'

async def test_queue_business_for_generation():
    """Test queuing business for website generation."""
    service = WebsiteGenerationQueueService(mock_db)
    result = await service.queue_for_generation(business_id)
    assert result['status'] == 'queued'
    assert 'task_id' in result
```

### Integration Tests

```python
# tests/integration/test_scraping_workflow.py

async def test_full_scraping_workflow():
    """Test complete workflow: scrape → validate → queue → generate."""
    # 1. Scrape businesses
    hunter = HunterService(db)
    result = await hunter.scrape_with_intelligent_strategy(
        city='Test City',
        state='CA',
        category='plumbers'
    )
    
    # 2. Verify businesses saved
    assert result['results']['raw_businesses'] > 0
    
    # 3. Verify businesses without websites queued
    businesses = await db.execute(
        select(Business).where(Business.website_status == 'queued')
    )
    assert len(businesses.scalars().all()) > 0
    
    # 4. Verify coverage metrics updated
    coverage = await coverage_service.get_zone_statistics(zone_id)
    assert coverage['without_websites'] > 0
    assert coverage['generation_pending'] > 0
```

### Frontend Tests

```typescript
// tests/components/ZoneStatisticsCard.test.tsx

describe('ZoneStatisticsCard', () => {
  it('displays zone statistics correctly', () => {
    const stats = {
      zone_id: 'la_downtown',
      total_businesses: 100,
      without_websites: 30,
      websites_generated: 15
    };
    
    render(<ZoneStatisticsCard stats={stats} />);
    
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByText('Total Businesses')).toBeInTheDocument();
    expect(screen.getByText('Generate 15 Websites')).toBeInTheDocument();
  });
});
```

---

## 📊 Success Metrics

### Technical Metrics

1. **Validation Accuracy**
   - Goal: 95%+ accuracy in detecting invalid URLs
   - Measure: False positive/negative rate

2. **Generation Success Rate**
   - Goal: 90%+ of queued websites generated successfully
   - Measure: (completed / queued) * 100

3. **Performance**
   - Validation: < 5 seconds per business
   - Coverage page load: < 2 seconds
   - Filter query: < 1 second

### Business Metrics

1. **Coverage Visibility**
   - Users can see detailed breakdown of scraping results
   - 100% of scrape details persisted and displayed

2. **Website Generation Volume**
   - Automated generation of 100+ websites per day
   - Zero manual intervention required

3. **User Efficiency**
   - Filter system reduces time to find target businesses by 80%
   - Saved presets used 50%+ of the time

---

## 🚀 Deployment Plan

### Pre-Deployment

1. **Staging Environment Testing**
   - Deploy to staging
   - Run full test suite
   - Load testing with production-like data
   - User acceptance testing

2. **Database Backup**
   - Full backup of production database
   - Test restore procedure

### Deployment Steps

1. **Phase 1: Database Migrations** (Maintenance window)
   - Put API in maintenance mode
   - Run migration scripts
   - Verify schema changes
   - Restore API

2. **Phase 2: Backend Deployment**
   - Deploy new backend code
   - Restart services
   - Verify API health

3. **Phase 3: Frontend Deployment**
   - Deploy new frontend build
   - Clear CDN cache
   - Verify UI loads correctly

4. **Phase 4: Monitoring**
   - Watch error logs for 24 hours
   - Monitor generation queue
   - Check validation accuracy

### Rollback Plan

If issues detected:
1. Restore previous backend version
2. Restore previous frontend version
3. Database schema changes are backwards-compatible (no rollback needed)

---

## 📝 Notes & Considerations

### Google Web Results

**Challenge**: Outscraper may not provide "web results" directly in their API response.

**Options**:
1. **Check `raw_data` field**: The full Outscraper response is stored - may contain web results
2. **Use Google Custom Search API**: Separate API call to get web results
3. **Direct scraping**: Last resort, risky due to rate limits

**Recommendation**: Start with option 1, implement option 2 if needed.

### URL Validation Rate Limits

**Challenge**: Validating 100+ URLs per scrape could hit rate limits or timeouts.

**Solution**:
- Implement validation in background task (Celery)
- Batch validations (10-20 at a time)
- Cache validation results (TTL: 7 days)
- Use connection pooling

### Website Generation Queue Management

**Challenge**: Queue could grow very large (1000+ pending websites).

**Solution**:
- Prioritize by qualification score
- Throttle generation (max 50/hour)
- Monitor queue depth
- Alert if queue exceeds threshold

---

## ✅ Definition of Done

This feature is complete when:

1. ✅ **Automated Validation**
   - Every scraped business has `website_validation_status`
   - Invalid URLs detected and flagged
   - Validation audit trail in `website_validations` table

2. ✅ **Automated Generation**
   - Businesses without websites automatically queued
   - Generation tasks run in background
   - `site_count` increments correctly

3. ✅ **Enhanced Reporting**
   - Per-zone statistics displayed on coverage page
   - Breakdown shows: raw, qualified, with/without websites, generated
   - Statistics persist after page refresh

4. ✅ **Advanced Filtering**
   - Can filter by website status, location, rating, etc.
   - "Businesses without websites" quick filter works
   - Filter presets save and load

5. ✅ **Quality Assurance**
   - All unit tests passing
   - All integration tests passing
   - Performance metrics met
   - No critical bugs

---

## 📚 References

- [Outscraper API Documentation](https://outscraper.com/documentation/)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html)
- [React TypeScript Best Practices](https://react-typescript-cheatsheet.netlify.app/)
- [SQLAlchemy Async Patterns](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)

---

**END OF IMPLEMENTATION PLAN**

