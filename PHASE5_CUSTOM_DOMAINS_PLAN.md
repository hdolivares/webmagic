# Phase 5: Custom Domain Support - Implementation Plan

**Estimated Time:** 4-6 hours  
**Priority:** High (Premium feature)  
**Complexity:** Medium-High  

---

## 🎯 OBJECTIVE

Enable customers with active subscriptions to connect their own custom domains (e.g., `www.johnplumbing.com`) to their generated websites with automatic SSL certificates.

---

## 💰 BUSINESS VALUE

### **Why This Matters:**
- **Professional Branding**: Customers get their own domain
- **SEO Benefits**: Better for search engine ranking
- **Trust Signal**: Custom domains build credibility
- **Subscription Driver**: Major reason to maintain $95/month
- **Competitive Parity**: Expected feature for professional sites

### **Requirements:**
```
Subscription Status: MUST be "active"
Monthly Fee: Already included in $95/month
Limitation: 1 custom domain per site
Process: Customer brings their own domain
```

---

## 📋 FEATURES TO IMPLEMENT

### **1. Domain Verification System** ✅ (Database ready)
```
Table: domain_verification_records
- id (UUID)
- site_id (FK to sites)
- domain (string)  # e.g., "www.johnplumbing.com"
- verification_method (string)  # dns_txt, dns_cname
- verification_token (string)  # Random token for DNS record
- verification_status (string)  # pending, verified, failed
- verified_at (timestamp)
- dns_records (JSONB)  # What customer needs to add
```

### **2. Customer Interface** (Frontend)
```tsx
// Domain connection wizard
<DomainSetup>
  Step 1: Enter Domain
    - Input: "www.johnplumbing.com"
    - Validation: DNS check
    
  Step 2: Verification Method
    - Option A: Add TXT record (recommended)
    - Option B: Add CNAME record
    
  Step 3: DNS Instructions
    - Clear instructions
    - Copy-paste records
    - Verify button
    
  Step 4: SSL Provisioning
    - Automatic Let's Encrypt
    - Progress indicator
    
  Step 5: Complete
    - Domain is live
    - Both URLs work
</DomainSetup>

// Domain management
<DomainManagement>
  - Current domain
  - Verification status
  - SSL status
  - Remove domain button
  - Troubleshooting help
</DomainManagement>
```

---

## 🏗️ ARCHITECTURE

### **Service Layer:**
```python
# backend/services/domain_service.py
class DomainService:
    @staticmethod
    async def request_domain_connection(
        db: AsyncSession,
        site_id: UUID,
        domain: str
    ) -> Dict:
        """Initiate custom domain setup."""
        # 1. Validate domain format
        # 2. Check if domain already in use
        # 3. Create verification record
        # 4. Generate DNS instructions
        
    @staticmethod
    async def verify_domain(
        db: AsyncSession,
        site_id: UUID
    ) -> bool:
        """Check if DNS records are correct."""
        # 1. Query DNS for TXT/CNAME
        # 2. Compare with expected value
        # 3. Update verification status
        
    @staticmethod
    async def provision_ssl(
        db: AsyncSession,
        site_id: UUID,
        domain: str
    ) -> bool:
        """Get Let's Encrypt certificate."""
        # 1. Verify domain ownership
        # 2. Request cert from Let's Encrypt
        # 3. Install on nginx
        # 4. Configure auto-renewal
        
    @staticmethod
    async def configure_nginx(
        db: AsyncSession,
        site_id: UUID,
        domain: str
    ) -> bool:
        """Add domain to nginx config."""
        # 1. Generate nginx config block
        # 2. Test configuration
        # 3. Reload nginx
        # 4. Verify accessibility
        
    @staticmethod
    async def remove_domain(
        db: AsyncSession,
        site_id: UUID
    ) -> bool:
        """Remove custom domain."""
        # 1. Remove from nginx
        # 2. Delete SSL cert
        # 3. Update database
        # 4. Notify customer
```

---

## 🔄 DOMAIN CONNECTION WORKFLOW

### **Complete Flow:**
```
1. Customer enters domain in portal
   ↓
2. System validates format
   ↓
3. Generate verification token
   ↓
4. Show DNS instructions:
   "Add TXT record:
   Host: _webmagic-verify
   Value: abc123xyz789"
   ↓
5. Customer adds DNS record
   ↓
6. Customer clicks "Verify"
   ↓
7. System checks DNS (can take 24hrs)
   ↓
8. Once verified:
   - Request Let's Encrypt certificate
   - Add to nginx configuration
   - Reload nginx
   ↓
9. Domain is live! ✅
   - Both URLs work:
     - sites.lavish.solutions/slug
     - www.johnplumbing.com
```

---

## 📝 API ENDPOINTS

