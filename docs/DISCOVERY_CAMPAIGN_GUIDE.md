# 📍 Discovery Campaign System - Complete Guide

## 🎯 Overview

WebMagic's Discovery Campaign is an intelligent, systematic approach to finding businesses across the United States. Instead of random scraping, it uses a **Coverage Grid** system that tracks exactly what you've searched, where, and when.

---

## 🗂️ What the System Tracks

### **1. Location Data**
- **Country**: Always "US" by default
- **State**: All 50 US states
- **City**: 346 major cities with populations over 100,000
- **Population**: Used for prioritization (larger cities = higher priority)

### **2. Industry Data**
- **Industry**: Main category (e.g., "Lawyers", "Dentists", "Restaurants")
- **Industry Category**: Sub-category/specialization (e.g., "Personal Injury Lawyer", "Pediatric Dentist")
- **Business Type**: Captured from Outscraper data automatically

### **3. Search Status & Progress**
| Field | Purpose | Values |
|-------|---------|--------|
| `status` | Current state of this grid | `pending`, `in_progress`, `completed`, `cooldown` |
| `priority` | Importance (1-10) | Higher = scraped first |
| `scrape_count` | How many times scraped | Increments each scrape |
| `scrape_offset` | Pagination offset | For multi-page results |
| `has_more_results` | More businesses available? | `true` / `false` |
| `max_results_available` | Total businesses in area | From Outscraper |
| `last_scrape_size` | Results from last scrape | Number of businesses |

### **4. Business Metrics**
- **lead_count**: Total businesses found
- **qualified_count**: Businesses that meet your criteria (no website, has reviews, etc.)
- **site_count**: How many sites you've generated for these businesses
- **conversion_count**: How many became paying customers

### **5. Timing & Scheduling**
- **last_scraped_at**: When this location was last searched
- **cooldown_until**: Don't scrape again until this date (prevents re-scraping too soon)
- **next_scheduled**: When autopilot will scrape this next
- **estimated_businesses**: Expected number of businesses (for planning)

### **6. Error Tracking**
- **error_message**: If scraping failed, what went wrong

---

## 🔄 How Continuation/Resumption Works

### **Problem:**
Outscraper might return 50 results, but there are actually 200+ businesses in that location.

### **Solution:**
1. **First Search**: 
   - Scrapes 50 businesses from "Lawyers in Miami, FL"
   - Sets `scrape_offset = 50`
   - Sets `has_more_results = true` (if Outscraper indicates more exist)
   - Status = `completed`, but no cooldown yet

2. **Second Search** (Same location):
   - System sees `has_more_results = true`
   - Allows re-scraping (skips cooldown)
   - Scrapes next 50 businesses (offset 50-100)
   - Updates `scrape_offset = 100`

3. **Final Search**:
   - When no more results, sets `has_more_results = false`
   - Applies 7-day cooldown
   - Status = `cooldown` until cooldown expires

### **Smart Resume Logic:**
```
IF has_more_results = true AND status = completed:
    → Allow immediate re-scrape (continuation)
ELSE IF cooldown_until < NOW:
    → Allow re-scrape (cooldown expired)
ELSE:
    → Skip (still on cooldown)
```

---

## 🧪 Manual Testing Feature

### **Purpose:**
Test the system with 1-25 searches before enabling autopilot. Get immediate, detailed results.

### **How to Use:**

1. **Navigate to**: Coverage page (`/coverage`)

2. **Find the "Manual Testing" section** (below stats cards)

3. **Adjust the slider**: Choose 1-25 searches

4. **Click "Test X Searches"**

5. **Watch it run**: Shows progress in real-time

6. **Review results**: 
   - See which locations were searched
   - How many businesses found per location
   - Qualification rate (% that meet your criteria)
   - Sample business names

### **What Happens Behind the Scenes:**

