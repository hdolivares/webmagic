"""
Image Generation Service using Google Gemini (Nano Banana).
Generates contextual images per website using gemini-2.5-flash-image.

For informational sites: 3 images (hero, about, services).
For ecommerce sites:     3 base images + up to 7 per-product images (product-1…product-7).

Images are saved to disk and served via a dedicated FastAPI endpoint.
"""
import asyncio
import base64
import io
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import httpx

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Category → image subject knowledge ──────────────────────────────────────

# For each category cluster we define what the 3 images should show.
# "woman" means the prompt will describe a beautiful, attractive woman as subject.
_CATEGORY_PROMPTS: Dict[str, List[Dict[str, str]]] = {
    # ── Plumbing / HVAC ──────────────────────────────────────────────────────
    "plumber": [
        {
            "slot": "hero",
            "aspect": "16:9",
            "desc": (
                "A confident, beautiful woman in crisp navy plumbing uniform "
                "smiling at camera while holding professional tools in a modern "
                "bright kitchen. Cinematic lighting, photorealistic, 8K quality, "
                "ultra-detailed, clean and polished home background."
            ),
        },
        {
            "slot": "about",
            "aspect": "4:3",
            "desc": (
                "A professional female plumber with an attractive appearance "
                "fixing a modern under-sink pipe, focused and competent. "
                "Warm residential lighting, ultra-realistic photography."
            ),
        },
        {
            "slot": "services",
            "aspect": "4:3",
            "desc": (
                "Close-up of gleaming modern plumbing fixtures — chrome faucet, "
                "clean pipes — professional product photography, bright studio lighting."
            ),
        },
    ],
    "hvac": [
        {
            "slot": "hero",
            "aspect": "16:9",
            "desc": (
                "A beautiful, attractive female HVAC technician in a branded "
                "uniform smiling in front of a modern home exterior on a sunny day. "
                "Photorealistic, cinematic, 8K."
            ),
        },
        {
            "slot": "about",
            "aspect": "4:3",
            "desc": (
                "A stunning woman technician adjusting a modern smart thermostat "
                "inside a bright, airy living room. Ultra-realistic."
            ),
        },
        {
            "slot": "services",
            "aspect": "4:3",
            "desc": (
                "Modern HVAC equipment — sleek air conditioning unit, professional "
                "tools laid out neatly. Studio product photography."
            ),
        },
    ],
    # ── Massage / Spa ─────────────────────────────────────────────────────────
    "massage": [
        {
            "slot": "hero",
            "aspect": "16:9",
            "desc": (
                "A serene, elegant spa treatment room with a beautiful woman in a "
                "plush white towel resting peacefully on a professional massage table. "
                "Warm dim candlelight, orchids, stone accessories, luxurious atmosphere. "
                "Cinematic photography, 8K, ultra-realistic, no people working."
            ),
        },
        {
            "slot": "about",
            "aspect": "4:3",
            "desc": (
                "A skilled female massage therapist in white attire standing beside the "
                "HEAD-END of a professional massage table, both feet on the floor on the "
                "SAME SIDE of the table as the camera. Therapist gently placing hands on "
                "the upper back and shoulders of a client lying face-down, draped in soft "
                "white linen. 3/4 front-angle view: the camera is positioned in front of "
                "and slightly to the side of the therapist so that BOTH her legs appear "
                "clearly in the FOREGROUND, in front of the white table draping — NOT "
                "behind or through the linen. Therapist leaning slightly forward from the "
                "waist, natural relaxed posture. Warm candlelit spa interior with natural "
                "elements, serene tranquil atmosphere. Correct human anatomy, realistic "
                "proportions, no depth or occlusion artifacts."
            ),
        },
        {
            "slot": "services",
            "aspect": "4:3",
            "desc": (
                "Elegant spa treatment setting — smooth hot stones, aromatic essential "
                "oil bottles, bamboo accessories, fresh flowers, and soft towels arranged "
                "on a dark wooden surface. Product photography, warm candlelit tones."
            ),
        },
    ],
    # ── Health / Wellness ─────────────────────────────────────────────────────
    "chiropractor": [
        {
            "slot": "hero",
            "aspect": "16:9",
            "desc": (
                "A beautiful, professional female chiropractor in white coat "
                "warmly welcoming a patient in a modern, bright clinical office. "
                "Natural light, premium healthcare photography, 8K."
            ),
        },
        {
            "slot": "about",
            "aspect": "4:3",
            "desc": (
                "An attractive female chiropractor performing a gentle spinal "
                "adjustment on a relaxed patient. Bright, clean clinical setting."
            ),
        },
        {
            "slot": "services",
            "aspect": "4:3",
            "desc": (
                "Modern chiropractic treatment room with adjustment table and "
                "natural light. Clean, professional interior photography."
            ),
        },
    ],
    "counselor": [
        {
            "slot": "hero",
            "aspect": "16:9",
            "desc": (
                "A beautiful, empathetic female therapist with warm smile sitting "
                "in a cozy, stylish therapy office with soft natural light and "
                "indoor plants. Professional portrait photography, 8K."
            ),
        },
        {
            "slot": "about",
            "aspect": "4:3",
            "desc": (
                "An attractive female counselor listening attentively to a client "
                "in a calm, modern therapy room. Warm tones, natural light."
            ),
        },
        {
            "slot": "services",
            "aspect": "4:3",
            "desc": (
                "A serene, beautifully decorated therapy office interior — "
                "comfortable chairs, soft lighting, plants. Architectural photography."
            ),
        },
    ],
    "veterinarian": [
        {
            "slot": "hero",
            "aspect": "16:9",
            "desc": (
                "A stunning female veterinarian in white coat gently holding "
                "an adorable golden retriever puppy, smiling warmly. "
                "Bright clinic background, photorealistic, 8K."
            ),
        },
        {
            "slot": "about",
            "aspect": "4:3",
            "desc": (
                "An attractive female vet examining a happy cat on a clean "
                "examination table. Professional clinic lighting."
            ),
        },
        {
            "slot": "services",
            "aspect": "4:3",
            "desc": (
                "Modern veterinary clinic reception area — bright, welcoming, "
                "with pets visible. Clean interior photography."
            ),
        },
    ],
    # ── Finance / Professional Services ───────────────────────────────────────
    "accountant": [
        {
            "slot": "hero",
            "aspect": "16:9",
            "desc": (
                "A beautiful, professional female CPA in a modern glass-walled "
                "office, confidently reviewing documents, bright city view behind her. "
                "Corporate photography, 8K."
            ),
        },
        {
            "slot": "about",
            "aspect": "4:3",
            "desc": (
                "An attractive female accountant in elegant business attire "
                "working on financial reports at a sleek desk. Natural office light."
            ),
        },
        {
            "slot": "services",
            "aspect": "4:3",
            "desc": (
                "Modern financial charts and documents on a clean desk with a "
                "laptop. Professional business photography."
            ),
        },
    ],
    # ── Default fallback for any other category ───────────────────────────────
    "default": [
        {
            "slot": "hero",
            "aspect": "16:9",
            "desc": (
                "A beautiful, confident professional woman in business casual "
                "attire smiling at a modern bright office or storefront. "
                "Cinematic lighting, photorealistic, 8K."
            ),
        },
        {
            "slot": "about",
            "aspect": "4:3",
            "desc": (
                "An attractive professional woman working with focus and "
                "competence in a clean, modern workspace. Natural light."
            ),
        },
        {
            "slot": "services",
            "aspect": "4:3",
            "desc": (
                "Modern professional workspace — desk, tools of the trade, "
                "clean design. Architectural / product photography."
            ),
        },
    ],
}