### **Domain Management:**
```python
POST   /api/v1/domains/connect
  Body: {
    "domain": "www.johnplumbing.com"
  }
  Response: {
    "verification_token": "abc123...",
    "dns_records": {
      "type": "TXT",
      "host": "_webmagic-verify",
      "value": "abc123..."
    },
    "instructions": "..."
  }

POST   /api/v1/domains/verify
  Response: {
    "verified": true,
    "ssl_status": "provisioning",
    "estimated_time": "5 minutes"
  }

GET    /api/v1/domains/status
  Response: {
    "domain": "www.johnplumbing.com",
    "verification_status": "verified",
    "ssl_status": "active",
    "ssl_expires": "2026-04-21",
    "last_checked": "2026-01-21T10:00:00Z"
  }

DELETE /api/v1/domains/disconnect
  Response: {
    "success": true,
    "message": "Domain disconnected. Site still accessible at default URL."
  }
```

---

## 🔧 NGINX CONFIGURATION

### **Dynamic Config Generation:**
```nginx
# /etc/nginx/sites-available/custom-domains/{site_slug}.conf

server {
    listen 80;
    listen [::]:80;
    server_name www.johnplumbing.com johnplumbing.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name www.johnplumbing.com johnplumbing.com;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/www.johnplumbing.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/www.johnplumbing.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Site files
    root /var/www/sites/la-plumbing-pros;
    index index.html;
    
    location / {
        try_files $uri $uri/ =404;
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
}
```

---

## 🔒 SSL/TLS MANAGEMENT

### **Let's Encrypt Integration:**
```python
# backend/services/ssl_service.py
class SSLService:
    @staticmethod
    async def request_certificate(
        domain: str,
        site_slug: str
    ) -> bool:
        """Request SSL cert from Let's Encrypt."""
        # Use certbot python API
        # Or shell out to certbot command
        
    @staticmethod
    async def renew_certificate(
        domain: str
    ) -> bool:
        """Renew expiring certificate."""
        # Check expiry
        # Renew if < 30 days
        
    @staticmethod
    async def setup_auto_renewal():
        """Configure automatic renewal."""
        # Celery beat task
        # Check all domains daily
        # Renew if needed
```

### **Certbot Command:**
```bash
# Request new certificate
certbot certonly \
  --webroot \
  --webroot-path /var/www/sites/{site_slug} \
  --domain www.johnplumbing.com \
  --email admin@lavish.solutions \
  --agree-tos \
  --non-interactive

# Auto-renewal (cron or Celery)
certbot renew --quiet
```

---

## 🔍 DNS VERIFICATION

### **Verification Methods:**

**Method 1: TXT Record (Recommended)**
```
Host: _webmagic-verify.www.johnplumbing.com
Type: TXT
Value: webmagic-verification=abc123xyz789
TTL: 3600

Benefits:
✓ No downtime
✓ Works while site is elsewhere
✓ Can verify before switching
```

**Method 2: CNAME Record**
```
Host: www.johnplumbing.com
Type: CNAME
Value: verify.sites.lavish.solutions
TTL: 3600

Benefits:
✓ Simpler for some users
✓ Direct domain pointing
```

### **Verification Check:**
```python
import dns.resolver

async def verify_txt_record(domain: str, token: str) -> bool:
    """Check if TXT record exists."""
    try:
        answers = dns.resolver.resolve(
            f"_webmagic-verify.{domain}",
            'TXT'
        )
        for rdata in answers:
            if token in str(rdata):
                return True
        return False
    except Exception as e:
        logger.error(f"DNS verification failed: {e}")
        return False
```

---

## 🧪 TESTING STRATEGY

### **Unit Tests:**
```python
test_domain_format_validation()
test_generate_verification_token()
test_dns_verification()
test_ssl_certificate_request()
test_nginx_config_generation()
test_domain_removal()
```

### **Integration Tests:**
```python
test_complete_domain_setup_flow()
test_ssl_auto_renewal()
test_domain_conflict_handling()
test_verification_timeout()
test_nginx_reload()
```

### **Manual Tests:**
```
✓ Add custom domain
✓ Verify DNS records
✓ Confirm SSL certificate
✓ Test HTTPS access
✓ Test redirect (HTTP → HTTPS)
✓ Test both www and non-www
✓ Remove custom domain
✓ Verify fallback to default URL
```

---

## 📧 EMAIL NOTIFICATIONS

### **Domain Verification Pending:**
```
Subject: Action Required: Verify Your Custom Domain
Body:
- Domain entered: www.johnplumbing.com
- DNS records to add
- Step-by-step instructions
- Help link
```

### **Domain Verified:**
```
Subject: Domain Verified - SSL Setup in Progress
Body:
- Confirmation of verification
- SSL provisioning status
- Estimated completion time
```

### **Domain Active:**
```
Subject: Your Custom Domain is Live! 🎉
Body:
- Domain: www.johnplumbing.com
- SSL certificate active
- Both URLs work
- Next steps
```