```
1. System selects the X highest-priority "pending" grids
   └─ Priority based on: population, industry tier, unfilled areas

2. For each grid:
   ├─ Marks status as "in_progress"
   ├─ Calls Outscraper API (searches Google Maps)
   ├─ Gets ~50 businesses per search
   ├─ Filters/qualifies leads automatically
   │  ├─ Must have: Name, category, rating
   │  ├─ Prefer: No website (bigger opportunity)
   │  ├─ Prefer: Email or phone available
   │  └─ Prefer: 3+ star rating
   ├─ Saves to database
   │  ├─ Linked to coverage_grid_id
   │  └─ Tracks: location, industry, contact info
   ├─ Updates metrics
   │  ├─ lead_count += 50
   │  ├─ qualified_count += X
   │  └─ scrape_offset += 50
   └─ Marks status as "completed"

3. Returns immediate results
   └─ No waiting for Celery queue!
```

### **Cost Estimation:**
- **Outscraper charges ~$0.50 per 50 results**
- **1 search** = ~$0.50
- **10 searches** = ~$5.00
- **25 searches** = ~$12.50

---

## 🎯 Prioritization System

The system automatically prioritizes which locations to scrape first using a **1-10 scale**:

### **Priority 10** (Urgent):
- Major metros (NYC, LA, Chicago)
- High-value industries (Lawyers, Dentists)
- Zero coverage (never scraped)

### **Priority 7-9** (High):
- Large cities (100K-500K population)
- Medium-value industries (Accountants, Real Estate)
- Partial coverage (scraped, but has_more_results = true)

### **Priority 4-6** (Medium):
- Mid-size cities (50K-100K)
- Standard industries (Restaurants, Gyms)
- Recently scraped (cooldown expiring soon)

### **Priority 1-3** (Low):
- Small towns
- Saturated industries
- Recently completed (long cooldown)

### **How Priority is Calculated:**
```python
priority = 0

# Population factor (0-4 points)
if population > 1_000_000: priority += 4
elif population > 500_000: priority += 3
elif population > 100_000: priority += 2
else: priority += 1

# Industry tier (0-3 points)
if industry in ["Lawyers", "Dentists", "Doctors"]: priority += 3
elif industry in ["Accountants", "HVAC", "Plumbers"]: priority += 2
else: priority += 1

# Coverage factor (0-3 points)
if scrape_count == 0: priority += 3  # Never scraped
elif has_more_results: priority += 2  # Partial coverage
elif scrape_count < 3: priority += 1  # Lightly scraped

# MAX: 4 + 3 + 3 = 10
```

---

## 📊 Coverage Grid Example

### **Entry:**
```json
{
  "id": "uuid-here",
  "country": "US",
  "state": "FL",
  "city": "Miami",
  "population": 467963,
  
  "industry": "Lawyers",
  "industry_category": "Personal Injury",
  
  "status": "completed",
  "priority": 9,
  
  "lead_count": 150,
  "qualified_count": 87,
  "site_count": 12,
  "conversion_count": 3,
  
  "scrape_count": 3,
  "scrape_offset": 150,
  "has_more_results": true,
  "max_results_available": 250,
  "last_scrape_size": 50,
  "estimated_businesses": 250,
  
  "last_scraped_at": "2026-01-11T10:30:00Z",
  "cooldown_until": null,
  "next_scheduled": "2026-01-12T14:00:00Z",
  
  "error_message": null
}
```

### **What This Tells Us:**
- ✅ **Location**: Miami, Florida (population 467K)
- ✅ **Industry**: Personal Injury Lawyers
- ✅ **Status**: Completed 3 scrapes (150 businesses so far)
- ✅ **More Available**: Yes! 100 more businesses to scrape
- ✅ **Performance**: 58% qualification rate (87/150)
- ✅ **Conversions**: 3 paying customers from this grid
- ✅ **Next Action**: Scrape again tomorrow at 2pm to get next 50

---

## 🚀 Recommended Testing Workflow

### **Phase 1: Initial Test (5 searches)**
1. Set slider to **5 searches**
2. Click "Test 5 Searches"
3. **Verify**:
   - ✅ Businesses are being found
   - ✅ Qualification logic works
   - ✅ Contact info captured correctly
   - ✅ No errors

