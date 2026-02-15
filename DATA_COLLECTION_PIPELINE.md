# Complete Data Collection Pipeline

**Last Updated:** February 15, 2026  
**Status:** 🟢 Fully Operational

---

## Overview

This document outlines our complete business data collection pipeline, from initial scraping through website verification, showing **exactly what data we collect at each stage**.

---

## Pipeline Stages

```
1. Outscraper GMB → 2. Website Detection → 3. HTTP Validation → 4. ScrapingDog + LLM → 5. Playwright → 6. Database
```

---

## Stage 1: Outscraper Google My Business

### What We Send:
```python
query = "law firms, Los Angeles, CA, USA"
region = "US"
limit = 100
```

### What We Get Back (50+ fields):
```json
{
  "query": "law firms, Los Angeles, CA, USA",
  "name": "Sepulveda Sanchez Accident Lawyers",
  "place_id": "ChIJ...",
  "google_id": "0x...",
  "cid": "123456789",
  "full_address": "123 Main St, Los Angeles, CA 90001",
  "borough": "Los Angeles",
  "street": "123 Main St",
  "postal_code": "90001",
  "country_code": "US",
  "country": "United States of America",
  "city": "Los Angeles",
  "us_state": "California",
  "state": "California",
  "latitude": 34.0522,
  "longitude": -118.2437,
  "time_zone": "America/Los_Angeles",
  "site": "https://sepulvedalawgroup.com/",  // Often present!
  "phone": "+1 213-431-0621",
  "type": "Law firm",
  "category": "Law firm",
  "subtypes": "Law firm, Personal injury attorney, Criminal defense attorney",
  "rating": 4.9,
  "reviews": 150,
  "photos_count": 45,
  "working_hours": {
    "Monday": "9 AM-5 PM",
    "Tuesday": "9 AM-5 PM",
    // ...
  },
  "business_status": "OPERATIONAL",
  "about": {
    "Service options": {
      "In-person visits": true,
      "Online appointments": true
    },
    "Accessibility": {
      "Wheelchair accessible entrance": true
    }
  },
  "reviews_per_score": {
    "5": 120,
    "4": 20,
    "3": 5,
    "2": 3,
    "1": 2
  },
  "owner_id": "...",
  "verified": true,
  // ... 30+ more fields
}
```

### What We Store:
✅ **Everything** - stored in `businesses.raw_data` JSONB field

---

## Stage 2: Website Detection (Multi-Tier)

### Source 1: Outscraper Data
```python
website_url = raw_data.get("site") or raw_data.get("website")
```

### Source 2: Data Quality Analysis
```python
# Checks multiple fields for website URLs:
- raw_data["site"]
- raw_data["website"] 
- raw_data["menu_link"]
- raw_data["order_links"]
# Returns: website_type, confidence, website_url
```

### What We Determine:
- `website_type`: "real", "social", "directory", "uncertain", "none"
- `website_confidence`: 0.0 to 1.0
- `has_website`: boolean

---

## Stage 3: HTTP Validation (Quick Check)

### What We Send:
```python
url = "https://sepulvedalawgroup.com/"
timeout = 30  # seconds
```

### What We Check:
- HTTP status code (200 = OK)
- Response time
- Content type (HTML vs PDF)
- Basic accessibility

### What We Store:
```json
{
  "website_validation_status": "pending" | "needs_verification" | "missing",
  "website_url": "https://sepulvedalawgroup.com/" or null
}
```

**Decision Tree:**
- ✅ **HTTP Pass** → `status = "pending"` → Queue for Playwright
- ⚠️ **HTTP Fail** → `status = "needs_verification"` → Send to ScrapingDog
- ❌ **No URL** → `status = "missing"` → Send to ScrapingDog

---

## Stage 4: ScrapingDog + LLM (Deep Verification)

### What We Send to ScrapingDog:
```python
query = '"Sepulveda Sanchez Accident Lawyers" Los Angeles California website'
results = 10  # Top 10 organic results
country = "us"
```

