# Test Purchase Flow - $1 Test Site

## Test Site Created ✅

A test website has been set up for testing the complete purchase flow.

### Test Site Details

| Property | Value |
|----------|-------|
| **Site ID** | `596ef3e8-bb81-48ac-8688-1cb4c26cc21a` |
| **Slug** | `test-cpa-site` |
| **Title** | Marshall Campbell & Co., CPA's - Test Site ($1) |
| **Price** | **$1.00** (instead of normal $495) |
| **Status** | `preview` (available for purchase) |
| **Business** | Marshall Campbell & Co., CPA's |
| **Version ID** | `b3abd291-0474-4939-8a10-555cb7cc8c4d` |

## How to Test the Purchase Flow

### Option 1: API Testing (Direct)

#### Step 1: Create Checkout Session
```bash
curl -X POST https://api.lavish.solutions/api/v1/sites/test-cpa-site/purchase \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "test@example.com",
    "customer_name": "Test Customer",
    "success_url": "https://sites.lavish.solutions/purchase-success",
    "cancel_url": "https://sites.lavish.solutions/purchase-cancelled"
  }'
```

**Expected Response:**
```json
{
  "checkout_id": "recurrente_checkout_id",
  "checkout_url": "https://recurrente.com/checkout/...",
  "site_slug": "test-cpa-site",
  "site_title": "Marshall Campbell & Co., CPA's - Test Site ($1)",
  "amount": 1.0,
  "currency": "USD"
}
```

#### Step 2: Complete Payment
1. Open the `checkout_url` in your browser
2. Complete the Recurrente payment form ($1 charge)
3. After payment, Recurrente will send a webhook to your backend

### Option 2: Frontend Testing (User Journey)

#### Prerequisites
Check if there's a site preview/purchase page in the frontend. The typical flow would be:

1. **Visit Site Preview**
   - URL: `https://sites.lavish.solutions/test-cpa-site` (if routing is set up)
   - Or: `https://web.lavish.solutions/sites/preview/test-cpa-site`

2. **Click "Purchase This Site" Button**
   - Should trigger checkout creation
   - Redirect to Recurrente payment page

3. **Complete Payment**
   - Enter test card details (if Recurrente has test mode)
   - Complete $1 payment

4. **Post-Purchase**
   - Webhook processes payment
   - Customer account created
   - Site status changes to `owned`
   - Customer redirected to success page

## What Gets Tested

### Backend Processing ✅

1. **Checkout Creation**
   - ✅ Site exists and is in `preview` status
   - ✅ Recurrente checkout created with $1 amount
   - ✅ Metadata includes site_id, slug, and URL

2. **Webhook Processing**
   - ✅ Payment webhook received from Recurrente
   - ✅ Payment verified and processed
   - ✅ Customer user account created (if new)
   - ✅ Site ownership record created
   - ✅ Site status updated to `owned`
   - ✅ Purchase transaction recorded

3. **Customer Account**
   - ✅ Customer record created in `customer_users` table
   - ✅ Hashed password generated
   - ✅ Welcome email sent (if email service configured)
   - ✅ Customer can log in

4. **Site Access**
   - ✅ Site now owned by customer
   - ✅ Customer can access site dashboard
   - ✅ Customer can request edits

### Database Changes to Verify

After successful purchase, check these tables:

```sql
-- 1. Site status should be 'owned'
SELECT id, slug, status, purchased_at, purchase_amount, purchase_transaction_id
FROM sites
WHERE slug = 'test-cpa-site';

-- 2. Customer user should be created
SELECT id, email, created_at
FROM customer_users
WHERE email = 'test@example.com';

-- 3. Ownership record should exist
SELECT id, site_id, customer_id, created_at
FROM customer_site_ownership
WHERE site_id = '596ef3e8-bb81-48ac-8688-1cb4c26cc21a';

-- 4. Payment record should exist
SELECT id, recurrente_payment_id, status, amount, payment_type
FROM payments
WHERE recurrente_payment_id = '<checkout_id_from_webhook>';
```

## Test Payment Methods

### Recurrente Test Cards (if in test mode)
Check Recurrente documentation for test card numbers, typically:
- **Success**: Various test card numbers that complete payment
- **Decline**: Test cards that simulate failures

## Cleanup After Testing

To reset the test site for another test:

```sql
-- Reset site to preview status
UPDATE sites
SET 
    status = 'preview',
    purchased_at = NULL,
    purchase_transaction_id = NULL,
    subscription_status = NULL,
    subscription_id = NULL
WHERE slug = 'test-cpa-site';

-- Optionally delete test customer
DELETE FROM customer_users WHERE email = 'test@example.com';

-- Optionally delete ownership records
DELETE FROM customer_site_ownership 
WHERE site_id = '596ef3e8-bb81-48ac-8688-1cb4c26cc21a';
```

## Troubleshooting

### Issue: Checkout creation fails
- Check site exists: `SELECT * FROM sites WHERE slug = 'test-cpa-site';`
- Check site status is `preview`
- Check Recurrente API credentials in system_settings

### Issue: Webhook not received
- Check webhook URL is configured in Recurrente dashboard
- Check webhook endpoint: `/api/v1/webhooks/recurrente`
- Check API logs: `/var/log/webmagic/api.log`

### Issue: Customer can't log in
- Verify customer record exists
- Check email is correct
- Try password reset flow

## Additional Test Scenarios

### 1. Test with Existing Customer
- Create checkout with email of existing customer
- Should link site to existing account (not create new one)

### 2. Test Subscription (if enabled)
- After purchase, verify monthly subscription created
- Check `subscription_status`, `subscription_id`, `monthly_amount`

### 3. Test Custom Domain
- After purchase, customer adds custom domain
- Verify domain verification flow

### 4. Test Site Edits
- After purchase, customer requests edit
- Verify edit request flow works

## Success Criteria ✅

The purchase flow is working correctly if:

1. ✅ Checkout session created with $1 amount
2. ✅ Payment processed successfully via Recurrente
3. ✅ Webhook received and processed
4. ✅ Customer account created
5. ✅ Site ownership transferred
6. ✅ Site status updated to `owned`
7. ✅ Customer can log in
8. ✅ Customer can access their site
9. ✅ Payment recorded in database
10. ✅ No errors in API logs

## Next Steps

1. Complete a test purchase using the test site
2. Verify all backend processing works correctly
3. Check customer login and site access
4. Test any additional flows (subscriptions, edits, etc.)
5. Once validated, you can create more test sites or test with real pricing

---

**Test Site Ready!** 🎉

You can now test the complete purchase flow end-to-end with just a $1 payment instead of $495.
