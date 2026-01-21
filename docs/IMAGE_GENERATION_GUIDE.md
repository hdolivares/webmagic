# Image Generation with Nano Banana (Gemini)

This guide explains how to implement Google's Gemini image generation (Nano Banana) in WebMagic for creating website imagery.

## Overview

**What is Nano Banana?**
- Google's native image generation capability built into Gemini models
- Fast, cost-effective, and high-quality image generation
- Integrated conversationally with text

**Models Available:**
- `gemini-2.5-flash-image` (**Recommended for WebMagic**) - Fast, 1K resolution
- `gemini-3-pro-image-preview` - Professional quality, up to 4K, with thinking mode

## Setup

### 1. Get Gemini API Key

1. Visit [https://ai.google.dev/](https://ai.google.dev/)
2. Sign in with your Google account
3. Click "Get API Key" → "Create API key"
4. Copy your API key

### 2. Add to Environment Variables

Update your `.env` file:

```bash
# Image Generation (Google Gemini)
GEMINI_API_KEY=your-gemini-api-key-here
```

### 3. Install Dependencies

The image service uses `httpx` for async HTTP requests (already in requirements.txt):

```bash
pip install httpx
```

## Architecture

### Image Service (`backend/services/creative/image_service.py`)

Centralized service for all image generation:

```
ImageGenerationService
├── generate_hero_image()       → Main hero/banner images
├── generate_section_background() → Section backgrounds
├── generate_product_image()     → Product/service photos
├── generate_icon()              → Icons and graphics
└── save_image_to_disk()         → Save to /var/www/sites/
```

### Integration with Architect Agent

The Architect agent orchestrates website creation and can now generate images:

```python
from services.creative.image_service import ImageGenerationService

class ArchitectAgent(BaseAgent):
    def __init__(self, prompt_builder: PromptBuilder):
        super().__init__(...)
        self.image_service = ImageGenerationService()
    
    async def generate_website(self, business_data, creative_dna, design_brief):
        # ... existing code ...
        
        # Generate hero image
        if settings.GEMINI_API_KEY:
            hero_image = await self.image_service.generate_hero_image(
                business_name=business_data.get("name"),
                category=business_data.get("category"),
                brand_archetype=creative_dna.get("brand_archetype"),
                color_palette=design_brief.get("color_palette"),
                aspect_ratio="16:9"
            )
            
            if hero_image:
                # Save to disk
                hero_path = await self.image_service.save_image_to_disk(
                    image_bytes=hero_image,
                    filename="hero.png",
                    subdomain=site_subdomain
                )
                
                # Include in HTML generation
                assets["hero_image"] = hero_path
```

## Usage Examples

### 1. Generate Hero Image

```python
from services.creative.image_service import ImageGenerationService

image_service = ImageGenerationService()

# Generate hero image
hero_bytes = await image_service.generate_hero_image(
    business_name="The Daily Grind",
    category="coffee shop",
    brand_archetype="Creator",
    color_palette={
        "primary": "#8B4513",
        "secondary": "#FFFFFF",
        "accent": "#FF6B35"
    },
    aspect_ratio="16:9"
)

# Save it
if hero_bytes:
    path = await image_service.save_image_to_disk(
        image_bytes=hero_bytes,
        filename="hero.png",
        subdomain="daily-grind"
    )
    print(f"Saved to: {path}")
```

### 2. Generate Section Background

```python
# Generate a warm background for testimonials section
bg_bytes = await image_service.generate_section_background(
    section_type="testimonials",
    mood="warm and welcoming",
    color_palette={
        "primary": "#FF6B35",
        "secondary": "#FFFFFF"
    },
    aspect_ratio="16:9"
)
```

### 3. Generate Product Images

```python
# Generate product photo
product_bytes = await image_service.generate_product_image(
    product_description="a freshly brewed cappuccino with latte art in a white ceramic cup",
    style="professional",
    aspect_ratio="1:1"  # Square for products
)
```

### 4. Generate Icons

```python
# Generate icon
icon_bytes = await image_service.generate_icon(
    icon_description="a steaming coffee cup",
    style="modern minimalist"
)
```

## Image Generation Strategy

### What to Generate

**Always Generate:**
- ✅ **Hero Images** - Main visual impact for homepage
- ✅ **Section Backgrounds** - Subtle, text-friendly backgrounds
- ✅ **Missing Product Images** - When business has no photos

**Sometimes Generate:**
- ⚠️ **Service Icons** - If custom icons are needed
- ⚠️ **Team Placeholders** - Generic professional photos

**Never Generate:**
- ❌ **Business Logos** - Use actual logo if provided
- ❌ **Real People** - Only use actual team photos

### Prompt Best Practices

From the [Gemini docs](https://ai.google.dev/gemini-api/docs/image-generation):

1. **Describe the Scene** - Use full sentences, not keywords
   - ✅ "A modern, minimalist coffee shop interior with warm lighting and plants"
   - ❌ "coffee shop modern minimalist"

2. **Be Hyper-Specific** - Include details about:
   - Lighting ("soft, golden hour light", "studio lighting")
   - Style ("photorealistic", "minimalist", "artistic")
   - Mood ("welcoming", "professional", "energetic")
   - Colors (specific hex codes or named colors)

3. **Use Photography Terms** - For realistic images:
   - Camera angles ("close-up portrait", "wide-angle shot")
   - Lens types ("85mm portrait lens", "macro shot")
   - Composition ("rule of thirds", "centered composition")

4. **Negative Space** - For backgrounds that need text:
   - "significant negative space for text overlay"
   - "minimalist composition with empty areas"

### Example Prompts

**Hero Image (Restaurant):**
```
A stunning, photorealistic interior shot of a modern Italian restaurant. 
Warm ambient lighting from Edison bulbs creates a cozy atmosphere. 
Rustic wooden tables with white tablecloths, wine glasses catching the light. 
Exposed brick walls with vintage wine bottles on shelves. 
Soft focus on background diners, creating depth. 
Color palette: warm browns (#8B4513), cream (#FFFDD0), and burgundy (#800020). 
Professional food photography style, shot with 35mm lens. 
No text or logos. High resolution, suitable for website hero banner.
```

**Section Background (Services):**
```
A minimalist, abstract background with soft gradients transitioning from 
light blue (#E3F2FD) to white (#FFFFFF). Subtle geometric patterns creating 
visual interest without distraction. Significant negative space for text overlay. 
Professional, modern design suitable for a services section. 
Soft, diffused lighting from the top. High resolution for web use.
```

## Cost & Performance

### Pricing (as of Jan 2025)

Check latest pricing: [https://ai.google.dev/pricing](https://ai.google.dev/pricing)

**gemini-2.5-flash-image** (Recommended):
- ~1290 tokens per 1024x1024 image
- Very cost-effective for high-volume generation

**gemini-3-pro-image-preview**:
- ~1120 tokens for 1K resolution
- ~2000 tokens for 4K resolution
- Use for professional asset production

### Performance Tips

1. **Batch Generation** - Generate multiple images in parallel
2. **Cache Responses** - Store generated images for reuse
3. **Fallback Strategy** - Have placeholder images ready
4. **Lazy Loading** - Generate images asynchronously after site creation

### Rate Limits

- Check [Rate Limits docs](https://ai.google.dev/gemini-api/docs/rate-limits)
- Implement exponential backoff for retries
- Use request queuing for high volume

## Advanced Features

### Multi-turn Editing

Use chat/conversation to iterate on images:

```python
from google import genai
from google.genai import types

client = genai.Client()

chat = client.chats.create(
    model="gemini-2.5-flash-image",
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
    )
)

# Initial generation
response = chat.send_message("Create a coffee shop hero image...")

# Refine it
response = chat.send_message("Make the lighting warmer and add more plants")

# Final tweak
response = chat.send_message("Perfect! Now add morning sunlight through windows")
```

### Image Editing

Edit existing images by providing them as input:

```python
from PIL import Image

# Load existing image
existing_image = Image.open("path/to/image.png")

# Generate edited version
response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=[
        "Change only the blue sofa to brown leather, keep everything else the same",
        existing_image
    ]
)
```

## Troubleshooting

### Image Not Generated

```python
# Check response
if hero_bytes is None:
    logger.error("Image generation failed")
    # Use fallback placeholder
    hero_bytes = load_placeholder_image()
```

### API Key Issues

```bash
# Test API key
curl -H "x-goog-api-key: YOUR_API_KEY" \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image"
```

### Rate Limit Errors

```python
# Implement exponential backoff
import asyncio

async def generate_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await image_service.generate_hero_image(...)
        except RateLimitError:
            wait_time = (2 ** attempt) * 1  # 1s, 2s, 4s
            await asyncio.sleep(wait_time)
    return None
```

## Next Steps

1. ✅ Add `GEMINI_API_KEY` to your `.env` file
2. ✅ Test the image service with sample prompts
3. ✅ Integrate with Architect agent for automated generation
4. ✅ Implement fallback strategy for failed generations
5. ✅ Monitor usage and costs in Google Cloud Console

## Resources

- [Gemini Image Generation Docs](https://ai.google.dev/gemini-api/docs/image-generation)
- [Pricing](https://ai.google.dev/pricing)
- [Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Cookbook Examples](https://github.com/google-gemini/cookbook)