### What ScrapingDog Returns (Complete):
```json
{
  "organic_results": [
    {
      "position": 1,
      "title": "Sepulveda Sanchez Law - Los Angeles Personal Injury Lawyers",
      "link": "https://sepulvedalawgroup.com/los-angeles-injury-lawyers/",
      "url": "https://sepulvedalawgroup.com/los-angeles-injury-lawyers/",
      "snippet": "Call us today at 213-431-0621 for a free consultation. We serve clients in Los Angeles, California...",
      "displayed_link": "sepulvedalawgroup.com › los-angeles-injury-lawyers",
      "domain": "sepulvedalawgroup.com",
      "cached_page_link": "https://...",
      "related_pages_link": "https://..."
    },
    {
      "position": 2,
      "title": "Sepulveda Sanchez Accident Lawyers - Yelp",
      "link": "https://www.yelp.com/biz/sepulveda-sanchez-accident-lawyers-los-angeles",
      "snippet": "150 reviews of Sepulveda Sanchez Accident Lawyers \"Great service!\"...",
      "domain": "yelp.com"
    },
    {
      "position": 3,
      "title": "Sepulveda Sanchez - LinkedIn",
      "link": "https://www.linkedin.com/company/sepulveda-sanchez-law",
      "snippet": "...",
      "domain": "linkedin.com"
    }
    // ... 7 more results
  ],
  "related_searches": [
    "personal injury lawyer los angeles",
    "accident attorney near me",
    // ...
  ],
  "knowledge_graph": {
    // If business has a knowledge panel
  },
  "search_parameters": {
    "q": "\"Sepulveda Sanchez Accident Lawyers\" Los Angeles California website",
    "gl": "us",
    "num": 10
  }
}
```

### What We Send to LLM (Claude):
```json
{
  "business_data": {
    "name": "Sepulveda Sanchez Accident Lawyers",
    "phone": "+1 213-431-0621",
    "address": "123 Main St, Los Angeles, CA 90001",
    "city": "Los Angeles",
    "state": "California"
  },
  "search_results": [
    // All 10 organic results from ScrapingDog
  ]
}
```

### What LLM Returns:
```json
{
  "url": "https://sepulvedalawgroup.com/",
  "confidence": 0.95,
  "reasoning": "The phone number +1 213-431-0621 from the business data matches the snippet in Result #1, confirming this is the correct website.",
  "match_signals": {
    "phone_match": true,
    "phone_match_position": 1,
    "name_match": true,
    "name_similarity": 0.92,
    "location_match": true,
    "domain_quality": "high",
    "excluded_directories": ["yelp.com", "linkedin.com"]
  },
  "rejected_urls": [
    {
      "url": "https://www.yelp.com/biz/sepulveda-sanchez-accident-lawyers-los-angeles",
      "reason": "Directory/review site - not the official business website",
      "position": 2
    },
    {
      "url": "https://www.linkedin.com/company/sepulveda-sanchez-law",
      "reason": "Social media profile - not a business website",
      "position": 3
    }
  ],
  "alternative_urls": [
    "https://sepulvedalawgroup.com/contact",
    "https://sepulvedalawgroup.com/los-angeles-injury-lawyers"
  ]
}
```

