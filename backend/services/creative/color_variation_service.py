"""
Color Variation Service - Adds subtle variations to industry-recommended colors.

Ensures that businesses in the same category don't all look identical while 
maintaining the psychological impact of the base color palette.
"""
import hashlib
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class ColorVariationService:
    """
    Generates color variations based on business ID to ensure uniqueness
    while maintaining the psychological impact of the base palette.
    """
    
    # Variation strategies for different color types
    VARIATION_MODES = [
        "lighter",      # Lighten the primary color
        "darker",       # Darken the primary color
        "saturated",    # Increase saturation
        "muted",        # Decrease saturation
        "shifted_warm", # Shift hue towards warm
        "shifted_cool", # Shift hue towards cool
    ]
    
    @classmethod
    def generate_variations(
        cls,
        base_colors: Dict[str, str],
        business_id: str,
        variation_intensity: float = 0.15
    ) -> Dict[str, str]:
        """
        Generate color variations based on business ID.
        
        Args:
            base_colors: Base color palette from industry persona
            business_id: Unique business identifier (for deterministic variation)
            variation_intensity: How much to vary (0.0-1.0, default 0.15 = 15%)
            
        Returns:
            Modified color palette with variations applied
        """
        # Use business ID hash to deterministically select variation mode
        hash_val = int(hashlib.md5(business_id.encode()).hexdigest(), 16)
        mode_index = hash_val % len(cls.VARIATION_MODES)
        variation_mode = cls.VARIATION_MODES[mode_index]
        
        logger.info(f"Applying '{variation_mode}' color variation for business {business_id[:8]}...")
        
        varied_colors = base_colors.copy()
        
        # Apply variation to primary, secondary, and accent colors
        varied_colors["primary"] = cls._vary_color(
            base_colors.get("primary", "#2563eb"),
            variation_mode,
            variation_intensity
        )
        varied_colors["secondary"] = cls._vary_color(
            base_colors.get("secondary", "#7c3aed"),
            variation_mode,
            variation_intensity * 0.7  # Less variation for secondary
        )
        varied_colors["accent"] = cls._vary_color(
            base_colors.get("accent", "#f59e0b"),
            variation_mode,
            variation_intensity * 0.8  # Moderate variation for accent
        )
        
        # Update gradients to match new colors
        varied_colors["gradient_start"] = varied_colors["primary"]
        varied_colors["gradient_end"] = cls._darken_color(varied_colors["primary"], 0.15)
        
        return varied_colors
    
    @classmethod
    def _vary_color(cls, hex_color: str, mode: str, intensity: float) -> str:
        """
        Apply a variation mode to a hex color.
        
        Args:
            hex_color: Hex color string (e.g., "#FF5733")
            mode: Variation mode (lighter, darker, saturated, etc.)
            intensity: Variation intensity (0.0-1.0)
            
        Returns:
            Modified hex color string
        """
        r, g, b = cls._hex_to_rgb(hex_color)
        h, s, l = cls._rgb_to_hsl(r, g, b)
        
        if mode == "lighter":
            l = min(1.0, l + (intensity * 0.3))  # Increase lightness
        elif mode == "darker":
            l = max(0.0, l - (intensity * 0.2))  # Decrease lightness
        elif mode == "saturated":
            s = min(1.0, s + (intensity * 0.4))  # Increase saturation
        elif mode == "muted":
            s = max(0.0, s - (intensity * 0.3))  # Decrease saturation
        elif mode == "shifted_warm":
            h = (h + (intensity * 20)) % 360  # Shift hue towards red/yellow
        elif mode == "shifted_cool":
            h = (h - (intensity * 20)) % 360  # Shift hue towards blue/green
        
        r, g, b = cls._hsl_to_rgb(h, s, l)
        return cls._rgb_to_hex(r, g, b)
    
    @classmethod
    def _darken_color(cls, hex_color: str, amount: float) -> str:
        """Darken a color by a specific amount."""
        r, g, b = cls._hex_to_rgb(hex_color)
        h, s, l = cls._rgb_to_hsl(r, g, b)
        l = max(0.0, l - amount)
        r, g, b = cls._hsl_to_rgb(h, s, l)
        return cls._rgb_to_hex(r, g, b)
    
    @staticmethod
    def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def _rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB tuple to hex color."""
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
    
    @staticmethod
    def _rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
        """Convert RGB to HSL."""
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        l = (max_c + min_c) / 2.0
        
        if max_c == min_c:
            h = s = 0.0
        else:
            d = max_c - min_c
            s = d / (2.0 - max_c - min_c) if l > 0.5 else d / (max_c + min_c)
            
            if max_c == r:
                h = (g - b) / d + (6.0 if g < b else 0.0)
            elif max_c == g:
                h = (b - r) / d + 2.0
            else:
                h = (r - g) / d + 4.0
            h /= 6.0
        
        return h * 360, s, l
    
    @staticmethod
    def _hsl_to_rgb(h: float, s: float, l: float) -> Tuple[int, int, int]:
        """Convert HSL to RGB."""
        h = h / 360.0
        
        def hue_to_rgb(p, q, t):
            if t < 0: t += 1
            if t > 1: t -= 1
            if t < 1/6: return p + (q - p) * 6 * t
            if t < 1/2: return q
            if t < 2/3: return p + (q - p) * (2/3 - t) * 6
            return p
        
        if s == 0:
            r = g = b = l
        else:
            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = hue_to_rgb(p, q, h + 1/3)
            g = hue_to_rgb(p, q, h)
            b = hue_to_rgb(p, q, h - 1/3)
        
        return int(r * 255), int(g * 255), int(b * 255)

