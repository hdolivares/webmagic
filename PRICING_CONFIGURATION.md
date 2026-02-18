# Pricing Configuration Guide

## 🎯 **Current Pricing Strategy**

### **Production Sites: $497 + $97/month**
All real generated sites use the optimal pricing based on psychology research:
- **Setup:** $497 (one-time)
- **Monthly:** $97/month

### **Test Site: $2 + $1/month**
For testing checkout flow without real charges:
- **Setup:** $2 (one-time)
- **Monthly:** $1/month
- **Site:** `test-cpa-site`

---

## 🔧 **How Pricing Is Configured**

### **Default Pricing (New Sites)**

When generating new sites, use these constants in your generation code:

```python
# backend/tasks/generation.py or similar
DEFAULT_PURCHASE_AMOUNT = 497.00  # $497 one-time
DEFAULT_MONTHLY_AMOUNT = 97.00    # $97/month
```

### **Database Structure**

```sql
-- sites table
CREATE TABLE sites (
    id UUID PRIMARY KEY,
    slug VARCHAR(100) UNIQUE NOT NULL,
    purchase_amount NUMERIC(10,2) DEFAULT 497.00,  -- One-time setup
    monthly_amount NUMERIC(10,2) DEFAULT 97.00,    -- Monthly hosting
    status VARCHAR(20) DEFAULT 'preview',
    -- ... other fields
);
```

### **Per-Site Override**

You can override pricing for specific sites:

```sql
-- Test site (low amounts)
UPDATE sites 
SET purchase_amount = 2.00, monthly_amount = 1.00 
WHERE slug = 'test-cpa-site';

-- Premium location (higher pricing)
UPDATE sites 
SET purchase_amount = 697.00, monthly_amount = 127.00 
WHERE city = 'Beverly Hills';

-- Promotional pricing
UPDATE sites 
SET purchase_amount = 397.00, monthly_amount = 77.00 
WHERE created_at > '2026-03-01'  -- March promotion
AND created_at < '2026-04-01';
```

---

## 📊 **Pricing Tiers (Future)**

### **Current: Single Tier**
```
Setup: $497
Monthly: $97
```

### **Planned: Multi-Tier (After 100 customers)**

**Starter:**
- Setup: $297
- Monthly: $77/month
- Features: 5 pages, basic SEO, standard support

**Professional:** (Current)
- Setup: $497
- Monthly: $97/month
- Features: Unlimited pages, advanced SEO, priority support

**Enterprise:**
- Setup: $997
- Monthly: $197/month
- Features: Multi-location, custom integrations, dedicated account manager

---

## 🧪 **Testing Pricing Changes**

### **For Testing:**

```sql
-- Update test site
UPDATE sites 
SET purchase_amount = 2.00, 
    monthly_amount = 1.00 
WHERE slug = 'test-cpa-site';
```

### **For Production Launch:**

```sql
-- Update all preview sites to new pricing
UPDATE sites 
SET purchase_amount = 497.00, 
    monthly_amount = 97.00 
WHERE status = 'preview' 
AND purchase_amount != 497.00;

-- Don't touch test site
UPDATE sites 
SET purchase_amount = 497.00, 
    monthly_amount = 97.00 
WHERE status = 'preview' 
AND slug != 'test-cpa-site';
```

---

## 💡 **A/B Testing Setup (After 10 Customers)**

### **Test Variants:**

```sql
-- Assign customers randomly to pricing groups
CREATE TABLE pricing_experiments (
    customer_id UUID,
    variant VARCHAR(20),  -- 'control', 'variant_a', 'variant_b'
    setup_amount NUMERIC(10,2),
    monthly_amount NUMERIC(10,2),
    assigned_at TIMESTAMP DEFAULT NOW()
);

-- Control: $497 + $97 (50% of traffic)
INSERT INTO pricing_experiments (customer_id, variant, setup_amount, monthly_amount)
VALUES (customer_uuid, 'control', 497.00, 97.00);

-- Variant A: $495 + $97 (25% of traffic)
INSERT INTO pricing_experiments (customer_id, variant, setup_amount, monthly_amount)
VALUES (customer_uuid, 'variant_a', 495.00, 97.00);

-- Variant B: $497 + $99 (25% of traffic)
INSERT INTO pricing_experiments (customer_id, variant, setup_amount, monthly_amount)
VALUES (customer_uuid, 'variant_b', 497.00, 99.00);
```

---

## 📈 **Monitoring & Analytics**

### **Metrics to Track:**

```sql
-- Conversion rate by pricing
SELECT 
    pricing_variant,
    COUNT(DISTINCT customer_id) as customers,
    COUNT(DISTINCT CASE WHEN status = 'owned' THEN id END) as purchased,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN status = 'owned' THEN id END) / 
          COUNT(DISTINCT customer_id), 2) as conversion_rate
FROM sites
JOIN pricing_experiments USING (customer_id)
GROUP BY pricing_variant;

-- Revenue by variant
SELECT 
    pricing_variant,
    SUM(purchase_amount) as setup_revenue,
    SUM(monthly_amount * 12) as annual_recurring_revenue,
    SUM(purchase_amount + (monthly_amount * 12)) as total_annual_revenue
FROM sites
JOIN pricing_experiments USING (customer_id)
WHERE status = 'owned'
GROUP BY pricing_variant;

-- Retention by variant
SELECT 
    pricing_variant,
    COUNT(*) as total_subscriptions,
    COUNT(CASE WHEN subscription_status = 'active' THEN 1 END) as active,
    COUNT(CASE WHEN subscription_status = 'cancelled' THEN 1 END) as cancelled,
    ROUND(100.0 * COUNT(CASE WHEN subscription_status = 'active' THEN 1 END) / 
          COUNT(*), 2) as retention_rate
FROM sites
JOIN pricing_experiments USING (customer_id)
WHERE subscription_status IS NOT NULL
GROUP BY pricing_variant;
```

---

## 🎯 **Current Configuration Summary**

| Site Type | Setup | Monthly | Purpose |
|-----------|-------|---------|---------|
| **Test Site** | $2 | $1/mo | Testing checkout flow |
| **Production Sites** | $497 | $97/mo | Optimal psychology pricing |

---

## ✅ **Updated Successfully**

- ✅ Test site: $2 + $1/month (for easy testing)
- ✅ Production sites: $497 + $97/month (optimized for conversion)
- ✅ Clear separation for testing vs real customers

---

## 🧪 **Ready to Test**

**Test URL:** https://web.lavish.solutions/site-preview/test-cpa-site

**Expected:**
- Pricing shows: "$2 one-time + $1/month"
- Checkout: ONE item = $2
- After payment: $1/month subscription auto-created
- Total test cost: $2 (safe for testing with real card)

**Try it now!** 🚀