### What We Store in Database:
```json
{
  "raw_data": {
    "llm_discovery": {
      "url": "https://sepulvedalawgroup.com/",
      "confidence": 0.95,
      "reasoning": "The phone number +1 213-431-0621...",
      "verified_at": "2026-02-15T01:33:48.920170",
      "method": "scrapingdog_llm",
      "query": "\"Sepulveda Sanchez Accident Lawyers\" Los Angeles California website",
      "llm_model": "claude-3-haiku-20240307",
      
      // COMPLETE ScrapingDog results (NEW!)
      "scrapingdog_results": {
        "organic_results": [
          // All 10 results with titles, snippets, URLs
        ],
        "related_searches": [...],
        "search_parameters": {...}
      },
      
      // COMPLETE LLM analysis (NEW!)
      "llm_analysis": {
        "url": "https://sepulvedalawgroup.com/",
        "confidence": 0.95,
        "reasoning": "...",
        "match_signals": {
          "phone_match": true,
          "name_match": true,
          "location_match": true
        },
        "rejected_urls": [
          {
            "url": "https://yelp.com/...",
            "reason": "Directory site"
          }
        ],
        "alternative_urls": [...]
      }
    }
  },
  "website_url": "https://sepulvedalawgroup.com/",
  "website_validation_status": "pending",
  "verified": true,
  "discovered_urls": ["https://sepulvedalawgroup.com/"]
}
```

---

## Stage 5: Playwright Validation (Deep Check)

### What We Do:
1. Launch headless browser
2. Navigate to URL
3. Wait for page load
4. Take screenshot
5. Extract page title, description, content
6. Check for business name/phone on page
7. Validate it's a real business website (not parked domain)

### What We Store:
```json
{
  "website_validation_result": {
    "is_valid": true,
    "is_real_website": true,
    "has_business_info": true,
    "page_title": "Sepulveda Sanchez Law | Personal Injury Lawyers Los Angeles",
    "meta_description": "...",
    "phone_found_on_page": true,
    "name_found_on_page": true,
    "screenshot_url": "https://s3.../screenshot.png",
    "load_time_ms": 1234,
    "validated_at": "2026-02-15T..."
  },
  "website_validation_status": "valid",
  "website_validated_at": "2026-02-15T...",
  "website_screenshot_url": "https://s3.../screenshot.png"
}
```

---

## Complete Database Record Example

### After All Stages:

```json
{
  "id": "uuid",
  "gmb_id": "123456789",
  "name": "Sepulveda Sanchez Accident Lawyers",
  "phone": "+1 213-431-0621",
  "email": "contact@example.com",
  "website_url": "https://sepulvedalawgroup.com/",
  "address": "123 Main St, Los Angeles, CA 90001",
  "city": "Los Angeles",
  "state": "California",
  "country": "US",
  "latitude": 34.0522,
  "longitude": -118.2437,
  "category": "Law firm",
  "subcategory": "Personal injury attorney",
  "rating": 4.9,
  "review_count": 150,
  "photos_count": 45,
  "website_type": "real",
  "website_confidence": 0.95,
  "website_validation_status": "valid",
  "website_validated_at": "2026-02-15T...",
  "website_screenshot_url": "https://s3.../screenshot.png",
  "verified": true,
  "operational": true,
  "qualification_score": 85,
  "quality_score": 9.2,
  
  "raw_data": {
    // COMPLETE Outscraper response (50+ fields)
    "query": "law firms, Los Angeles, CA, USA",
    "name": "Sepulveda Sanchez Accident Lawyers",
    "site": "https://sepulvedalawgroup.com/",
    "place_id": "ChIJ...",
    "working_hours": {...},
    "about": {...},
    // ... all other Outscraper fields
    
    // COMPLETE LLM discovery data (NEW!)
    "llm_discovery": {
      "url": "https://sepulvedalawgroup.com/",
      "confidence": 0.95,
      "reasoning": "...",
      "verified_at": "2026-02-15T...",
      "method": "scrapingdog_llm",
      "query": "\"Sepulveda Sanchez Accident Lawyers\" Los Angeles California website",
      "llm_model": "claude-3-haiku-20240307",
      
      "scrapingdog_results": {
        "organic_results": [
          // 10 complete search results
        ],
        "related_searches": [...],
        "search_parameters": {...}
      },
      
      "llm_analysis": {
        "match_signals": {...},
        "rejected_urls": [...],
        "alternative_urls": [...]
      }
    }
  },
  
  "website_validation_result": {
    // Playwright validation details
    "is_valid": true,
    "is_real_website": true,
    "page_title": "...",
    "screenshot_url": "..."
  },
  
  "created_at": "2026-02-15T...",
  "updated_at": "2026-02-15T..."
}
```

