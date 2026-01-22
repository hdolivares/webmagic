# CRM Businesses Tab Enhancement Plan

**Date:** January 22, 2026  
**Purpose:** Make the businesses tab a powerful lead management tool

---

## 📊 Current State Analysis

### What We Have
✅ **Core Fields:**
- `contact_status`: pending, emailed, sms_sent, opened, clicked, replied, purchased, unsubscribed, bounced
- `website_status`: none, generating, generated, deployed, sold, archived
- `email`, `phone` fields
- `qualification_score` (0-100)
- `category`, `city`, `state`
- `rating`, `review_count`

### What's Missing
❌ **At-a-glance indicators:**
- Has email? (✓/✗)
- Has phone? (✓/✗)
- Contacted via email? (✓/✗)
- Contacted via SMS? (✓/✗)
- Contact bounced? (✓/✗)

❌ **Campaign history:**
- Total campaigns sent
- Last contact date
- Last contact channel

❌ **Advanced filters:**
- Filter by "has phone but no email"
- Filter by "contacted but no reply"
- Filter by "high score + not contacted"
- Filter by contact channel used

---

## 🎯 Proposed Enhancements

### 1. **Enhanced Business Response Schema**

Add computed fields to `BusinessResponse`:

```python
class EnhancedBusinessResponse(BusinessResponse):
    """Enhanced business response with CRM indicators."""
    
    # Contact Data Indicators
    has_email: bool  # ✓ if email is not None
    has_phone: bool  # ✓ if phone is not None
    
    # Contact Status Indicators
    was_contacted: bool  # ✓ if contact_status != "pending"
    contacted_via_email: bool  # ✓ if contact_status in [emailed, opened, clicked]
    contacted_via_sms: bool  # ✓ if contact_status == "sms_sent"
    contact_bounced: bool  # ✓ if contact_status == "bounced"
    is_unsubscribed: bool  # ✓ if contact_status == "unsubscribed"
    is_customer: bool  # ✓ if contact_status == "purchased"
    
    # Campaign Summary
    total_campaigns: int  # Count of all campaigns sent
    last_contact_date: Optional[datetime]  # Most recent campaign send date
    last_contact_channel: Optional[str]  # "email" or "sms"
    
    # Site Summary
    has_generated_site: bool  # ✓ if website_status != "none"
    site_url: Optional[str]  # URL if site exists
    
    # Data Quality Score (0-100)
    data_completeness: int  # % of fields filled (email, phone, address, etc.)
    
    # Human-Readable Status
    status_label: str  # "New Lead", "Contacted", "Replied", "Customer", etc.
    status_color: str  # "gray", "blue", "green", "gold", etc. for UI
```

### 2. **Advanced Filtering Options**

Extend `/api/v1/businesses` endpoint with new filters:

```python
@router.get("/", response_model=EnhancedBusinessListResponse)
async def list_businesses(
    # Existing filters
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    
    # NEW: Contact data filters
    has_email: Optional[bool] = None,
    has_phone: Optional[bool] = None,
    has_both: Optional[bool] = None,  # Has email AND phone
    has_either: Optional[bool] = None,  # Has email OR phone
    
    # NEW: Contact status filters
    contact_status: Optional[str] = None,  # Exact match
    contact_statuses: Optional[List[str]] = None,  # Multiple values
    was_contacted: Optional[bool] = None,  # Any contact attempt
    not_contacted: Optional[bool] = None,  # Still pending
    is_customer: Optional[bool] = None,  # Purchased status
    is_bounced: Optional[bool] = None,  # Bounced contacts
    is_unsubscribed: Optional[bool] = None,  # Opted out
    
    # NEW: Website status filters
    website_status: Optional[str] = None,
    has_site: Optional[bool] = None,  # Any site generated
    
    # NEW: Qualification filters
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    min_reviews: Optional[int] = Query(None, ge=0),
    
    # NEW: Campaign filters
    contacted_after: Optional[datetime] = None,  # Last contact after date
    contacted_before: Optional[datetime] = None,  # Last contact before date
    never_contacted: Optional[bool] = None,  # No campaigns sent
    
    # NEW: Sorting
    sort_by: Optional[str] = Query("created_at", regex="^(created_at|qualification_score|rating|last_contact_date|name)$"),
    sort_order: Optional[str] = Query("desc", regex="^(asc|desc)$"),
    
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    List businesses with advanced CRM filtering.
    
    Examples:
    - Get all businesses with phone but no email:
      ?has_phone=true&has_email=false
      
    - Get high-value leads not yet contacted:
      ?min_score=70&not_contacted=true
      
    - Get bounced contacts to clean up:
      ?is_bounced=true
      
    - Get customers:
      ?is_customer=true
      
    - Get leads contacted in last 7 days:
      ?contacted_after=2026-01-15T00:00:00Z
    """
    pass
```

