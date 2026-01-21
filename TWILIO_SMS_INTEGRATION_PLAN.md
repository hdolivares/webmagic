# Twilio SMS Integration Plan

## Overview
Integrate Twilio SMS to reach businesses without email addresses, particularly emergency services (locksmiths, plumbers, electricians) where SMS is more effective and immediate.

---

## 1. Current System Analysis

### Existing Architecture
- **Email-First**: Campaign system built around email (`Campaign` model)
- **Multi-Provider**: Abstract `EmailProvider` class with SES, SendGrid, Brevo implementations
- **Campaign Service**: Orchestrates generation, sending, and tracking
- **Business Model**: Has `email` and `phone` fields (phone already captured!)
- **Async Processing**: Celery tasks for bulk campaigns

### Key Components
```
services/pitcher/
├── email_generator.py      # AI-powered email content
├── email_sender.py         # Multi-provider email sending
├── campaign_service.py     # Campaign orchestration
└── tracking.py             # Email tracking (opens, clicks)
```

---

## 2. Recommended Architecture: **Unified Multi-Channel Campaigns**

### Design Philosophy
Instead of creating separate SMS campaigns, **enhance the existing campaign system to support multiple channels** (email + SMS). This approach:
- ✅ Reuses existing campaign tracking infrastructure
- ✅ Allows intelligent fallback (email → SMS if no email)
- ✅ Enables A/B testing across channels
- ✅ Centralizes analytics and reporting
- ✅ Future-proofs for additional channels (WhatsApp, push notifications)

---

## 3. Implementation Plan

### Phase 1: Database Schema Updates ⚙️

#### Update `Campaign` Model
```python
# Add to backend/models/campaign.py

class Campaign(BaseModel):
    # ... existing fields ...
    
    # NEW: Multi-Channel Support
    channel = Column(String(20), default="email", nullable=False, index=True)
    # Options: "email", "sms", "whatsapp", "voice"
    
    # NEW: SMS-Specific Fields
    recipient_phone = Column(String(20), nullable=True, index=True)
    sms_body = Column(Text, nullable=True)
    sms_provider = Column(String(50), nullable=True)  # "twilio", "messagebird"
    sms_sid = Column(String(255), nullable=True, index=True)  # Twilio message SID
    sms_segments = Column(Integer, nullable=True)  # SMS parts (for cost tracking)
    sms_cost = Column(Numeric(10, 4), nullable=True)  # Actual cost in USD
    
    # Update existing email fields to be optional (not all campaigns use email)
    recipient_email = Column(String(255), nullable=True, index=True)  # Was: nullable=False
```

#### Migration Script
```sql
-- Add new columns
ALTER TABLE campaigns 
  ADD COLUMN channel VARCHAR(20) DEFAULT 'email' NOT NULL,
  ADD COLUMN recipient_phone VARCHAR(20),
  ADD COLUMN sms_body TEXT,
  ADD COLUMN sms_provider VARCHAR(50),
  ADD COLUMN sms_sid VARCHAR(255),
  ADD COLUMN sms_segments INTEGER,
  ADD COLUMN sms_cost NUMERIC(10, 4);

-- Add indexes
CREATE INDEX idx_campaigns_channel ON campaigns(channel);
CREATE INDEX idx_campaigns_recipient_phone ON campaigns(recipient_phone);
CREATE INDEX idx_campaigns_sms_sid ON campaigns(sms_sid);

-- Make recipient_email optional
ALTER TABLE campaigns ALTER COLUMN recipient_email DROP NOT NULL;
```

---

### Phase 2: SMS Provider Service 📱

