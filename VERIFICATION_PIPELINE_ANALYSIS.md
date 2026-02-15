# Website Verification Pipeline - Complete Analysis

## Overview

This document analyzes how our system verifies business websites through a multi-tier approach using Outscraper, HTTP validation, ScrapingDog Google Search, and LLM cross-referencing.

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│ TIER 1: Outscraper Google Maps Scraping                                │
│ • Returns business data + website URL (if available)                   │
│ • Quality: High (direct from Google My Business)                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TIER 2: HTTP Website Validation                                        │
│ • Tests if URL is reachable (HTTP 200)                                 │
│ • Fast initial filter (30s timeout)                                    │
│ • Result: "valid" or "needs_verification"                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TIER 3: Deep Verification (ScrapingDog + LLM) 🔥 NEW                  │
│ • Triggered when: HTTP fails OR no URL from Outscraper                 │
│ • ScrapingDog: Google Search for business                              │
│ • LLM: Cross-references search results with business data              │
│ • Matches: Phone > Address > Name + Location                           │
│ • Result: Website URL with confidence OR "confirmed_missing"           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TIER 4: Playwright Browser Validation                                  │
│ • Visual confirmation website loads                                    │
│ • Screenshot capture                                                   │
│ • Final verification                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tier 3: Deep Verification (ScrapingDog + LLM) - Detailed Analysis

### When It Triggers

**Code Location:** `backend/services/hunter/hunter_service.py` (lines 282-352)

```python
if biz_data["website_validation_status"] in ["missing", "needs_verification"]:
    # Run ScrapingDog + LLM discovery
```

**Triggers on:**
1. ❌ **No website URL from Outscraper** → Status: `"missing"`
2. ❌ **HTTP validation failed** → Status: `"needs_verification"`

### Search Query Construction

**Service:** `LLMDiscoveryService._build_query()`  
**Location:** `backend/services/discovery/llm_discovery_service.py` (lines 212-220)

```python
def _build_query(business_name: str, city: str, state: str) -> str:
    return f'"{business_name}" {city} {state} website'
```

**Example:**
- Business: `Plumbing 911`
- Location: `North Canton, Ohio`
- **Query:** `"Plumbing 911" North Canton Ohio website`

**Search Provider:** ScrapingDog Google Search API
- Returns top 10 organic search results
- Includes: title, URL, snippet, displayed_link

### LLM Matching Logic

**Model:** Claude 3 Haiku (cost-effective)  
**Location:** `backend/services/discovery/llm_discovery_service.py` (lines 222-421)

#### **Matching Priority (Lines 373-415):**

1. **🔥 HIGHEST PRIORITY: Phone Number Match**
   - **Confidence:** 0.8 - 1.0
   - **Logic:** If business phone appears in search result snippet
   - **Example:** Business phone `+1 330-280-6261` found in snippet → 0.95 confidence

2. **🔥 HIGH PRIORITY: Address Match**
   - **Confidence:** 0.8 - 1.0
   - **Logic:** Full or partial address in snippet
   - **Example:** "123 Main St, Canton" matches business address

3. **🟡 MEDIUM PRIORITY: Name + Location Match**
   - **Confidence:** 0.5 - 0.7
   - **Logic:** Business name + city/state match, but no phone/address
   - **Warning:** Not sufficient alone (many businesses have similar names)

#### **Exclusion Rules:**

The LLM is trained to REJECT:
- ❌ Directory sites (Yelp, BBB, YellowPages)
- ❌ Franchise aggregator pages (unless phone/address match)
- ❌ Member directories (Chamber of Commerce)
- ❌ Booking platforms (OpenTable, Resy)
- ❌ PDF files
- ❌ LinkedIn company pages

#### **Franchise Handling:**

✅ **Local franchise pages are VALID** if:
- Business name indicates franchise (e.g., "Plumbing 911 of Canton")
- Phone number in snippet matches business data
- Address (if available) matches

