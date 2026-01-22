# Phase 2: Webhook Integration - Implementation Complete

**Date:** January 22, 2026  
**Status:** ✅ Complete  
**Priority:** HIGH (Real-time CRM Tracking)

## 🎯 Objective

Integrate webhook handlers with the CRM lifecycle service to automatically update business status based on real-time events from external services (Recurrente payments, Twilio SMS, email tracking).

---

## 📋 Changes Made

### 1. **Payment Webhooks Integration** (`backend/api/v1/webhooks.py`)

**Updated Handlers:**
- `handle_subscription_cancelled()`: Now updates business `website_status → archived` when subscription is cancelled

**CRM Status Flow:**
```
Recurrente Event → Webhook Handler → Site Status Update → CRM Lifecycle Service → Business Status Update
```

**Example:**
```python
# When subscription is cancelled
if site.business_id:
    lifecycle_service = BusinessLifecycleService(db)
    await lifecycle_service.mark_website_archived(site.business_id)
    # website_status: sold → archived
    logger.info(f"Updated business {site.business_id}: website_status=archived")
```

---

### 2. **Twilio SMS Webhooks Integration** (`backend/api/v1/webhooks_twilio.py`)

**Updated Handlers:**

#### A. `handle_sms_status_callback()` - Delivery Status
Integrates CRM status updates based on SMS delivery status:

**Status Mappings:**
- `delivered` → `mark_campaign_sent(channel="sms")`: pending → sms_sent
- `failed/undelivered` → `mark_bounced()`: any → bounced

**Code:**
```python
# After updating campaign status
if campaign.business_id and message_status == "delivered":
    lifecycle_service = BusinessLifecycleService(db)
    await lifecycle_service.mark_campaign_sent(campaign.business_id, channel="sms")
    # contact_status: pending → sms_sent
elif message_status in ["failed", "undelivered"]:
    await lifecycle_service.mark_bounced(campaign.business_id)
    # contact_status: any → bounced
```

#### B. `handle_incoming_sms()` - Reply Processing
Integrates CRM status updates based on customer replies:

**Reply Actions:**
- `opt_out` → `mark_unsubscribed()`: any → unsubscribed (TERMINAL)
- `reply` → `mark_replied()`: any → replied

**Code:**
```python
# After processing reply
if result['action'] == 'opt_out':
    lifecycle_service = BusinessLifecycleService(db)
    await lifecycle_service.mark_unsubscribed(latest_campaign.business_id)
    # contact_status: any → unsubscribed
elif result['action'] == 'reply':
    await lifecycle_service.mark_replied(latest_campaign.business_id)
    # contact_status: any → replied
```

---

### 3. **Campaign Service Integration** (`backend/services/pitcher/campaign_service.py`)

**Updated Methods:**

#### `_send_email_campaign()`
Integrates CRM status update immediately after successful email send:

```python
# After email is sent successfully
if campaign.business_id:
    lifecycle_service = BusinessLifecycleService(self.db)
    await lifecycle_service.mark_campaign_sent(campaign.business_id, channel="email")
    # contact_status: pending → emailed
    logger.info(f"Updated business {campaign.business_id}: contact_status=emailed")
```

---

### 4. **SMS Campaign Helper Integration** (`backend/services/pitcher/sms_campaign_helper.py`)

**Updated Methods:**

#### `send_sms_campaign()`
Integrates CRM status update after SMS is queued at Twilio:

```python
# After SMS is sent to Twilio
if campaign.business_id:
    lifecycle_service = BusinessLifecycleService(db)
    await lifecycle_service.mark_campaign_sent(campaign.business_id, channel="sms")
    # contact_status: pending → sms_sent (will be confirmed by webhook)
    logger.info(f"Updated business {campaign.business_id}: contact_status=sms_sent")
```

**Note:** SMS campaigns have two-stage status updates:
1. **Immediate (send_sms_campaign):** pending → sms_sent (when queued at Twilio)
2. **Webhook (Twilio callback):** Confirmed delivered or marked as bounced

---

## 🔄 Complete Status Flow Diagrams

### Email Campaign Flow
```
┌─────────────────────────────────────────────────────────────┐
│ Admin Creates Email Campaign                                 │
│ (CampaignService.create_campaign)                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Campaign Status: pending                                     │
│ Business contact_status: pending                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Campaign Sent via Email Provider                             │
│ (_send_email_campaign)                                       │
│                                                               │
│ ✅ Updates:                                                  │
│   - Campaign status → "sent"                                 │
│   - Business contact_status → "emailed" (CRM)               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├──────────────────────────┐
                     │                          │
                     ▼                          ▼
┌────────────────────────────┐  ┌──────────────────────────┐
│ Email Opened (future)      │  │ Link Clicked (future)    │
│ → contact_status: opened   │  │ → contact_status:clicked │
└────────────────────────────┘  └──────────────────────────┘
```