# Map common category keywords to our known buckets.
# ORDER MATTERS: more-specific keywords must come before substrings that could
# accidentally match (e.g. "massage therapist" contains "therap" — "massage"
# must be checked first so it routes to the massage bucket, not counselor).
_CATEGORY_KEYWORDS: Dict[str, str] = {
    "plumb": "plumber",
    "drain": "plumber",
    "sewer": "plumber",
    "hvac": "hvac",
    "air condition": "hvac",
    "heating": "hvac",
    "chiropract": "chiropractor",
    "chiro": "chiropractor",
    # Massage / spa — must come before generic "therap" to avoid mis-routing
    "massage": "massage",
    "spa": "massage",
    "facial": "massage",
    "estheti": "massage",
    "reflexolog": "massage",
    "nail salon": "massage",
    "waxing": "massage",
    # Mental health / counseling
    "counsel": "counselor",
    "therap": "counselor",
    "psycholog": "counselor",
    "psychiatr": "counselor",
    "mental health": "counselor",
    "vet": "veterinarian",
    "animal": "veterinarian",
    "pet": "veterinarian",
    "account": "accountant",
    "cpa": "accountant",
    "tax": "accountant",
    "bookkeep": "accountant",
}


def _resolve_category_key(category: str) -> str:
    lower = (category or "").lower()
    for kw, bucket in _CATEGORY_KEYWORDS.items():
        if kw in lower:
            return bucket
    return "default"


