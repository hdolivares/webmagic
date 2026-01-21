# 🚀 Phase 3: Subscription System ($95/Month)

**Start Date:** January 21, 2026  
**Estimated Time:** 4-6 hours  
**Goal:** Enable $95/month recurring billing for site hosting

---

## 🎯 PHASE 3 OBJECTIVES

### **Primary Goal:**
Enable customers to activate monthly subscriptions ($95/month) after purchasing their site ($495).

### **Key Features:**
1. ✅ Subscription activation endpoint
2. ✅ Recurring billing via Recurrente
3. ✅ Site status management (owned → active)
4. ✅ Billing date tracking
5. ✅ Subscription management (pause/cancel)
6. ✅ Payment failure handling
7. ✅ Grace period management
8. ✅ Email notifications

---

## 💰 BUSINESS MODEL (Current Implementation)

### **Customer Journey:**
```
Step 1: Purchase Site
   Cost: $495 one-time ✅ DONE (Phase 2)
   Status: preview → owned
   Access: Site preview only

Step 2: Activate Subscription (THIS PHASE)
   Cost: $95/month ⏳ TO IMPLEMENT
   Status: owned → active
   Access: Full site + custom domain + AI edits
```

### **Revenue Streams:**
```
One-Time Purchase:      $495  ✅ Working (Phase 2)
Monthly Subscription:    $95  ⏳ Phase 3
Custom Domain (Phase 5): included in subscription
AI Edits (Phase 4):      included in subscription
```

---

## 🏗️ ARCHITECTURE OVERVIEW

### **New Components:**
```
1. Subscription Service
   - Create subscription
   - Activate subscription
   - Update payment method
   - Cancel subscription
   - Handle payment failures

2. Subscription API Endpoints
   - POST   /api/v1/customer/subscription/activate
   - GET    /api/v1/customer/subscription
   - PUT    /api/v1/customer/subscription/payment-method
   - POST   /api/v1/customer/subscription/cancel
   - GET    /api/v1/admin/subscriptions

3. Webhook Handlers (extend existing)
   - subscription.activated
   - subscription.payment_succeeded
   - subscription.payment_failed
   - subscription.cancelled
   - subscription.expired

4. Email Templates
   - Subscription activated
   - Payment successful (monthly)
   - Payment failed
   - Subscription cancelled
   - Grace period warning
```

---

## 📊 DATABASE SCHEMA (Already exists from Phase 2!)

### **sites table** (already has subscription fields):
```sql
-- Subscription tracking
subscription_id          VARCHAR(255)
subscription_status      VARCHAR(50)   -- active, past_due, cancelled, expired
subscription_started_at  TIMESTAMP
subscription_ends_at     TIMESTAMP
next_billing_date        DATE
monthly_amount           NUMERIC(10,2)  -- $95.00
```

**No new tables needed!** ✅ All schema already in place.

---

## 🔄 SUBSCRIPTION LIFECYCLE

### **States:**
```
1. No Subscription (Initial)
   - Site status: owned
   - Customer can view site
   - Cannot use custom domain
   - Cannot request AI edits

2. Active Subscription
   - Site status: active
   - Full access granted
   - Custom domain enabled
   - AI edits available
   - Billing on next_billing_date

3. Past Due (Payment Failed)
   - Site status: active (grace period)
   - 7-day grace period
   - Warning emails sent
   - After grace: owned (downgrade)

4. Cancelled
   - Site status: owned
   - Billing stopped
   - Access until period end
   - Then downgrade to owned

5. Expired
   - Site status: owned
   - No active billing
   - Features disabled
   - Can reactivate
```

---

## 🛠️ IMPLEMENTATION TASKS

### **Task 1: Subscription Service** (150 lines)
```python
services/subscription_service.py

class SubscriptionService:
    @staticmethod
    async def create_subscription(
        db: AsyncSession,
        site_id: UUID,
        customer_id: UUID,
        payment_method_token: str
    ) -> Dict[str, Any]:
        """Create recurring subscription via Recurrente."""
        
    @staticmethod
    async def activate_subscription(
        db: AsyncSession,
        subscription_id: str,
        subscription_data: dict
    ) -> Site:
        """Activate subscription after Recurrente confirmation."""
        
    @staticmethod
    async def handle_payment_success(
        db: AsyncSession,
        subscription_id: str,
        payment_data: dict
    ) -> None:
        """Process successful recurring payment."""
        
    @staticmethod
    async def handle_payment_failure(
        db: AsyncSession,
        subscription_id: str,
        failure_data: dict
    ) -> None:
        """Handle failed payment (start grace period)."""
        
    @staticmethod
    async def cancel_subscription(
        db: AsyncSession,
        site_id: UUID,
        immediate: bool = False
    ) -> Site:
        """Cancel subscription (immediate or end of period)."""
        
    @staticmethod
    async def reactivate_subscription(
        db: AsyncSession,
        site_id: UUID
    ) -> Dict[str, Any]:
        """Reactivate cancelled subscription."""
```