### SMS Campaign Flow
```
┌─────────────────────────────────────────────────────────────┐
│ Admin Creates SMS Campaign                                   │
│ (CampaignService.create_campaign)                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Campaign Status: pending                                     │
│ Business contact_status: pending                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ SMS Sent to Twilio                                           │
│ (send_sms_campaign)                                          │
│                                                               │
│ ✅ Updates:                                                  │
│   - Campaign status → "sent"                                 │
│   - Business contact_status → "sms_sent" (CRM)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Twilio Webhook: Delivery Status                             │
│ (handle_sms_status_callback)                                │
│                                                               │
│ ✅ Updates:                                                  │
│   - "delivered" → contact_status: sms_sent (confirmed)      │
│   - "failed" → contact_status: bounced                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Customer Replies to SMS                                      │
│ (handle_incoming_sms)                                        │
│                                                               │
│ ✅ Updates:                                                  │
│   - "STOP" → contact_status: unsubscribed (TERMINAL)        │
│   - Regular reply → contact_status: replied                 │
└─────────────────────────────────────────────────────────────┘
```

### Subscription/Purchase Flow
```
┌─────────────────────────────────────────────────────────────┐
│ Site Generated                                               │
│ (Phase 1: CreativeOrchestrator)                             │
│                                                               │
│ ✅ Updates:                                                  │
│   - Business website_status → "generated"                   │
│   - Business contact_status → "pending"                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Site Purchased                                               │
│ (Phase 1: site_purchase_service)                            │
│                                                               │
│ ✅ Updates:                                                  │
│   - Site status → "owned"                                    │
│   - Business website_status → "sold" (CRM)                  │
│   - Business contact_status → "purchased" (CRM)             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Subscription Activated                                       │
│ (Recurrente webhook)                                         │
│                                                               │
│ ✅ Updates:                                                  │
│   - Site subscription_status → "active"                      │
│   - No CRM change (already "purchased")                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Subscription Cancelled                                       │
│ (handle_subscription_cancelled)                              │
│                                                               │
│ ✅ Updates:                                                  │
│   - Site subscription_status → "cancelled"                   │
│   - Business website_status → "archived" (CRM)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture & Best Practices

### Separation of Concerns
- **Webhook Handlers:** Verify signatures, parse events, route to services
- **Services:** Business logic, status updates
- **Lifecycle Service:** CRM status transitions only

### Error Handling
- Non-blocking CRM updates (won't fail webhooks)
- Comprehensive logging for audit trail
- Graceful degradation if business_id is missing

### Idempotency
- All lifecycle methods are idempotent
- Safe to call multiple times with same event
- Only updates if transition is valid

### Observability
```python
# Every status change is logged
logger.info(
    f"Updated business {business_id}: "
    f"contact_status={new_status} (event: {event_type})"
)
```

---

## 📊 Status Tracking Coverage

### ✅ Implemented Events

| Event Source | Event Type | CRM Status Updated |
|--------------|------------|-------------------|
| **Site Generation** | generation_started | website_status: generating |
| **Site Generation** | generation_completed | website_status: generated |
| **Site Purchase** | purchase_completed | website_status: sold<br>contact_status: purchased |
| **Recurrente** | subscription.cancelled | website_status: archived |
| **Email Campaign** | campaign_sent | contact_status: emailed |
| **Twilio SMS** | sms_sent | contact_status: sms_sent |
| **Twilio SMS** | sms_delivered | contact_status: sms_sent (confirmed) |
| **Twilio SMS** | sms_failed | contact_status: bounced |
| **Twilio SMS** | sms_reply | contact_status: replied |
| **Twilio SMS** | sms_opt_out | contact_status: unsubscribed |

### 🔮 Future Events (Phase 3+)

| Event Source | Event Type | CRM Status To Update |
|--------------|------------|---------------------|
| **Email Tracking** | email_opened | contact_status: opened |
| **Email Tracking** | link_clicked | contact_status: clicked |
| **Support Ticket** | ticket_created | (Add ticket_status field) |
| **Site Deployment** | site_deployed | website_status: deployed |

---

## 🧪 Testing Scenarios

### Test 1: Email Campaign Send
```python
# Send email campaign
campaign = await campaign_service.create_campaign(business_id, channel="email")
await campaign_service.send_campaign(campaign.id)