#### Create `services/pitcher/sms_sender.py`
```python
"""
SMS sender service with Twilio support.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from core.config import get_settings
from core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)
settings = get_settings()


class SMSProvider(ABC):
    """Abstract base class for SMS providers."""
    
    @abstractmethod
    async def send_sms(
        self,
        to_phone: str,
        body: str,
        from_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send SMS and return message details."""
        pass


class TwilioSMSProvider(SMSProvider):
    """Twilio SMS provider."""
    
    def __init__(self):
        """Initialize Twilio client."""
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            raise ValueError("Twilio credentials not configured")
        
        self.client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        self.from_phone = settings.TWILIO_PHONE_NUMBER
        logger.info("Twilio SMS client initialized")
    
    async def send_sms(
        self,
        to_phone: str,
        body: str,
        from_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send SMS via Twilio."""
        try:
            # Validate and format phone number
            if not to_phone.startswith('+'):
                # Assume US number if no country code
                to_phone = f"+1{to_phone.lstrip('1')}"
            
            # Send message
            message = self.client.messages.create(
                body=body,
                from_=from_phone or self.from_phone,
                to=to_phone,
                # Optional: Status callback for delivery tracking
                status_callback=f"{settings.API_URL}/api/v1/webhooks/twilio/status"
            )
            
            logger.info(f"SMS sent to {to_phone}: {message.sid}")
            
            return {
                "message_id": message.sid,
                "status": message.status,
                "provider": "twilio",
                "to": message.to,
                "from": message.from_,
                "segments": message.num_segments,
                "price": float(message.price) if message.price else None,
                "price_unit": message.price_unit,
                "sent_at": message.date_created.isoformat() if message.date_created else None
            }
            
        except TwilioRestException as e:
            logger.error(f"Twilio error sending to {to_phone}: {e}")
            raise ExternalAPIException(f"SMS failed: {e.msg}")
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {e}")
            raise ExternalAPIException(f"SMS failed: {str(e)}")


class SMSSender:
    """
    SMS sender that auto-selects provider.
    Currently supports Twilio only.
    """
    
    def __init__(self):
        """Initialize SMS sender with configured provider."""
        self.provider = self._init_provider()
    
    def _init_provider(self) -> SMSProvider:
        """Initialize the configured SMS provider."""
        # For now, only Twilio
        # Can add MessageBird, AWS SNS, etc. later
        try:
            return TwilioSMSProvider()
        except Exception as e:
            logger.error(f"Failed to initialize Twilio: {e}")
            raise ValueError(f"SMS provider not configured: {e}")
    
    async def send(
        self,
        to_phone: str,
        body: str,
        from_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send SMS via configured provider."""
        return await self.provider.send_sms(to_phone, body, from_phone)
```

---

### Phase 3: SMS Content Generator 💬

#### Create `services/pitcher/sms_generator.py`
```python
"""
SMS content generator using Claude AI.
"""
from typing import Dict, Any, Optional
import logging
from anthropic import AsyncAnthropic

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SMSGenerator:
    """Generate personalized SMS messages using Claude AI."""
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-5-sonnet-20241022"
    
    async def generate_sms(
        self,
        business_data: Dict[str, Any],
        site_url: Optional[str] = None,
        variant: str = "default"
    ) -> str:
        """
        Generate SMS content for outreach.
        
        Args:
            business_data: Business info (name, category, city, rating)
            site_url: Optional generated site URL
            variant: SMS style (urgent, friendly, professional)
        
        Returns:
            SMS body text (max 160 chars recommended for single segment)
        """
        # Build prompt
        prompt = f"""Generate a short, professional SMS message for business outreach.

Business: {business_data['name']}
Category: {business_data['category']}
Location: {business_data['city']}, {business_data['state']}
Rating: {business_data.get('rating', 'N/A')}⭐

Website: {site_url or 'Creating custom site...'}

REQUIREMENTS:
- Maximum 160 characters (single SMS segment)
- Professional and respectful tone
- Mention we built them a free website
- Include call-to-action (visit or reply)
- NO emojis unless variant is "friendly"
- Be concise and direct

Variant: {variant}
- "professional": Formal business tone
- "friendly": Warm, approachable  
- "urgent": For emergency services (plumbers, locksmiths)

Return ONLY the SMS message text, no quotes or explanations."""

        # Get AI response
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=200,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        
        sms_body = message.content[0].text.strip()
        
        # Ensure it's not too long (warn if > 160 chars)
        if len(sms_body) > 160:
            logger.warning(f"SMS too long ({len(sms_body)} chars), will use multiple segments")
        
        return sms_body
```