### **Task 2: API Schemas** (100 lines)
```python
api/schemas/subscription.py

class SubscriptionActivateRequest:
    payment_method_token: str

class SubscriptionResponse:
    subscription_id: str
    status: str
    monthly_amount: float
    next_billing_date: date
    started_at: datetime

class SubscriptionCancelRequest:
    reason: Optional[str]
    immediate: bool = False
```

### **Task 3: API Endpoints** (200 lines)
```python
api/v1/subscriptions.py

@router.post("/customer/subscription/activate")
async def activate_subscription(...):
    """Activate $95/month subscription."""

@router.get("/customer/subscription")
async def get_subscription(...):
    """Get current subscription status."""

@router.post("/customer/subscription/cancel")
async def cancel_subscription(...):
    """Cancel subscription."""

@router.post("/customer/subscription/reactivate")
async def reactivate_subscription(...):
    """Reactivate cancelled subscription."""
```

### **Task 4: Webhook Extensions** (150 lines)
```python
api/v1/webhooks.py (extend existing)

async def handle_subscription_activated(...):
    """Process subscription activation from Recurrente."""

async def handle_subscription_payment_succeeded(...):
    """Process successful monthly payment."""

async def handle_subscription_payment_failed(...):
    """Handle failed payment, start grace period."""

async def handle_subscription_cancelled(...):
    """Process subscription cancellation."""
```

### **Task 5: Email Templates** (400 lines)
```python
services/emails/templates.py (extend existing)

def render_subscription_activated_email(...):
    """Congratulations! Your subscription is active."""

def render_subscription_payment_success_email(...):
    """Your monthly payment was successful."""

def render_subscription_payment_failed_email(...):
    """Payment failed - please update your payment method."""

def render_subscription_cancelled_email(...):
    """Your subscription has been cancelled."""

def render_grace_period_warning_email(...):
    """Your subscription will be suspended in X days."""
```

### **Task 6: Celery Tasks (Optional)** (100 lines)
```python
tasks/subscriptions.py

@celery_app.task
def check_grace_periods():
    """Check for expired grace periods daily."""

@celery_app.task
def send_billing_reminders():
    """Send reminder emails 3 days before billing."""

@celery_app.task
def process_subscription_renewals():
    """Update next_billing_date after successful payments."""
```

---

## 📝 ESTIMATED CODE

```
Subscription Service:        150 lines
API Schemas:                 100 lines
API Endpoints:               200 lines
Webhook Extensions:          150 lines
Email Templates:             400 lines
Celery Tasks (optional):     100 lines
Tests:                       150 lines

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL NEW CODE:           ~1,250 lines
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🧪 TESTING PLAN

### **Unit Tests:**
```
✓ Create subscription (Recurrente)
✓ Activate subscription
✓ Handle payment success
✓ Handle payment failure
✓ Cancel subscription
✓ Reactivate subscription
✓ Grace period logic
✓ Status transitions
```

### **Integration Tests:**
```
✓ Full activation flow
✓ Monthly billing cycle
✓ Payment failure recovery
✓ Cancellation workflow
✓ Webhook processing
✓ Email delivery
```

### **Manual Tests:**
```
✓ Test Recurrente subscription creation
✓ Test webhook receipt
✓ Test subscription dashboard
✓ Test cancellation flow
✓ Test reactivation
```

---

## 🔄 WORKFLOW DIAGRAMS

### **Activation Flow:**
```
Customer (owns site)
    ↓
Click "Activate Subscription" ($95/month)
    ↓
POST /api/v1/customer/subscription/activate
    ↓
Create subscription in Recurrente
    ↓
Return subscription_id + payment_method_url
    ↓