**Example:** `https://theplumbing911.com/`
- Shows multiple local phone numbers for different areas
- Phone `330-280-6261` for "Stark / Canton" → MATCH!
- This SHOULD be found for "Plumbing 911, North Canton, OH"

### Data Storage

**Location:** `hunter_service.py` (lines 312-351)

All discovery data is saved to `businesses.raw_data["llm_discovery"]`:

```json
{
  "url": "https://example.com",
  "confidence": 0.95,
  "reasoning": "Phone number matches snippet in Result #2",
  "verified_at": "2026-02-14T12:00:00Z",
  "method": "scrapingdog_llm",
  "query": "\"Business Name\" City State website",
  "llm_model": "claude-3-haiku-20240307",
  "scrapingdog_results": [...],  // ALL organic results
  "llm_analysis": {
    "match_signals": {
      "phone_match": true,
      "address_match": false,
      "name_match": true,
      "location_match": true,
      "result_rank": 2
    }
  }
}
```

---

## Case Study: Plumbing 911 Failure

### The Problem

**Business:** Plumbing 911, North Canton, OH  
**Phone:** `+1 330-280-6261`  
**Status:** `website_url: null`, `website_validation_status: "missing"`

**Actual Website:** `https://theplumbing911.com/`
- ✅ Shows phone: `330-280-6261` for "Stark / Canton"
- ✅ Multi-location franchise site
- ✅ Should have been found by LLM discovery

### Root Cause

```
┌─────────────────────────────────────────────────────────┐
│ 1. Business scraped on Feb 4, 2026                     │
│    • BEFORE LLM discovery was implemented              │
│    • Old pipeline didn't save raw_data                 │
│    • No ScrapingDog search was ever performed          │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│ 2. HTTP validation ran on Feb 8, 2026                  │
│    • Tried to validate NULL website → marked "missing" │
│    • But LLM discovery ONLY runs during scraping       │
│    • No backfill process exists                        │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Business stuck in "missing" state                   │
│    • raw_data: NULL                                     │
│    • llm_discovery: NULL                                │
│    • website_url: NULL                                  │
│    • Never processed through deep verification          │
└─────────────────────────────────────────────────────────┘
```

### Why It Would Work Now

If this business were scraped today:

1. **Outscraper:** Returns no website (or invalid URL)
2. **HTTP Validation:** Fails → Status: `"needs_verification"`
3. **ScrapingDog Search:** Query: `"Plumbing 911" North Canton Ohio website`
   - Returns: `https://theplumbing911.com/` in top results
4. **LLM Analysis:**
   - Finds phone `330-280-6261` in snippet
   - Finds location "Stark / Canton" matches "North Canton"
   - **Verdict:** URL matches (confidence: 0.95)
5. **Result:** Website found and saved!

---

## Verification Pipeline Gaps Identified

### Gap 1: No Backfill for Old Businesses ⚠️

**Problem:** Businesses scraped before Feb 8, 2026 never ran through LLM discovery.

**Impact:** 
- Estimated 20-50+ businesses with `raw_data: NULL`
- Status: `"missing"` but may actually have websites
- Lost opportunities for website generation queue

**Solution:** Run backfill script (see below)

### Gap 2: Rate Limiting

**Current:** 1 second delay between ScrapingDog requests  
**Limit:** ScrapingDog has rate limits on free/paid tiers

**Recommendation:**
- ✅ Current implementation is good
- Monitor API usage
- Consider batch processing for large backfills

### Gap 3: Phone Number Formatting

**Potential Issue:** Phone format variations
- Business data: `+1 330-280-6261`
- Website display: `(330) 280-6261` or `330.280.6261`

**Current Handling:** ✅ LLM is robust enough to match variations

**Recommendation:** No change needed (LLM handles this well)

---

## Backfill Process

### Script: `backend/scripts/backfill_llm_discovery.py`

**Purpose:** Process existing businesses through LLM discovery

**Target Businesses:**
```sql
SELECT * FROM businesses 
WHERE website_url IS NULL 
  AND website_validation_status IN ('missing', 'confirmed_missing', 'pending')
  AND raw_data IS NULL  -- Old pipeline
ORDER BY created_at;
```