---

### Phase 4: Update Campaign Service 🔄

#### Enhance `services/pitcher/campaign_service.py`
```python
# Add these methods to CampaignService class

async def create_campaign(
    self,
    business_id: UUID,
    site_id: Optional[UUID] = None,
    channel: str = "auto",  # NEW: auto, email, sms
    variant: str = "default",
    scheduled_for: Optional[datetime] = None
) -> Campaign:
    """
    Create campaign with automatic channel selection.
    
    channel options:
    - "auto": Use email if available, else SMS
    - "email": Force email (fail if no email)
    - "sms": Force SMS (fail if no phone)
    - "both": Create both email and SMS campaigns
    """
    business = await self._get_business(business_id)
    
    # Determine channel
    if channel == "auto":
        if business.email:
            channel = "email"
        elif business.phone:
            channel = "sms"
        else:
            raise ValidationException("Business has no email or phone")
    
    if channel == "email":
        return await self._create_email_campaign(business, site_id, variant, scheduled_for)
    elif channel == "sms":
        return await self._create_sms_campaign(business, site_id, variant, scheduled_for)
    elif channel == "both":
        # Create both (useful for A/B testing)
        email_campaign = await self._create_email_campaign(business, site_id, variant, scheduled_for)
        sms_campaign = await self._create_sms_campaign(business, site_id, variant, scheduled_for)
        return email_campaign  # Return primary
    
    raise ValidationException(f"Invalid channel: {channel}")


async def _create_sms_campaign(
    self,
    business: Business,
    site_id: Optional[UUID],
    variant: str,
    scheduled_for: Optional[datetime]
) -> Campaign:
    """Create SMS campaign."""
    if not business.phone:
        raise ValidationException(f"Business has no phone: {business.name}")
    
    # Get site URL
    site_url = await self._get_site_url(site_id) if site_id else None
    
    # Generate SMS content
    business_data = {
        "name": business.name,
        "category": business.category,
        "city": business.city,
        "state": business.state,
        "rating": float(business.rating) if business.rating else 0,
    }
    
    sms_body = await self.sms_generator.generate_sms(
        business_data=business_data,
        site_url=site_url,
        variant=variant
    )
    
    # Create campaign record
    campaign = Campaign(
        business_id=business.id,
        site_id=site_id,
        channel="sms",
        recipient_phone=business.phone,
        business_name=business.name,
        sms_body=sms_body,
        variant=variant,
        scheduled_for=scheduled_for,
        status="pending"
    )
    
    self.db.add(campaign)
    await self.db.commit()
    await self.db.refresh(campaign)
    
    logger.info(f"SMS campaign created: {campaign.id}")
    return campaign


async def send_sms_campaign(self, campaign_id: UUID) -> Campaign:
    """Send SMS campaign immediately."""
    campaign = await self._get_campaign(campaign_id)
    
    if campaign.channel != "sms":
        raise ValidationException("Campaign is not SMS")
    
    if not campaign.recipient_phone:
        raise ValidationException("No recipient phone")
    
    try:
        # Send SMS
        result = await self.sms_sender.send(
            to_phone=campaign.recipient_phone,
            body=campaign.sms_body
        )
        
        # Update campaign
        campaign.status = "sent"
        campaign.sent_at = datetime.utcnow()
        campaign.sms_provider = result["provider"]
        campaign.sms_sid = result["message_id"]
        campaign.sms_segments = result.get("segments", 1)
        campaign.sms_cost = result.get("price")
        
        await self.db.commit()
        logger.info(f"SMS sent: {campaign.id}")
        
        return campaign
        
    except Exception as e:
        campaign.status = "failed"
        campaign.error_message = str(e)
        campaign.retry_count += 1
        await self.db.commit()
        logger.error(f"SMS failed: {campaign.id} - {e}")
        raise
```

