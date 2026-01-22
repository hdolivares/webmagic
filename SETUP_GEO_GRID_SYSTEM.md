# 🚀 Setup Guide: Geo-Grid Business Discovery System

## Overview

This guide will walk you through setting up and testing the new geo-grid business discovery system.

---

## ✅ Prerequisites

- [x] PostgreSQL database running
- [x] Python environment activated
- [x] Backend dependencies installed
- [x] Outscraper API key configured

---

## 📋 Setup Steps

### Step 1: Install New Dependency

```bash
cd backend
pip install aiohttp
```

**What it does:** Installs the HTTP client library needed for website validation.

---

### Step 2: Apply Database Migration

**Option A: Using Python Script (Recommended)**

```bash
cd backend
python scripts/apply_geo_grid_migration.py
```

**Option B: Using SQL Directly**

```bash
cd backend
psql -d webmagic -U your_username -f migrations/003_add_geo_grid_zones.sql
```

**What it does:** Adds 4 new fields to the `coverage_grid` table:
- `zone_id` - Geographic zone identifier
- `zone_lat` - Zone center latitude  
- `zone_lon` - Zone center longitude
- `zone_radius_km` - Search radius for the zone

**Verification:**

```sql
-- Check if columns were added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'coverage_grid' 
AND column_name IN ('zone_id', 'zone_lat', 'zone_lon', 'zone_radius_km');
```

Expected output:
```
  column_name   | data_type
----------------+----------------------
 zone_id        | character varying
 zone_lat       | character varying
 zone_lon       | character varying
 zone_radius_km | character varying
```

---

### Step 3: Test the Geo-Grid System

```bash
cd backend

# Test geo-grid generation
python -m services.hunter.geo_grid
```

**Expected output:**
```
Small City: {'total_zones': 4, 'grid_size': '2x2', ...}
Medium City: {'total_zones': 16, 'grid_size': '4x4', ...}
Large City: {'total_zones': 25, 'grid_size': '5x5', ...}

Sample Search Queries:
  Zone 1x1: plumbers near 34.2677,-118.5038
  Zone 1x2: plumbers near 34.2677,-118.3737
  Zone 1x3: plumbers near 34.2677,-118.2437
```

---

### Step 4: Test Website Validator

```bash
cd backend
python -m services.hunter.website_validator
```

**Expected output:**
```
============================================================
Website Validation Results:
============================================================

URL: https://example.com
  Valid: True
  Accessible: True
  Real Website: True
  Has Content: True
  Status: 200

URL: facebook.com/somebusiness
  Valid: False
  Accessible: False
  Real Website: False
  Error: Social media or directory listing, not a real website
```

---

### Step 5: Run Demo Comparison

```bash
cd backend
python scripts/demo_geo_grid_scraping.py \
    --city "Los Angeles" \
    --state "CA" \
    --industry "plumbers" \
    --compare
```

**Expected output:**
```
🔬 SCRAPING STRATEGY COMPARISON
============================================================

📍 Location: Los Angeles, CA
🏢 Industry: plumbers
👥 Population: 3,900,000

📊 Strategy A: Traditional Single Search
   • Searches: 1
   • Expected Results: ~50 businesses (near city center)
   • Coverage: Limited to downtown/central area
   • Cost: $0.50
   • Problem: Misses outlying neighborhoods

📊 Strategy B: Geo-Grid Multi-Zone Search
   • Grid Size: 5×5
   • Searches: 25
   • Expected Results: ~1,250 businesses
   • Coverage: 1256.6 km² (entire metro area)
   • Cost: $12.50
   • Benefit: Complete, systematic coverage

🎯 Recommendation:
   ✅ Use Geo-Grid Strategy B for maximum coverage
   ⚡ 25x more businesses discovered
```

---

## 🧪 Test with Real Scraping

### Test 1: Small City (Safe & Inexpensive)

