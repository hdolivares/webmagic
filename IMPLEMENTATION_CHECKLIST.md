# Implementation Checklist: RLS Fix & Image Generation

## 🚨 Critical: Fix RLS Database Connection

### Issue
Your RLS policies use Supabase Auth (`auth.uid()`), but your backend uses custom authentication. This causes all database queries to be blocked.

### Solution: Use Service Role Key

**Action Required:**

1. **Get your Supabase service_role key:**
   - Go to [Supabase Dashboard](https://supabase.com/dashboard)
   - Select your project
   - Settings → API
   - Copy the `service_role` key (⚠️ Keep it secret!)

2. **Update DATABASE_URL on VPS:**

```bash
# SSH into your VPS
ssh root@104.251.211.183

# Edit the .env file
nano /var/www/webmagic/backend/.env

# Find the DATABASE_URL line and update it:
# OLD (using anon key - RLS blocks this):
DATABASE_URL=postgresql+asyncpg://postgres.xxx:[ANON_KEY]@xxx.supabase.co:5432/postgres

# NEW (using service_role key - bypasses RLS):
DATABASE_URL=postgresql+asyncpg://postgres.xxx:[SERVICE_ROLE_KEY]@xxx.supabase.co:5432/postgres

# Save and exit (Ctrl+X, Y, Enter)
```

3. **Restart the backend:**

```bash
# Restart supervisor services
supervisorctl restart webmagic-api
supervisorctl restart webmagic-celery

# Verify they're running
supervisorctl status
```

### Why This is Safe

✅ **RLS is still enabled** - Protects direct database access  
✅ **Backend bypasses RLS** - Standard for server-side apps with custom auth  
✅ **Your API security layer** handles authorization (JWT tokens)  
✅ **Only authenticated admins** can access your FastAPI endpoints

---

## 🎨 New Feature: Image Generation with Nano Banana

### What's New

We've implemented Google's Gemini image generation (Nano Banana) to automatically create:
- Hero images for websites
- Section backgrounds
- Product/service photos
- Icons and graphics

### Setup Steps

#### 1. Get Gemini API Key

1. Visit [https://ai.google.dev/](https://ai.google.dev/)
2. Click "Get API key" → "Create API key"
3. Copy your API key

#### 2. Add to Local `.env`

```bash
# In your local c:\Projects\webmagic\backend\.env
GEMINI_API_KEY=your-gemini-api-key-here
```

#### 3. Add to VPS `.env`

```bash
# SSH into VPS
ssh root@104.251.211.183

# Edit .env
nano /var/www/webmagic/backend/.env

# Add this line:
GEMINI_API_KEY=your-gemini-api-key-here

# Save and exit
```

#### 4. Test the Image Service

```bash
# On your local machine
cd c:\Projects\webmagic\backend

# Create a test script
cat > test_image_gen.py << 'EOF'
import asyncio
from services.creative.image_service import ImageGenerationService

async def test():
    service = ImageGenerationService()
    
    # Test hero image generation
    print("Generating hero image...")
    image_bytes = await service.generate_hero_image(
        business_name="Test Coffee Shop",
        category="cafe",
        brand_archetype="Creator",
        color_palette={
            "primary": "#8B4513",
            "secondary": "#FFFFFF",
            "accent": "#FF6B35"
        }
    )
    
    if image_bytes:
        with open("test_hero.png", "wb") as f:
            f.write(image_bytes)
        print(f"✅ Success! Generated {len(image_bytes)} bytes")
        print("Saved as test_hero.png")
    else:
        print("❌ Failed to generate image")

asyncio.run(test())
EOF

# Run the test
python test_image_gen.py
```

### Integration with Architect Agent

The image service is ready to use. To integrate with the Architect agent:

**Option 1: Automatic Generation (Recommended)**

Update `backend/services/creative/agents/architect.py`:

```python
from services.creative.image_service import ImageGenerationService

class ArchitectAgent(BaseAgent):
    def __init__(self, prompt_builder: PromptBuilder):
        super().__init__(...)
        self.image_service = ImageGenerationService()
    
    async def generate_website(self, business_data, creative_dna, design_brief):
        # ... existing code ...
        
        # Generate hero image if Gemini API key is configured
        hero_image_path = None
        if settings.GEMINI_API_KEY:
            try:
                hero_bytes = await self.image_service.generate_hero_image(
                    business_name=business_data.get("name"),
                    category=business_data.get("category"),
                    brand_archetype=creative_dna.get("brand_archetype"),
                    color_palette=design_brief.get("color_palette"),
                    aspect_ratio="16:9"
                )
                
                if hero_bytes and site_subdomain:
                    hero_image_path = await self.image_service.save_image_to_disk(
                        image_bytes=hero_bytes,
                        filename="hero.png",
                        subdomain=site_subdomain
                    )
                    logger.info(f"Generated hero image: {hero_image_path}")
            except Exception as e:
                logger.warning(f"Failed to generate hero image: {e}")
        
        # Include in assets
        if hero_image_path:
            result["assets_urls"] = result.get("assets_urls", [])
            result["assets_urls"].append(hero_image_path)
```

**Option 2: On-Demand Generation**

Create a new API endpoint for manual image generation:

```python
# In backend/api/v1/sites.py
from services.creative.image_service import ImageGenerationService

@router.post("/{site_id}/generate-images")
async def generate_site_images(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Generate images for an existing site."""
    
    # Get site and business data
    site = await db.get(GeneratedSite, site_id)
    business = await db.get(Business, site.business_id)
    
    # Generate images
    image_service = ImageGenerationService()
    
    hero_bytes = await image_service.generate_hero_image(
        business_name=business.name,
        category=business.category,
        brand_archetype=business.creative_dna.get("brand_archetype"),
        color_palette={...},
    )
    
    if hero_bytes:
        path = await image_service.save_image_to_disk(
            image_bytes=hero_bytes,
            filename="hero.png",
            subdomain=site.subdomain
        )
        
        return {"success": True, "hero_image": path}
```

---

## 📝 Summary of Changes

### Files Created

1. ✅ `backend/services/creative/image_service.py` - Image generation service
2. ✅ `docs/IMAGE_GENERATION_GUIDE.md` - Complete implementation guide

### Files Modified

1. ✅ `backend/core/config.py` - Added `GEMINI_API_KEY` setting
2. ✅ `backend/env.template` - Added Gemini API key documentation

### Configuration Changes

1. ⚠️ **REQUIRED**: Update `DATABASE_URL` to use service_role key
2. ⚠️ **OPTIONAL**: Add `GEMINI_API_KEY` for image generation

---

## ✅ Action Items

### Immediate (Required)

- [ ] Get Supabase service_role key
- [ ] Update DATABASE_URL in VPS `.env`
- [ ] Restart supervisor services
- [ ] Test API endpoints work correctly

### Optional (Image Generation)

- [ ] Get Gemini API key from [ai.google.dev](https://ai.google.dev/)
- [ ] Add GEMINI_API_KEY to local `.env`
- [ ] Test image generation locally
- [ ] Add GEMINI_API_KEY to VPS `.env`
- [ ] Integrate with Architect agent (choose Option 1 or 2)
- [ ] Test end-to-end website generation with images

---

## 📚 Documentation

- **RLS Security**: See [Supabase RLS Docs](https://supabase.com/docs/guides/auth/row-level-security)
- **Service Role**: See [Supabase API Docs](https://supabase.com/docs/guides/api#the-service_role-key)
- **Image Generation**: See `docs/IMAGE_GENERATION_GUIDE.md`
- **Gemini API**: See [https://ai.google.dev/gemini-api/docs/image-generation](https://ai.google.dev/gemini-api/docs/image-generation)

---

## 🆘 Troubleshooting

### Database Connection Issues

```bash
# Test database connection
cd /var/www/webmagic/backend
source .venv/bin/activate
python -c "from core.database import engine; import asyncio; asyncio.run(engine.connect())"
```

### Image Generation Issues

```bash
# Test Gemini API key
curl -H "x-goog-api-key: YOUR_KEY" \
  "https://generativelanguage.googleapis.com/v1beta/models"
```

### Service Status

```bash
# Check if services are running
supervisorctl status

# View logs
tail -f /var/log/webmagic/api.log
tail -f /var/log/webmagic/celery.log
```

---

## 💰 Cost Estimation

### Image Generation (Gemini)

- **gemini-2.5-flash-image**: ~1290 tokens per image (~$0.001 per image at current rates)
- Very cost-effective for generating 10-100 images per website
- Check latest pricing: [https://ai.google.dev/pricing](https://ai.google.dev/pricing)

### Example Costs

- **1 website with 5 images**: ~$0.005
- **100 websites per month**: ~$0.50
- **1000 websites per month**: ~$5.00

---

## 🎯 Next Steps

After completing the checklist:

1. **Commit changes to GitHub**
   ```bash
   git add .
   git commit -m "Add Gemini image generation and fix RLS configuration"
   git push origin main
   ```

2. **Pull changes to VPS**
   ```bash
   ssh root@104.251.211.183
   cd /var/www/webmagic
   git pull origin main
   supervisorctl restart all
   ```

3. **Test the full pipeline**
   - Create a test campaign
   - Generate a website
   - Verify images are generated and saved
   - Check the website renders correctly

---

**Questions or issues?** Check the detailed documentation in `docs/IMAGE_GENERATION_GUIDE.md`