# ── Ecommerce product image prompts ──────────────────────────────────────────
# Keyed by ecommerce sub-category.  Each entry has exactly 7 product slots
# (product-1 … product-7) with square 1:1 aspect ratio for product cards.

_ECOMMERCE_PRODUCT_PROMPTS: Dict[str, List[Dict[str, str]]] = {
    # ── Pet / cat products ────────────────────────────────────────────────────
    "pet": [
        {
            "slot": "product-1",
            "aspect": "1:1",
            "desc": (
                "A tall, modern multi-level cat tree tower with sisal rope scratching posts, "
                "cozy hammock perches, dangling toy balls, and plush platforms in warm neutral tones. "
                "Isolated on a clean white background. Studio product photography, sharp focus, "
                "soft diffused lighting, no cats in frame."
            ),
        },
        {
            "slot": "product-2",
            "aspect": "1:1",
            "desc": (
                "An ultra-plush round cloud-shaped cat bed in cream and blush pink faux fur, "
                "perfectly clean and puffy, set on a minimalist white surface. "
                "Overhead studio product shot, soft shadows, no cats."
            ),
        },
        {
            "slot": "product-3",
            "aspect": "1:1",
            "desc": (
                "A set of two elevated ceramic cat bowls on a bamboo stand — clean white ceramic "
                "with subtle pink accents, matching saucers. Studio product photography on white "
                "background, top-angle view, premium tableware aesthetic."
            ),
        },
        {
            "slot": "product-4",
            "aspect": "1:1",
            "desc": (
                "A cheerful colorful collection of cat toys spread on a white surface: feather "
                "wands, crinkle balls, a catnip mouse, a jingle bell ring, and interactive puzzle "
                "pieces. Flat-lay product photography, bright studio lighting, vibrant colors."
            ),
        },
        {
            "slot": "product-5",
            "aspect": "1:1",
            "desc": (
                "A modern automatic cat water fountain in glossy white with a flowing waterfall "
                "feature, LED ring, and charcoal filter visible. Isolated on a clean white "
                "background. Sleek product photography, soft reflections."
            ),
        },
        {
            "slot": "product-6",
            "aspect": "1:1",
            "desc": (
                "A stylish transparent bubble-window cat carrier backpack in blush pink and "
                "light grey, standing upright on a white surface. The round porthole window "
                "shows a plush interior. Studio product shot, clean modern design."
            ),
        },
        {
            "slot": "product-7",
            "aspect": "1:1",
            "desc": (
                "A collection of cute cat accessories on a white surface: a personalized leather "
                "collar with a heart-shaped tag, a matching leash, and a small bowtie. "
                "Flat-lay product photography, elegant styling, pastel pink and gold tones."
            ),
        },
    ],
    # ── Fashion / apparel ─────────────────────────────────────────────────────
    "fashion": [
        {
            "slot": "product-1",
            "aspect": "1:1",
            "desc": (
                "A neatly folded premium quality women's dress in soft pastel color, "
                "studio product photography on white background, clean minimal styling."
            ),
        },
        {
            "slot": "product-2",
            "aspect": "1:1",
            "desc": (
                "A stylish handbag in structured leather with gold hardware, standing "
                "upright on a white surface. Product photography, soft studio shadows."
            ),
        },
        {
            "slot": "product-3",
            "aspect": "1:1",
            "desc": (
                "A pair of elegant high heels in nude tone, isolated on white. "
                "Studio product photography from slight side angle, clean background."
            ),
        },
        {
            "slot": "product-4",
            "aspect": "1:1",
            "desc": (
                "A cozy knit sweater in warm camel color, folded neatly. "
                "Studio product shot, white background, soft lighting."
            ),
        },
        {
            "slot": "product-5",
            "aspect": "1:1",
            "desc": (
                "A delicate gold necklace with a pendant on a clean white jewelry display card. "
                "Macro product photography, soft focus background."
            ),
        },
        {
            "slot": "product-6",
            "aspect": "1:1",
            "desc": (
                "A pair of fashionable sunglasses with tortoiseshell frames, product photography "
                "on white background, slight reflections."
            ),
        },
        {
            "slot": "product-7",
            "aspect": "1:1",
            "desc": (
                "A silk floral scarf neatly arranged, showing the pattern clearly. "
                "Flat-lay product photography on white background."
            ),
        },
    ],
    # ── Food / bakery ─────────────────────────────────────────────────────────
    "food": [
        {
            "slot": "product-1",
            "aspect": "1:1",
            "desc": (
                "An artisan sourdough bread loaf with a golden crust, sliced on a wooden board, "
                "studio food photography, warm lighting."
            ),
        },
        {
            "slot": "product-2",
            "aspect": "1:1",
            "desc": (
                "Assorted premium pastries and macarons arranged beautifully on a white plate, "
                "top-down food photography."
            ),
        },
        {
            "slot": "product-3",
            "aspect": "1:1",
            "desc": (
                "A premium coffee gift set — whole beans in a kraft bag, an elegant mug — "
                "flat-lay product photography on light background."
            ),
        },
        {
            "slot": "product-4",
            "aspect": "1:1",
            "desc": (
                "A beautifully decorated celebration cake with fresh flowers, studio photography "
                "on white background."
            ),
        },
        {
            "slot": "product-5",
            "aspect": "1:1",
            "desc": (
                "Premium dark chocolate truffles in a luxury gift box, macro product photography, "
                "soft lighting."
            ),
        },
        {
            "slot": "product-6",
            "aspect": "1:1",
            "desc": (
                "A jar of artisan honey with a wooden honey dipper, golden tones, "
                "minimalist product photography."
            ),
        },
        {
            "slot": "product-7",
            "aspect": "1:1",
            "desc": (
                "A selection of gourmet spice blends in elegant small jars with handwritten labels, "
                "flat-lay product photography."
            ),
        },
    ],
    # ── Default fallback for any ecommerce category ───────────────────────────
    "default": [
        {
            "slot": "product-1",
            "aspect": "1:1",
            "desc": (
                "A premium product with clean modern packaging on a white studio background. "
                "Professional product photography, sharp focus, soft shadows."
            ),
        },
        {
            "slot": "product-2",
            "aspect": "1:1",
            "desc": (
                "A stylish lifestyle product displayed elegantly on a light surface. "
                "Studio product photography, minimal background, premium feel."
            ),
        },
        {
            "slot": "product-3",
            "aspect": "1:1",
            "desc": (
                "A high-quality product in sleek design isolated on white. "
                "Clean product photography, diffused studio lighting."
            ),
        },
        {
            "slot": "product-4",
            "aspect": "1:1",
            "desc": (
                "A curated set of complementary products arranged neatly. "
                "Flat-lay product photography on a neutral surface."
            ),
        },
        {
            "slot": "product-5",
            "aspect": "1:1",
            "desc": (
                "An eye-catching product with vibrant design on white background. "
                "Studio product shot, clean and modern."
            ),
        },
        {
            "slot": "product-6",
            "aspect": "1:1",
            "desc": (
                "A deluxe boxed gift set with premium items neatly arranged. "
                "Top-down product photography, elegant presentation."
            ),
        },
        {
            "slot": "product-7",
            "aspect": "1:1",
            "desc": (
                "A bestselling product shown from its best angle on a pure white background. "
                "Professional product photography, sharp details."
            ),
        },
    ],
}

