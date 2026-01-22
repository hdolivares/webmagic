# WebMagic CRM Analysis & Implementation Plan

## Executive Summary

**Current Status:** ❌ **Critical CRM Gap Identified**

Your plumbing company test site (`la-plumbing-pros`) exists in the database, but **NO business record was created** for it. This means:
- ✅ Site was generated successfully
- ❌ No business/lead tracking
- ❌ No contact status tracking  
- ❌ No campaign tracking
- ❌ No conversion funnel visibility

## Database Analysis Results

### What We Found

```sql
-- Site exists (created Jan 21, 2026)
Site: "Los Angeles Plumbing Pros"
Slug: la-plumbing-pros
Status: preview
Business ID: NULL ⚠️ (ORPHANED SITE)
Purchase Status: Not purchased
```

```sql
-- No business records at all
Total Businesses: 0
With Email: 0
With Phone: 0
Sites Generated: 0
Sites Sold: 0
```

### The Problem

When you test-generated the plumbing company site, the system:
1. ✅ Created a `Site` record
2. ❌ **Did NOT create a `Business` record**
3. ❌ **Did NOT link the two together**

This means you have **zero visibility** into your sales funnel.

---

## Current System Architecture

### What EXISTS (But Incomplete)

#### 1. **Business Model** (`businesses` table)
```python
# Fields for tracking:
contact_status = Column(String(30), default="pending")
# Values: pending, emailed, opened, clicked, replied, 
#         purchased, unsubscribed, bounced

website_status = Column(String(30), default="none")  
# Values: none, generating, generated, deployed, sold, archived

qualification_score = Column(Integer, default=0)
```

✅ **Good:** Fields exist for CRM tracking  
❌ **Problem:** Not being populated or used

#### 2. **Sites Model** (`sites` table)
```python
status = Column(String(30), default="preview")
purchased_at = Column(DateTime)
subscription_status = Column(String(30))
subscription_started_at = Column(DateTime)
subscription_ends_at = Column(DateTime)
```

✅ **Good:** Tracks site lifecycle  
❌ **Problem:** Not linked to Business records

#### 3. **Campaigns Model** (`campaigns` table)
```python
# Tracks email/SMS campaigns with:
status, sent_at, opened_at, clicked_at, replied_at, converted_at
channel (email/sms)
business_id (foreign key)
```

✅ **Good:** Comprehensive tracking  
❌ **Problem:** No campaigns have been created (table is empty)

#### 4. **Customers/Subscriptions/Payments**
```python
# Full payment tracking exists:
- customers table (for paying clients)
- subscriptions table
- payments table
```

✅ **Good:** Complete payment infrastructure  
❌ **Problem:** Not integrated with lead flow

---

## What's MISSING for Full CRM

### 1. **Business Record Creation**

**Current:** Sites are created WITHOUT business records  
**Needed:** Automatic business record creation

```python
# Missing workflow:
1. Scrape business from GMB → Create Business record
2. Analyze & qualify → Update qualification_score
3. Generate website → Create Site, link to Business, 
                        update website_status='generated'
4. Send campaign → Create Campaign, link to Business
5. Customer clicks → Update contact_status='clicked'
6. Customer purchases → Update contact_status='purchased', 
                         website_status='sold'
7. Create Customer record → Link to Business + Site
8. Create Subscription → Track recurring revenue
```

### 2. **Status Synchronization**

**Problem:** Status updates don't cascade between related entities

**Needed:**
- When a campaign is opened → Update business.contact_status = 'opened'
- When a site is purchased → Update business.website_status = 'sold' + business.contact_status = 'purchased'
- When subscription starts → Create customer record + link to business
- When subscription cancels → Update statuses accordingly

### 3. **CRM Dashboard / Filtering**

**Current:** Basic business list API exists (GET `/api/v1/businesses`)  
**Needed:** Enhanced CRM features:

```python
# Missing features:
- Filter by contact_status (pending, emailed, replied, etc.)
- Filter by website_status (generated, sold, etc.)  
- Filter by campaign engagement (opened, clicked)
- Filter by date ranges
- Bulk actions (start campaign for filtered set)
- Pipeline stage visualization
- Conversion funnel analytics
```

### 4. **Campaign Management from CRM**