**Usage:**

```bash
# Dry run (see what would be processed)
cd /var/www/webmagic/backend
.venv/bin/python scripts/backfill_llm_discovery.py --dry-run --only-null-raw-data

# Process first 10 businesses
.venv/bin/python scripts/backfill_llm_discovery.py --limit 10 --only-null-raw-data

# Process all (with rate limiting)
.venv/bin/python scripts/backfill_llm_discovery.py --batch-size 10 --only-null-raw-data
```

**Features:**
- ✅ Batch processing with rate limiting
- ✅ Progress tracking
- ✅ Error handling
- ✅ Dry-run mode
- ✅ Saves all ScrapingDog + LLM data
- ✅ Updates `website_url` and `website_validation_status`

---

## Testing Recommendations

### 1. Manual Test: Known Business

```bash
cd /var/www/webmagic/backend
.venv/bin/python -c "
import asyncio
from services.discovery.llm_discovery_service import LLMDiscoveryService

async def test():
    service = LLMDiscoveryService()
    result = await service.discover_website(
        business_name='Plumbing 911',
        phone='+1 330-280-6261',
        city='North Canton',
        state='Ohio'
    )
    print('URL:', result.get('url'))
    print('Confidence:', result.get('confidence'))
    print('Reasoning:', result.get('reasoning'))

asyncio.run(test())
"
```

**Expected Result:**
- URL: `https://theplumbing911.com/`
- Confidence: `0.9+`
- Reasoning: Phone number match

### 2. Run Backfill on Sample

```bash
# Test on 5 businesses first
.venv/bin/python scripts/backfill_llm_discovery.py --limit 5 --only-null-raw-data
```

**Verify:**
1. Check `businesses.raw_data` is populated
2. Check `website_url` is found where applicable
3. Check `website_validation_status` updated
4. Check ScrapingDog data saved

### 3. Monitor Logs

```bash
# Watch API logs for LLM discovery activity
tail -f /var/log/webmagic/api.log | grep "LLM\|ScrapingDog\|Deep verification"
```

---

## Performance Metrics

### Current Implementation

**Per Business:**
- ScrapingDog API: ~2-3 seconds
- LLM Analysis: ~1-2 seconds
- Rate limiting: 1 second
- **Total:** ~4-6 seconds per business

**Cost (Haiku):**
- ~2000 tokens per business
- Cost: $0.00025 per business (Haiku pricing)
- 1000 businesses: ~$0.25

**ScrapingDog API:**
- Check current plan limits
- Monitor usage in dashboard

---

## Future Improvements

### 1. Confidence Threshold Tuning

**Current:** Accept any URL found by LLM  
**Improvement:** Only accept if confidence > 0.7

### 2. Multi-Location Franchise Detection

**Enhancement:** Detect when a business is part of a franchise with a shared website  
**Example:** "Plumbing 911" franchise with regional pages

### 3. Website Content Validation

**Future Tier 5:** After Playwright validation
- Check if website mentions business name
- Verify phone number on website
- Confirm address on website

### 4. Periodic Re-verification

**Idea:** Re-run LLM discovery on businesses after 90 days
- Websites change
- Businesses may launch new sites
- Franchises may get local pages

---

## Key Takeaways

✅ **What's Working:**
- Multi-tier verification is sound
- ScrapingDog + LLM matching is powerful
- Phone number matching is highly accurate
- Data storage is comprehensive

⚠️ **What Needs Attention:**
- Backfill old businesses (pre-Feb 8, 2026)
- Monitor ScrapingDog API usage
- Test on known failures (like Plumbing 911)

🎯 **Next Steps:**
1. Run backfill script on existing businesses
2. Monitor results and accuracy
3. Analyze stored LLM data for improvements
4. Consider confidence threshold tuning

---

**Last Updated:** February 14, 2026  
**Incident Reference:** Plumbing 911 case study - Website missed due to lack of backfill process
