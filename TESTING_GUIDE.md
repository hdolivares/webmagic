# Testing Guide: Recurrente Checkout Integration

## ✅ Deployment Status

**Backend Changes:**
- ✅ Git pulled successfully (commit db7be9c)
- ✅ API service restarted (pid 991777)
- ✅ Files deployed:
  - `backend/services/payments/recurrente_models.py` (NEW)
  - `backend/services/payments/recurrente_client.py` (MODIFIED)
  - `backend/services/site_purchase_service.py` (MODIFIED)

---

## 🧪 Test Plan

### Test 1: Basic Checkout Flow

**URL to test:**
```
https://web.lavish.solutions/site-preview/test-cpa-site
```

**Expected Behavior:**

1. **Preview Page Loads**
   - ✅ Site details are displayed
   - ✅ "Claim This Site" form is visible
   - ✅ Form has email and name fields

2. **Form Submission**
   - Fill in:
     - Email: `test@example.com`
     - Name: `Test User`
   - Click "Claim This Site"
   - ✅ Button shows loading state
   - ✅ No console errors

3. **Redirect to Recurrente**
   - ✅ Redirects to `https://app.recurrente.com/checkout-session/ch_xxxxx`
   - ✅ Checkout page loads successfully

4. **Shopping Bag Contains Items**
   - ✅ **Item 1:** Website Setup - Test CPA Site ($1.00) - One-time
   - ✅ **Item 2:** Monthly Hosting - Test CPA Site ($1.00/month) - Subscription
   - ✅ Total amount shown correctly

5. **Test Payment (Sandbox Mode)**
   - Use test card: `4242 4242 4242 4242`
   - Expiry: Any future date (e.g., `12/26`)
   - CVV: Any 3 digits (e.g., `123`)
   - Fill in customer details
   - ✅ Payment processes successfully

6. **Success Redirect**
   - ✅ Redirects to: `https://web.lavish.solutions/purchase-success?slug=test-cpa-site`
   - ✅ Success message is displayed
   - ✅ Countdown timer works

---

## 🔍 What to Look For

### ✅ SUCCESS Indicators

1. **Shopping bag shows TWO items:**
   - One-time payment: $1.00
   - Monthly subscription: $1.00/month

2. **Form is pre-populated:**
   - Email field has `test@example.com`
   - Name field has `Test User`

3. **Payment completes successfully**

4. **Webhook is received:**
   - Check backend logs: `tail -f /var/www/webmagic/backend/logs/app.log`
   - Look for: `payment_intent.succeeded` webhook

### ❌ FAILURE Indicators

1. **Empty shopping bag** - This was the original issue, should be FIXED now

2. **API errors in browser console:**
   - Check: F12 → Console tab
   - Look for: 500 errors, 422 validation errors

3. **Backend errors:**
   - SSH into VPS
   - Check logs: `tail -f /var/www/webmagic/backend/logs/app.log`

---

## 🐛 Debugging

### If shopping bag is still empty:

1. **Check API request format:**
   ```bash
   # SSH to VPS
   tail -f /var/www/webmagic/backend/logs/app.log
   
   # Look for the checkout creation request
   # Should show: "Created purchase checkout for site test-cpa-site: ch_xxxxx"
   ```

2. **Check Recurrente API response:**
   ```bash
   # Look for debug logs showing:
   # - Request body with "items" array
   # - Response with checkout_id and checkout_url
   ```

3. **Verify Pydantic models are loaded:**
   ```bash
   cd /var/www/webmagic/backend
   source /var/www/webmagic/venv/bin/activate
   python -c "from services.payments.recurrente_models import CheckoutItem; print('OK')"
   ```

### If API returns 500 error:

1. **Check for import errors:**
   ```bash
   supervisorctl tail -f webmagic-api stderr
   ```

2. **Check for missing dependencies:**
   ```bash
   source /var/www/webmagic/venv/bin/activate
   pip list | grep pydantic
   ```

3. **Restart services:**
   ```bash
   supervisorctl restart webmagic-api
   supervisorctl restart webmagic-celery
   ```

---

## 📋 Test Checklist

- [ ] Preview page loads without errors
- [ ] Form fields are present (email, name)
- [ ] "Claim This Site" button works
- [ ] Redirects to Recurrente checkout page
- [ ] **CRITICAL:** Shopping bag shows TWO items (one-time + subscription)
- [ ] Customer form is pre-populated with email and name
- [ ] Test card payment completes successfully
- [ ] Redirects to success page
- [ ] Success page shows site details
- [ ] Backend logs show checkout creation
- [ ] Webhook is received (payment_intent.succeeded)

---

## 📊 Expected API Request Format

When you click "Claim This Site", the backend should send this to Recurrente:

```json
{
  "items": [
    {
      "name": "Website Setup - Test CPA Site",
      "amount_in_cents": 100,
      "currency": "USD",
      "quantity": 1,
      "charge_type": "one_time",
      "description": "One-time setup and customization for Test CPA Site"
    },
    {
      "name": "Monthly Hosting - Test CPA Site",
      "amount_in_cents": 100,
      "currency": "USD",
      "quantity": 1,
      "charge_type": "recurring",
      "billing_interval": "month",
      "billing_interval_count": 1,
      "description": "Monthly hosting, maintenance, and unlimited AI-powered updates",
      "periods_before_automatic_cancellation": null,
      "free_trial_interval_count": 0
    }
  ],
  "success_url": "https://web.lavish.solutions/purchase-success?slug=test-cpa-site",
  "cancel_url": "https://web.lavish.solutions/site-preview/test-cpa-site",
  "user_id": "us_xxxxx",
  "metadata": {
    "site_id": "596ef3e8-bb81-48ac-8688-1cb4c26cc21a",
    "site_slug": "test-cpa-site",
    "site_url": "https://sites.lavish.solutions/test-cpa-site",
    "purchase_type": "website",
    "customer_email": "test@example.com",
    "setup_amount_usd": "1.00",
    "monthly_amount_usd": "1.00"
  }
}
```

---

## 🎯 Success Criteria

The fix is successful when:

1. ✅ Shopping bag shows **both** items (one-time + subscription)
2. ✅ No empty shopping bag error
3. ✅ Customer can complete test payment
4. ✅ Both payments are recorded in Recurrente dashboard:
   - One-time payment: $1.00 (status: paid)
   - Subscription: $1.00/month (status: active)

---

## 📞 Support

If you encounter issues:

1. **Check backend logs** for detailed error messages
2. **Verify API keys** in `/var/www/webmagic/backend/.env`
3. **Test API connection** with curl:
   ```bash
   curl -X GET https://app.recurrente.com/api/test \
     -H "X-PUBLIC-KEY: pk_live_xxx" \
     -H "X-SECRET-KEY: sk_live_xxx" \
     -H "Content-Type: application/json"
   ```

4. **Contact Recurrente support:**
   - Email: soporte@recurrente.com
   - Discord: https://discord.gg/QhKPEkSKp2