```bash
cd backend
python scripts/demo_geo_grid_scraping.py \
    --city "Denver" \
    --state "CO" \
    --industry "dentists" \
    --limit 20
```

**What happens:**
- Creates 16 zones (4×4 grid) for Denver
- Scrapes 20 businesses per zone
- Total API calls: 16
- Estimated cost: $8.00
- Expected businesses found: 250-320

---

### Test 2: Check Your Database

```sql
-- View coverage grids with zones
SELECT 
    city,
    industry,
    zone_id,
    zone_lat,
    zone_lon,
    lead_count,
    qualified_count,
    status
FROM coverage_grid
WHERE zone_id IS NOT NULL
ORDER BY city, zone_id
LIMIT 20;

-- View businesses from your test
SELECT 
    name,
    city,
    category,
    website_url,
    phone,
    email,
    rating,
    qualification_score
FROM businesses
WHERE city = 'Denver'
ORDER BY qualification_score DESC
LIMIT 20;

-- Check coverage statistics
SELECT 
    city,
    COUNT(DISTINCT zone_id) as zones,
    SUM(lead_count) as total_businesses,
    SUM(qualified_count) as qualified_businesses,
    ROUND(AVG(qualification_rate), 2) as avg_qual_rate
FROM coverage_grid
WHERE zone_id IS NOT NULL
GROUP BY city;
```

---

## 🔧 Integration with Existing System

### Option 1: Update Coverage Page API

Add a new endpoint to `backend/api/v1/coverage_campaigns.py`:

```python
@router.post("/scrape-with-zones")
async def scrape_location_with_zones(
    city: str = Query(...),
    state: str = Query(...),
    industry: str = Query(...),
    population: int = Query(...),
    city_lat: float = Query(...),
    city_lon: float = Query(...),
    limit_per_zone: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Scrape a location using geo-grid subdivision for maximum coverage.
    """
    hunter = HunterService(db)
    
    result = await hunter.scrape_location_with_zones(
        city=city,
        state=state,
        industry=industry,
        country="US",
        limit_per_zone=limit_per_zone,
        priority=8,
        population=population,
        city_lat=city_lat,
        city_lon=city_lon
    )
    
    await db.commit()
    return result
```

### Option 2: Update Seed Script

Modify `backend/scripts/seed_us_cities.py` to use geo-grid scraping:

```python
from services.hunter.hunter_service import HunterService
from services.hunter.geo_grid import should_subdivide_city

for city, state, lat, lon, population in US_CITIES:
    if should_subdivide_city(population):
        # Use geo-grid scraping
        result = await hunter.scrape_location_with_zones(
            city=city,
            state=state,
            industry=category,
            population=population,
            city_lat=lat,
            city_lon=lon
        )
    else:
        # Use traditional scraping
        result = await hunter.scrape_location(
            city=city,
            state=state,
            industry=category
        )
```

### Option 3: Add to Conductor (Autopilot)

Update `backend/conductor.py` to prefer geo-grid scraping:

```python
# In scrape_pending_territories task
if grid.population and grid.population >= 100_000:
    # Use geo-grid scraping
    await hunter.scrape_location_with_zones(
        city=grid.city,
        state=grid.state,
        industry=grid.industry,
        population=grid.population,
        city_lat=grid.latitude,
        city_lon=grid.longitude
    )
else:
    # Use traditional scraping
    await hunter.scrape_location(
        city=grid.city,
        state=grid.state,
        industry=grid.industry
    )
```

---

## 📊 Monitoring & Analytics

### Dashboard Queries

**Zone Coverage by City:**
```sql
SELECT 
    city,
    state,
    COUNT(DISTINCT zone_id) as zones_created,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as zones_completed,
    SUM(lead_count) as businesses_found,
    SUM(qualified_count) as qualified_leads,
    ROUND(100.0 * COUNT(CASE WHEN status = 'completed' THEN 1 END) / COUNT(*), 1) as completion_pct
FROM coverage_grid
WHERE zone_id IS NOT NULL
GROUP BY city, state
ORDER BY zones_created DESC
LIMIT 20;
```

