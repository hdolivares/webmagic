# Purchase Flow Testing Guide

## ✅ Test Site is Ready!

Your $1 test site is now fully configured and ready for testing the complete purchase flow.

### Test Site Details

| Property | Value |
|----------|-------|
| **Test Page URL** | `https://web.lavish.solutions/site-preview/test-cpa-site` |
| **Site Title** | Marshall Campbell & Co., CPA's - Test Site ($1) |
| **One-Time Price** | **$1.00** |
| **Monthly Hosting** | $1.00/month |
| **Status** | `preview` (ready for purchase) |

## 🧪 How to Test the Complete Flow

### Step 1: Access the Preview Page

Navigate to: **`https://web.lavish.solutions/site-preview/test-cpa-site`**

**Note**: If you see "Site Not Found", hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R) to clear your browser cache.

### Step 2: Click "Claim This Site" Button

The page will show:
- ✨ AI-Generated Website badge
- Site title and description
- Features list (Lightning Fast, Secure & Reliable, Fully Customizable)
- Pricing: $1.00 one-time + $1.00/mo hosting
- **Big "Claim This Site" button**

### Step 3: Enter Your Details

After clicking "Claim This Site", a form appears:
- **Full Name**: Enter your name
- **Email Address**: Enter your test email
- View pricing breakdown
- Click **"Continue to Payment"**

### Step 4: Complete Payment on Recurrente

You'll be redirected to Recurrente's payment page:
- Amount: **$1.00 USD**
- Enter payment details (use test card if in test mode)
- Complete the payment

### Step 5: Verify Purchase Success

After payment:
- ✅ Redirected to success page (`/purchase-success`)
- ✅ Success message with site details
- ✅ "Check your email" instructions
- ✅ Auto-redirect to customer login (10 second countdown)

## 🔍 Backend Verification

### What Happens Behind the Scenes

When you complete the $1 payment, the backend will:

1. **Receive Webhook** from Recurrente
   - Endpoint: `/api/v1/webhooks/recurrente`
   - Payment verification

2. **Create/Update Customer Account**
   ```sql
   -- New customer record created
   SELECT * FROM customer_users WHERE email = 'your-email@example.com';
   ```

3. **Transfer Site Ownership**
   ```sql
   -- Site status changes to 'owned'
   UPDATE sites SET 
     status = 'owned',
     purchased_at = NOW(),
     purchase_transaction_id = '<recurrente_id>'
   WHERE slug = 'test-cpa-site';
   ```

4. **Create Ownership Record**
   ```sql
   -- Links customer to site
   SELECT * FROM customer_site_ownership 
   WHERE site_id = '596ef3e8-bb81-48ac-8688-1cb4c26cc21a';
   ```

5. **Record Payment**
   ```sql
   -- Payment record created
   SELECT * FROM payments 
   WHERE recurrente_payment_id = '<checkout_id>';
   ```

6. **Send Welcome Email**
   - Login credentials
   - Dashboard link
   - Next steps

## 📊 Verify After Purchase

### Check Site Status
```sql
SELECT 
    slug,
    status,
    purchase_amount,
    purchased_at,
    purchase_transaction_id
FROM sites
WHERE slug = 'test-cpa-site';
```

**Expected**: status = `'owned'`, purchased_at = timestamp

### Check Customer Account
```sql
SELECT 
    id,
    email,
    hashed_password,
    created_at,
    last_login
FROM customer_users
WHERE email = 'your-test-email@example.com';
```

**Expected**: New customer record with hashed password

### Check Ownership
```sql
SELECT 
    cu.email,
    s.slug,
    cso.created_at as ownership_created
FROM customer_site_ownership cso
JOIN customer_users cu ON cso.customer_id = cu.id
JOIN sites s ON cso.site_id = s.id
WHERE s.slug = 'test-cpa-site';
```

**Expected**: Ownership record linking customer to site

## 🔄 Reset for Another Test

If you want to test again:

```sql
-- Reset site to preview
UPDATE sites
SET 
    status = 'preview',
    purchased_at = NULL,
    purchase_transaction_id = NULL
WHERE slug = 'test-cpa-site';

-- Delete test customer (optional)
DELETE FROM customer_users WHERE email = 'test@example.com';

-- Delete ownership
DELETE FROM customer_site_ownership 
WHERE site_id = '596ef3e8-bb81-48ac-8688-1cb4c26cc21a';
```

## 🎯 Test Scenarios

### Scenario 1: New Customer Purchase
- Use a new email address
- Complete $1 payment
- Verify new customer account created
- Verify welcome email sent

### Scenario 2: Existing Customer Purchase
- Use email of existing customer
- Complete payment
- Verify site added to existing account (no new user created)

### Scenario 3: Payment Failure
- Use a test card that declines
- Verify site stays in `preview` status
- Verify no ownership created

### Scenario 4: Duplicate Purchase Attempt
- Try to purchase same site twice
- Should get error: "Site is not available for purchase"

## 🐛 Troubleshooting

### "Site Not Found" Error
- **Clear browser cache** (Ctrl+Shift+R)
- Verify API endpoint: `curl https://api.lavish.solutions/api/v1/sites/public/test-cpa-site`
- Check site exists: `SELECT * FROM sites WHERE slug = 'test-cpa-site'`

### Checkout Creation Fails
- Check Recurrente API credentials in `system_settings` table
- Check API logs: `tail -100 /var/log/webmagic/api.log`

### Webhook Not Processed
- Check webhook URL configured in Recurrente dashboard
- Should be: `https://api.lavish.solutions/api/v1/webhooks/recurrente`
- Check webhook logs for errors

### Customer Can't Log In
- Verify email was sent with credentials
- Check customer record exists
- Try password reset flow

## ✅ Success Checklist

After completing the test purchase, verify:

- [ ] Site accessed at preview URL
- [ ] "Claim This Site" button appeared
- [ ] Form collected name and email
- [ ] Redirected to Recurrente ($1.00 displayed)
- [ ] Payment completed successfully
- [ ] Redirected to success page
- [ ] Site status changed to `owned` in database
- [ ] Customer account created
- [ ] Ownership record created
- [ ] Payment record created
- [ ] Welcome email sent (if email service configured)
- [ ] Customer can log in to dashboard

## 🚀 Ready to Test!

**Your test URL**: `https://web.lavish.solutions/site-preview/test-cpa-site`

1. Navigate to the URL
2. Click "Claim This Site"
3. Enter your details
4. Complete the $1 payment
5. Verify all backend processes work correctly

The entire purchase flow will be validated with just $1 instead of $495! 🎉
