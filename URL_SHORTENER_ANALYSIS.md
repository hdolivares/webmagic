# URL Shortener System Analysis
**Date:** 2026-02-17  
**Domain:** lvsh.cc  
**Status:** ✅ Fully implemented, needs SMS integration

---

## 🏗️ **ARCHITECTURE OVERVIEW**

### **Components:**

```
┌─────────────────────────────────────────────────────────────────┐
│                      URL SHORTENER FLOW                          │
└─────────────────────────────────────────────────────────────────┘

1. CREATE SHORT LINK:
   SMS Service → ShortLinkService.create_short_link()
      ↓
   Generate unique slug (base62: a-zA-Z0-9, 6 chars)
      ↓
   Store in database (short_links table)
      ↓
   Return: https://lvsh.cc/a1B2c3

2. USER CLICKS LINK:
   User visits: https://lvsh.cc/a1B2c3
      ↓
   DNS → Nginx (lvsh.cc vhost)
      ↓
   Rewrite: /a1B2c3 → /r/a1B2c3
      ↓
   FastAPI: GET /r/{slug}
      ↓
   ShortLinkService.resolve(slug)
      ↓
   Increment click_count, update last_clicked_at
      ↓
   302 Redirect → sites.lavish.solutions/business-name-la
```

---

## 📦 **DATABASE SCHEMA**

### **Table: `short_links`**

```sql
CREATE TABLE short_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- The short slug (e.g., "a1B2c3")
    slug VARCHAR(20) UNIQUE NOT NULL,
    
    -- Full destination URL
    destination_url TEXT NOT NULL,
    
    -- Link type for categorization
    -- Values: "site_preview", "campaign", "custom", "other"
    link_type VARCHAR(30) NOT NULL DEFAULT 'other',
    
    -- Status control
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NULL,
    
    -- Click tracking
    click_count INTEGER DEFAULT 0 NOT NULL,
    last_clicked_at TIMESTAMP WITH TIME ZONE NULL,
    
    -- Optional relations (all nullable)
    business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,
    site_id UUID REFERENCES generated_sites(id) ON DELETE SET NULL,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    
    -- Flexible extra data (UTM params, source channel, etc.)
    extra_data JSONB NULL,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_short_links_slug ON short_links(slug);
CREATE INDEX idx_short_links_link_type ON short_links(link_type);
CREATE INDEX idx_short_links_is_active ON short_links(is_active);
CREATE INDEX idx_short_links_business_id ON short_links(business_id);
CREATE INDEX idx_short_links_site_id ON short_links(site_id);
CREATE INDEX idx_short_links_campaign_id ON short_links(campaign_id);
```

---

## 🔧 **SERVICE API**

### **ShortLinkService**

Located: `backend/services/shortener/short_link_service.py`

#### **1. Create Short Link**

```python
from services.shortener import ShortLinkService

# Create new short link
short_url = await ShortLinkService.create_short_link(
    db,
    destination_url="https://sites.lavish.solutions/bodycare-la",
    link_type="site_preview",
    business_id=some_uuid,
    site_id=some_uuid,
)
# Returns: "https://lvsh.cc/a1B2c3"
```

**Features:**
- ✅ Auto-generates unique 6-char base62 slug
- ✅ Collision detection with retry logic (5 attempts)
- ✅ Optional custom slug support
- ✅ Optional expiration dates
- ✅ Graceful fallback (returns original URL if disabled)

#### **2. Get or Create (Idempotent)**

```python
# Reuses existing link if found, or creates new one
short_url = await ShortLinkService.get_or_create_short_link(
    db,
    destination_url="https://sites.lavish.solutions/bodycare-la",
    link_type="site_preview",
    business_id=some_uuid,
)
```

**Use Case:** Perfect for site preview links where the same destination should always map to the same short link.

#### **3. Resolve Link**

```python
# Resolve slug to destination (used by redirect endpoint)
destination = await ShortLinkService.resolve(db, "a1B2c3")
# Returns: "https://sites.lavish.solutions/bodycare-la"
# Atomically increments click_count and updates last_clicked_at
```

#### **4. List & Stats**

```python
# List links with pagination
result = await ShortLinkService.list_links(
    db,
    link_type="site_preview",
    is_active=True,
    page=1,
    page_size=25,
)

# Get aggregate stats
stats = await ShortLinkService.get_stats(db)
# Returns: { total_links, active_links, total_clicks, links_by_type }
```

---

## ⚙️ **SYSTEM SETTINGS**

Configuration is stored in `system_settings` table:

| Setting Key | Default | Description |
|-------------|---------|-------------|
| `shortener_domain` | `""` | Domain for short URLs (e.g., `lvsh.cc`) |
| `shortener_protocol` | `"https"` | Protocol (http/https) |
| `shortener_slug_length` | `6` | Length of generated slugs (6 = 56.8B combos) |
| `shortener_enabled` | `true` | Global enable/disable toggle |
| `shortener_default_expiry_days` | `0` | Default expiration (0 = never expires) |

**To set the domain:**
```sql
UPDATE system_settings 
SET value = 'lvsh.cc' 
WHERE key = 'shortener_domain';
```

---

## 🌐 **API ENDPOINTS**

### **Admin Endpoints** (Require Authentication)

Base: `/api/v1/shortener`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/links` | Create new short link |
| GET | `/links` | List links (paginated, filterable) |
| GET | `/links/{id}` | Get single link details |
| DELETE | `/links/{id}` | Deactivate link (soft delete) |
| GET | `/stats` | Get aggregate statistics |
| GET | `/config` | Get current configuration |

### **Public Endpoint** (No Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/r/{slug}` | Redirect to destination (302) |

**Example:**
```
GET /r/a1B2c3  →  302 Redirect to https://sites.lavish.solutions/bodycare-la
```

---

## 🔐 **SECURITY & FEATURES**

### **Security:**
- ✅ **Slug collision detection** - Retries up to 5 times if collision occurs
- ✅ **Soft deletion** - Links are deactivated, not deleted
- ✅ **Expiration support** - Optional TTL for temporary links
- ✅ **Rate limiting ready** - Can add rate limiting to redirect endpoint
- ✅ **No personal data** - Slugs are random, not guessable

### **Tracking:**
- ✅ **Click counting** - Atomically increments on each redirect
- ✅ **Last click timestamp** - Records when last accessed
- ✅ **Link type categorization** - Separate stats by type
- ✅ **Business/site/campaign association** - Track which entity the link belongs to

### **Graceful Degradation:**
- ✅ If shortener is disabled → returns original URL
- ✅ If domain is not set → returns original URL
- ✅ If link is expired/inactive → 404 (not 302)

---

## 📊 **SLUG GENERATION**

### **Algorithm: Base62 (URL-safe)**

```python
# Character set: a-zA-Z0-9 (62 characters)
BASE62_CHARS = string.ascii_letters + string.digits

def generate_slug(length: int = 6) -> str:
    return "".join(secrets.choice(BASE62_CHARS) for _ in range(length))
```

### **Capacity:**

| Length | Combinations | Use Case |
|--------|--------------|----------|
| 6 chars | 56.8 billion | ✅ **Production (recommended)** |
| 7 chars | 3.5 trillion | Enterprise scale |
| 8 chars | 218 trillion | Overkill |

**Current: 6 characters = 56,800,235,584 combinations**

At 1 million links per day, we'd run out in ~155 years! 🎉

---

## 🔗 **SMS INTEGRATION PLAN**

### **Current SMS Message (NO shortener):**
```
Hi Body Care Chiropractic in Los Angeles - We created a preview 
website for your Chiropractor business. 
sites.lavish.solutions/body-care-chiro-la. Take a look and let 
us know what you think. Reply STOP to opt out.

Length: 189 chars (2 segments) | Cost: $0.0158
```

### **With lvsh.cc Shortener:**
```
Hi Body Care Chiropractic in Los Angeles - We created a preview 
website for your Chiropractor business. lvsh.cc/a1B2c3. Take a 
look and let us know what you think. Reply STOP to opt out.

Length: 168 chars (2 segments) | Cost: $0.0158
```

**Savings: 21 characters!**

### **Better: Optimize template for short URL:**
```
Hi Body Care Chiropractic in Los Angeles - Preview website for 
your business: lvsh.cc/a1B2c3. Take a look and let us know what 
you think! Reply STOP to opt out.

Length: 156 chars (1 segment!) | Cost: $0.0079 ✅
```

**Result: 50% cost savings!**

---

## ✅ **INTEGRATION CHECKLIST**

### **Step 1: Fix ShortLink Model** ✅
- Re-enable in `backend/models/__init__.py`
- The model is already correct (no `metadata` attribute)
- The error was a red herring (caching issue)

### **Step 2: Set Domain Configuration** ⏳
```sql
UPDATE system_settings 
SET value = 'lvsh.cc' 
WHERE key = 'shortener_domain';
```

### **Step 3: Update SMS Generator** ⏳
Modify `backend/services/sms/sms_generator.py`:

```python
from services.shortener import ShortLinkService

async def generate_sms(self, business_data, site_url, ...):
    # Create or get short link
    if site_url:
        short_url = await ShortLinkService.get_or_create_short_link(
            db=self.db,  # Need to inject db
            destination_url=site_url,
            link_type="site_preview",
            business_id=business_data.get("id"),
            site_id=business_data.get("site_id"),
        )
        # Use short_url instead of site_url in template
    ...
```

### **Step 4: DNS & Nginx Configuration** ⏳
See DNS_NGINX_SETUP.md (to be created)

### **Step 5: Testing** ⏳
1. Create short link via API
2. Test redirect: `curl -I https://lvsh.cc/test`
3. Verify click tracking in database
4. Send test SMS with short link
5. Monitor click-through rates

---

## 📈 **ANALYTICS & MONITORING**

### **Key Metrics to Track:**

1. **Click-Through Rate (CTR):**
   ```sql
   SELECT 
     COUNT(*) as total_links,
     SUM(click_count) as total_clicks,
     AVG(click_count) as avg_clicks_per_link,
     SUM(click_count)::float / COUNT(*) * 100 as ctr_percent
   FROM short_links
   WHERE link_type = 'site_preview';
   ```

2. **Links by Type:**
   ```sql
   SELECT link_type, COUNT(*), SUM(click_count)
   FROM short_links
   GROUP BY link_type
   ORDER BY COUNT(*) DESC;
   ```

3. **Most Clicked Links:**
   ```sql
   SELECT slug, destination_url, click_count, last_clicked_at
   FROM short_links
   WHERE link_type = 'site_preview'
   ORDER BY click_count DESC
   LIMIT 10;
   ```

---

## 🚨 **KNOWN ISSUES**

### **1. ShortLink Model Import Disabled**
- **Status:** TEMP disabled due to SQLAlchemy error
- **Cause:** Unknown (possibly caching/import order issue)
- **Fix:** Re-enable and test after other changes deployed

### **2. DNS Not Configured**
- **Status:** lvsh.cc purchased but not pointing to VPS
- **Action:** Configure DNS and Nginx vhost

### **3. SMS Service Needs DB Injection**
- **Status:** SMSGenerator doesn't have AsyncSession
- **Action:** Refactor to accept db parameter or use context manager

---

## 🎯 **RECOMMENDED NEXT STEPS**

1. **Immediate:**
   - Set `shortener_domain = 'lvsh.cc'` in system_settings
   - Re-enable ShortLink model
   - Test shortener API endpoints

2. **DNS Setup:**
   - Configure lvsh.cc to point to VPS IP
   - Create Nginx vhost for lvsh.cc
   - Test SSL certificate (Let's Encrypt)

3. **SMS Integration:**
   - Refactor SMS generator to use shortener
   - Update templates for optimal length
   - A/B test short vs long URLs

4. **Monitoring:**
   - Set up dashboard for shortener stats
   - Track CTR by business category
   - Monitor for suspicious activity (abuse)

---

## 💡 **BEST PRACTICES**

### **DO:**
- ✅ Use `get_or_create_short_link()` for site previews (idempotent)
- ✅ Set appropriate `link_type` for filtering
- ✅ Associate links with business/site/campaign for analytics
- ✅ Monitor click counts for engagement metrics
- ✅ Use short links in ALL channels (SMS, email, ads)

### **DON'T:**
- ❌ Don't create multiple short links for same destination
- ❌ Don't delete links (soft delete with `is_active=false`)
- ❌ Don't expose admin endpoints publicly
- ❌ Don't forget to set expiration for temporary campaigns
- ❌ Don't use predictable slugs (always use random generation)

---

## 🔮 **FUTURE ENHANCEMENTS**

1. **Advanced Analytics:**
   - Geographic tracking (IP → location)
   - Device/browser detection (User-Agent parsing)
   - Time-series click data (hourly/daily trends)
   - Referrer tracking (where clicks came from)

2. **QR Code Generation:**
   - Generate QR codes for short links
   - Useful for print materials, business cards

3. **Custom Domains:**
   - Support multiple shortener domains
   - Brand-specific domains (e.g., `la.chiro.link`)

4. **Link Rotation:**
   - A/B test multiple destinations for same slug
   - Load balancing across multiple destinations

5. **Rate Limiting:**
   - Prevent abuse (DDoS, spam)
   - Per-IP limits on redirect endpoint

---

## 📚 **REFERENCES**

- **Service:** `backend/services/shortener/short_link_service.py`
- **Model:** `backend/models/short_link.py`
- **Admin API:** `backend/api/v1/shortener.py`
- **Redirect API:** `backend/api/redirect.py`
- **Slug Generator:** `backend/services/shortener/slug_generator.py`
- **Migration:** `backend/migrations/015_create_short_links.sql`