**Current:** Campaigns exist but no way to START them from CRM  
**Needed:**

```python
POST /api/v1/crm/campaigns/start
{
  "name": "Plumbers in LA - January Batch",
  "filters": {
    "category": "Plumber",
    "city": "Los Angeles",
    "contact_status": ["pending", "opened"],
    "website_status": ["generated"],
    "min_rating": 4.0
  },
  "channel": "email",  # or "sms"
  "schedule": "immediate"
}
```

### 5. **Business Lifecycle Tracking**

**Needed:** Automatic status updates based on actions:

| Event | Business Update |
|-------|----------------|
| Business scraped | `contact_status='pending'`, `website_status='none'` |
| Site generated | `website_status='generating' → 'generated'` |
| Campaign sent | `contact_status='emailed'` (or 'texted' for SMS) |
| Email opened | `contact_status='opened'` |
| Link clicked | `contact_status='clicked'` |
| Reply received | `contact_status='replied'` |
| Checkout created | `contact_status='interested'` |
| Purchase completed | `contact_status='purchased'`, `website_status='sold'` |
| Subscription active | Link to `customers` table |
| Opted out | `contact_status='unsubscribed'` |

---

## Recommended Implementation Plan

### Phase 1: Fix Orphaned Sites (Immediate)

**Goal:** Ensure all future sites have business records

```python
# 1. Create migration to add business records retroactively
# For existing orphaned sites like 'la-plumbing-pros'

# 2. Update site generation workflow:
async def generate_site(business_data):
    # Step 1: Create/get business record FIRST
    business = await create_or_get_business(business_data)
    
    # Step 2: Update business status
    business.website_status = 'generating'
    await db.commit()
    
    # Step 3: Generate site
    site = await build_site(business)
    site.business_id = business.id
    
    # Step 4: Update business status
    business.website_status = 'generated'
    await db.commit()
    
    return site, business
```

### Phase 2: CRM API Endpoints (Week 1)

```python
# New endpoints in /api/v1/crm/

GET  /crm/leads                 # List with advanced filters
GET  /crm/leads/{id}            # Single lead detail
PATCH /crm/leads/{id}/status    # Manual status update
GET  /crm/pipeline              # Funnel visualization data
GET  /crm/stats                 # CRM dashboard stats

POST /crm/campaigns/preview     # Preview who would be targeted
POST /crm/campaigns/start       # Start campaign from filters
GET  /crm/campaigns             # List campaigns
GET  /crm/campaigns/{id}/results # Campaign performance
```

### Phase 3: Status Automation (Week 2)

```python
# Webhook handlers and event listeners

# 1. Email Provider Webhooks (already exists)
@router.post("/webhooks/email/opened")
async def handle_email_opened(event):
    campaign = get_campaign(event.message_id)
    business = get_business(campaign.business_id)
    
    # Update campaign
    campaign.opened_at = now()
    campaign.opened_count += 1
    
    # Update business
    if business.contact_status == 'emailed':
        business.contact_status = 'opened'
    
    await db.commit()

# 2. SMS Provider Webhooks (Twilio - already created!)
@router.post("/webhooks/twilio/status")
async def handle_sms_status(event):
    # Similar logic for SMS

# 3. Checkout/Payment Webhooks (Recurrente - exists)
@router.post("/webhooks/recurrente/payment")
async def handle_payment(event):
    site = get_site_by_checkout_id(event.checkout_id)
    business = get_business_by_site(site.id)
    
    if event.status == 'completed':
        # Update site
        site.status = 'active'
        site.purchased_at = now()
        
        # Update business
        business.contact_status = 'purchased'
        business.website_status = 'sold'
        
        # Create customer record
        customer = create_customer(business, site)
        
        await db.commit()
```

### Phase 4: CRM Frontend UI (Week 3-4)

```tsx
// New pages:
/admin/crm/leads          # CRM dashboard
/admin/crm/leads/{id}     # Lead detail page
/admin/crm/campaigns      # Campaign management
/admin/crm/pipeline       # Visual funnel

// Features:
- Advanced filtering sidebar
- Bulk actions toolbar
- Status badges with colors
- Quick actions (email, call, generate site)
- Timeline view of interactions
- Campaign builder with preview
```

### Phase 5: Analytics & Reporting (Week 5)

