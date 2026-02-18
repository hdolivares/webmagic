# Recurrente Checkout Integration Fix

## Summary

Fixed the "empty shopping bag" error by implementing the correct Recurrente API format. The previous implementation was using incorrect field names and structure, causing Recurrente to reject the checkout request.

---

## Root Cause Analysis

### ❌ Previous (Incorrect) Implementation

```python
{
    "description": "Website Purchase - ...",
    "price": 49500,           # ❌ Wrong key name
    "currency": "USD",
    "recurrence_type": "once"  # ❌ Wrong key name
}
```

**Why it failed:**
- Recurrente API expects an `items` array, not flat fields
- Used `price` instead of `amount_in_cents`
- Used `recurrence_type` instead of `charge_type` in items
- Missing required `name` field

### ✅ Correct Implementation

```python
{
    "items": [  # ✅ Must be an array
        {
            "name": "Website Setup - ...",
            "amount_in_cents": 49500,  # ✅ Correct key name
            "currency": "USD",
            "quantity": 1,
            "charge_type": "one_time"  # ✅ Inside item
        }
    ],
    "success_url": "...",
    "cancel_url": "...",
    "metadata": {}
}
```

---

## Solution Architecture

### 1. **Pydantic Models** (`recurrente_models.py`)

Created strongly-typed models for type safety and validation:

```python
class CheckoutItem(BaseModel):
    """Represents a single item in a checkout."""
    name: str
    amount_in_cents: int
    currency: Literal["USD", "GTQ"] = "USD"
    quantity: int = 1
    charge_type: Optional[Literal["one_time", "recurring"]] = None
    
    # Subscription-specific fields
    billing_interval: Optional[Literal["week", "month", "year"]] = None
    billing_interval_count: Optional[int] = None
    # ... more fields

class CheckoutRequest(BaseModel):
    """Full checkout request following Recurrente API format."""
    items: List[CheckoutItem]
    success_url: Optional[str]
    cancel_url: Optional[str]
    user_id: Optional[str]
    metadata: Optional[Dict[str, Any]]
```

**Benefits:**
- ✅ Type safety at compile time
- ✅ Automatic validation
- ✅ Self-documenting code
- ✅ Prevents API format errors

### 2. **Refactored RecurrenteClient** (`recurrente_client.py`)

#### New Methods

**`create_checkout(items, success_url, cancel_url, user_id, metadata)`**
- Low-level method that accepts CheckoutItem list
- Follows Recurrente API format exactly
- Returns CheckoutResponse object

**`create_one_time_checkout(...)`**
- Helper for one-time payments
- Automatically creates CheckoutItem with `charge_type="one_time"`
- Example: $495 website setup fee

**`create_subscription_checkout(...)`**
- Helper for recurring subscriptions
- Automatically creates CheckoutItem with `charge_type="recurring"`
- Requires `billing_interval` and `billing_interval_count`
- Example: $99/month hosting

**`get_or_create_user(email, full_name, phone)`**
- Creates Recurrente user to prepopulate checkout form
- Returns user_id for use in checkout
- Automatically returns existing user if already exists

### 3. **Updated SitePurchaseService** (`site_purchase_service.py`)

#### New `create_purchase_checkout()` Implementation

Now creates a checkout with **TWO items**:

1. **One-time setup payment:** $495
   ```python
   CheckoutItem(
       name="Website Setup - {site_title}",
       amount_in_cents=49500,
       currency="USD",
       charge_type="one_time"
   )
   ```

2. **Monthly subscription:** $99/month
   ```python
   CheckoutItem(
       name="Monthly Hosting - {site_title}",
       amount_in_cents=9900,
       currency="USD",
       charge_type="recurring",
       billing_interval="month",
       billing_interval_count=1
   )
   ```

**Flow:**
1. Get site from database
2. Validate site status is "preview"
3. Get or create Recurrente user (optional, prepopulates form)
4. Build two checkout items (one-time + subscription)
5. Create checkout via Recurrente API
6. Return checkout URL for redirect

---

## Code Quality Improvements

### ✅ Separation of Concerns

- **Models layer:** Data validation and structure (`recurrente_models.py`)
- **Client layer:** HTTP communication with Recurrente (`recurrente_client.py`)
- **Service layer:** Business logic for purchases (`site_purchase_service.py`)
- **API layer:** Request handling and response formatting (`site_purchase.py`)

