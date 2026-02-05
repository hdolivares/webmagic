# Quick Fix Guide: Coverage Page Issues

## What Was Fixed

1. **Zone data showing 0 for everything** - Businesses weren't linked to coverage grids
2. **Dark mode not working** - CSS only responded to system preference, not manual toggle

## Run the Fix (3 Steps)

### Step 1: Run the Migration Script
```bash
cd backend
python scripts/fix_business_coverage_links.py
```

**This will:**
- Link all 190 existing businesses to their coverage grids
- Show you before/after statistics
- Verify that la_downtown and la_koreatown zones now show data

**Expected Output:**
```
✅ Fixed 190 businesses
📊 Zone: la_downtown
   Businesses Linked: 29 ✅
```

### Step 2: Restart Backend Services
```bash
# If using systemd:
sudo systemctl restart webmagic-backend

# If using supervisor:
supervisorctl restart webmagic-backend

# If running manually:
# Stop the current process and restart
```

### Step 3: Verify in Browser
1. Open the Coverage page: `http://your-domain/coverage`
2. Click on the "Los Angeles, CA - plumbers" campaign
3. Click "Detailed Zone Statistics"
4. Expand "la_downtown" zone
5. **Should now show:**
   - ✅ Total Businesses: 29 (not 0!)
   - ✅ Qualified Leads: 29
   - ✅ Website metrics populated

6. **Test dark mode:**
   - Click the dark mode toggle button
   - All coverage components should change colors ✅

## What Changed in the Code

### Backend (Auto-deployed with your files)
- `services/hunter/hunter_service.py` - Creates coverage grid before processing businesses
- `services/hunter/business_service.py` - Links businesses to coverage grids

### Frontend (Auto-deployed with your files)  
- `styles/coverage-theme.css` - Supports manual dark mode toggle

### New File
- `scripts/fix_business_coverage_links.py` - One-time migration to fix existing data

## Troubleshooting

### If you still see 0s after running the script:

**Check if businesses were linked:**
```sql
SELECT COUNT(*) FROM businesses WHERE coverage_grid_id IS NOT NULL;
-- Should return 190 (or close to it)
```

**Check a specific zone:**
```sql
SELECT 
  cg.zone_id,
  cg.lead_count,
  COUNT(b.id) as actual_business_count
FROM coverage_grid cg
LEFT JOIN businesses b ON b.coverage_grid_id = cg.id
WHERE cg.zone_id = 'la_downtown'
GROUP BY cg.zone_id, cg.lead_count;
```

**Expected result:**
```
zone_id       | lead_count | actual_business_count
--------------|------------|----------------------
la_downtown   | 29         | 29
```

### If dark mode still doesn't work:

**Clear browser cache:**
```bash
# In browser DevTools:
1. Open DevTools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"
```

**Or force CSS reload:**
- Add `?v=2` to the end of the URL
- Example: `http://your-domain/coverage?v=2`

## Need More Details?

See `COVERAGE_PAGE_FIX_SUMMARY.md` for:
- Complete technical analysis
- Root cause investigation
- Database query results
- Code change explanations