---

### Phase 5: Configuration Updates 🔧

#### Update `backend/core/config.py`
```python
class Settings(BaseSettings):
    # ... existing fields ...
    
    # SMS Configuration
    SMS_PROVIDER: str = "twilio"  # Currently only twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None  # Your Twilio number (e.g., +12345678900)
    
    # SMS Limits & Costs
    MAX_SMS_LENGTH: int = 160  # Single segment
    SMS_COST_WARNING_THRESHOLD: float = 0.10  # Warn if cost > $0.10
    
    # Campaign Defaults
    DEFAULT_CAMPAIGN_CHANNEL: str = "auto"  # auto, email, sms, both
```

#### Update `backend/env.template`
```bash
# SMS Configuration (Twilio)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+12345678900  # Your Twilio phone number

# SMS Settings
SMS_PROVIDER=twilio
DEFAULT_CAMPAIGN_CHANNEL=auto  # auto, email, sms, both
```

---

### Phase 6: Webhooks for SMS Status Tracking 📡

#### Create `backend/api/v1/webhooks/twilio.py`
```python
"""
Twilio webhook handlers for SMS delivery status.
"""
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import logging

from api.deps import get_db
from models.campaign import Campaign

router = APIRouter(prefix="/twilio", tags=["Twilio Webhooks"])
logger = logging.getLogger(__name__)


@router.post("/status")
async def twilio_status_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Twilio SMS status callbacks.
    
    Twilio sends status updates: queued, sent, delivered, failed, undelivered
    """
    try:
        form_data = await request.form()
        
        message_sid = form_data.get("MessageSid")
        message_status = form_data.get("MessageStatus")
        error_code = form_data.get("ErrorCode")
        error_message = form_data.get("ErrorMessage")
        
        if not message_sid:
            raise HTTPException(status_code=400, detail="Missing MessageSid")
        
        # Find campaign by Twilio SID
        result = await db.execute(
            select(Campaign).where(Campaign.sms_sid == message_sid)
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            logger.warning(f"Campaign not found for SMS SID: {message_sid}")
            return {"status": "ok", "message": "Campaign not found"}
        
        # Update campaign status
        status_map = {
            "queued": "pending",
            "sent": "sent",
            "delivered": "delivered",
            "failed": "failed",
            "undelivered": "failed"
        }
        
        campaign.status = status_map.get(message_status, campaign.status)
        
        if message_status == "delivered":
            campaign.delivered_at = datetime.utcnow()
        
        if error_code:
            campaign.error_message = f"Twilio Error {error_code}: {error_message}"
        
        await db.commit()
        
        logger.info(f"Updated SMS campaign {campaign.id} status: {message_status}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Twilio webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

### Phase 7: Celery Task Updates 🔄

#### Update `backend/tasks/campaigns.py`
```python
# Add SMS campaign task

@celery_app.task(name="send_sms_campaign")
def send_sms_campaign_task(campaign_id: str):
    """Send SMS campaign asynchronously."""
    async def _send():
        async with get_db_session() as db:
            service = CampaignService(db)
            await service.send_sms_campaign(UUID(campaign_id))
    
    asyncio.run(_send())


