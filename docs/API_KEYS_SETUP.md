# 🔑 API Keys Setup Guide

This guide explains where to get each API key and what they're used for.

---

## 🚨 **Required for Discovery Campaign Testing**

### 1. **ANTHROPIC_API_KEY** 🤖
**Purpose**: Powers all AI agents (Analyst, Concept, Art Director, Architect)

**How to Get**:
1. Go to: https://console.anthropic.com/
2. Sign up or log in
3. Click **"API Keys"** in the left sidebar
4. Click **"Create Key"**
5. Copy your key (starts with `sk-ant-...`)
6. Paste into `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

**Cost**: 
- ~$3-5 per 1,000 messages
- For testing: ~$0.50 per site generated
- Start with $10 credit (usually free for new accounts)

**Used by**:
- ✅ Analyzing business reviews
- ✅ Generating brand concepts
- ✅ Creating design systems
- ✅ Building HTML/CSS for sites

---

### 2. **OUTSCRAPER_API_KEY** 🗺️
**Purpose**: Scrapes business data from Google Maps

**Why Outscraper vs ScrapingDog?**
While ScrapingDog is ~70% cheaper ($0.003/business vs $0.01/business), **Outscraper is required for WebMagic** because:
- ✅ **Includes full review text** - Your AI Analyst needs this to find "what customers love"
- ✅ **Includes business photos** - Your generated websites need these images
- ✅ **Better data quality** - More reliable for agency-grade output
- ❌ ScrapingDog only provides review COUNT, no text or photos

**The extra $0.007 per business is worth it** when you're charging $50-500/site and need rich data for AI content generation.

**How to Get**:
1. Go to: https://app.outscraper.com/
2. Sign up with Google or email
3. Go to **Profile** → **API** (top-right menu)
4. Copy your API key
5. Paste into `.env`: `OUTSCRAPER_API_KEY=...`

**Cost**:
- ~$10 per 1,000 businesses (with reviews & photos)
- $2 free credit for new accounts (~200 businesses)
- Recommended: Add $20 credit for testing (~2,000 businesses)

**Used by**:
- ✅ Discovery Campaign scraping
- ✅ Finding businesses without websites
- ✅ Getting contact info, reviews, and photos

---

### 3. **RECURRENTE_PUBLIC_KEY** 💳
**Purpose**: Handles payments and subscriptions

**How to Get**:
1. Go to: https://app.recurrente.com/
2. Sign up (Costa Rica-based payment processor)
3. Go to **Settings** → **API Keys**
4. Copy your **Public Key** (starts with `pk_...`)
5. Copy your **Secret Key** (starts with `sk_...`)
6. Paste into `.env`:
   ```
   RECURRENTE_PUBLIC_KEY=pk_...
   RECURRENTE_SECRET_KEY=sk_...
   ```

**Cost**: 
- Free to set up
- Transaction fees: ~2.9% + $0.30 per charge
- No monthly fees

**Used by**:
- ✅ Charging customers for websites
- ✅ Managing subscriptions
- ✅ Processing refunds
- ✅ Webhook notifications

---

## 🔧 **Optional (Not Needed for Initial Testing)**

### 4. **REDIS_URL** (Optional)
**Purpose**: Task queue for background jobs (Celery)

**For Local Testing**: You don't need this! Tasks will run synchronously.

**If You Want It**:
- **Windows**: Install Redis via Docker or WSL
- **Cloud**: Use Redis Cloud (free tier available)
  - https://redis.com/try-free/
  - Copy connection URL
  - Paste into `.env`: `REDIS_URL=redis://...`

**Used by**:
- ✅ Batch scraping (running 100+ searches in background)
- ✅ Scheduled campaigns
- ✅ Email sending queue

---

### 5. **Email Provider** (Optional)
**Purpose**: Sending outreach emails to businesses

#### Option A: Brevo (RECOMMENDED - Best for startups) ⭐
1. Go to: https://app.brevo.com/
2. Sign up (free account)
3. Verify your sending domain (optional but recommended)
4. Go to: **Settings** → **SMTP & API** → **API Keys**
5. Click "Create a new API key"
6. Copy the key
7. Paste into `.env`:
   ```
   EMAIL_PROVIDER=brevo
   BREVO_API_KEY=...
   ```

**Cost**: 
- **FREE: 300 emails/day** (9,000/month)
- Paid: $25/month for 20K emails
- Excellent deliverability

**Why Brevo?**
- ✅ Most generous free tier (300/day vs 100/day)
- ✅ No credit card required for free tier
- ✅ Better UI than SendGrid
- ✅ Includes marketing automation features