### **Phase 2: Expanded Test (10 searches)**
1. Review Phase 1 results
2. Adjust qualification rules if needed (in code)
3. Run **10 more searches**
4. **Verify**:
   - ✅ Consistent quality across cities
   - ✅ Different industries working well
   - ✅ Database filling correctly

### **Phase 3: Full Test (25 searches)**
1. Run **25 searches** across diverse locations
2. **Analyze**:
   - Average businesses per location
   - Qualification rates by industry
   - Which cities/industries are most profitable
3. **Optimize**:
   - Adjust priority scores
   - Refine qualification criteria
   - Update cooldown periods

### **Phase 4: Enable Autopilot**
1. Once confident, enable automated scheduling
2. Set daily search limit (e.g., 100/day)
3. Monitor first few days closely
4. Adjust as needed

---

## 🔧 Configuration Options

### **Scraping Settings** (in code):
```python
# services/hunter/hunter_service.py
RESULTS_PER_SEARCH = 50  # Businesses to get per scrape
COOLDOWN_DAYS = 7  # Days to wait before re-scraping
CONTINUATION_ENABLED = True  # Allow multi-page results
```

### **Qualification Criteria** (in code):
```python
# services/hunter/filters.py
LeadQualifier(
    min_score=50,  # Minimum quality score (0-100)
    require_no_website=True,  # Must not have a website
    require_email=False,  # Email optional but preferred
    min_rating=3.0,  # Minimum Google rating
    min_reviews=5  # Minimum number of reviews
)
```

### **Priority Weights** (in database):
Adjust `priority` field per grid in database or via admin UI (future feature).

---

## 📈 Key Metrics to Monitor

### **Coverage Metrics:**
- **Total Grids**: 346 cities × N industries = X grids
- **Completion %**: How many grids are fully scraped
- **Pending Grids**: Awaiting first scrape
- **Active Grids**: has_more_results = true (more to scrape)

### **Business Metrics:**
- **Total Businesses Found**: Sum of all lead_count
- **Qualification Rate**: qualified_count / lead_count
- **Site Generation Rate**: site_count / qualified_count
- **Conversion Rate**: conversion_count / site_count

### **Cost Metrics:**
- **Cost per Search**: ~$0.50
- **Cost per Qualified Lead**: total_cost / total_qualified
- **Cost per Customer**: total_cost / total_conversions
- **ROI**: customer_lifetime_value / cost_per_customer

---

## ❓ FAQs

### **Q: Can I search the same location multiple times?**
A: Yes! If `has_more_results = true`, you can scrape again immediately to get more businesses. Once all businesses are found, a 7-day cooldown applies.

### **Q: What if a scrape fails?**
A: The system marks it as `failed` and logs the error. You can retry manually or the autopilot will retry after a delay.

### **Q: Can I scrape custom cities not in the 346 list?**
A: Yes! Add them to the database manually or via API. The system works with any US city.

### **Q: How do I change industry priorities?**
A: Edit `backend/scripts/business_categories.py` and adjust tier assignments.

### **Q: Can I scrape internationally?**
A: Yes! Change `country` field. Outscraper supports 200+ countries. Adjust the seed scripts accordingly.

### **Q: What if I want to scrape MORE than 50 businesses per search?**
A: Adjust `limit=50` in `hunter_service.py`. Be aware Outscraper charges more for larger batches.

---

## 🎉 Summary

**The Discovery Campaign system is:**
- ✅ **Smart**: Prioritizes high-value targets automatically
- ✅ **Trackable**: Every search is logged with full metrics
- ✅ **Resumable**: Can continue scraping same location if more results exist
- ✅ **Testable**: Manual testing before committing to autopilot
- ✅ **Scalable**: Handles 346 cities × unlimited industries
- ✅ **Cost-Effective**: Only scrapes once per cooldown period
- ✅ **Data-Rich**: Tracks location, industry, sub-category, and business types

**Start with 5 test searches, analyze results, then scale up!** 🚀
