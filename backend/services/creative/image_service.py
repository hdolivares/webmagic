"""
Image Generation Service using Google Gemini (Nano Banana).
Generates images for website creation using gemini-2.5-flash-image model.
"""
import logging
import base64
import httpx
from typing import Dict, Any, List, Optional
from pathlib import Path
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ImageGenerationService:
    """
    Service for generating images using Google's Gemini image generation API.
    Uses gemini-2.5-flash-image (Nano Banana) for fast, cost-effective generation.
    """
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = "gemini-2.5-flash-image"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
    async def generate_hero_image(
        self,
        business_name: str,
        category: str,
        brand_archetype: str,
        color_palette: Dict[str, str],
        aspect_ratio: str = "16:9"
    ) -> Optional[bytes]:
        """
        Generate a hero image for the website.
        
        Args:
            business_name: Name of the business
            category: Business category (e.g., "restaurant", "spa")
            brand_archetype: Brand archetype (e.g., "Explorer", "Caregiver")
            color_palette: Dict with primary, secondary, accent colors
            aspect_ratio: Image aspect ratio (default: 16:9)
            
        Returns:
            Image bytes (PNG format) or None if generation fails
        """
        prompt = self._build_hero_prompt(
            business_name, 
            category, 
            brand_archetype, 
            color_palette
        )
        
        return await self._generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            response_modalities=["IMAGE"]  # Image only, no text
        )
    
    async def generate_section_background(
        self,
        section_type: str,
        mood: str,
        color_palette: Dict[str, str],
        aspect_ratio: str = "16:9"
    ) -> Optional[bytes]:
        """
        Generate a background image for a specific section.
        
        Args:
            section_type: Type of section (e.g., "services", "about", "testimonials")
            mood: Desired mood (e.g., "warm", "professional", "energetic")
            color_palette: Color palette for the image
            aspect_ratio: Image aspect ratio
            
        Returns:
            Image bytes or None
        """
        prompt = self._build_background_prompt(section_type, mood, color_palette)
        
        return await self._generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            response_modalities=["IMAGE"]
        )
    
    async def generate_product_image(
        self,
        product_description: str,
        style: str = "professional",
        aspect_ratio: str = "1:1"
    ) -> Optional[bytes]:
        """
        Generate a product/service image.
        
        Args:
            product_description: Description of the product/service
            style: Visual style (e.g., "professional", "minimal", "artistic")
            aspect_ratio: Image aspect ratio (default: 1:1 for products)
            
        Returns:
            Image bytes or None
        """
        prompt = f"""A high-resolution, {style} product photograph of {product_description}. 
        Studio lighting with soft shadows. Clean, professional composition. 
        Ultra-realistic with sharp focus."""
        
        return await self._generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            response_modalities=["IMAGE"]
        )
    
    async def generate_icon(
        self,
        icon_description: str,
        style: str = "modern minimalist"
    ) -> Optional[bytes]:
        """
        Generate an icon or small graphic.
        
        Args:
            icon_description: What the icon should represent
            style: Visual style of the icon
            
        Returns:
            Image bytes or None
        """
        prompt = f"""A {style} icon representing {icon_description}. 
        Clean lines, simple design, professional quality. 
        Transparent or white background. 
        Suitable for web use at various sizes."""
        
        return await self._generate_image(
            prompt=prompt,
            aspect_ratio="1:1",
            response_modalities=["IMAGE"]
        )
    
    async def _generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        response_modalities: List[str] = ["TEXT", "IMAGE"]
    ) -> Optional[bytes]:
        """
        Core method to generate an image using Gemini API.
        
        Args:
            prompt: Text prompt for image generation
            aspect_ratio: Aspect ratio (1:1, 16:9, 4:3, etc.)
            response_modalities: What to return (TEXT, IMAGE, or both)
            
        Returns:
            Image bytes (PNG) or None if generation fails
        """
        url = f"{self.base_url}/models/{self.model}:generateContent"
        
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseModalities": response_modalities,
                "imageConfig": {
                    "aspectRatio": aspect_ratio
                }
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract image from response
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    
                    # Check if content exists
                    if "content" not in candidate:
                        logger.error(f"No content in candidate. Response: {data}")
                        return None
                    
                    parts = candidate["content"]["parts"]
                    
                    for part in parts:
                        if "inlineData" in part:
                            # Decode base64 image data
                            image_data = part["inlineData"]["data"]
                            image_bytes = base64.b64decode(image_data)
                            logger.info(f"Successfully generated image ({len(image_bytes)} bytes)")
                            return image_bytes
                
                logger.warning(f"No image data found in response. Candidates: {len(data.get('candidates', []))}")
                return None
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error generating image: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response body: {e.response.text}")
            return None
        except KeyError as e:
            logger.error(f"KeyError accessing response data: {str(e)}")
            logger.error(f"Response structure: {data if 'data' in locals() else 'No data'}")
            return None
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return None
    
    def _build_hero_prompt(
        self,
        business_name: str,
        category: str,
        brand_archetype: str,
        color_palette: Dict[str, str]
    ) -> str:
        """Build an optimized prompt for hero image generation."""
        
        # Map archetypes to visual styles
        archetype_styles = {
            "Explorer": "adventurous, dynamic, expansive landscapes",
            "Creator": "artistic, innovative, creative workshop atmosphere",
            "Caregiver": "warm, nurturing, comfortable and welcoming",
            "Ruler": "prestigious, authoritative, elegant and commanding",
            "Hero": "powerful, courageous, bold and inspiring",
            "Magician": "transformative, mystical, enchanting and visionary",
            "Regular Guy": "relatable, authentic, down-to-earth and friendly",
            "Lover": "passionate, intimate, sensual and romantic",
            "Jester": "playful, fun, energetic and lighthearted",
            "Sage": "wise, knowledgeable, thoughtful and educational",
            "Innocent": "pure, optimistic, simple and wholesome",
            "Outlaw": "rebellious, edgy, bold and unconventional"
        }
        
        style_desc = archetype_styles.get(brand_archetype, "professional, high-quality")
        
        colors = f"with a color palette of {color_palette.get('primary', 'blue')}, " \
                f"{color_palette.get('secondary', 'white')}, " \
                f"and {color_palette.get('accent', 'orange')}"
        
        prompt = f"""A stunning, photorealistic hero image for a {category} business called '{business_name}'. 
        The scene should be {style_desc}, {colors}. 
        High-resolution, professional photography with perfect composition and lighting. 
        Suitable as a website hero banner. 
        Focus on visual impact and emotional connection. 
        No text or logos in the image."""
        
        return prompt
    
    def _build_background_prompt(
        self,
        section_type: str,
        mood: str,
        color_palette: Dict[str, str]
    ) -> str:
        """Build a prompt for section background generation."""
        
        colors = f"using colors {color_palette.get('primary', 'blue')} and {color_palette.get('secondary', 'white')}"
        
        prompt = f"""A minimalist, abstract background image for a website {section_type} section. 
        {mood} atmosphere, {colors}. 
        Subtle texture and depth, suitable for text overlay. 
        Significant negative space for content. 
        Professional, modern design with soft gradients and minimal distractions. 
        High resolution, optimized for web use."""
        
        return prompt
    
    async def save_image_to_disk(
        self,
        image_bytes: bytes,
        filename: str,
        subdomain: str
    ) -> str:
        """
        Save generated image to the sites directory.
        
        Args:
            image_bytes: Image data
            filename: Name for the image file (e.g., "hero.png")
            subdomain: Subdomain of the site
            
        Returns:
            Relative path to the saved image
        """
        sites_path = Path(settings.SITES_BASE_PATH)
        site_dir = sites_path / subdomain / "assets" / "images"
        site_dir.mkdir(parents=True, exist_ok=True)
        
        image_path = site_dir / filename
        
        try:
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            
            logger.info(f"Saved image to: {image_path}")
            return f"assets/images/{filename}"
            
        except Exception as e:
            logger.error(f"Error saving image: {str(e)}")
            raise