Customer enters payment method
    ↓
Recurrente webhook: subscription.activated
    ↓
Update site: status = active
Update site: subscription_id, subscription_status, started_at
Calculate: next_billing_date = started_at + 30 days
    ↓
Send: Subscription Activated Email
    ↓
Customer Dashboard: Full Access ✅
```

### **Monthly Billing Flow:**
```
Billing date arrives
    ↓
Recurrente charges payment method
    ↓
Success?
    ├─ YES → Webhook: subscription.payment_succeeded
    │         ↓
    │         Update: next_billing_date + 30 days
    │         Send: Payment Success Email
    │         Status: active (continues)
    │
    └─ NO → Webhook: subscription.payment_failed
              ↓
              Start: 7-day grace period
              Update: status = past_due
              Set: grace_period_ends = now + 7 days
              Send: Payment Failed Email
              ↓
              After 7 days → status = owned (downgrade)
              Send: Subscription Suspended Email
```

### **Cancellation Flow:**
```
Customer clicks "Cancel Subscription"
    ↓
Immediate or End of Period?
    ├─ Immediate → Cancel now
    │              Update: status = cancelled
    │              Update: subscription_ends_at = now
    │              Site: owned
    │
    └─ End of Period → Cancel at period end
                       Update: status = cancelled
                       Update: subscription_ends_at = next_billing_date
                       Site: active (until end)
                       ↓
                       At end date → status = owned
```

---

## 🎯 SUCCESS CRITERIA

Phase 3 is complete when:

- [ ] Customer can activate subscription
- [ ] Subscription creates in Recurrente
- [ ] Webhook processes activation
- [ ] Site status updates to active
- [ ] Monthly billing works
- [ ] Payment success/failure handled
- [ ] Grace period implemented
- [ ] Cancellation works
- [ ] Reactivation works
- [ ] All emails send
- [ ] Tests pass
- [ ] Documentation complete

---

## 📈 EXPECTED OUTCOMES

### **Business:**
```
✓ Recurring revenue enabled ($95/month)
✓ Customer retention system
✓ Payment failure recovery
✓ Churn management
```

### **Technical:**
```
✓ Subscription lifecycle complete
✓ Recurrente integration extended
✓ Webhook handlers complete
✓ Email notifications
✓ Grace period automation
```

### **Customer Experience:**
```
✓ Easy activation (one click)
✓ Clear billing information
✓ Self-service cancellation
✓ Transparent pricing
✓ Helpful email notifications
```

---

## 🚀 IMPLEMENTATION ORDER

### **Hour 1: Service Layer**
1. Create `SubscriptionService`
2. Implement core functions
3. Add Recurrente integration

### **Hour 2: API Layer**
1. Create schemas
2. Implement endpoints
3. Add authentication

### **Hour 3: Webhooks**
1. Extend webhook handler
2. Process subscription events
3. Handle edge cases

### **Hour 4: Email Templates**
1. Create 5 email templates
2. Integrate with email service
3. Test email rendering

### **Hour 5: Testing**
1. Write unit tests
2. Test integration
3. Manual testing

### **Hour 6: Documentation**
1. API documentation
2. Update progress docs
3. Create examples

---

## 💡 TECHNICAL DECISIONS

### **1. No New Tables**
**Decision:** Use existing `sites` table  
**Reason:** All fields already present  
**Benefit:** Faster implementation

### **2. Grace Period: 7 Days**
**Decision:** 7-day grace period after payment failure  
**Reason:** Industry standard, fair to customers  
**Benefit:** Reduces involuntary churn

### **3. Cancel at Period End (Default)**
**Decision:** Default to end-of-period cancellation  
**Reason:** Maximizes revenue, customer gets value  
**Benefit:** Better retention

### **4. Subscription Status: 5 States**
**Decision:** active, past_due, cancelled, expired, none  
**Reason:** Covers all scenarios  
**Benefit:** Clear state management

---

## 🎓 LESSONS FROM PHASE 2

### **What Worked Well:**
✅ Modular service layer  
✅ Comprehensive testing first  
✅ Beautiful email templates  
✅ Clear documentation  

### **Apply to Phase 3:**
✅ Start with service layer  
✅ Write tests early  
✅ Make emails beautiful  
✅ Document as we go  

---

**Ready to build Phase 3!** 🚀

_Let's enable recurring revenue and complete the business model!_
