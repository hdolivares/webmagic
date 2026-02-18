# Pricing Update - Test vs Production

## ✅ **Updated Successfully**

### **Test Site (For Development/Testing)**
```sql
UPDATE sites 
SET purchase_amount = 2.00, 
    monthly_amount = 1.00 
WHERE slug = 'test-cpa-site';
```

**Result:**
- ✅ Setup: $2 (one-time)
- ✅ Monthly: $1/month
- ✅ Safe for testing with real payment methods
- ✅ Total test cost: $2 upfront + $1 next month = $3

---

### **Production Sites**
All real generated sites will use optimized pricing:
- **Setup:** $497 (one-time)
- **Monthly:** $97/month

**Note:** The `generated_sites` table stores the site data, but pricing is configured in the `sites` table when a site is made available for purchase.

---

## 🎯 **Why Different Pricing for Test Site?**

1. **Development Testing:**
   - Need to test checkout flow frequently
   - Don't want to waste $497 each test
   - $2 is negligible for unlimited testing

2. **Payment Verification:**
   - Can test with real credit cards safely
   - Verify webhook flow end-to-end
   - Check subscription auto-creation

3. **Client Demos:**
   - Show clients how checkout works
   - Let them complete test purchase
   - Minimal cost for demonstration

---

## 📋 **Pricing Flow**

### **For Test Site:**
```
Customer pays: $2 today
Webhook creates: $1/month subscription starting in 30 days
Total Year 1: $2 + ($1 × 11) = $13
```

### **For Production Sites:**
```
Customer pays: $497 today  
Webhook creates: $97/month subscription starting in 30 days
Total Year 1: $497 + ($97 × 11) = $1,564
```

---

## 🚀 **Ready to Test**

**Test URL:** https://web.lavish.solutions/site-preview/test-cpa-site

**Expected Experience:**
1. Pricing shows: "$2 one-time + $1/month"
2. Checkout shows: ONE item = "$2"
3. Payment completes successfully
4. Webhook auto-creates $1/month subscription
5. Total charged today: **$2**
6. Next charge in 30 days: **$1**

---

## 📌 **Important Notes**

### **For Future Site Generation:**

When creating new sites for real customers, ensure the pricing defaults are set:

```python
# In site generation code
new_site = Site(
    slug=generated_slug,
    business_id=business_id,
    purchase_amount=497.00,  # Default production pricing
    monthly_amount=97.00,    # Default production pricing
    status='preview'
)
```

### **Special Cases:**

**Premium Locations:**
```python
if city in ['Beverly Hills', 'Manhattan', 'Malibu']:
    purchase_amount = 697.00
    monthly_amount = 127.00
```

**Promotional Pricing:**
```python
if is_launch_week:
    purchase_amount = 397.00  # $100 off
    monthly_amount = 97.00    # Keep monthly same
```

---

## ✅ **Configuration Complete**

- ✅ Test site: $2 + $1/month
- ✅ Production strategy: $497 + $97/month  
- ✅ Documentation created
- ✅ Ready for testing

**Go ahead and test the checkout flow with the $2 test payment!** 🎉