```python
# New analytics endpoints:
GET /crm/analytics/funnel
GET /crm/analytics/conversion-rates
GET /crm/analytics/revenue-by-source
GET /crm/analytics/campaign-performance

# Funnel stages:
1. Scraped → Total businesses
2. Qualified → qualification_score > threshold
3. Site Generated → website_status='generated'
4. Contacted → contact_status in ['emailed', 'texted']
5. Engaged → contact_status in ['opened', 'clicked']
6. Interested → contact_status='replied'
7. Purchased → contact_status='purchased'
8. Active → subscription_status='active'
```

---

## CRM Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     LEAD ACQUISITION                             │
└───────────────┬─────────────────────────────────────────────────┘
                │
                ▼
    ┌──────────────────────┐
    │   Scrape GMB Data    │
    │  (Coverage Grid)     │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Create Business     │◄───── Store: name, email, phone,
    │     (LEAD)           │       category, location, rating
    └──────────┬───────────┘
               │  contact_status='pending'
               │  website_status='none'
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      QUALIFICATION                                │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  AI Analysis         │
    │  Score: 0-100        │◄───── Factors: email?, rating,
    └──────────┬───────────┘       reviews, photo quality
               │
               ▼
        [qualification_score]
               │
               ▼
    ┌──────────────────────┐
    │  Generate Website    │
    └──────────┬───────────┘
               │  website_status='generated'
               │
               ▼
    ┌──────────────────────┐
    │   Create Site        │◄───── Link: business_id
    │   (PREVIEW)          │       status='preview'
    └──────────┬───────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      OUTREACH                                     │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  Start Campaign      │
    │  (Email or SMS)      │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Create Campaign     │◄───── Link: business_id, site_id
    │      Record          │       status='pending'
    └──────────┬───────────┘
               │  contact_status='emailed'
               │
               ▼
    ┌──────────────────────┐
    │   Send Message       │
    │  (SES/Twilio)        │
    └──────────┬───────────┘
               │
               ▼
        [Webhooks Update]
               │
               ├─► Delivered → campaign.delivered_at
               ├─► Opened → campaign.opened_at
               │            contact_status='opened'
               ├─► Clicked → campaign.clicked_at
               │             contact_status='clicked'
               └─► Replied → campaign.replied_at
                            contact_status='replied'
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      CONVERSION                                   │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  Customer Visits     │
    │  Site Preview        │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Clicks "Purchase"   │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Completes Payment   │
    │  (Recurrente)        │
    └──────────┬───────────┘
               │  contact_status='purchased'
               │  website_status='sold'
               │
               ▼
    ┌──────────────────────┐
    │  Create Customer     │◄───── Link: business_id, site_id
    │      Record          │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Create Subscription │
    │      Record          │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Site Status:        │
    │  'active'            │
    └──────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                  CUSTOMER LIFECYCLE                               │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ├─► Active Subscription (recurring revenue)
           ├─► Support Tickets (ticket_system)
           ├─► Site Edits (edit_requests)
           └─► Renewals/Cancellations
```

---

## Sample CRM Dashboard Mockup

```
╔═══════════════════════════════════════════════════════════════════╗
║                    WEBMAGIC CRM DASHBOARD                         ║
╚═══════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────┐
│ PIPELINE OVERVIEW                                    [This Week] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Leads Scraped:  247  ──────►  Qualified: 186 (75%)            │
│                                     │                            │
│                                     ▼                            │
│                          Sites Generated: 142 (76%)             │
│                                     │                            │
│                                     ▼                            │
│                          Campaigns Sent: 142 (100%)             │
│                                     │                            │
│                          ├─► Opened: 89 (63%)                   │
│                          ├─► Clicked: 34 (24%)                  │
│                          └─► Replied: 12 (8%)                   │
│                                     │                            │
│                                     ▼                            │
│                          Purchased: 3 (2.1%)   💰 $1,485       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ LEADS BY STATUS                          [Filter ▼] [Actions ▼] │
├──────┬──────────────────────┬────────┬─────────────┬───────────┤
│ ☐    │ Business Name        │ Status │ Contact     │ Actions   │
├──────┼──────────────────────┼────────┼─────────────┼───────────┤
│ ☐    │ LA Plumbing Pros     │ 🟢 GEN │ 📧 Opened   │ 👁️ 📧 📞  │
│      │ Los Angeles, CA      │        │ 2 days ago  │           │
├──────┼──────────────────────┼────────┼─────────────┼───────────┤
│ ☐    │ Quick Fix Plumbing   │ 🟡 PEND│ ⏳ Pending  │ 🌐 📧 📞  │
│      │ Santa Monica, CA     │        │             │           │
├──────┼──────────────────────┼────────┼─────────────┼───────────┤
│ ☐    │ Elite Plumbers Inc   │ 🔵 SOLD│ ✅ Purchased│ 👁️ 💬 📊  │
│      │ Beverly Hills, CA    │        │ 1 week ago  │           │
└──────┴──────────────────────┴────────┴─────────────┴───────────┘