### ✅ Modular Code

Each method has a single, clear responsibility:
- `CheckoutItem`: Validates single item structure
- `create_checkout()`: Low-level API call
- `create_one_time_checkout()`: High-level one-time helper
- `create_subscription_checkout()`: High-level subscription helper
- `create_purchase_checkout()`: Business logic for site purchase

### ✅ Readable Functions

- Clear, descriptive names
- Type hints on all parameters and returns
- Comprehensive docstrings with examples
- Inline comments explaining "why" not "what"

### ✅ Error Handling

- Pydantic validation catches bad data before API call
- Specific exception types (NotFoundError, ValidationError)
- Detailed logging at each step
- Graceful degradation (e.g., if user creation fails, continue without)

---

## Testing Guide

### Step 1: Test One-Time Payment Only

```bash
# Navigate to test site preview page
https://web.lavish.solutions/site-preview/test-cpa-site

# Fill in form:
# Email: test@example.com
# Name: Test User

# Click "Claim This Site"
# You should be redirected to Recurrente checkout page
# The shopping bag should show:
# - Website Setup - {site_title}: $495.00
# - Monthly Hosting - {site_title}: $99.00/month
```

### Step 2: Complete Test Payment

```bash
# On Recurrente checkout page:
# Use test card: 4242 4242 4242 4242
# Any future expiry date (e.g., 12/26)
# Any CVV (e.g., 123)

# After successful payment:
# Should redirect to: https://web.lavish.solutions/purchase-success?slug=test-cpa-site
```

### Step 3: Verify in Recurrente Dashboard

```bash
# Login to https://app.recurrente.com
# Go to "Transacciones" (Transactions)
# You should see:
# 1. One-time payment of $495.00 - Status: Paid
# 2. Subscription created for $99.00/month - Status: Active
```

---

## API Reference

### POST `/api/v1/sites/{slug}/purchase`

**Request Body:**
```json
{
  "customer_email": "customer@example.com",
  "customer_name": "John Doe"
}
```

**Response:**
```json
{
  "checkout_id": "ch_xxxxx",
  "checkout_url": "https://app.recurrente.com/checkout-session/ch_xxxxx",
  "site_slug": "test-cpa-site",
  "site_title": "Test CPA Site",
  "setup_amount": 495.0,
  "monthly_amount": 99.0,
  "currency": "USD"
}
```

---

## Recurrente API Documentation References

- **Checkout creation (one-time):** Lines 228-374 of `recurrente-final-file.md`
- **Checkout creation (subscription):** Lines 377-570 of `recurrente-final-file.md`
- **User creation:** Lines 2662-2735 of `recurrente-final-file.md`
- **Webhooks:** Lines 2974-3612 of `recurrente-final-file.md`

---

## Files Modified

1. **NEW:** `backend/services/payments/recurrente_models.py` (191 lines)
   - Pydantic models for type safety

2. **MODIFIED:** `backend/services/payments/recurrente_client.py`
   - Added Literal import
   - Refactored `create_checkout()` to use items array
   - Added `create_one_time_checkout()` helper
   - Added `create_subscription_checkout()` helper
   - Updated `create_user()` to use `full_name` field

3. **MODIFIED:** `backend/services/site_purchase_service.py`
   - Updated `create_purchase_checkout()` to create TWO items
   - Added user creation before checkout
   - Improved error handling and logging
   - Better metadata for tracking

---

## Expected Behavior

### Before Fix
❌ Empty shopping bag error
❌ Checkout page shows no items
❌ User cannot complete purchase

### After Fix
✅ Checkout page shows two items:
   - Website Setup: $495.00 (one-time)
   - Monthly Hosting: $99.00/month (subscription)
✅ Customer can complete payment
✅ Both one-time payment and subscription are created in Recurrente

---

## Next Steps

1. **Test the checkout flow** with test credentials
2. **Verify webhook handling** for payment_intent.succeeded
3. **Update frontend** to display both amounts clearly
4. **Add email notifications** for purchase confirmation
5. **Implement subscription management** for customers

---

## Contact

For questions about this implementation:
- Recurrente API Docs: https://docs.recurrente.com
- Recurrente Support: soporte@recurrente.com
- Recurrente Discord: https://discord.gg/QhKPEkSKp2