#### Option B: AWS SES (For high volume)
1. Go to: https://aws.amazon.com/ses/
2. Create an account
3. Request production access (required to send to any email)
4. Create IAM user with SES permissions
5. Get Access Key ID and Secret Key
6. Paste into `.env`:
   ```
   EMAIL_PROVIDER=ses
   AWS_ACCESS_KEY_ID=...
   AWS_SECRET_ACCESS_KEY=...
   AWS_REGION=us-east-1
   ```

**Cost**: $0.10 per 1,000 emails (cheapest at scale)

#### Option C: SendGrid (Alternative)
1. Go to: https://sendgrid.com/
2. Sign up (free tier: 100 emails/day)
3. Create API key: Settings → API Keys
4. Paste into `.env`:
   ```
   EMAIL_PROVIDER=sendgrid
   SENDGRID_API_KEY=...
   ```

**Cost**: Free for 100/day, then $15/month for 40K emails

---

## 📋 **Quick Setup Checklist**

### **For Testing Discovery Campaign** (Minimum Required):
- [ ] 1. Get **Anthropic API Key** ($10 free credit)
- [ ] 2. Get **Outscraper API Key** ($2 free credit)
- [ ] 3. Get **Recurrente Keys** (free setup)
- [ ] 4. Update `.env` with all 3 keys
- [ ] 5. Run `python backend/scripts/init_campaign.py`
- [ ] 6. Test with 5 searches on Coverage page

### **For Full Production System**:
- [ ] 1-4. Above ✅
- [ ] 5. Set up Redis (for background tasks)
- [ ] 6. Set up AWS SES or SendGrid (for emails)
- [ ] 7. Configure domain for hosted sites
- [ ] 8. Set up monitoring/logging

---

## 💰 **Total Cost to Start Testing**

| Service | Free Credit | Recommended Add | Purpose |
|---------|-------------|-----------------|---------|
| **Anthropic** | $10 | $20 | AI content generation |
| **Outscraper** | $2 (~100 biz) | $20 (~2,000 biz) | Business scraping |
| **Recurrente** | Free | $0 | Payment processing (only fees on sales) |
| **TOTAL** | **$12 free** | **+$40** | **52 total to test properly** |

### **What This Gets You**:
- ✅ **~2,000 businesses** scraped across 40 searches
- ✅ **~20-40 websites** generated with AI
- ✅ **Full system testing** before going live
- ✅ **Payment system ready** for first customers

---

## 🔐 **Security Best Practices**

### **DO**:
- ✅ Keep `.env` in `.gitignore` (already done)
- ✅ Use different keys for development vs production
- ✅ Rotate keys every 90 days
- ✅ Set spending limits on each service
- ✅ Monitor usage dashboards

### **DON'T**:
- ❌ Commit `.env` to Git (it's ignored, but double-check)
- ❌ Share keys in Discord, Slack, or anywhere public
- ❌ Use production keys in local development
- ❌ Give keys to contractors without restrictions

---

## 🆘 **Troubleshooting**

### **"Invalid API Key" Error**

**Anthropic**:
- Key must start with `sk-ant-`
- Make sure no extra spaces in `.env`
- Check usage limits: https://console.anthropic.com/settings/limits

**Outscraper**:
- Key is ~40 characters
- Check balance: https://app.outscraper.com/profile
- Make sure account is verified (email confirmation)

**Recurrente**:
- Public key starts with `pk_`
- Secret key starts with `sk_`
- Make sure you're using production keys (not test keys)

### **"Rate Limit Exceeded"**

**Anthropic**: 
- Free tier: 50 requests/minute
- Upgrade to paid: https://console.anthropic.com/settings/plans

**Outscraper**:
- Free tier: 10 requests/minute
- Add credits to increase limit

### **Keys Not Loading**

1. **Check file encoding**: `.env` should be UTF-8
2. **Restart backend**: Keys are loaded on startup
3. **Check syntax**: No quotes needed around values
4. **Verify location**: `.env` must be in `backend/` folder

---

## 📞 **Support Links**

- **Anthropic**: https://docs.anthropic.com/
- **Outscraper**: https://outscraper.com/documentation/
- **Recurrente**: https://docs.recurrente.com/
- **Redis**: https://redis.io/docs/
- **AWS SES**: https://docs.aws.amazon.com/ses/
- **SendGrid**: https://docs.sendgrid.com/

---

## 🎉 **Next Steps**

Once you have all 3 required keys:

1. **Update `.env`** with your keys
2. **Restart backend**: 
   ```bash
   cd C:\Projects\webmagic\backend
   .\venv\Scripts\Activate.ps1
   python start.py
   ```
3. **Initialize campaign data**:
   ```bash
   python scripts/init_campaign.py
   ```
4. **Open browser**: http://localhost:3000/coverage
5. **Run test**: Slide to 5 searches, click "Test 5 Searches"
6. **Watch magic happen!** ✨

---

**Questions? Check the main README or QUICKSTART.md for more info!**
