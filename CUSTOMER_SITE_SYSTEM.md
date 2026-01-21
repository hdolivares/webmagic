# 🌐 Customer Site System - Complete Specification

**Version:** 1.0  
**Date:** January 21, 2026  
**Status:** In Development

---

## 📋 Table of Contents

1. [Business Model](#business-model)
2. [Customer Journey](#customer-journey)
3. [Technical Architecture](#technical-architecture)
4. [Database Schema](#database-schema)
5. [API Endpoints](#api-endpoints)
6. [Implementation Phases](#implementation-phases)
7. [Pricing Structure](#pricing-structure)

---

## 🎯 Business Model

### Core Offering

WebMagic provides **fully-managed AI-generated websites** with three key components:

1. **Initial Purchase:** $495 one-time fee
   - Site ownership
   - Initial deployment
   - Custom domain setup included

2. **Monthly Subscription:** $95/month
   - Site stays online (hosting)
   - AI-powered edits (text, styles, images)
   - Custom domain included
   - Email support
   - Site stays live as long as subscription is active

3. **Advanced Features:** Custom quotes
   - Ecommerce conversion
   - Complex functionality
   - Third-party integrations

### Key Differentiators

- **Zero technical knowledge required** - Customers never access VPS or code
- **AI-powered edits** - Natural language requests for changes
- **Fully managed** - We handle hosting, domains, SSL, everything
- **Preview before purchase** - Free preview at `sites.lavish.solutions/{slug}`

---

## 🚀 Customer Journey

```
┌─────────────────────────────────────────────────────────────┐
│                    CUSTOMER JOURNEY                          │
└─────────────────────────────────────────────────────────────┘

STEP 1: SITE GENERATION (Admin-initiated)
├── Admin scrapes/collects business data
├── AI generates complete website
├── Site deployed to: sites.lavish.solutions/business-name
└── Status: PREVIEW

STEP 2: PREVIEW SHARING
├── Admin sends preview link to potential customer
├── Customer reviews site in browser
└── Customer decides to purchase or pass

STEP 3: PURCHASE ($495 one-time)
├── Customer clicks "Purchase This Site"
├── Payment via Recurrente
├── Customer creates account (email + password)
├── Status: OWNED
└── Customer receives welcome email + portal access

STEP 4: SUBSCRIPTION ACTIVATION ($95/month)
├── Customer logs into portal
├── Activates monthly subscription
├── Site goes LIVE
├── Status: ACTIVE
└── Custom domain setup becomes available

STEP 5: ONGOING MANAGEMENT
├── Customer uses portal to:
│   ├── View live site
│   ├── Request AI edits
│   ├── Setup custom domain
│   ├── Manage billing
│   └── Contact support
└── Monthly billing continues

STEP 6: SUBSCRIPTION MANAGEMENT
├── Active: Site stays live, edits available
├── Cancelled: Grace period (30 days), then suspended
├── Past Due: Grace period (7 days), then suspended
└── Suspended: Site offline until reactivated
```

---

## 🏗️ Technical Architecture

### URL Structure

```
FREE PREVIEW (Before Purchase)
└── https://sites.lavish.solutions/la-plumbing-pros
    ├── Path-based hosting
    ├── Single nginx server block
    └── Free SSL (Let's Encrypt for sites.lavish.solutions)

ACTIVE SITE (After Purchase + Subscription)
├── Default URL: https://sites.lavish.solutions/la-plumbing-pros
└── Custom Domain: https://www.laplumbingpros.com
    ├── Customer configures DNS
    ├── We provision SSL (Let's Encrypt per domain)
    └── Nginx creates dedicated server block
```

### Nginx Configuration Strategy

**Path-Based Hosting (Free Preview & Default)**
```nginx
# Single server block for all sites
server {
    listen 443 ssl http2;
    server_name sites.lavish.solutions;
    
    ssl_certificate /etc/letsencrypt/live/sites.lavish.solutions/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sites.lavish.solutions/privkey.pem;
    
    # Dynamic routing based on path
    location ~ ^/([a-z0-9-]+)(/.*)?$ {
        alias /var/www/sites/$1$2;
        try_files $uri $uri/ /index.html;
    }
}
```

**Custom Domain (Paid Feature)**
```nginx
# Dedicated server block per custom domain
server {
    listen 443 ssl http2;
    server_name laplumbingpros.com www.laplumbingpros.com;
    
    ssl_certificate /etc/letsencrypt/live/laplumbingpros.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/laplumbingpros.com/privkey.pem;
    
    root /var/www/sites/la-plumbing-pros;
    index index.html;
}
```

### File System Structure

```
/var/www/sites/
├── la-plumbing-pros/
│   ├── index.html
│   ├── assets/
│   │   ├── css/
│   │   │   └── main.css
│   │   ├── js/
│   │   │   └── main.js
│   │   └── images/
│   │       ├── hero.png
│   │       └── logo.png
│   └── versions/  # Version history
│       ├── v1/
│       ├── v2/
│       └── v3/
├── sunset-spa/
└── ... (other sites)
```

---

## 📊 Database Schema

### Sites Table (Main)

```sql
CREATE TABLE sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(255) UNIQUE NOT NULL,  -- URL-safe identifier
    business_id UUID REFERENCES businesses(id),
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'preview',  -- preview, owned, active, suspended, cancelled
    
    -- Purchase info
    purchased_at TIMESTAMP,
    purchase_amount DECIMAL(10, 2) DEFAULT 495.00,
    purchase_transaction_id VARCHAR(255),  -- Recurrente charge ID
    
    -- Subscription info
    subscription_status VARCHAR(50),  -- active, cancelled, past_due, suspended
    subscription_id VARCHAR(255),  -- Recurrente subscription ID
    subscription_started_at TIMESTAMP,
    subscription_ends_at TIMESTAMP,  -- For cancelled subscriptions
    monthly_amount DECIMAL(10, 2) DEFAULT 95.00,
    next_billing_date DATE,
    
    -- Custom domain
    custom_domain VARCHAR(255) UNIQUE,
    domain_verified BOOLEAN DEFAULT FALSE,
    domain_verification_token VARCHAR(255),
    domain_verified_at TIMESTAMP,
    ssl_provisioned BOOLEAN DEFAULT FALSE,
    ssl_certificate_path VARCHAR(500),
    ssl_provisioned_at TIMESTAMP,
    
    -- Site metadata
    current_version_id UUID,
    site_title VARCHAR(255),
    site_description TEXT,
    meta_tags JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_slug (slug),
    INDEX idx_status (status),
    INDEX idx_subscription_status (subscription_status),
    INDEX idx_custom_domain (custom_domain)
);
```

### Site Versions Table

```sql
CREATE TABLE site_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID REFERENCES sites(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    
    -- Content
    html_content TEXT NOT NULL,
    css_content TEXT,
    js_content TEXT,
    assets JSONB,  -- {images: [...], fonts: [...]}
    
    -- Metadata
    change_description TEXT,
    change_type VARCHAR(50),  -- initial, edit, major_update
    created_by_type VARCHAR(50),  -- admin, customer, ai
    created_by_id UUID,
    
    -- Status
    is_current BOOLEAN DEFAULT FALSE,
    is_preview BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(site_id, version_number),
    INDEX idx_site_current (site_id, is_current)
);
```

### Edit Requests Table

```sql
CREATE TABLE edit_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID REFERENCES sites(id) ON DELETE CASCADE,
    
    -- Request details
    request_text TEXT NOT NULL,  -- Natural language: "Change hero to..."
    request_type VARCHAR(50),  -- text, style, image, layout, content
    target_section VARCHAR(100),  -- hero, about, services, etc.
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, ready_for_review, approved, rejected, deployed
    
    -- AI processing
    ai_interpretation JSONB,  -- What the AI understood
    ai_confidence DECIMAL(3, 2),  -- 0.00 to 1.00
    changes_made JSONB,  -- Detailed list of changes
    
    -- Preview
    preview_version_id UUID REFERENCES site_versions(id),
    preview_url VARCHAR(500),
    
    -- Approval workflow
    customer_approved BOOLEAN,
    customer_feedback TEXT,
    approved_at TIMESTAMP,
    rejected_reason TEXT,
    
    -- Deployment
    deployed_version_id UUID REFERENCES site_versions(id),
    deployed_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    
    INDEX idx_site_status (site_id, status)
);
```

### Customer Users Table

```sql
CREATE TABLE customer_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Profile
    full_name VARCHAR(255),
    phone VARCHAR(50),
    
    -- Site ownership
    site_id UUID REFERENCES sites(id),
    
    -- Auth
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    email_verified_at TIMESTAMP,
    
    -- Password reset
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP,
    
    -- Activity
    last_login TIMESTAMP,
    login_count INTEGER DEFAULT 0,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_email (email),
    INDEX idx_site_id (site_id)
);
```

### Domain Verification Records Table

```sql
CREATE TABLE domain_verification_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID REFERENCES sites(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    
    -- Verification method
    verification_method VARCHAR(50) NOT NULL,  -- dns_txt, dns_cname, file_upload
    verification_token VARCHAR(255) NOT NULL,
    
    -- Status
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,
    verification_attempts INTEGER DEFAULT 0,
    last_check_at TIMESTAMP,
    
    -- DNS records found
    dns_records JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    
    INDEX idx_site_domain (site_id, domain)
);
```

---

## 🔌 API Endpoints

### Public Endpoints (No Auth)

```
POST   /api/v1/sites/{slug}/purchase
POST   /api/v1/customer/register
POST   /api/v1/customer/login
POST   /api/v1/customer/verify-email
POST   /api/v1/customer/forgot-password
POST   /api/v1/customer/reset-password
```

### Customer Endpoints (Customer Auth Required)

```
# Site Management
GET    /api/v1/customer/my-site
GET    /api/v1/customer/site/versions
POST   /api/v1/customer/site/subscribe
PUT    /api/v1/customer/site/cancel-subscription
GET    /api/v1/customer/site/billing-history

# Edit Requests
POST   /api/v1/customer/site/request-edit
GET    /api/v1/customer/site/edit-requests
GET    /api/v1/customer/site/edit-requests/{id}
POST   /api/v1/customer/site/edit-requests/{id}/approve
POST   /api/v1/customer/site/edit-requests/{id}/reject

# Custom Domain
POST   /api/v1/customer/site/setup-domain
GET    /api/v1/customer/site/domain-status
POST   /api/v1/customer/site/verify-domain
DELETE /api/v1/customer/site/remove-domain

# Profile
GET    /api/v1/customer/profile
PUT    /api/v1/customer/profile
PUT    /api/v1/customer/change-password
```

### Admin Endpoints (Admin Auth Required)

```
# Site Management (existing + new)
POST   /api/v1/sites/generate
GET    /api/v1/sites
GET    /api/v1/sites/{id}
PUT    /api/v1/sites/{id}
DELETE /api/v1/sites/{id}

# Customer Management
GET    /api/v1/admin/customers
GET    /api/v1/admin/customers/{id}
PUT    /api/v1/admin/customers/{id}
POST   /api/v1/admin/customers/{id}/send-message

# Edit Requests (Admin Override)
GET    /api/v1/admin/edit-requests
POST   /api/v1/admin/edit-requests/{id}/process
POST   /api/v1/admin/edit-requests/{id}/deploy

# Analytics
GET    /api/v1/admin/analytics/revenue
GET    /api/v1/admin/analytics/subscriptions
GET    /api/v1/admin/analytics/churn
```

---

## 📅 Implementation Phases

### Phase 1: Path-Based Hosting (Week 1)
**Goal:** Get sites working at `sites.lavish.solutions/{slug}`

- [ ] Update nginx configuration
- [ ] Update backend config (`SITES_BASE_URL`)
- [ ] Update site deployment service
- [ ] Create `sites` table migration
- [ ] Test with LA Plumbing site
- [ ] Verify SSL works

### Phase 2: Purchase Flow (Week 2)
**Goal:** Customers can purchase sites

- [ ] Create purchase endpoint
- [ ] Integrate Recurrente one-time payment
- [ ] Create customer user system
- [ ] Email verification flow
- [ ] Welcome email template
- [ ] Test end-to-end purchase

### Phase 3: Subscription System (Week 3)
**Goal:** Monthly billing and site activation

- [ ] Create subscription endpoint
- [ ] Integrate Recurrente subscriptions
- [ ] Webhook handler for payment events
- [ ] Subscription status monitoring
- [ ] Auto-suspension for failed payments
- [ ] Customer portal (basic)

### Phase 4: AI Edit System (Week 4)
**Goal:** Customers can request AI-powered edits

- [ ] Create `EditAgent` AI agent
- [ ] Implement edit request workflow
- [ ] Preview generation system
- [ ] Approval workflow
- [ ] Deploy approved changes
- [ ] Version history UI

### Phase 5: Custom Domain (Week 5)
**Goal:** Customers can use their own domains

- [ ] DNS verification system
- [ ] SSL certificate automation (Certbot)
- [ ] Nginx config generator
- [ ] Domain setup UI
- [ ] Health monitoring
- [ ] Documentation for customers

### Phase 6: Polish & Launch (Week 6)
**Goal:** Production-ready system

- [ ] Customer portal (complete)
- [ ] Admin dashboard updates
- [ ] Email templates (all scenarios)
- [ ] Error handling & logging
- [ ] Load testing
- [ ] Documentation
- [ ] Beta launch

---

## 💰 Pricing Structure

### Customer Pricing

| Item | Price | Frequency | Description |
|------|-------|-----------|-------------|
| **Site Purchase** | $495 | One-time | Site ownership, initial deployment |
| **Hosting + Edits** | $95 | Monthly | Hosting, AI edits, custom domain, support |
| **Ecommerce Upgrade** | Custom | One-time | Conversion to full ecommerce site |

### Revenue Projections

**Scenario: 100 Active Sites**
- Purchase revenue: $49,500 (one-time)
- Monthly recurring: $9,500/month
- Annual recurring: $114,000/year

**Scenario: 500 Active Sites**
- Purchase revenue: $247,500 (one-time)
- Monthly recurring: $47,500/month
- Annual recurring: $570,000/year

### Cost Analysis (per site)

| Item | Cost | Frequency |
|------|------|-----------|
| AI Generation | ~$2 | One-time |
| Hosting | ~$0.10 | Monthly |
| SSL Certificate | Free | (Let's Encrypt) |
| Domain (customer's) | $0 | (Customer owns) |
| **Total Cost** | ~$2.10 | First month |
| **Profit Margin** | **~99%** | After first month |

---

## 🔒 Security Considerations

### Customer Data
- All passwords hashed with bcrypt
- Email verification required
- Password reset with token expiry
- Rate limiting on auth endpoints

### Payment Security
- Never store credit card details
- All payments via Recurrente (PCI compliant)
- Webhook signature verification
- Transaction ID logging

### Site Security
- Customer sites isolated (separate directories)
- No code execution from customer input
- AI-generated code sanitized
- XSS protection in edit requests

### Domain Security
- Domain ownership verification required
- SSL certificates per domain
- Nginx security headers
- DDoS protection (via Cloudflare)

---

## 📧 Email Templates Required

1. **Welcome Email** (Post-purchase)
2. **Subscription Activated** (Site goes live)
3. **Edit Request Processed** (Preview ready)
4. **Edit Deployed** (Changes live)
5. **Payment Successful** (Monthly billing)
6. **Payment Failed** (Retry warning)
7. **Subscription Cancelled** (Confirmation)
8. **Site Suspended** (Past due)
9. **Custom Domain Setup** (Instructions)
10. **Domain Verified** (SSL provisioned)

---

## 🎨 Customer Portal Features

### Dashboard
- Site preview thumbnail
- Quick stats (visitors, uptime)
- Quick actions (request edit, view site)

### My Site
- Live site iframe preview
- Current version info
- View on custom domain button

### Request Edit
- Natural language input
- Section selector
- Example requests
- Edit history

### Custom Domain
- Current domain display
- Setup wizard
- DNS verification status
- SSL certificate status

### Billing
- Current subscription status
- Next billing date
- Payment method
- Invoice history
- Update payment method
- Cancel subscription

### Support
- Contact form
- FAQ section
- Request ecommerce evaluation
- View tickets

---

## 🚦 Status Definitions

### Site Status
- **preview**: Generated, not purchased (free preview)
- **owned**: Purchased, no active subscription
- **active**: Purchased + active subscription (live)
- **suspended**: Subscription past due or cancelled
- **cancelled**: Customer requested cancellation

### Subscription Status
- **active**: Paid and current
- **past_due**: Payment failed, in grace period
- **cancelled**: Customer cancelled, in grace period
- **suspended**: Subscription ended, site offline

### Edit Request Status
- **pending**: Just submitted
- **processing**: AI is working on it
- **ready_for_review**: Preview available
- **approved**: Customer approved, ready to deploy
- **rejected**: Customer rejected changes
- **deployed**: Changes are live

---

## 📈 Success Metrics

### Key Performance Indicators (KPIs)

1. **Conversion Rate**: Preview → Purchase
2. **Subscription Retention**: Monthly churn rate
3. **Edit Requests**: Average per customer per month
4. **Customer Satisfaction**: NPS score
5. **Time to Live**: Preview to active site
6. **Custom Domain Adoption**: % of customers using own domain

### Target Metrics (First 6 Months)

- Conversion Rate: 20%
- Monthly Churn: <5%
- Avg Edit Requests: 2-3/month
- Time to Live: <24 hours
- Custom Domain: 40%

---

## 🛠️ Development Best Practices

### Code Standards

1. **Modular Architecture**
   - Single responsibility principle
   - Reusable components
   - Clear separation of concerns

2. **Readable Functions**
   - Functions < 50 lines
   - Clear naming conventions
   - Comprehensive docstrings

3. **Semantic CSS**
   - CSS variables for theming
   - BEM naming convention
   - Reusable utility classes

4. **Error Handling**
   - Comprehensive try/catch
   - Detailed logging
   - User-friendly error messages

5. **Testing**
   - Unit tests for business logic
   - Integration tests for APIs
   - E2E tests for critical flows

---

**Document Version:** 1.0  
**Last Updated:** January 21, 2026  
**Next Review:** February 1, 2026