@celery_app.task(name="send_bulk_campaigns")
def send_bulk_campaigns_task(business_ids: List[str], channel: str = "auto"):
    """
    Create and send campaigns for multiple businesses.
    
    channel: "auto" (email if available, else SMS), "email", "sms", "both"
    """
    async def _bulk_send():
        async with get_db_session() as db:
            service = CampaignService(db)
            
            for business_id in business_ids:
                try:
                    # Create campaign with channel selection
                    campaign = await service.create_campaign(
                        business_id=UUID(business_id),
                        channel=channel
                    )
                    
                    # Send immediately based on channel
                    if campaign.channel == "email":
                        await service.send_email_campaign(campaign.id)
                    elif campaign.channel == "sms":
                        await service.send_sms_campaign(campaign.id)
                    
                    logger.info(f"Sent {campaign.channel} campaign to {business_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to send campaign to {business_id}: {e}")
    
    asyncio.run(_bulk_send())
```

---

### Phase 8: Frontend Updates 🎨

#### Add SMS Channel Support to Campaign UI

**`frontend/src/pages/Campaigns/CreateCampaignPage.tsx`**
```typescript
// Add channel selector
<div>
  <label className="label">Campaign Channel</label>
  <select value={channel} onChange={(e) => setChannel(e.target.value)}>
    <option value="auto">Auto (Email → SMS fallback)</option>
    <option value="email">Email Only</option>
    <option value="sms">SMS Only</option>
    <option value="both">Both Email + SMS</option>
  </select>
  <p className="text-sm text-text-secondary">
    Auto will use email if available, otherwise SMS
  </p>
</div>
```

**Campaign Analytics Dashboard**
- Show SMS vs Email breakdown
- Display SMS delivery rates
- Track SMS costs per campaign
- Compare engagement rates by channel

---

## 4. Cost Management 💰

### SMS Pricing Considerations
- **Twilio US SMS**: ~$0.0079 per segment (160 chars)
- **Long messages**: 2+ segments = 2x cost
- **International**: Much more expensive
- **Email**: Nearly free

### Cost Control Strategies

1. **Smart Channel Selection**
   ```python
   # Prefer email (free), fallback to SMS only when necessary
   if business.email:
       use_email()
   elif business.phone and business.category in URGENT_SERVICES:
       use_sms()
   ```

2. **SMS Length Optimization**
   - Target 160 characters (1 segment)
   - Use URL shortener for links
   - Keep messaging concise

3. **Budget Limits**
   ```python
   # Set daily SMS budget
   MAX_DAILY_SMS_BUDGET = 50.00  # $50/day
   
   # Track spending
   daily_sms_cost = await get_todays_sms_cost(db)
   if daily_sms_cost + estimated_cost > MAX_DAILY_SMS_BUDGET:
       logger.warning("Daily SMS budget reached")
       # Queue for tomorrow or use email instead
   ```

4. **Monitoring & Alerts**
   - Alert when approaching budget
   - Track ROI per channel
   - A/B test email vs SMS effectiveness

---

## 5. Phone Number Validation 📞

### Format & Validation Service

**`backend/services/phone_validator.py`**
```python
"""Phone number validation and formatting."""
import re
from typing import Optional, Tuple


class PhoneValidator:
    """Validate and format phone numbers for SMS."""
    
    @staticmethod
    def validate_us_phone(phone: str) -> Tuple[bool, Optional[str]]:
        """
        Validate US phone number and return E.164 format.
        
        Returns: (is_valid, formatted_phone)
        """
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)
        
        # Check US number (10 digits)
        if len(digits) == 10:
            return (True, f"+1{digits}")
        
        # Check with country code
        if len(digits) == 11 and digits.startswith('1'):
            return (True, f"+{digits}")
        
        return (False, None)
    
    @staticmethod
    def is_valid_for_sms(phone: Optional[str]) -> bool:
        """Check if phone number is valid for SMS."""
        if not phone:
            return False
        
        valid, _ = PhoneValidator.validate_us_phone(phone)
        return valid
