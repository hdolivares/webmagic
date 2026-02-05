# Google Business Profile Link Feature

## ✅ **Feature Complete**

### 🎯 **What Was Requested**

Add a link to the Google Business Profile in the expandable business data section on the AI Generated Sites page, so you can:
1. Click on a site card
2. Expand the business information
3. Click a link to view the Google Business Profile
4. Verify the data matches what's on the generated site

---

## 📊 **Data Analysis**

### **Outscraper Data Available**

✅ **YES** - Outscraper provides Google Business links via `gmb_place_id`:
- **456 out of 457 businesses** have `gmb_place_id`
- **Coverage**: 99.8%
- **URL Format**: `https://www.google.com/maps/place/?q=place_id:{place_id}`

### **What We Found**

| Field | Available | Count | Notes |
|-------|-----------|-------|-------|
| `gmb_place_id` | ✅ | 456/457 | Can construct Google Maps URL |
| `gmb_id` | ✅ | 456/457 | Alternative ID format |
| `raw_data` | ❌ | 0/457 | Not being saved (should be, but NULL) |

**Note**: The `raw_data` JSONB field exists in the database and is supposed to store the full Outscraper response (including direct links), but it's NULL for all businesses. We worked around this by using `gmb_place_id`.

---

## 🔧 **Changes Made**

### **1. Backend API** (`backend/api/v1/sites.py`)

**Added missing business fields to API response:**

```python
"business": {
    "id": str(s.business.id),
    "name": s.business.name,
    "category": s.business.category,
    "phone": s.business.phone,              # NEW
    "address": s.business.address,          # NEW
    "city": s.business.city,
    "state": s.business.state,
    "rating": float(s.business.rating) if s.business.rating else None,
    "review_count": s.business.review_count,
    "website_url": s.business.website_url,  # NEW
    "gmb_place_id": s.business.gmb_place_id, # NEW - For Google Maps URL
} if s.business else None
```

**Why**: The API was only sending name, category, city, state, and rating, but the frontend needed more data.

---

### **2. Frontend** (`frontend/src/pages/Sites/GeneratedSitesPage.tsx`)

**Construct Google Maps URL from place_id:**

```typescript
// Construct Google Maps URL from place_id if available
const googleMapsUrl = business?.gmb_place_id 
  ? `https://www.google.com/maps/place/?q=place_id:${business.gmb_place_id}`
  : (rawData?.link || rawData?.google_maps_url)
```

**Display prominent link button:**

```typescript
{googleMapsUrl && (
  <div className="pt-2 mt-2 border-t border-border">
    <a
      href={googleMapsUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-2 px-3 py-2 mt-2 text-xs font-semibold text-primary-600 bg-primary-50 hover:bg-primary-100 rounded-lg transition-colors"
    >
      <ExternalLink className="w-4 h-4" />
      View Google Business Profile
    </a>
  </div>
)}
```

**Why**: Creates a clear, clickable button that opens the Google Business Profile in a new tab.

---

## 🎨 **User Experience**

### **Before**
- Expandable section showed: name, category, phone, address, rating
- **No way to verify the business on Google**

### **After**
1. Click the **"Business Data"** button to expand
2. See all business details:
   - Name
   - Category
   - Phone
   - Address
   - Rating & Reviews
   - Website URL (if they had one)
3. **NEW**: At the bottom, a prominent button:
   - **"View Google Business Profile"** with external link icon
   - Styled as a primary button (blue background)
   - Opens in new tab
   - Direct link to Google Business/Maps

---

## 📝 **Example URLs**

### Sample Generated Sites with Google Business Links:

1. **Mayfair Plumbers**
   - Site: `https://sites.lavish.solutions/mayfair-plumbers-1770254203251-83b6e7b8`
   - Business: `https://www.google.com/maps/place/?q=place_id:ChIJ...`

2. **Citywide Plumbers**
   - Site: `https://sites.lavish.solutions/citywide-plumbers-1770254202750-4a65af24`
   - Business: `https://www.google.com/maps/place/?q=place_id:ChIJ...`

3. **East End Plumbers**
   - Site: `https://sites.lavish.solutions/east-end-plumbers-1770254203072-b4f50235`
   - Business: `https://www.google.com/maps/place/?q=place_id:ChIJ...`

---

## 🚀 **Deployment**

### **Steps Completed**

1. ✅ **Backend Changes**:
   - Updated `backend/api/v1/sites.py`
   - Added `phone`, `address`, `website_url`, `gmb_place_id` to API response

2. ✅ **Frontend Changes**:
   - Updated `frontend/src/pages/Sites/GeneratedSitesPage.tsx`
   - Construct Google Maps URL from `gmb_place_id`
   - Display prominent link button

3. ✅ **Git Commit**:
   ```bash
   git commit -m "feat: Add Google Business Profile link to generated sites page"
   ```

4. ✅ **Server Deployment**:
   - `git pull origin main` - ✅ Pulled latest
   - `supervisorctl restart webmagic-api` - ✅ API restarted
   - `npm run build` - ✅ Frontend built (7.87s)

5. ✅ **Build Output**:
   ```
   dist/index.html                   0.49 kB │ gzip:   0.32 kB
   dist/assets/index--Eqom7wW.css  190.72 kB │ gzip:  27.99 kB
   dist/assets/index-DKZNyRvo.js   467.19 kB │ gzip: 129.55 kB
   ✓ built in 7.87s
   ```

---

## 🧪 **Testing**

### **How to Test**

1. Go to: `https://web.lavish.solutions/sites/generated`
2. Click on any site card
3. Click **"Business Data"** to expand
4. Scroll to bottom
5. Click **"View Google Business Profile"**
6. Verify it opens the correct Google Business in a new tab

### **Expected Result**

✅ Button is visible for all sites (456 out of 457 have place_id)
✅ Button opens Google Maps/Business in new tab
✅ URL includes correct place_id parameter
✅ You can verify business information matches the generated site

---

## 📊 **Coverage**

- **Total Generated Sites**: 15
- **Sites with Google Business Link**: 15 (100%)
- **Total Businesses in DB**: 457
- **Businesses with place_id**: 456 (99.8%)

**Note**: 1 business doesn't have a `gmb_place_id`, so the link won't appear for that one.

---

## 🔍 **Future Improvement**

### **Fix raw_data Storage**

Currently, `raw_data` is NULL for all businesses. If we fix this, we could:
- Access the direct Google Maps link from Outscraper
- Store additional metadata (hours, services, etc.)
- Enable richer business profiles

**Root Cause**: The scraper is setting `"raw_data": business` but it's not being saved. Need to investigate the `BusinessService.create_or_update_business` method.

---

## ✅ **Status: COMPLETE**

**Feature is live and ready to use!**

- ✅ Backend API updated
- ✅ Frontend updated with prominent button
- ✅ Build completed successfully
- ✅ Deployed to production
- ✅ 456/457 businesses have Google Business links

**Test it now at**: `https://web.lavish.solutions/sites/generated` 🎉