**Website Validation Results:**
```sql
SELECT 
    website_status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as percentage
FROM businesses
WHERE website_status IS NOT NULL
GROUP BY website_status
ORDER BY count DESC;
```

**Top Performing Zones:**
```sql
SELECT 
    city || ', ' || state as location,
    zone_id,
    lead_count,
    qualified_count,
    ROUND(100.0 * qualified_count / NULLIF(lead_count, 0), 1) as qual_rate
FROM coverage_grid
WHERE zone_id IS NOT NULL AND lead_count > 0
ORDER BY qualified_count DESC
LIMIT 20;
```

---

## 🎯 Best Practices

### 1. Start with Test Cities
- Begin with medium-sized cities (250K-500K population)
- These create 9-16 zones (affordable cost for testing)
- Verify results before scaling to mega-cities

### 2. Monitor Costs
- Small city (100K-250K): 4 zones = $2.00
- Medium city (250K-500K): 9 zones = $4.50  
- Large city (500K-1M): 16 zones = $8.00
- Mega city (1M+): 25 zones = $12.50

### 3. Check for Duplicates
The system automatically prevents duplicates, but monitor:
```sql
SELECT 
    gmb_id,
    COUNT(*) as occurrences
FROM businesses
GROUP BY gmb_id
HAVING COUNT(*) > 1;
```

### 4. Optimize Grid Size
If you're finding too many duplicates across zones, consider:
- Reducing grid size (fewer, larger zones)
- Increasing zone radius
- Adjusting in `backend/services/hunter/geo_grid.py`

---

## 🐛 Troubleshooting

### Issue: Migration fails
**Error:** `relation "coverage_grid" does not exist`
**Solution:** Run main database migrations first, then geo-grid migration

### Issue: No city coordinates
**Error:** `TypeError: unsupported operand type(s) for +: 'NoneType' and 'float'`
**Solution:** Ensure city lat/lon are provided to `scrape_location_with_zones()`

### Issue: Website validation slow
**Symptom:** Validation takes > 5 minutes for 1000 businesses
**Solution:** Increase concurrent requests:
```python
await validator.validate_batch(urls, max_concurrent=20)  # Default: 10
```

### Issue: Too many API calls
**Symptom:** Costs are too high for large cities
**Solution:** 
- Increase `limit_per_zone` to get more results per search
- Reduce grid size for mega-cities
- Focus on high-priority cities only

---

## ✅ Verification Checklist

After setup, verify everything is working:

- [ ] Database migration applied successfully
- [ ] Geo-grid module runs without errors
- [ ] Website validator works (test with demo URLs)
- [ ] Demo script shows strategy comparison
- [ ] Test scrape completes successfully
- [ ] Zone data saved to database correctly
- [ ] Businesses have website validation data
- [ ] No duplicate businesses across zones
- [ ] Coverage stats show zone metrics
- [ ] Ready to integrate with main system

---

## 🎉 You're Ready!

The geo-grid system is now installed and tested. You can:

1. ✅ **Manually trigger** geo-grid scrapes using the demo script
2. ✅ **Integrate with API** to expose geo-grid scraping to frontend
3. ✅ **Update seed scripts** to use geo-grid for all cities
4. ✅ **Enable in autopilot** to automatically use geo-grid for large cities

**Next:** Start with manual testing, then gradually integrate into your automated workflows!

---

## 📚 Reference

- **Full Documentation:** `GEO_GRID_ENHANCEMENTS.md`
- **Quick Start:** `QUICK_START_GEO_GRID.md`
- **Implementation Details:** `IMPLEMENTATION_SUMMARY_GEO_GRID.md`
- **Demo Script:** `backend/scripts/demo_geo_grid_scraping.py`