# Verify CRM status
business = await business_service.get_business(business_id)
assert business.contact_status == "emailed"
```

### Test 2: SMS Delivery Webhook
```python
# Simulate Twilio delivery webhook
webhook_data = {
    "MessageSid": "SM123...",
    "MessageStatus": "delivered"
}
await handle_sms_status_callback(db, webhook_data)

# Verify CRM status
campaign = await Campaign.get_by_sms_sid("SM123...")
business = await business_service.get_business(campaign.business_id)
assert business.contact_status == "sms_sent"
```

### Test 3: SMS Reply (Opt-Out)
```python
# Simulate Twilio incoming SMS with STOP
webhook_data = {
    "From": "+15551234567",
    "Body": "STOP",
    "MessageSid": "SM456..."
}
await handle_incoming_sms(db, webhook_data)

# Verify CRM status
business = await business_service.get_business_by_phone("+15551234567")
assert business.contact_status == "unsubscribed"
```

### Test 4: Subscription Cancellation
```python
# Simulate Recurrente cancellation webhook
webhook_data = {
    "event": "subscription.cancelled",
    "data": {
        "id": "sub_123..."
    }
}
await handle_subscription_cancelled(db, webhook_data['data'])

# Verify CRM status
site = await Site.get_by_subscription_id("sub_123...")
business = await business_service.get_business(site.business_id)
assert business.website_status == "archived"
```

---

## 🚀 Deployment Steps

### Option 1: Using Nimly SSH (Recommended)
```python
# Deploy using MCP tool (automated)
# Nimly SSH will handle git pull, pip install, and service restart
```

### Option 2: Manual Deployment
```bash
# 1. SSH into VPS
ssh root@your-vps

# 2. Navigate to project
cd /var/www/webmagic

# 3. Pull latest code
git pull origin main

# 4. Install dependencies (if any new)
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 5. Restart services
cd /var/www/webmagic
./scripts/restart_services.sh

# 6. Verify
sudo supervisorctl status
sudo supervisorctl tail -f webmagic-api
```

---

## ✅ Verification Checklist

- [x] Payment webhooks integrated with lifecycle service
- [x] Twilio SMS webhooks integrated (delivery & replies)
- [x] Email campaign service integrated
- [x] SMS campaign helper integrated
- [x] Non-blocking error handling (CRM updates won't fail webhooks)
- [x] Comprehensive logging for audit trail
- [x] No linting errors
- [x] Backward compatible (no breaking changes)
- [x] Documentation complete

---

## 📊 Impact

### Immediate Benefits
1. ✅ **Real-time CRM Updates:** Status changes happen instantly
2. ✅ **Automated Tracking:** No manual status updates needed
3. ✅ **Audit Trail:** All status changes are logged
4. ✅ **Data Consistency:** Single source of truth for business status

### Long-Term Benefits
1. 🎯 **Accurate Funnel Metrics:** Track conversion rates at each stage
2. 📊 **Campaign Analytics:** Measure email/SMS effectiveness
3. 💰 **Churn Prevention:** Identify at-risk customers
4. 🔄 **Lifecycle Marketing:** Target customers based on their status

---

## 📝 Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `backend/api/v1/webhooks.py` | Added lifecycle integration to subscription webhook | +20 |
| `backend/api/v1/webhooks_twilio.py` | Added lifecycle integration to SMS webhooks | +70 |
| `backend/services/pitcher/campaign_service.py` | Added lifecycle integration to email campaigns | +30 |
| `backend/services/pitcher/sms_campaign_helper.py` | Added lifecycle integration to SMS campaigns | +30 |

**Total:** 4 files modified, ~150 lines added

---

## 🎉 Status: READY FOR DEPLOYMENT

**Implementation Time:** ~1.5 hours  
**Breaking Changes:** ❌ None  
**Backward Compatible:** ✅ Yes  
**Tests:** Ready for integration testing  

---

## 📚 Related Documentation

- `PHASE_1_IMPLEMENTATION_COMPLETE.md` - CRM Foundation
- `CRM_ANALYSIS_AND_PLAN.md` - Overall CRM Strategy
- `SMS_INTEGRATION_COMPLETE.md` - Twilio SMS Implementation

---

**Next Phase (Optional):** Phase 3 - CRM API & Frontend Dashboard