---

## Data Retention & Usage

### What We Use For:

**Immediate Use:**
- Website validation
- Lead qualification
- Campaign targeting
- Contact enrichment

**Analytics:**
- Data quality scoring
- Source reliability tracking
- Validation success rates
- LLM accuracy metrics

**Debugging:**
- Why did LLM choose this URL?
- Why was a business rejected?
- What alternatives were considered?
- How confident is each decision?

**Future Improvements:**
- Retrain LLM matching logic
- Optimize ScrapingDog queries
- Build fallback website discovery
- Identify false negatives

**Competitive Intelligence:**
- What businesses appear together?
- Which directories list competitors?
- Local SEO patterns
- Market saturation analysis

---

## Storage Efficiency

### Size Breakdown (Per Business):
- **Outscraper raw_data**: ~3-5 KB (50+ fields)
- **LLM discovery data**: ~5-10 KB (10 search results + analysis)
- **Playwright validation**: ~1-2 KB (metadata + URLs)
- **Total raw_data**: ~10-15 KB per business

### For 10,000 Businesses:
- Total raw_data: ~100-150 MB
- With JSONB compression: ~50-75 MB
- Negligible impact on performance

---

## Query Examples

### Get Complete Pipeline Data:
```sql
SELECT 
    name,
    website_url,
    raw_data->'site' as outscraper_site,
    raw_data->'llm_discovery'->>'url' as llm_found_url,
    raw_data->'llm_discovery'->>'confidence' as llm_confidence,
    raw_data->'llm_discovery'->'scrapingdog_results'->'organic_results' as search_results,
    website_validation_status
FROM businesses 
WHERE name = 'Sepulveda Sanchez Accident Lawyers';
```

### Analyze Match Signals:
```sql
SELECT 
    name,
    (raw_data->'llm_discovery'->'llm_analysis'->'match_signals'->>'phone_match')::boolean as phone_matched,
    (raw_data->'llm_discovery'->'llm_analysis'->'match_signals'->>'name_match')::boolean as name_matched,
    raw_data->'llm_discovery'->>'confidence' as confidence
FROM businesses 
WHERE raw_data->'llm_discovery' IS NOT NULL
ORDER BY (raw_data->'llm_discovery'->>'confidence')::float DESC;
```

### Find Alternative URLs:
```sql
SELECT 
    name,
    website_url as primary_url,
    raw_data->'llm_discovery'->'llm_analysis'->'alternative_urls' as alternatives
FROM businesses 
WHERE jsonb_array_length(raw_data->'llm_discovery'->'llm_analysis'->'alternative_urls') > 0;
```

---

## Pipeline Success Metrics

### Current Status (70 businesses with LLM data):
- **100%** have website_url saved ✅
- **94%** (66/70) validated as having website (`status = 'pending'` or `'valid'`)
- **6%** (4/70) confirmed as no website (`status = 'confirmed_missing'`)
- **100%** have complete ScrapingDog search results saved ✅
- **100%** have complete LLM analysis saved ✅

### Confidence Distribution:
- **High confidence (≥0.9):** ~60% of matches
- **Medium confidence (0.7-0.9):** ~30% of matches
- **Low confidence (<0.7):** ~10% of matches

---

## System Health

🟢 **All Pipeline Stages Operational**

- ✅ Outscraper GMB scraping
- ✅ Multi-tier website detection
- ✅ HTTP validation
- ✅ ScrapingDog integration
- ✅ LLM analysis (Claude Haiku)
- ✅ Complete data storage
- ✅ Playwright validation queue
- ✅ Database persistence

**Last Deployment:** February 15, 2026  
**Last Scrape:** February 15, 2026  
**Success Rate:** 100% (all data saved correctly)
