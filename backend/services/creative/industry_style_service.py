"""
Industry Style Service - Maps business categories to color psychology personas.
Based on conversion-rate optimization research and neuromarketing data.

Research shows users form an opinion within 50ms, and 90% of that 
snap judgment is based on color alone.
"""
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class IndustryStyleService:
    """
    Maps business categories to research-backed color psychology personas.
    
    Six Brand Personas based on psychological research:
    1. Heritage & Trust - Legal, Finance, Real Estate
    2. Clinical Precision - Healthcare, Dental, Senior Care
    3. Rapid Response - Emergency services, Auto, IT
    4. Craft & Structure - Contractors, Landscaping, Trades
    5. Aesthetic & Wellness - Beauty, Spas, Events
    6. Community & Nurture - Pets, Education, Cafes
    """
    
    PERSONA_DATA = {
        "heritage_trust": {
            "name": "Heritage & Trust",
            "description": "Evokes establishment, stability, and multi-generational authority",
            "emotional_response": "My money/rights are safe",
            "industries": [
                # Legal
                "lawyer", "attorney", "legal", "law firm", "legal services",
                "personal injury", "family law", "estate planning", "ip lawyer",
                "patent lawyer", "criminal defense", "immigration lawyer",
                "business attorney", "corporate lawyer", "litigation",
                # Finance
                "accountant", "cpa", "accounting", "tax", "bookkeeping",
                "tax preparation", "tax lawyer", "financial advisor",
                "wealth management", "financial planning", "investment advisor",
                "investment", "portfolio manager", "retirement planning",
                # Real Estate
                "real estate", "realtor", "property management", 
                "commercial real estate", "real estate broker", "real estate agent",
                # Insurance & Banking
                "insurance", "insurance agent", "mortgage", "mortgage broker",
                "banking", "credit union", "financial services"
            ],
            "colors": {
                "primary": "#1A2B48",         # Navy Blue - establishment, stability
                "secondary": "#2C3E50",       # Dark Slate
                "accent": "#C5A059",          # Deep Gold - high value, success
                "background": "#FAFAFA",      # Off-white
                "surface": "#FFFFFF",
                "text": "#1A2B48",
                "text_muted": "#6B7280",
                "gradient_start": "#1A2B48",
                "gradient_end": "#2C3E50"
            },
            "typography": {
                "display": "Libre Baskerville",
                "body": "Source Sans Pro",
                "accent": "Cinzel"
            },
            "typography_reasoning": "Serif fonts evoke 'old money', law books, and tradition. They look like established authority.",
            "imagery_style": "High-contrast, architectural, professional portraiture. Focus on 'The Expert'.",
            "cta_style": "conservative",
            "cta_text": "Schedule a Consultation",
            "vibe_recommendation": "Dark Luxury"
        },
        
        "clinical_precision": {
            "name": "Clinical Precision",
            "description": "Non-threatening, sterile, calming - reduces anxiety and projects cleanliness",
            "emotional_response": "I won't be hurt here",
            "industries": [
                # Medical
                "doctor", "physician", "medical", "healthcare", "clinic",
                "medical clinic", "urgent care", "hospital", "medical center",
                "specialist", "cardiologist", "dermatologist", "neurologist",
                "orthopedic", "oncologist", "pediatrician", "obgyn",
                "family medicine", "internal medicine", "primary care",
                # Dental
                "dentist", "dental", "dental clinic", "orthodontist",
                "endodontist", "periodontist", "oral surgeon", "dental implants",
                "cosmetic dentist", "pediatric dentist", "dental hygienist",
                # Senior & Home Care
                "senior care", "assisted living", "nursing home", "memory care",
                "home care", "home health", "hospice", "elder care",
                # Other Medical
                "pharmacy", "physical therapy", "occupational therapy",
                "chiropractor", "optometrist", "optician", "audiologist",
                "mental health", "psychiatrist", "psychologist", "therapist",
                "counselor", "addiction treatment", "rehab"
            ],
            "colors": {
                "primary": "#008080",         # Pure Teal - non-threatening, sterile
                "secondary": "#87CEEB",       # Sky Blue - calming
                "accent": "#10B981",          # Emerald - healing, growth
                "background": "#F9FAFB",      # Clean Slate White
                "surface": "#FFFFFF",
                "text": "#1F2937",
                "text_muted": "#6B7280",
                "gradient_start": "#008080",
                "gradient_end": "#10B981"
            },
            "typography": {
                "display": "DM Sans",
                "body": "Inter",
                "accent": "IBM Plex Sans"
            },
            "typography_reasoning": "Modern sans-serif is accessible, clear, and easy to read for all ages. Rounded edges feel less 'clinical'.",
            "imagery_style": "Bright lighting, diverse smiling faces, macro detail shots. Focus on 'The Outcome'.",
            "cta_style": "comfort",
            "cta_text": "Book Your Appointment",
            "vibe_recommendation": "Nordic Minimal"
        },
        
        "rapid_response": {
            "name": "Rapid Response",
            "description": "High visibility, immediate action, emergency availability. Triggers 'urgent' physiological arousal.",
            "emotional_response": "Help is coming fast",
            "industries": [
                # Plumbing & HVAC
                "plumber", "plumbing", "emergency plumber", "24/7 plumber",
                "drain cleaning", "water heater", "sewer", "septic",
                "hvac", "air conditioning", "ac repair", "heating",
                "furnace", "furnace repair", "heat pump",
                # Electrical
                "electrician", "electrical", "electrical contractor",
                "electrical repair", "panel upgrade", "rewiring",
                # Locksmith & Security
                "locksmith", "lock", "key", "security", "lockout",
                # Towing & Auto
                "towing", "tow truck", "roadside assistance",
                "auto repair", "mechanic", "car repair", "auto shop",
                "transmission", "brake repair", "brake", "tire",
                "oil change", "auto body", "collision repair",
                # Emergency Services
                "appliance repair", "garage door", "glass repair",
                "water damage", "fire damage", "mold removal", "mold remediation",
                "disaster restoration", "flood cleanup", "storm damage",
                # Pest Control
                "pest control", "exterminator", "termite", "bed bug",
                "rodent control", "wildlife removal",
                # IT Emergency
                "computer repair", "it support", "data recovery",
                "network repair", "tech support", "managed it"
            ],
            "colors": {
                "primary": "#D32F2F",         # Safety Red - immediate action
                "secondary": "#2962FF",       # Electric Blue - high visibility
                "accent": "#FFD600",          # High-Contrast Yellow - caution/attention
                "background": "#FFFFFF",
                "surface": "#F5F5F5",
                "text": "#212121",
                "text_muted": "#757575",
                "gradient_start": "#D32F2F",
                "gradient_end": "#B71C1C"
            },
            "typography": {
                "display": "Bebas Neue",
                "body": "Oswald",
                "accent": "Roboto Condensed"
            },
            "typography_reasoning": "Condensed bold fonts look like headlines - they suggest speed, strength, and urgency.",
            "imagery_style": "Action shots, tools in use, branded vehicles, night-time lighting. Focus on 'The Solution'.",
            "cta_style": "urgency",
            "cta_text": "Call Now - 24/7",
            "vibe_recommendation": "Bold Maximalist"
        },
        
        "craft_structure": {
            "name": "Craft & Structure",
            "description": "Reliability, physical growth, durable workmanship. Shows 'getting the job done'.",
            "emotional_response": "They will build it right",
            "industries": [
                # Roofing & Construction
                "roofing", "roofer", "roof repair", "roof replacement",
                "contractor", "general contractor", "construction",
                "home builder", "custom home", "commercial construction",
                "remodeling", "renovation", "home renovation",
                "kitchen remodel", "bathroom remodel", "basement finishing",
                "addition", "home addition", "room addition",
                # Foundation & Structural
                "foundation", "foundation repair", "concrete",
                "masonry", "brick", "stone", "stucco",
                # Solar & Green
                "solar", "solar installation", "solar panel", "solar energy",
                "green energy", "energy efficiency",
                # Landscaping & Outdoor
                "landscaping", "landscape design", "lawn care", "lawn service",
                "tree service", "tree removal", "arborist", "tree trimming",
                "irrigation", "sprinkler", "outdoor lighting",
                "pool", "pool installation", "pool service", "pool cleaning",
                "fence", "fence installation", "deck", "deck builder",
                "patio", "hardscape", "pavers", "retaining wall",
                # Moving & Storage
                "moving", "moving company", "movers", "relocation",
                "storage", "storage unit", "junk removal", "hauling",
                # Interior Trades
                "flooring", "floor installation", "hardwood", "tile",
                "painting", "painter", "house painting",
                "drywall", "plastering", "carpentry", "carpenter",
                "cabinet", "cabinetry", "countertop", "granite"
            ],
            "colors": {
                "primary": "#355E3B",         # Hunter Green - reliability, growth
                "secondary": "#4E3629",       # Earth Brown - grounded
                "accent": "#E65100",          # Industrial Orange - productivity
                "background": "#FAFAF5",      # Warm off-white
                "surface": "#FFFFFF",
                "text": "#2D2D2D",
                "text_muted": "#666666",
                "gradient_start": "#355E3B",
                "gradient_end": "#2D4A32"
            },
            "typography": {
                "display": "Montserrat",
                "body": "Source Sans Pro",
                "accent": "Roboto"
            },
            "typography_reasoning": "Geometric sans-serif feels 'well-built' - balanced, modern, and capable.",
            "imagery_style": "Wide-angle 'Before & After' shots, blueprints, texture close-ups. Focus on 'The Transformation'.",
            "cta_style": "value",
            "cta_text": "Get a Free Quote",
            "vibe_recommendation": "Warm Analog"
        },
        
        "aesthetic_wellness": {
            "name": "Aesthetic & Wellness",
            "description": "Luxury, aspiration, lifestyle transformation. Sells 'a better version of yourself'.",
            "emotional_response": "I want that lifestyle",
            "industries": [
                # Beauty & Hair
                "hair salon", "beauty salon", "salon", "hairdresser",
                "barber", "barbershop", "hair stylist", "colorist",
                "nail salon", "nail spa", "manicure", "pedicure",
                "makeup artist", "beauty", "esthetician", "waxing",
                # Med Spa & Cosmetic
                "med spa", "medspa", "medical spa", "spa",
                "massage", "massage therapy", "day spa",
                "facial", "skincare", "skin care",
                "plastic surgery", "cosmetic surgery", "plastic surgeon",
                "botox", "filler", "laser", "coolsculpting",
                "cosmetic dentistry", "teeth whitening", "veneers",
                # Wellness & Holistic
                "yoga", "yoga studio", "pilates", "barre",
                "meditation", "mindfulness", "wellness center",
                "reiki", "acupuncture", "holistic", "naturopath",
                "life coach", "wellness coach", "health coach",
                "nutrition", "nutritionist", "dietitian",
                # Fine Dining & Hospitality
                "fine dining", "upscale restaurant", "gourmet",
                "wine bar", "cocktail bar", "speakeasy",
                # Boutique & Luxury Retail
                "boutique", "fashion", "clothing store",
                "jewelry", "jeweler", "jewelry store",
                "florist", "flower", "flower shop",
                # Events & Photography
                "wedding planner", "event planner", "wedding venue",
                "event venue", "catering", "wedding",
                "photographer", "photography", "portrait",
                "videographer", "video production",
                # Design
                "interior design", "interior designer", "home staging",
                "home decor", "furniture", "antique"
            ],
            "colors": {
                "primary": "#333333",         # Soft Charcoal - elegant
                "secondary": "#F7E7CE",       # Champagne - sophisticated
                "accent": "#DCAE96",          # Dusty Rose - tranquility, luxury
                "background": "#FDFBF7",      # Warm cream
                "surface": "#FFFFFF",
                "text": "#2D2D2D",
                "text_muted": "#8B8B8B",
                "gradient_start": "#333333",
                "gradient_end": "#1a1a1a"
            },
            "typography": {
                "display": "Cormorant Garamond",
                "body": "Raleway",
                "accent": "Didot"
            },
            "typography_reasoning": "High-fashion aesthetic - minimalist serif/sans mix is aspirational and modern luxury.",
            "imagery_style": "Soft focus, lifestyle-centric, high-saturation, artistic angles. Focus on 'The Experience'.",
            "cta_style": "aspiration",
            "cta_text": "Book Your Experience",
            "vibe_recommendation": "Glassmorphism"
        },
        
        "community_nurture": {
            "name": "Community & Nurture",
            "description": "Energetic, friendly, approachable. Builds connection and belonging.",
            "emotional_response": "The Connection",
            "industries": [
                # Pet Services
                "veterinarian", "vet", "veterinary", "animal hospital",
                "pet", "pet store", "pet shop", "pet supplies",
                "dog grooming", "pet grooming", "groomer",
                "doggy daycare", "dog daycare", "pet boarding",
                "dog training", "pet training", "dog walker",
                # Education & Tutoring
                "tutoring", "tutor", "learning center", "education",
                "test prep", "sat prep", "college prep",
                "music lessons", "music school", "music teacher",
                "piano lessons", "guitar lessons", "voice lessons",
                "dance studio", "dance school", "dance lessons",
                "ballet", "hip hop dance", "ballroom",
                "martial arts", "karate", "taekwondo", "judo",
                "jiu jitsu", "boxing", "mma",
                "art classes", "art school", "painting classes",
                # Childcare
                "daycare", "childcare", "child care", "preschool",
                "montessori", "nursery", "after school", "nanny",
                # Food & Beverage (Casual)
                "cafe", "coffee shop", "coffee", "espresso",
                "bakery", "pastry", "cupcake", "donut",
                "ice cream", "frozen yogurt", "smoothie", "juice bar",
                "fast casual", "casual dining", "family restaurant",
                "pizza", "sandwich", "deli", "food truck",
                # Fitness & Recreation
                "gym", "fitness", "fitness center", "health club",
                "crossfit", "boot camp", "personal trainer",
                "swimming", "swim lessons", "tennis", "golf",
                "bowling", "arcade", "entertainment", "recreation",
                # Community & Faith
                "church", "religious", "synagogue", "mosque",
                "nonprofit", "charity", "community center",
                "community organization"
            ],
            "colors": {
                "primary": "#FF9800",         # Warm Orange - energetic, friendly
                "secondary": "#4CAF50",       # Leaf Green - growth, nature
                "accent": "#1A2B48",          # Navy Blue (safety anchor)
                "background": "#FFFDF7",      # Warm cream
                "surface": "#FFFFFF",
                "text": "#333333",
                "text_muted": "#666666",
                "gradient_start": "#FF9800",
                "gradient_end": "#F57C00"
            },
            "typography": {
                "display": "Quicksand",
                "body": "Varela Round",
                "accent": "Nunito"
            },
            "typography_reasoning": "Rounded geometric fonts are playful, soft, and inviting - perfect for community-focused businesses.",
            "imagery_style": "Candid shots, pet interaction, group activities, natural light. Focus on 'The Connection'.",
            "cta_style": "friendly",
            "cta_text": "Join Our Community",
            "vibe_recommendation": "Organic Flow"
        }
    }
    
    # Gradient anti-banding CSS techniques
    GRADIENT_BEST_PRACTICES = """
GRADIENT ANTI-BANDING TECHNIQUES (CRITICAL FOR SMOOTH GRADIENTS):

The Problem: CSS gradients often display visible "bands" or steps instead of 
smooth transitions, especially on 8-bit displays or with dark colors.

Solutions to Apply:

1. USE OFF-COLORS (Never pure white/black):
   - Instead of #FFFFFF use #FFFFF0 or #F5F5F5
   - Instead of #000000 use #0a0a0f or #1a1a1a
   - This softens the boundary and reduces banding

2. ADD NOISE OVERLAY:
   - Apply a subtle noise texture over gradients
   - Use a semi-transparent SVG or PNG pattern
   Example:
   .gradient-smooth {
     background: 
       url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.05'/%3E%3C/svg%3E"),
       linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
   }

3. APPLY SUBTLE BLUR:
   - Use pseudo-elements with filter: blur(1-2px)
   - Crop with overflow: hidden
   Example:
   .gradient-container {
     position: relative;
     overflow: hidden;
   }
   .gradient-container::before {
     content: "";
     position: absolute;
     inset: -2px;
     background: linear-gradient(...);
     filter: blur(1px);
     z-index: -1;
   }

4. USE MULTIPLE COLOR STOPS:
   - Instead of just start/end, use eased intermediate stops
   - Creates smoother perceptual transitions
   Example:
   background: linear-gradient(
     135deg,
     #1A2B48 0%,
     #1E3354 25%,
     #223B60 50%,
     #2C4A6E 75%,
     #355E3B 100%
   );

5. CSS VARIABLE APPROACH:
   :root {
     --gradient-start: #1A2B48;
     --gradient-end: #2C3E50;
     --off-white: #FFFFF0;
     --off-black: #0a0a0f;
   }
"""
    
    @classmethod
    def get_persona_for_category(cls, category: str) -> Optional[Dict[str, Any]]:
        """
        Get the brand persona for a business category.
        
        Args:
            category: Business category string (e.g., "plumber", "dentist")
            
        Returns:
            Persona data dictionary or None if no specific persona matches
        """
        if not category:
            return None
        
        category_lower = category.lower().strip()
        
        # Try to match against all personas
        for persona_key, persona_data in cls.PERSONA_DATA.items():
            for industry in persona_data["industries"]:
                # Check if industry keyword is in category or vice versa
                if industry in category_lower or category_lower in industry:
                    logger.info(
                        f"Matched category '{category}' to persona "
                        f"'{persona_data['name']}' via keyword '{industry}'"
                    )
                    return {
                        "persona_key": persona_key,
                        **persona_data
                    }
        
        # No specific match found
        logger.info(f"No specific persona for category '{category}', using defaults")
        return None
    
    @classmethod
    def get_style_overrides(cls, category: str) -> Dict[str, Any]:
        """
        Get style overrides for the Art Director agent based on industry.
        
        Args:
            category: Business category
            
        Returns:
            Dictionary of style overrides to inject into the Art Director prompt
        """
        persona = cls.get_persona_for_category(category)
        
        if not persona:
            return {
                "has_industry_guidance": False,
                "industry_guidance_text": "No specific industry guidance - use creative judgment."
            }
        
        # Format the guidance text for the prompt
        guidance_text = f"""
INDUSTRY-SPECIFIC STYLE GUIDANCE:
Based on color psychology research, this business category ({category}) 
falls under the "{persona['name']}" persona.

PSYCHOLOGICAL TARGET: "{persona['emotional_response']}"
{persona['description']}

RECOMMENDED COLOR PALETTE:
- Primary: {persona['colors']['primary']} (main brand color)
- Secondary: {persona['colors']['secondary']} (supporting color)
- Accent: {persona['colors']['accent']} (highlights, CTAs)
- Background: {persona['colors']['background']}
- Text: {persona['colors']['text']}
- Gradient: {persona['colors']['gradient_start']} → {persona['colors']['gradient_end']}

RECOMMENDED TYPOGRAPHY:
- Display/Headings: {persona['typography']['display']}
- Body Text: {persona['typography']['body']}
- Accent/Labels: {persona['typography']['accent']}
Reasoning: {persona['typography_reasoning']}

IMAGERY STYLE: {persona['imagery_style']}

CTA APPROACH: {persona['cta_style'].upper()} - Example: "{persona['cta_text']}"

RECOMMENDED VIBE: {persona['vibe_recommendation']}

IMPORTANT: These colors and fonts are RESEARCH-BACKED for this industry.
You can still apply creative vibes on top, but the core palette should 
align with the psychological expectations of this business type.
"""
        
        return {
            "has_industry_guidance": True,
            "industry_guidance_text": guidance_text,
            "persona_name": persona["name"],
            "persona_key": persona["persona_key"],
            "recommended_colors": persona["colors"],
            "recommended_typography": persona["typography"],
            "typography_reasoning": persona["typography_reasoning"],
            "imagery_style": persona["imagery_style"],
            "emotional_target": persona["emotional_response"],
            "cta_style": persona["cta_style"],
            "cta_text": persona["cta_text"],
            "vibe_recommendation": persona["vibe_recommendation"]
        }
    
    @classmethod
    def get_gradient_best_practices(cls) -> str:
        """
        Returns CSS gradient best practices to prevent banding.
        
        Returns:
            String containing gradient anti-banding techniques
        """
        return cls.GRADIENT_BEST_PRACTICES
    
    @classmethod
    def get_all_personas_summary(cls) -> List[Dict[str, str]]:
        """
        Get a summary of all personas for documentation/UI purposes.
        
        Returns:
            List of persona summaries
        """
        summaries = []
        for key, data in cls.PERSONA_DATA.items():
            summaries.append({
                "key": key,
                "name": data["name"],
                "description": data["description"],
                "emotional_response": data["emotional_response"],
                "primary_color": data["colors"]["primary"],
                "display_font": data["typography"]["display"],
                "industry_count": len(data["industries"])
            })
        return summaries
    
    @classmethod
    def validate_category_mapping(cls, categories: List[str]) -> Dict[str, Any]:
        """
        Validate which categories map to which personas.
        Useful for debugging and ensuring coverage.
        
        Args:
            categories: List of category strings to check
            
        Returns:
            Mapping results
        """
        results = {
            "mapped": [],
            "unmapped": []
        }
        
        for category in categories:
            persona = cls.get_persona_for_category(category)
            if persona:
                results["mapped"].append({
                    "category": category,
                    "persona": persona["name"]
                })
            else:
                results["unmapped"].append(category)
        
        return results