# Keywords to route ecommerce sites to the right product image set.
_ECOMMERCE_CATEGORY_KEYWORDS: Dict[str, str] = {
    "cat": "pet",
    "gato": "pet",
    "felina": "pet",
    "felino": "pet",
    "michi": "pet",
    "pet": "pet",
    "animal": "pet",
    "mascotas": "pet",
    "mascota": "pet",
    "perro": "pet",
    "dog": "pet",
    "fashion": "fashion",
    "cloth": "fashion",
    "apparel": "fashion",
    "ropa": "fashion",
    "moda": "fashion",
    "boutique": "fashion",
    "bakery": "food",
    "panadería": "food",
    "pastelería": "food",
    "café": "food",
    "restaurant": "food",
    "food": "food",
    "comida": "food",
}


def _resolve_ecommerce_category_key(category: str) -> str:
    """Map a business category string to an ecommerce product image bucket."""
    lower = (category or "").lower()
    for kw, bucket in _ECOMMERCE_CATEGORY_KEYWORDS.items():
        if kw in lower:
            return bucket
    return "default"


class ImageGenerationService:
    """
    Generates 3 contextual images per website using Gemini 2.5 Flash Image.
    Images are JPEG-compressed to ~200-350 KB each and saved to disk.
    """

    MODEL = "gemini-2.5-flash-image"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    TARGET_JPEG_KB = 350          # max target size after compression
    JPEG_QUALITY_START = 82       # starting JPEG quality; lowered if still too large

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            logger.warning("[ImageGen] GEMINI_API_KEY is not set — image generation disabled")

    # ── Public API ────────────────────────────────────────────────────────────

    async def generate_images_for_site(
        self,
        business_name: str,
        category: str,
        subdomain: str,
        brand_colors: Optional[Dict[str, str]] = None,
        creative_dna: Optional[Dict[str, Any]] = None,
        website_type: str = "informational",
    ) -> List[Dict[str, Any]]:
        """
        Generate contextual images for a site.

        For informational sites: generates 3 images (hero, about, services).
        For ecommerce sites:     generates 3 base images + 7 per-product images
                                 (product-1 … product-7) in parallel.

        Returns a list of dicts:
        [
          {"slot": "hero",      "filename": "img/hero.jpg",      "saved": True},
          {"slot": "about",     "filename": "img/about.jpg",     "saved": True},
          {"slot": "services",  "filename": "img/services.jpg",  "saved": True},
          # ecommerce only:
          {"slot": "product-1", "filename": "img/product-1.jpg", "saved": True},
          ...
          {"slot": "product-7", "filename": "img/product-7.jpg", "saved": True},
        ]
        Files are saved under SITES_BASE_PATH/{subdomain}/img/.

        Args:
            creative_dna: Optional output from the Concept agent. When provided,
                the brand's unique positioning is injected into every prompt so
                images reflect the specific brand angle rather than a generic template.
            website_type: "informational" or "ecommerce". Ecommerce sites receive
                7 additional per-product images beyond the standard 3.
        """
        if not self.api_key:
            logger.warning("[ImageGen] Skipping — no API key")
            return []

        bucket = _resolve_category_key(category)
        base_specs = _CATEGORY_PROMPTS[bucket]

        # For ecommerce, append 7 product-specific image specs.
        if website_type == "ecommerce":
            ecommerce_bucket = _resolve_ecommerce_category_key(category)
            product_specs = _ECOMMERCE_PRODUCT_PROMPTS[ecommerce_bucket]
            all_specs = base_specs + product_specs
        else:
            all_specs = base_specs

        color_hint = self._color_hint(brand_colors)
        brand_hint = self._brand_hint(creative_dna)

        logger.info(
            f"[ImageGen] Generating {len(all_specs)} images for '{business_name}' "
            f"(category={category}, bucket={bucket}, type={website_type}, "
            f"brand_hint={bool(brand_hint)})"
        )

        tasks = [
            self._generate_and_save(
                spec=spec,
                business_name=business_name,
                color_hint=color_hint,
                brand_hint=brand_hint,
                subdomain=subdomain,
            )
            for spec in all_specs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = []
        for spec, res in zip(all_specs, results):
            if isinstance(res, Exception):
                logger.error(f"[ImageGen] Failed {spec['slot']}: {res}")
                output.append({"slot": spec["slot"], "filename": None, "saved": False, "full_prompt": None})
            else:
                output.append(res)

        saved = sum(1 for r in output if r.get("saved"))
        logger.info(f"[ImageGen] {saved}/{len(all_specs)} images saved for {subdomain}")
        return output

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _generate_and_save(
        self,
        spec: Dict[str, str],
        business_name: str,
        color_hint: str,
        subdomain: str,
        brand_hint: str = "",
    ) -> Dict[str, Any]:
        slot = spec["slot"]
        aspect = spec["aspect"]

        full_prompt = (
            f"{spec['desc']} "
            f"For a business called '{business_name}'. "
            f"{brand_hint} "
            f"{color_hint} "
            "No text overlays, no logos, no watermarks. "
            "Ultra-realistic, high-fidelity, premium quality."
        )

        png_bytes = await self._call_gemini(full_prompt, aspect)
        if not png_bytes:
            return {"slot": slot, "filename": None, "saved": False, "full_prompt": full_prompt}

        jpeg_bytes = self._compress_to_jpeg(png_bytes)
        filename = f"img/{slot}.jpg"
        await self._save(jpeg_bytes, subdomain, f"{slot}.jpg")

        size_kb = len(jpeg_bytes) / 1024
        logger.info(f"[ImageGen] {slot}: {size_kb:.0f} KB saved → {filename}")
        return {"slot": slot, "filename": filename, "saved": True, "full_prompt": full_prompt}

    async def _call_gemini(self, prompt: str, aspect_ratio: str) -> Optional[bytes]:
        url = f"{self.BASE_URL}/models/{self.MODEL}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {"aspectRatio": aspect_ratio},
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            candidates = data.get("candidates", [])
            if not candidates:
                logger.warning("[ImageGen] No candidates in response")
                return None

            candidate = candidates[0]
            if "content" not in candidate:
                logger.error(f"[ImageGen] No content in candidate: {data}")
                return None

            for part in candidate["content"].get("parts", []):
                if "inlineData" in part:
                    return base64.b64decode(part["inlineData"]["data"])

            logger.warning("[ImageGen] No inlineData in response parts")
            return None

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[ImageGen] HTTP {e.response.status_code}: {e.response.text[:300]}"
            )
            return None
        except Exception as e:
            logger.error(f"[ImageGen] Unexpected error: {e}")
            return None

    def _compress_to_jpeg(self, png_bytes: bytes) -> bytes:
        """Convert PNG → JPEG and iteratively lower quality until ≤ TARGET_JPEG_KB."""
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            quality = self.JPEG_QUALITY_START

            for _ in range(6):
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=quality, optimize=True)
                result = buf.getvalue()
                if len(result) <= self.TARGET_JPEG_KB * 1024:
                    return result
                quality -= 8

            # Return last attempt even if slightly over target
            return result

        except Exception as e:
            logger.warning(f"[ImageGen] PIL compression failed ({e}), using raw PNG")
            return png_bytes

    async def _save(self, image_bytes: bytes, subdomain: str, filename: str) -> str:
        img_dir = Path(settings.SITES_BASE_PATH) / subdomain / "img"
        img_dir.mkdir(parents=True, exist_ok=True)
        dest = img_dir / filename
        dest.write_bytes(image_bytes)
        return str(dest)

    @staticmethod
    def _color_hint(brand_colors: Optional[Dict[str, str]]) -> str:
        if not brand_colors:
            return ""
        primary = brand_colors.get("primary", "")
        secondary = brand_colors.get("secondary", "")
        if primary or secondary:
            return f"The image should subtly echo the brand palette: {primary}, {secondary}."
        return ""

    @staticmethod
    def _brand_hint(creative_dna: Optional[Dict[str, Any]]) -> str:
        """
        Build a short prompt fragment from the Concept agent's creative DNA so
        that images reflect the specific brand positioning rather than a generic
        category template.

        Pulls from (in priority order):
        - visual_identity  — explicit visual direction from the art director
        - value_proposition — the brand's unique selling angle
        - emotional_core   — the feeling the brand wants to evoke
        - personality_traits — adjectives that describe the brand voice
        """
        if not creative_dna:
            return ""

        fragments: List[str] = []

        visual = creative_dna.get("visual_identity", "")
        if visual:
            fragments.append(f"Visual style: {visual}.")

        vp = creative_dna.get("value_proposition", "")
        if vp:
            fragments.append(f"Brand positioning: {vp}.")

        ec = creative_dna.get("emotional_core", "")
        if ec:
            fragments.append(f"Mood and feeling: {ec}.")

        traits = creative_dna.get("personality_traits", [])
        if traits:
            fragments.append(f"Brand character: {', '.join(traits[:4])}.")

        return " ".join(fragments)