Legend:
🟢 Generated  🟡 Pending  🔵 Sold  🔴 Archived
👁️ View  🌐 Generate Site  📧 Email  📞 Call  💬 Message  📊 Analytics

┌─────────────────────────────────────────────────────────────────┐
│ QUICK ACTIONS                                                    │
├─────────────────────────────────────────────────────────────────┤
│  [Start Campaign with Selected]  [Export to CSV]  [Bulk Update] │
└─────────────────────────────────────────────────────────────────┘
```

---

## Immediate Action Items

### 1. **Create Business Record for Plumbing Site** (Today)

```python
# Run this migration to fix orphaned site:
INSERT INTO businesses (
    id,
    name,
    slug,
    email,
    phone,
    city,
    state,
    country,
    category,
    contact_status,
    website_status,
    created_at
) VALUES (
    gen_random_uuid(),
    'Los Angeles Plumbing Pros',
    'la-plumbing-pros-business',
    'info@laplumbingpros.com',  -- If known
    '(310) 861-9785',
    'Los Angeles',
    'CA',
    'US',
    'Plumber',
    'pending',
    'generated',
    NOW()
) RETURNING id;

-- Link to existing site
UPDATE sites 
SET business_id = [business_id_from_above]
WHERE slug = 'la-plumbing-pros';
```

### 2. **Update Site Generation Service** (This Week)

Ensure `services/builder/` creates Business records BEFORE creating sites.

### 3. **Build CRM API Endpoints** (Week 1-2)

Start with Phase 2 endpoints above.

### 4. **Setup Webhook Status Sync** (Week 2)

Implement Phase 3 webhook handlers.

### 5. **Build CRM Frontend** (Week 3-4)

Create admin CRM dashboard interface.

---

## Cost-Benefit Analysis

### Without CRM
- ❌ No visibility into sales funnel
- ❌ Manual tracking required
- ❌ Can't measure conversion rates
- ❌ Can't identify bottlenecks
- ❌ Can't start targeted campaigns
- ❌ Lost revenue from poor follow-up

### With CRM
- ✅ Complete funnel visibility
- ✅ Automated status tracking
- ✅ Data-driven decisions
- ✅ Targeted campaign management
- ✅ Higher conversion rates
- ✅ Better customer retention
- ✅ Revenue forecasting
- ✅ ROI measurement per campaign

### Estimated Impact
- **Conversion Rate Improvement:** 2-3x (industry average with CRM)
- **Time Saved:** 10-15 hours/week on manual tracking
- **Revenue Impact:** $5k-$15k additional MRR within 3 months

---

## Next Steps

1. **Review this analysis** with your team
2. **Decide on priority** (I recommend immediate Phase 1 + Phase 2)
3. **Assign resources** (1 developer can complete Phase 1-3 in 2-3 weeks)
4. **Create sprint plan** (break into 2-week sprints)
5. **Set success metrics** (conversion rate, time-to-first-contact, etc.)

---

## Questions to Discuss

1. What's your current manual process for tracking leads?
2. What's your target conversion rate (scraped → purchased)?
3. Should we prioritize email or SMS campaigns first?
4. Do you want to import existing business data?
5. What CRM filters are most important to you?
6. Should we build mobile app later or web-only first?

---

**Status:** Ready for implementation  
**Priority:** HIGH (Revenue-critical feature)  
**Estimated Effort:** 3-4 weeks full-time development  
**Dependencies:** None (all infrastructure exists)  

**Created:** January 22, 2026  
**Last Updated:** January 22, 2026

