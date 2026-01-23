"""
Category Knowledge Service - Intelligent content generation based on business type.
Provides category-specific services, content, and strategies.

Now integrated with IndustryStyleService for color psychology personas.
"""
from typing import Dict, List, Any, Optional
import logging

from services.creative.industry_style_service import IndustryStyleService

logger = logging.getLogger(__name__)


class CategoryKnowledgeService:
    """
    Service that provides intelligent, category-specific content.
    Used to generate realistic websites even with minimal business data.
    """
    
    # Category-specific knowledge base
    CATEGORY_DATA = {
        "plumber": {
            "display_name": "Plumbing",
            "services": [
                {
                    "name": "Emergency Plumbing Repairs",
                    "description": "24/7 emergency response for burst pipes, major leaks, and urgent plumbing issues. Fast, reliable service when you need it most.",
                    "icon": "🚨",
                    "priority": 1
                },
                {
                    "name": "Drain Cleaning & Unclogging",
                    "description": "Professional drain cleaning services for sinks, tubs, and main sewer lines. Advanced equipment for tough clogs.",
                    "icon": "🚰",
                    "priority": 2
                },
                {
                    "name": "Water Heater Services",
                    "description": "Installation, repair, and maintenance of traditional and tankless water heaters. Expert diagnosis and solutions.",
                    "icon": "🔥",
                    "priority": 3
                },
                {
                    "name": "Pipe Repair & Replacement",
                    "description": "Complete pipe services including leak repairs, repiping, and pipe replacement for residential and commercial properties.",
                    "icon": "🔧",
                    "priority": 4
                },
                {
                    "name": "Fixture Installation",
                    "description": "Professional installation of faucets, toilets, sinks, and other plumbing fixtures. Quality workmanship guaranteed.",
                    "icon": "🚽",
                    "priority": 5
                },
                {
                    "name": "Leak Detection & Repair",
                    "description": "Advanced leak detection technology to find hidden leaks. Prevent water damage and reduce water bills.",
                    "icon": "💧",
                    "priority": 6
                }
            ],
            "contact_preference": "phone",
            "contact_emphasis": "24/7 Emergency Hotline",
            "cta_primary": "Call Now for Emergency Service",
            "cta_secondary": "Request a Free Quote",
            "hours_default": "24/7 Emergency Service Available",
            "trust_factors": [
                "Licensed & Insured",
                "24/7 Emergency Response",
                "Upfront Pricing - No Hidden Fees",
                "Experienced Technicians",
                "Satisfaction Guaranteed"
            ],
            "value_props": [
                "Same-day service available",
                "Free estimates on major repairs",
                "Senior & military discounts",
                "Clean, professional service"
            ],
            "process_steps": [
                "Call us or book online",
                "We arrive promptly - often within the hour",
                "Inspect and diagnose the issue",
                "Provide upfront, honest pricing",
                "Complete repairs with quality parts",
                "Clean up and guarantee our work"
            ],
            "typical_about": "With years of experience serving the local community, we provide reliable plumbing services you can trust. Our licensed plumbers are available 24/7 for emergencies and offer comprehensive solutions for all your plumbing needs."
        },
        
        "electrician": {
            "display_name": "Electrical",
            "services": [
                {
                    "name": "Electrical Repairs",
                    "description": "Fast, safe repairs for all electrical issues including outlets, switches, and circuit problems.",
                    "icon": "⚡",
                    "priority": 1
                },
                {
                    "name": "Panel Upgrades",
                    "description": "Electrical panel replacement and circuit breaker upgrades for modern power demands.",
                    "icon": "🔌",
                    "priority": 2
                },
                {
                    "name": "Lighting Installation",
                    "description": "Indoor and outdoor lighting design and installation including LED upgrades.",
                    "icon": "💡",
                    "priority": 3
                },
                {
                    "name": "Wiring Services",
                    "description": "Complete rewiring, new construction wiring, and electrical system updates.",
                    "icon": "🔧",
                    "priority": 4
                },
                {
                    "name": "Safety Inspections",
                    "description": "Comprehensive electrical safety inspections and code compliance checks.",
                    "icon": "🔍",
                    "priority": 5
                },
                {
                    "name": "Smart Home Installation",
                    "description": "Installation of smart switches, thermostats, and home automation systems.",
                    "icon": "🏠",
                    "priority": 6
                }
            ],
            "contact_preference": "phone",
            "contact_emphasis": "24/7 Emergency Electrical Service",
            "cta_primary": "Call for Electrical Service",
            "cta_secondary": "Schedule an Inspection",
            "hours_default": "24/7 Emergency Service Available",
            "trust_factors": [
                "Licensed & Insured Electricians",
                "Emergency Service Available",
                "Code Compliant Work",
                "Warranty on All Services",
                "Safety First Approach"
            ],
            "value_props": [
                "Same-day appointments available",
                "Free safety inspections with service",
                "Energy-efficient solutions",
                "Clean, professional work"
            ],
            "process_steps": [
                "Contact us for service",
                "We schedule a convenient time",
                "Licensed electrician inspects the issue",
                "Receive clear pricing and options",
                "Professional installation or repair",
                "Final inspection and cleanup"
            ],
            "typical_about": "Our licensed electricians provide safe, reliable electrical services for homes and businesses. From emergency repairs to complete installations, we deliver quality workmanship and exceptional customer service."
        },
        
        "hvac": {
            "display_name": "HVAC",
            "services": [
                {
                    "name": "AC Repair & Service",
                    "description": "Fast air conditioning repairs and maintenance to keep you cool all summer.",
                    "icon": "❄️",
                    "priority": 1
                },
                {
                    "name": "Heating Repair & Service",
                    "description": "Furnace and heating system repairs to keep your home warm and comfortable.",
                    "icon": "🔥",
                    "priority": 2
                },
                {
                    "name": "HVAC Installation",
                    "description": "Professional installation of new heating and cooling systems with expert recommendations.",
                    "icon": "🏠",
                    "priority": 3
                },
                {
                    "name": "Maintenance Plans",
                    "description": "Preventive maintenance plans to extend equipment life and improve efficiency.",
                    "icon": "🔧",
                    "priority": 4
                },
                {
                    "name": "Air Quality Services",
                    "description": "Indoor air quality solutions including filtration, purification, and duct cleaning.",
                    "icon": "🌬️",
                    "priority": 5
                },
                {
                    "name": "Emergency Service",
                    "description": "24/7 emergency HVAC service for heating and cooling emergencies.",
                    "icon": "🚨",
                    "priority": 6
                }
            ],
            "contact_preference": "phone",
            "contact_emphasis": "24/7 HVAC Emergency Service",
            "cta_primary": "Call for Service Today",
            "cta_secondary": "Schedule Maintenance",
            "hours_default": "24/7 Emergency Service Available",
            "trust_factors": [
                "Licensed & Certified Technicians",
                "24/7 Emergency Service",
                "Financing Available",
                "Satisfaction Guaranteed",
                "Same-Day Service"
            ],
            "value_props": [
                "Free estimates on system replacement",
                "Maintenance plans available",
                "Energy-efficient solutions",
                "Honest, upfront pricing"
            ],
            "process_steps": [
                "Call or book online",
                "We schedule a convenient appointment",
                "Certified technician diagnoses the issue",
                "Receive transparent pricing",
                "Expert repair or installation",
                "Follow-up to ensure satisfaction"
            ],
            "typical_about": "We provide reliable heating and cooling services to keep your home comfortable year-round. Our certified HVAC technicians deliver quality service with honest pricing and guaranteed satisfaction."
        },
        
        "restaurant": {
            "display_name": "Restaurant",
            "services": [
                {
                    "name": "Dine-In Experience",
                    "description": "Enjoy our delicious menu in our welcoming atmosphere with attentive service.",
                    "icon": "🍽️",
                    "priority": 1
                },
                {
                    "name": "Takeout & Delivery",
                    "description": "Order your favorite dishes for pickup or delivery right to your door.",
                    "icon": "🥡",
                    "priority": 2
                },
                {
                    "name": "Catering Services",
                    "description": "Full-service catering for events, parties, and corporate functions of any size.",
                    "icon": "🎉",
                    "priority": 3
                },
                {
                    "name": "Private Events",
                    "description": "Host your special event in our private dining area with customized menus.",
                    "icon": "🎊",
                    "priority": 4
                }
            ],
            "contact_preference": "phone",
            "contact_emphasis": "Call for Reservations",
            "cta_primary": "View Menu & Order",
            "cta_secondary": "Make a Reservation",
            "hours_default": "Open Daily 11AM - 10PM",
            "trust_factors": [
                "Fresh, Quality Ingredients",
                "Experienced Chefs",
                "Family-Friendly Atmosphere",
                "Highly Rated by Customers",
                "Takeout & Delivery Available"
            ],
            "value_props": [
                "Daily specials and happy hour",
                "Online ordering available",
                "Family-owned and operated",
                "Authentic recipes"
            ],
            "process_steps": [
                "View our menu online or in person",
                "Call ahead for reservations (recommended)",
                "Enjoy our welcoming atmosphere",
                "Experience exceptional service",
                "Savor delicious, freshly prepared food",
                "Leave satisfied and come back soon"
            ],
            "typical_about": "We're passionate about serving delicious food in a warm, welcoming environment. Our menu features fresh ingredients and authentic flavors that keep customers coming back."
        },
        
        "locksmith": {
            "display_name": "Locksmith",
            "services": [
                {
                    "name": "Emergency Lockout Service",
                    "description": "Fast response for home, car, and business lockouts. Available 24/7 when you're locked out.",
                    "icon": "🚨",
                    "priority": 1
                },
                {
                    "name": "Lock Repair & Replacement",
                    "description": "Professional repair and replacement of all types of locks for maximum security.",
                    "icon": "🔐",
                    "priority": 2
                },
                {
                    "name": "Key Cutting & Duplication",
                    "description": "Precise key cutting and duplication for homes, cars, and businesses.",
                    "icon": "🔑",
                    "priority": 3
                },
                {
                    "name": "Security System Installation",
                    "description": "Complete security system installation including smart locks and access control.",
                    "icon": "🔒",
                    "priority": 4
                },
                {
                    "name": "Commercial Locksmith Services",
                    "description": "Master key systems, panic bars, and commercial security solutions.",
                    "icon": "🏢",
                    "priority": 5
                },
                {
                    "name": "Safe Services",
                    "description": "Safe installation, opening, and repair for residential and commercial safes.",
                    "icon": "💰",
                    "priority": 6
                }
            ],
            "contact_preference": "phone",
            "contact_emphasis": "24/7 Emergency Locksmith",
            "cta_primary": "Call Now - 24/7 Service",
            "cta_secondary": "Request a Quote",
            "hours_default": "24/7 Emergency Service Available",
            "trust_factors": [
                "Licensed & Insured",
                "24/7 Emergency Response",
                "Fast 15-30 Min Response Time",
                "No Hidden Fees",
                "All Work Guaranteed"
            ],
            "value_props": [
                "Mobile service - we come to you",
                "No extra charge for nights/weekends",
                "Upfront pricing",
                "Experienced locksmiths"
            ],
            "process_steps": [
                "Call us anytime, day or night",
                "We arrive within 15-30 minutes",
                "Verify identification and ownership",
                "Provide upfront pricing",
                "Complete the job quickly and professionally",
                "Get you back inside safely"
            ],
            "typical_about": "Our professional locksmiths provide fast, reliable service 24/7. Whether you're locked out or need security upgrades, we deliver honest service with fair pricing."
        },
        
        "auto_repair": {
            "display_name": "Auto Repair",
            "services": [
                {
                    "name": "General Auto Repair",
                    "description": "Comprehensive diagnostics and repairs for all makes and models of vehicles.",
                    "icon": "🔧",
                    "priority": 1
                },
                {
                    "name": "Oil Changes & Maintenance",
                    "description": "Fast, professional oil changes and routine maintenance to keep your car running smoothly.",
                    "icon": "🛢️",
                    "priority": 2
                },
                {
                    "name": "Brake Service",
                    "description": "Complete brake inspection, repair, and replacement for your safety.",
                    "icon": "🛑",
                    "priority": 3
                },
                {
                    "name": "Engine Diagnostics & Repair",
                    "description": "Advanced computer diagnostics and expert engine repairs.",
                    "icon": "⚙️",
                    "priority": 4
                },
                {
                    "name": "Transmission Service",
                    "description": "Transmission repair, service, and rebuilds by experienced technicians.",
                    "icon": "🚗",
                    "priority": 5
                },
                {
                    "name": "Tire Services",
                    "description": "Tire sales, installation, rotation, balancing, and alignment services.",
                    "icon": "🚙",
                    "priority": 6
                }
            ],
            "contact_preference": "phone",
            "contact_emphasis": "Schedule Your Service",
            "cta_primary": "Book Appointment",
            "cta_secondary": "Get a Free Estimate",
            "hours_default": "Monday-Friday: 8AM-6PM, Saturday: 9AM-3PM",
            "trust_factors": [
                "ASE Certified Technicians",
                "Warranty on All Repairs",
                "Honest, Transparent Pricing",
                "Shuttle Service Available",
                "All Makes & Models"
            ],
            "value_props": [
                "Free diagnostic with repair",
                "Fleet services available",
                "Loaner cars available",
                "Comprehensive digital inspections"
            ],
            "process_steps": [
                "Call or book online",
                "Drop off your vehicle",
                "We perform thorough diagnostics",
                "Receive detailed estimate",
                "Approve repairs",
                "Pick up your vehicle running great"
            ],
            "typical_about": "Our ASE-certified technicians provide honest, reliable auto repair services. We treat every vehicle like it's our own and stand behind our work with comprehensive warranties."
        },
        
        # ============ NEW CATEGORIES FOR INDUSTRY PERSONAS ============
        
        "dentist": {
            "display_name": "Dental",
            "services": [
                {
                    "name": "General Dentistry",
                    "description": "Comprehensive dental exams, cleanings, and preventive care for the whole family.",
                    "icon": "🦷",
                    "priority": 1
                },
                {
                    "name": "Cosmetic Dentistry",
                    "description": "Teeth whitening, veneers, and smile makeovers to enhance your confidence.",
                    "icon": "✨",
                    "priority": 2
                },
                {
                    "name": "Dental Implants",
                    "description": "Permanent tooth replacement solutions that look and feel natural.",
                    "icon": "🔩",
                    "priority": 3
                },
                {
                    "name": "Emergency Dental Care",
                    "description": "Same-day appointments for dental emergencies, pain relief, and urgent care.",
                    "icon": "🚨",
                    "priority": 4
                },
                {
                    "name": "Invisalign & Orthodontics",
                    "description": "Clear aligners and braces for straighter teeth and a beautiful smile.",
                    "icon": "😁",
                    "priority": 5
                },
                {
                    "name": "Sedation Dentistry",
                    "description": "Comfortable, anxiety-free dental care with sedation options.",
                    "icon": "💤",
                    "priority": 6
                }
            ],
            "contact_preference": "phone",
            "contact_emphasis": "Schedule Your Appointment",
            "cta_primary": "Book Your Visit",
            "cta_secondary": "New Patient Special",
            "hours_default": "Monday-Friday: 8AM-5PM, Saturday: By Appointment",
            "trust_factors": [
                "Gentle, Caring Approach",
                "State-of-the-Art Technology",
                "Experienced Dental Team",
                "Insurance Accepted",
                "Financing Available"
            ],
            "value_props": [
                "Same-day emergency appointments",
                "Sedation options available",
                "New patient specials",
                "Family-friendly practice"
            ],
            "process_steps": [
                "Schedule your appointment",
                "Complete new patient forms",
                "Comprehensive dental exam",
                "Personalized treatment plan",
                "Gentle, comfortable care",
                "Follow-up and preventive care"
            ],
            "typical_about": "Our dental practice is committed to providing gentle, personalized care in a comfortable environment. We use the latest technology to ensure the best outcomes for your smile."
        },
        
        "lawyer": {
            "display_name": "Legal Services",
            "services": [
                {
                    "name": "Free Consultation",
                    "description": "Confidential case evaluation to understand your legal options.",
                    "icon": "⚖️",
                    "priority": 1
                },
                {
                    "name": "Legal Representation",
                    "description": "Experienced advocacy in court and throughout the legal process.",
                    "icon": "📜",
                    "priority": 2
                },
                {
                    "name": "Case Strategy",
                    "description": "Strategic legal planning tailored to your unique situation.",
                    "icon": "🎯",
                    "priority": 3
                },
                {
                    "name": "Settlement Negotiation",
                    "description": "Skilled negotiation to achieve the best possible outcome.",
                    "icon": "🤝",
                    "priority": 4
                }
            ],
            "contact_preference": "phone",
            "contact_emphasis": "Free Consultation",
            "cta_primary": "Schedule Free Consultation",
            "cta_secondary": "Learn About Your Rights",
            "hours_default": "Monday-Friday: 9AM-6PM",
            "trust_factors": [
                "Years of Experience",
                "Proven Track Record",
                "No Fee Unless We Win",
                "Confidential Consultations",
                "Personalized Attention"
            ],
            "value_props": [
                "Free initial consultation",
                "Contingency fee arrangements",
                "24/7 availability for emergencies",
                "Aggressive representation"
            ],
            "process_steps": [
                "Contact us for free consultation",
                "We review your case",
                "Develop legal strategy",
                "Handle all legal proceedings",
                "Fight for the best outcome",
                "No fee unless we win"
            ],
            "typical_about": "With years of experience and a commitment to our clients, we provide aggressive legal representation while treating every case with the attention it deserves."
        },
        
        "roofing": {
            "display_name": "Roofing",
            "services": [
                {
                    "name": "Roof Replacement",
                    "description": "Complete roof replacement with quality materials and expert installation.",
                    "icon": "🏠",
                    "priority": 1
                },
                {
                    "name": "Roof Repair",
                    "description": "Fast, reliable repairs for leaks, storm damage, and general wear.",
                    "icon": "🔧",
                    "priority": 2
                },
                {
                    "name": "Free Roof Inspection",
                    "description": "Comprehensive roof inspection to assess condition and identify issues.",
                    "icon": "🔍",
                    "priority": 3
                },
                {
                    "name": "Storm Damage Repair",
                    "description": "Emergency repairs and insurance claim assistance for storm damage.",
                    "icon": "⛈️",
                    "priority": 4
                },
                {
                    "name": "Gutter Installation",
                    "description": "Seamless gutter installation and repair to protect your home.",
                    "icon": "💧",
                    "priority": 5
                }
            ],
            "contact_preference": "phone",
            "contact_emphasis": "Free Roof Inspection",
            "cta_primary": "Get Free Estimate",
            "cta_secondary": "Schedule Inspection",
            "hours_default": "Monday-Saturday: 7AM-6PM",
            "trust_factors": [
                "Licensed & Insured",
                "Manufacturer Certified",
                "Quality Workmanship Warranty",
                "Local & Trusted",
                "Insurance Claim Specialists"
            ],
            "value_props": [
                "Free roof inspections",
                "Financing available",
                "Insurance claim assistance",
                "Written warranty on all work"
            ],
            "process_steps": [
                "Schedule free inspection",
                "Detailed assessment & photos",
                "Receive honest estimate",
                "Quality installation",
                "Final inspection & cleanup",
                "Warranty documentation"
            ],
            "typical_about": "As a locally owned roofing company, we take pride in protecting your home with quality materials and expert craftsmanship. We stand behind every job with comprehensive warranties."
        },
        
        "salon": {
            "display_name": "Hair Salon",
            "services": [
                {
                    "name": "Haircuts & Styling",
                    "description": "Expert cuts and styling for all hair types and textures.",
                    "icon": "✂️",
                    "priority": 1
                },
                {
                    "name": "Color & Highlights",
                    "description": "Professional hair color, highlights, and balayage services.",
                    "icon": "🎨",
                    "priority": 2
                },
                {
                    "name": "Treatments & Conditioning",
                    "description": "Deep conditioning, keratin, and restorative hair treatments.",
                    "icon": "💆",
                    "priority": 3
                },
                {
                    "name": "Blowouts & Updos",
                    "description": "Special occasion styling, blowouts, and elegant updos.",
                    "icon": "👰",
                    "priority": 4
                }
            ],
            "contact_preference": "phone",
            "contact_emphasis": "Book Your Appointment",
            "cta_primary": "Book Now",
            "cta_secondary": "View Our Work",
            "hours_default": "Tuesday-Saturday: 9AM-7PM",
            "trust_factors": [
                "Award-Winning Stylists",
                "Premium Products",
                "Welcoming Atmosphere",
                "Continuing Education",
                "Satisfaction Guaranteed"
            ],
            "value_props": [
                "Complimentary consultation",
                "Premium hair products",
                "Online booking available",
                "Referral rewards program"
            ],
            "process_steps": [
                "Book your appointment",
                "Consultation with stylist",
                "Relax with complimentary beverage",
                "Expert service & styling",
                "Style tips & product recommendations",
                "Leave feeling beautiful"
            ],
            "typical_about": "Our talented stylists create personalized looks that enhance your natural beauty. We use premium products in a welcoming atmosphere where you can relax and enjoy being pampered."
        },
        
        "veterinarian": {
            "display_name": "Veterinary",
            "services": [
                {
                    "name": "Wellness Exams",
                    "description": "Comprehensive health checkups to keep your pet healthy and happy.",
                    "icon": "🩺",
                    "priority": 1
                },
                {
                    "name": "Vaccinations",
                    "description": "Core and lifestyle vaccinations to protect against disease.",
                    "icon": "💉",
                    "priority": 2
                },
                {
                    "name": "Surgery & Dental",
                    "description": "Safe surgical procedures and dental care for your pet.",
                    "icon": "🔬",
                    "priority": 3
                },
                {
                    "name": "Emergency Care",
                    "description": "Urgent care when your pet needs help fast.",
                    "icon": "🚨",
                    "priority": 4
                },
                {
                    "name": "Grooming & Boarding",
                    "description": "Professional grooming and comfortable boarding services.",
                    "icon": "🐕",
                    "priority": 5
                }
            ],
            "contact_preference": "phone",
            "contact_emphasis": "Schedule Your Visit",
            "cta_primary": "Book Appointment",
            "cta_secondary": "New Patient Info",
            "hours_default": "Monday-Friday: 8AM-6PM, Saturday: 9AM-2PM",
            "trust_factors": [
                "Compassionate Care",
                "Experienced Veterinarians",
                "State-of-the-Art Facility",
                "Fear-Free Certified",
                "Emergency Services"
            ],
            "value_props": [
                "Same-day sick appointments",
                "Wellness plan packages",
                "Pet portal access",
                "Caring, gentle approach"
            ],
            "process_steps": [
                "Schedule appointment",
                "Complete pet history forms",
                "Thorough examination",
                "Discuss findings & recommendations",
                "Treatment with gentle care",
                "Follow-up & preventive care"
            ],
            "typical_about": "Our compassionate team treats every pet like family. We provide comprehensive veterinary care in a fear-free environment, ensuring your furry friends feel safe and loved."
        }
    }
    
    # Default for unknown categories
    DEFAULT_CATEGORY = {
        "display_name": "Professional Services",
        "services": [
            {
                "name": "Expert Services",
                "description": "Professional services tailored to your specific needs with quality results.",
                "icon": "⭐",
                "priority": 1
            },
            {
                "name": "Consultation",
                "description": "Expert consultation to understand your needs and provide the best solutions.",
                "icon": "💼",
                "priority": 2
            },
            {
                "name": "Quality Workmanship",
                "description": "Experienced professionals delivering high-quality work and excellent results.",
                "icon": "🔧",
                "priority": 3
            }
        ],
        "contact_preference": "phone",
        "contact_emphasis": "Contact Us Today",
        "cta_primary": "Get Started",
        "cta_secondary": "Request Information",
        "hours_default": "Monday-Friday: 9AM-5PM",
        "trust_factors": [
            "Experienced Professionals",
            "Customer Satisfaction Guaranteed",
            "Competitive Pricing",
            "Quality Service",
            "Locally Owned & Operated"
        ],
        "value_props": [
            "Free consultations",
            "Flexible scheduling",
            "Professional service",
            "Trusted in the community"
        ],
        "process_steps": [
            "Contact us to discuss your needs",
            "Schedule a convenient appointment",
            "Receive expert service",
            "Enjoy quality results"
        ],
        "typical_about": "We provide professional services with a commitment to quality and customer satisfaction. Our experienced team is dedicated to delivering excellent results."
    }
    
    @classmethod
    def get_category_data(cls, category: str) -> Dict[str, Any]:
        """
        Get complete data for a business category.
        Normalizes category name and returns relevant data.
        """
        if not category:
            return cls.DEFAULT_CATEGORY.copy()
        
        # Normalize category name
        category_normalized = category.lower().strip()
        
        # Try exact match
        if category_normalized in cls.CATEGORY_DATA:
            return cls.CATEGORY_DATA[category_normalized].copy()
        
        # Try partial match
        for key in cls.CATEGORY_DATA.keys():
            if key in category_normalized or category_normalized in key:
                return cls.CATEGORY_DATA[key].copy()
        
        # Return default
        logger.info(f"No specific data for category '{category}', using default")
        return cls.DEFAULT_CATEGORY.copy()
    
    @classmethod
    def get_services(cls, category: str, limit: Optional[int] = 6) -> List[Dict[str, Any]]:
        """Get list of services for a category."""
        data = cls.get_category_data(category)
        services = data.get("services", [])
        return services[:limit] if limit else services
    
    @classmethod
    def get_contact_strategy(cls, category: str, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine the best contact strategy based on category and available data.
        """
        data = cls.get_category_data(category)
        phone = business_data.get("phone")
        email = business_data.get("email")
        
        preference = data.get("contact_preference", "phone")
        
        # Determine primary contact method
        if preference == "phone" and phone:
            primary_contact = "phone"
            primary_value = phone
            primary_action = f"tel:{phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')}"
        elif email:
            primary_contact = "email"
            primary_value = email
            primary_action = f"mailto:{email}"
        elif phone:
            primary_contact = "phone"
            primary_value = phone
            primary_action = f"tel:{phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')}"
        else:
            primary_contact = "form"
            primary_value = None
            primary_action = "#contact"
        
        return {
            "primary_contact": primary_contact,
            "primary_value": primary_value,
            "primary_action": primary_action,
            "cta_primary": data.get("cta_primary", "Get Started"),
            "cta_secondary": data.get("cta_secondary", "Learn More"),
            "contact_emphasis": data.get("contact_emphasis", "Contact Us"),
            "show_phone": bool(phone),
            "show_email": bool(email),
            "show_form": True,  # Always show form as backup
            "hours_default": data.get("hours_default", "Contact us for hours")
        }
    
    @classmethod
    def get_trust_factors(cls, category: str) -> List[str]:
        """Get trust factors/badges for a category."""
        data = cls.get_category_data(category)
        return data.get("trust_factors", [])
    
    @classmethod
    def get_value_props(cls, category: str) -> List[str]:
        """Get value propositions for a category."""
        data = cls.get_category_data(category)
        return data.get("value_props", [])
    
    @classmethod
    def get_process_steps(cls, category: str) -> List[str]:
        """Get typical process/journey steps for a category."""
        data = cls.get_category_data(category)
        return data.get("process_steps", [])
    
    @classmethod
    def get_typical_about(cls, category: str) -> str:
        """Get typical 'about' content for a category."""
        data = cls.get_category_data(category)
        return data.get("typical_about", "")
    
    @classmethod
    def enhance_business_data(cls, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance business data with category-specific defaults.
        This fills in missing data intelligently based on business type.
        
        Now also includes industry style persona information for color psychology.
        """
        category = business_data.get("category", "")
        enhanced = business_data.copy()
        
        # Get category data
        category_info = cls.get_category_data(category)
        
        # Add services if not present
        if not enhanced.get("services"):
            enhanced["services"] = cls.get_services(category, limit=6)
        
        # Add hours if not present
        if not enhanced.get("hours") or enhanced.get("hours") == "":
            enhanced["hours"] = category_info.get("hours_default", "Contact us for hours")
        
        # Add about text if not present
        if not enhanced.get("about"):
            enhanced["about"] = cls.get_typical_about(category)
        
        # Add trust factors
        enhanced["trust_factors"] = cls.get_trust_factors(category)
        
        # Add value propositions
        enhanced["value_propositions"] = cls.get_value_props(category)
        
        # Add process steps
        enhanced["process_steps"] = cls.get_process_steps(category)
        
        # Add contact strategy
        enhanced["contact_strategy"] = cls.get_contact_strategy(category, business_data)
        
        # Add display category name
        enhanced["category_display"] = category_info.get("display_name", category)
        
        # NEW: Add industry style persona for color psychology
        style_overrides = IndustryStyleService.get_style_overrides(category)
        if style_overrides.get("has_industry_guidance"):
            enhanced["industry_persona"] = {
                "name": style_overrides.get("persona_name"),
                "key": style_overrides.get("persona_key"),
                "emotional_target": style_overrides.get("emotional_target"),
                "cta_style": style_overrides.get("cta_style"),
                "cta_text": style_overrides.get("cta_text"),
                "vibe_recommendation": style_overrides.get("vibe_recommendation"),
                "imagery_style": style_overrides.get("imagery_style")
            }
            enhanced["recommended_colors"] = style_overrides.get("recommended_colors")
            enhanced["recommended_typography"] = style_overrides.get("recommended_typography")
            logger.info(
                f"Enhanced '{category}' with '{style_overrides.get('persona_name')}' persona"
            )
        
        return enhanced