### 3. **Saved Filter Presets**

Create common filter combinations:

```python
FILTER_PRESETS = {
    "hot_leads": {
        "min_score": 70,
        "not_contacted": True,
        "has_either": True,  # Has email or phone
        "sort_by": "qualification_score",
        "sort_order": "desc"
    },
    "needs_email": {
        "has_phone": True,
        "has_email": False,
        "not_contacted": True
    },
    "needs_sms": {
        "has_email": False,
        "has_phone": True,
        "not_contacted": True
    },
    "needs_follow_up": {
        "was_contacted": True,
        "contact_statuses": ["emailed", "sms_sent", "opened"],
        "contacted_before": "7_days_ago",  # Contacted >7 days ago, no reply
    },
    "bounced_contacts": {
        "is_bounced": True
    },
    "customers": {
        "is_customer": True,
        "sort_by": "created_at",
        "sort_order": "desc"
    },
    "has_site_no_purchase": {
        "has_site": True,
        "is_customer": False
    }
}
```

### 4. **Bulk Actions**

Add bulk operations to businesses endpoint:

```python
@router.post("/bulk/update-status")
async def bulk_update_status(
    business_ids: List[UUID],
    contact_status: Optional[str] = None,
    website_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Bulk update status for multiple businesses."""
    pass

@router.post("/bulk/create-campaigns")
async def bulk_create_campaigns(
    business_ids: List[UUID],
    channel: str = "auto",  # auto, email, sms
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Create campaigns for multiple businesses at once."""
    pass

@router.post("/bulk/export")
async def bulk_export(
    filters: Dict[str, Any],
    format: str = "csv",  # csv, json, xlsx
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Export filtered businesses to CSV/Excel."""
    pass
```

---

## 🎨 Frontend UI Enhancements

### Business List Table Columns

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ☑ │ Name              │ Contact Info    │ Status      │ Score │ Actions    │
├───┼───────────────────┼─────────────────┼─────────────┼───────┼────────────┤
│ ☐ │ LA Plumbing Pros  │ ✓📧 ✓📱         │ 🔵 Emailed  │ 85    │ [Actions▾] │
│   │ Los Angeles, CA   │ (310) 555-1234  │ 2 days ago  │       │            │
├───┼───────────────────┼─────────────────┼─────────────┼───────┼────────────┤
│ ☐ │ NYC Locksmith     │ ✗📧 ✓📱         │ 🟢 Replied  │ 92    │ [Actions▾] │
│   │ New York, NY      │ (212) 555-5678  │ 1 day ago   │       │            │
├───┼───────────────────┼─────────────────┼─────────────┼───────┼────────────┤
│ ☐ │ Miami Electric    │ ✓📧 ✗📱         │ ⚪ Pending  │ 65    │ [Actions▾] │
│   │ Miami, FL         │ john@miami.com  │ Not yet     │       │            │
├───┼───────────────────┼─────────────────┼─────────────┼───────┼────────────┤
│ ☐ │ Austin HVAC       │ ✗📧 ✗📱         │ ⚪ Pending  │ 40    │ [Actions▾] │
│   │ Austin, TX        │ No contact info │ Not yet     │       │            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Status Badges (Color-Coded)

```
⚪ Pending       - Gray   - Not contacted yet
🔵 Emailed       - Blue   - Email sent
📱 SMS Sent      - Purple - SMS sent
👁️ Opened        - Cyan   - Email opened
🔗 Clicked       - Indigo - Link clicked
🟢 Replied       - Green  - Customer replied
🟡 Customer      - Gold   - Purchased site
🔴 Bounced       - Red    - Contact failed
⚫ Unsubscribed  - Black  - Opted out
```

### Filter Bar