### **SSL Renewal Reminder:**
```
Subject: SSL Certificate Renewed
Body:
- Auto-renewed successfully
- New expiration date
- No action needed
```

---

## 🚨 ERROR HANDLING

### **Common Issues:**

**1. Domain Already in Use**
```
Error: "This domain is already connected to another site"
Solution: Disconnect from other site first
```

**2. DNS Propagation Delay**
```
Error: "DNS records not found"
Solution: Wait 24-48 hours, retry verification
```

**3. SSL Certificate Failure**
```
Error: "Failed to obtain SSL certificate"
Causes:
- Domain not pointing to our servers
- Port 80/443 not accessible
- Rate limit exceeded
Solution: Check DNS, firewall, wait 1 hour
```

**4. Nginx Reload Failure**
```
Error: "Configuration test failed"
Causes:
- Syntax error in config
- Certificate path wrong
Solution: Rollback config, fix issue
```

---

## 🔒 SECURITY CONSIDERATIONS

### **Domain Ownership:**
```
✓ Verify via DNS (prevents hijacking)
✓ Require active subscription
✓ One domain per site
✓ Audit log all changes
```

### **SSL Security:**
```
✓ Only TLS 1.2+
✓ Strong cipher suites
✓ HSTS headers
✓ Auto-renewal 30 days before expiry
```

### **Nginx Security:**
```
✓ Prevent directory traversal
✓ Security headers
✓ Rate limiting
✓ Config validation before reload
```

---

## 📊 MONITORING

### **Metrics to Track:**
```
- Total domains connected
- Verification success rate
- Average verification time
- SSL certificate status
- Failed renewals
- Nginx reload failures
```

### **Alerts:**
```
⚠️ SSL certificate expires in < 7 days
⚠️ Domain verification pending > 48 hours
⚠️ Nginx reload failed
⚠️ SSL renewal failed
```

---

## 🚀 IMPLEMENTATION PHASES

### **Phase 5.1: Domain Verification** (2 hours)
```
✓ API endpoints for domain management
✓ DNS verification logic
✓ Verification token generation
✓ Customer instructions
```

### **Phase 5.2: SSL Integration** (2 hours)
```
✓ Let's Encrypt integration
✓ Certificate request automation
✓ Storage and management
✓ Auto-renewal system
```

### **Phase 5.3: Nginx Configuration** (1.5 hours)
```
✓ Dynamic config generation
✓ Config validation
✓ Safe reload mechanism
✓ Rollback capability
```

### **Phase 5.4: Testing & Polish** (0.5 hours)
```
✓ End-to-end testing
✓ Error handling
✓ Email notifications
✓ Documentation
```

---

## 💡 TECHNICAL DECISIONS

### **1. DNS Verification Method:**
**Decision:** TXT record (primary), CNAME (alternative)  
**Reason:** TXT is safer, no downtime during verification  

### **2. SSL Provider:**
**Decision:** Let's Encrypt  
**Reason:** Free, automatic, trusted, 90-day rotation  

### **3. Nginx Management:**
**Decision:** Dynamic config files per domain  
**Reason:** Easier to manage, isolated configs  

### **4. Domain Limit:**
**Decision:** 1 domain per site  
**Reason:** Simplicity, clear pricing  

---

## 📦 DEPENDENCIES

### **Python Packages:**
```python
# requirements.txt additions
certbot==2.7.4  # Let's Encrypt client
dnspython==2.4.2  # DNS queries
acme==2.7.4  # ACME protocol
```

### **System Requirements:**
```bash
# Nginx with SSL modules
sudo apt install nginx-full

# Certbot
sudo apt install certbot python3-certbot-nginx

# DNS tools
sudo apt install dnsutils
```

---

## 🎯 SUCCESS CRITERIA

### **Technical:**
- ✓ Domain verification works in < 5 minutes
- ✓ SSL certificates provision automatically
- ✓ Nginx reloads without downtime
- ✓ 99.9% SSL renewal success rate

### **User Experience:**
- ✓ Clear step-by-step instructions
- ✓ Real-time status updates
- ✓ Helpful error messages
- ✓ One-click verification

---

## 🔮 FUTURE ENHANCEMENTS

### **Phase 5+:**
```
1. Multiple domains per site
   - Redirects to primary
   - Different content per domain

2. Subdomain support
   - blog.johnplumbing.com
   - shop.johnplumbing.com

3. Cloudflare integration
   - Automatic DNS configuration
   - Built-in CDN
   - DDoS protection

4. Custom SSL certificates
   - Customer brings own cert
   - Wildcard certificates
```

---

_Planning Document Created: January 21, 2026_  
_Estimated Implementation: 4-6 hours_  
_Dependencies: Phase 3 complete (active subscription)_  
_Priority: HIGH (Premium feature)_

**Ready to implement custom domains!** 🌐