```

---

## 6. Migration Strategy 🚀

### Step-by-Step Rollout

#### Week 1: Foundation
- ✅ Add Twilio credentials to `.env`
- ✅ Install Twilio SDK: `pip install twilio`
- ✅ Database migration (add SMS columns)
- ✅ Create `SMSSender` service
- ✅ Create `SMSGenerator` service

#### Week 2: Integration
- ✅ Update `CampaignService` for multi-channel
- ✅ Add Twilio webhook endpoint
- ✅ Update Celery tasks
- ✅ Phone number validation

#### Week 3: Testing
- ✅ Test with small batch (10-20 businesses)
- ✅ Verify delivery tracking
- ✅ Monitor costs
- ✅ Test fallback logic (email → SMS)

#### Week 4: Production
- ✅ Frontend updates (channel selector)
- ✅ Analytics dashboard updates
- ✅ Documentation
- ✅ Full rollout

---

## 7. Best Practices & Considerations ⚠️

### Legal & Compliance
1. **TCPA Compliance** (US)
   - Get consent before sending SMS
   - Include opt-out instructions: "Reply STOP to unsubscribe"
   - Honor opt-outs immediately

2. **International Regulations**
   - GDPR (EU), CASL (Canada), etc.
   - Different rules per country

3. **Business Hours**
   - Don't send SMS late at night
   - Respect time zones
   - Emergency services: More flexible

### Message Templates
```python
# Professional (General Business)
"Hi [Name]! We built you a free website: [URL]. Check it out and let us know what you think. Reply STOP to opt out."

# Urgent (Emergency Services)
"[Business Name] - We created a professional website for your [Service] business. View it here: [URL]. Text STOP to unsubscribe."

# Friendly (Local Services)
"Hey [Name]! 👋 Built you a website for [Business]. Take a look: [URL]. Love it? Let's chat! Reply STOP to opt out."
```

### Opt-Out Handling
```python
# Add to Campaign model
class Campaign(BaseModel):
    opted_out = Column(Boolean, default=False)
    opted_out_at = Column(DateTime, nullable=True)

# Create opt-out list table
class SMSOptOut(BaseModel):
    __tablename__ = "sms_opt_outs"
    
    phone_number = Column(String(20), unique=True, nullable=False)
    opted_out_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50))  # "reply", "manual", "complaint"
```

---

## 8. Recommended Packages 📦

Add to `backend/requirements.txt`:
```
# SMS
twilio==8.11.0  # Twilio Python SDK
phonenumbers==8.13.27  # Phone number validation (more robust than regex)
```

---

## 9. Success Metrics 📊

Track these KPIs:
- **Delivery Rate**: SMS delivered / SMS sent
- **Response Rate**: Replies / Delivered
- **Cost per Lead**: Total SMS cost / Responses
- **Channel Comparison**: SMS vs Email engagement
- **ROI**: Revenue generated / SMS cost

---

## 10. Future Enhancements 🔮

### Phase 2 Features
1. **Two-Way SMS**: Handle replies automatically
2. **MMS Support**: Send images/screenshots
3. **SMS Scheduling**: Optimal send times
4. **Drip Campaigns**: Multi-message sequences
5. **WhatsApp Business**: Alternative channel
6. **Voice Calls**: For non-responsive businesses

---

## Summary: Why This Approach? ✨

### Pros
✅ **Unified System**: One campaign model for all channels
✅ **Intelligent Fallback**: Auto-select best channel
✅ **Cost Efficient**: Prefer free email, use SMS when needed
✅ **Scalable**: Easy to add WhatsApp, push notifications later
✅ **Comprehensive Tracking**: All metrics in one place
✅ **Future-Proof**: Multi-channel architecture from day 1

### Cons
⚠️ **More Complex**: More logic than separate SMS system
⚠️ **Migration Required**: Update existing campaign records
⚠️ **Cost Management**: Need careful monitoring

### Recommended Start
**Week 1 Priority**: 
1. Add Twilio to `.env`
2. Run database migration
3. Create `SMSSender` service
4. Test with 5-10 businesses manually

Then iterate based on results!

---

**Ready to implement? Let me know and I'll start building the services!** 🚀