```
┌─────────────────────────────────────────────────────────────────────┐
│ [🔍 Search...]  [Filter ▾]  [Sort: Score ▾]  [126 results]         │
├─────────────────────────────────────────────────────────────────────┤
│ Quick Filters:                                                       │
│ [🔥 Hot Leads (70+)] [📧 Needs Email] [📱 Needs SMS]               │
│ [💬 Follow Up] [❌ Bounced] [✅ Customers]                          │
├─────────────────────────────────────────────────────────────────────┤
│ Advanced Filters:                                                    │
│ Contact Info: [Has Email ✓] [Has Phone ✓]                          │
│ Status: [Pending] [Emailed] [Replied] [Purchased]                  │
│ Score: [Min: 70] [Max: 100]                                         │
│ Location: [State: CA ▾] [City: Los Angeles ▾]                      │
│ Category: [All ▾]                                                    │
│ Last Contact: [Last 7 days ▾]                                       │
│ [Apply Filters] [Clear All]                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Bulk Actions Bar

```
┌─────────────────────────────────────────────────────────────────────┐
│ ☑ 12 selected  [Bulk Actions ▾]                                     │
│                                                                       │
│ Actions:                                                             │
│ • Create Email Campaign                                              │
│ • Create SMS Campaign                                                │
│ • Mark as Contacted                                                  │
│ • Export to CSV                                                      │
│ • Delete Selected                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Completeness Calculation

```python
def calculate_data_completeness(business: Business) -> int:
    """
    Calculate how complete a business record is (0-100%).
    
    Fields checked (with weights):
    - Name (required, always counted)
    - Email (30 points)
    - Phone (30 points)
    - Address (10 points)
    - City/State (10 points)
    - Category (10 points)
    - Rating/Reviews (10 points)
    """
    score = 0
    
    if business.email:
        score += 30
    if business.phone:
        score += 30
    if business.address:
        score += 10
    if business.city and business.state:
        score += 10
    if business.category:
        score += 10
    if business.rating and business.review_count > 0:
        score += 10
    
    return score
```

---

## 🚀 Implementation Priority

### Phase 1: Backend API Enhancements (HIGH PRIORITY)
1. ✅ Create `EnhancedBusinessResponse` schema
2. ✅ Add computed fields (has_email, has_phone, etc.)
3. ✅ Implement advanced filtering
4. ✅ Add campaign summary to response

### Phase 2: Frontend UI (MEDIUM PRIORITY)
1. Update business list table with new columns
2. Add status badges with colors
3. Implement filter bar with presets
4. Add bulk selection checkboxes

### Phase 3: Bulk Actions (MEDIUM PRIORITY)
1. Bulk status updates
2. Bulk campaign creation
3. CSV/Excel export

### Phase 4: Analytics Dashboard (LOW PRIORITY)
1. Lead funnel visualization
2. Conversion metrics
3. Campaign performance charts

---

## 💡 Use Cases Enabled

### Use Case 1: Find High-Value Leads to Contact
**Filter:** `min_score=80 & not_contacted=true & has_either=true`
**Result:** All high-scoring leads with contact info that haven't been reached yet

### Use Case 2: Clean Up Bounced Contacts
**Filter:** `is_bounced=true`
**Action:** Review and remove invalid emails/phones

### Use Case 3: Follow Up on Non-Responders
**Filter:** `was_contacted=true & contact_statuses=[emailed,sms_sent] & contacted_before=7_days_ago`
**Result:** Leads contacted >7 days ago with no reply

### Use Case 4: SMS Campaign for Email-Less Businesses
**Filter:** `has_phone=true & has_email=false & not_contacted=true & min_score=60`
**Action:** Bulk create SMS campaigns

### Use Case 5: Track Customer Acquisition
**Filter:** `is_customer=true & sort_by=created_at`
**Result:** All paying customers, newest first

---

## 📝 Summary

### What This Gives You:
1. ✅ **At-a-Glance Lead Quality** - See contact info availability instantly
2. ✅ **Smart Filtering** - Find exactly the leads you need
3. ✅ **Campaign History** - Know who was contacted when
4. ✅ **Bounce Detection** - Identify bad contacts
5. ✅ **Bulk Operations** - Act on multiple leads at once
6. ✅ **Data Quality Metrics** - Prioritize complete records

### Next Steps:
1. Implement Phase 1 (Enhanced API)
2. Test with real data
3. Gather feedback on filters needed
4. Build frontend UI updates
5. Add analytics dashboard

---

**Ready to implement?** Let's start with Phase 1!

