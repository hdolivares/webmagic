"""
Comprehensive list of business categories for systematic discovery.

Organized by industry verticals with estimated profitability scores.
"""

# Format: (category, search_term, profitability_score_1_10, avg_deal_value)
BUSINESS_CATEGORIES = [
    # ==========================================
    # PROFESSIONAL SERVICES (High Value)
    # ==========================================
    ("Legal Services", "lawyers", 9, 5000),
    ("Law Firms", "law firms", 9, 8000),
    ("Personal Injury Lawyers", "personal injury attorneys", 10, 15000),
    ("Family Law", "family law attorneys", 8, 4000),
    ("Estate Planning", "estate planning attorneys", 8, 3000),
    ("Business Attorneys", "business lawyers", 9, 6000),
    
    ("Accounting", "accountants", 8, 3000),
    ("CPA Firms", "certified public accountants", 8, 4000),
    ("Tax Preparation", "tax preparation services", 7, 1500),
    ("Bookkeeping", "bookkeeping services", 6, 1000),
    
    ("Financial Services", "financial advisors", 9, 5000),
    ("Wealth Management", "wealth management", 10, 10000),
    ("Financial Planning", "financial planners", 8, 4000),
    ("Investment Advisors", "investment advisors", 9, 6000),
    
    ("Insurance", "insurance agents", 7, 2000),
    ("Life Insurance", "life insurance agents", 7, 3000),
    ("Health Insurance", "health insurance brokers", 7, 2500),
    ("Business Insurance", "commercial insurance", 8, 4000),
    
    ("Real Estate", "real estate agents", 8, 4000),
    ("Real Estate Brokers", "real estate brokers", 8, 5000),
    ("Property Management", "property management companies", 7, 3000),
    ("Commercial Real Estate", "commercial real estate", 9, 8000),
    
    ("Consulting", "business consultants", 8, 5000),
    ("Management Consulting", "management consultants", 9, 8000),
    ("Marketing Agencies", "marketing agencies", 8, 4000),
    ("Digital Marketing", "digital marketing agencies", 8, 4500),
    ("SEO Services", "seo companies", 7, 3000),
    ("Social Media Marketing", "social media agencies", 7, 2500),
    ("Web Design", "web design companies", 7, 3500),
    
    # ==========================================
    # HEALTHCARE (High Value)
    # ==========================================
    ("Dentists", "dentists", 9, 5000),
    ("Dental Clinics", "dental clinics", 9, 6000),
    ("Orthodontists", "orthodontists", 10, 8000),
    ("Cosmetic Dentistry", "cosmetic dentists", 10, 7000),
    ("Pediatric Dentistry", "pediatric dentists", 8, 4000),
    
    ("Medical Doctors", "doctors", 8, 3000),
    ("Primary Care", "primary care physicians", 7, 2000),
    ("Specialists", "medical specialists", 9, 5000),
    ("Dermatologists", "dermatologists", 9, 6000),
    ("Cardiologists", "cardiologists", 9, 5000),
    
    ("Veterinarians", "veterinarians", 8, 3000),
    ("Animal Hospitals", "animal hospitals", 8, 4000),
    ("Pet Clinics", "pet clinics", 7, 2500),
    
    ("Chiropractors", "chiropractors", 7, 2500),
    ("Physical Therapy", "physical therapists", 7, 2500),
    ("Massage Therapy", "massage therapists", 6, 1500),
    ("Acupuncture", "acupuncturists", 6, 1500),
    
    ("Mental Health", "therapists", 7, 2000),
    ("Counseling", "counseling services", 7, 2000),
    ("Psychiatrists", "psychiatrists", 8, 3000),
    
    ("Medical Clinics", "medical clinics", 8, 3500),
    ("Urgent Care", "urgent care centers", 8, 4000),
    ("Pharmacies", "pharmacies", 6, 1500),
    
    # ==========================================
    # HOME SERVICES (Medium-High Value)
    # ==========================================
    ("Plumbing", "plumbers", 7, 2500),
    ("Emergency Plumbing", "emergency plumbers", 8, 3500),
    
    ("Electrical", "electricians", 7, 2500),
    ("Electrical Contractors", "electrical contractors", 8, 4000),
    
    ("HVAC", "hvac companies", 8, 4000),
    ("Air Conditioning", "air conditioning repair", 7, 2500),
    ("Heating Repair", "heating repair", 7, 2500),
    
    ("Roofing", "roofers", 8, 6000),
    ("Roof Repair", "roof repair", 7, 3000),
    ("Roof Replacement", "roof replacement", 9, 10000),
    
    ("General Contractors", "general contractors", 9, 10000),
    ("Home Remodeling", "home remodeling", 9, 15000),
    ("Kitchen Remodeling", "kitchen remodeling", 9, 20000),
    ("Bathroom Remodeling", "bathroom remodeling", 8, 12000),
    ("Basement Finishing", "basement finishing", 8, 15000),
    
    ("Painting", "painters", 6, 2000),
    ("Interior Painting", "interior painters", 6, 2500),
    ("Exterior Painting", "exterior painters", 7, 3500),
    
    ("Flooring", "flooring contractors", 7, 4000),
    ("Carpet Installation", "carpet installers", 6, 2000),
    ("Hardwood Flooring", "hardwood flooring", 8, 5000),
    
    ("Landscaping", "landscaping companies", 7, 3000),
    ("Lawn Care", "lawn care services", 6, 1200),
    ("Tree Services", "tree service", 7, 2500),
    ("Landscape Design", "landscape designers", 8, 5000),
    
    ("Cleaning Services", "cleaning services", 5, 800),
    ("House Cleaning", "house cleaning", 5, 600),
    ("Commercial Cleaning", "commercial cleaning", 6, 1500),
    ("Carpet Cleaning", "carpet cleaning", 5, 500),
    
    ("Pest Control", "pest control", 6, 1000),
    ("Termite Control", "termite control", 7, 2000),
    
    ("Window Cleaning", "window cleaning", 5, 500),
    ("Gutter Cleaning", "gutter cleaning", 6, 800),
    ("Power Washing", "pressure washing", 6, 1000),
    
    # ==========================================
    # AUTOMOTIVE (Medium Value)
    # ==========================================
    ("Auto Repair", "auto repair shops", 7, 1500),
    ("Car Mechanics", "car mechanics", 7, 1500),
    ("Auto Service", "auto service centers", 7, 2000),
    
    ("Car Dealerships", "car dealerships", 8, 5000),
    ("Used Car Dealers", "used car dealers", 7, 3000),
    
    ("Auto Detailing", "auto detailing", 6, 800),
    ("Car Wash", "car washes", 5, 500),
    
    ("Tire Shops", "tire shops", 6, 1000),
    ("Tire Dealers", "tire dealers", 6, 1200),
    
    ("Auto Body Shops", "auto body shops", 7, 2500),
    ("Collision Repair", "collision repair", 7, 3000),
    
    ("Oil Change", "oil change", 5, 300),
    ("Brake Repair", "brake repair", 6, 800),
    ("Transmission Repair", "transmission repair", 7, 2000),
    
    # ==========================================
    # BEAUTY & WELLNESS (Medium Value)
    # ==========================================
    ("Hair Salons", "hair salons", 6, 1000),
    ("Barber Shops", "barber shops", 5, 600),
    ("Hair Stylists", "hair stylists", 6, 1200),
    
    ("Nail Salons", "nail salons", 5, 600),
    ("Nail Spa", "nail spa", 6, 800),
    
    ("Day Spas", "day spas", 7, 1500),
    ("Spa Services", "spa services", 7, 1800),
    ("Med Spas", "med spas", 8, 3000),
    
    ("Gyms", "gyms", 6, 1200),
    ("Fitness Centers", "fitness centers", 6, 1500),
    ("Personal Trainers", "personal trainers", 6, 1000),
    ("Yoga Studios", "yoga studios", 6, 800),
    ("Pilates Studios", "pilates studios", 6, 1000),
    
    ("Weight Loss", "weight loss centers", 7, 2000),
    ("Nutrition Counseling", "nutritionists", 6, 1000),
    
    # ==========================================
    # FOOD & HOSPITALITY (Variable)
    # ==========================================
    ("Restaurants", "restaurants", 6, 1500),
    ("Fine Dining", "fine dining restaurants", 7, 2500),
    ("Cafes", "cafes", 5, 800),
    ("Coffee Shops", "coffee shops", 5, 600),
    ("Bars", "bars", 6, 1200),
    ("Catering", "catering services", 7, 2000),
    ("Food Trucks", "food trucks", 5, 800),
    ("Bakeries", "bakeries", 5, 700),
    
    # ==========================================
    # RETAIL (Variable)
    # ==========================================
    ("Boutiques", "boutiques", 6, 1000),
    ("Clothing Stores", "clothing stores", 6, 1200),
    ("Florists", "florists", 6, 1000),
    ("Jewelry Stores", "jewelry stores", 7, 2500),
    ("Gift Shops", "gift shops", 5, 600),
    ("Bookstores", "bookstores", 5, 700),
    ("Pet Stores", "pet stores", 6, 1000),
    
    # ==========================================
    # CONSTRUCTION & TRADES (High Value)
    # ==========================================
    ("Architects", "architects", 9, 8000),
    ("Engineering Firms", "engineering firms", 9, 10000),
    ("Interior Designers", "interior designers", 7, 4000),
    
    ("Concrete Contractors", "concrete contractors", 7, 5000),
    ("Masonry", "masonry contractors", 7, 4000),
    ("Siding Contractors", "siding contractors", 7, 4000),
    ("Window Installation", "window installation", 7, 4000),
    ("Door Installation", "door installation", 6, 2000),
    
    # ==========================================
    # EDUCATION & TRAINING (Medium Value)
    # ==========================================
    ("Tutoring", "tutoring services", 6, 1000),
    ("Music Lessons", "music lessons", 5, 600),
    ("Dance Studios", "dance studios", 6, 800),
    ("Martial Arts", "martial arts schools", 6, 1000),
    ("Driving Schools", "driving schools", 5, 600),
]

# Priority tiers for systematic rollout
PRIORITY_TIERS = {
    "tier_1_critical": [  # Start here - highest ROI
        "lawyers", "dentists", "financial advisors", "real estate agents",
        "orthodontists", "cosmetic dentists", "wealth management",
        "personal injury attorneys", "home remodeling", "roof replacement"
    ],
    "tier_2_high": [  # Week 2-3
        "accountants", "chiropractors", "plumbers", "electricians",
        "hvac companies", "roofers", "general contractors", "insurance agents",
        "auto repair shops", "car dealerships"
    ],
    "tier_3_medium": [  # Week 4-6
        "physical therapists", "veterinarians", "pest control",
        "landscaping companies", "painting", "flooring contractors",
        "hair salons", "gyms", "restaurants", "med spas"
    ],
    "tier_4_standard": [  # Ongoing
        # All remaining categories
    ]
}


def get_categories_by_tier(tier: str) -> list:
    """Get all categories in a specific priority tier."""
    return [cat for cat in BUSINESS_CATEGORIES if cat[1] in PRIORITY_TIERS.get(tier, [])]


def get_high_value_categories() -> list:
    """Get categories with profitability score >= 8."""
    return [cat for cat in BUSINESS_CATEGORIES if cat[2] >= 8]


def get_categories_for_location(population: int) -> list:
    """
    Get recommended categories based on location size.
    
    Smaller cities may not have enough volume for niche categories.
    """
    if population >= 500_000:
        # Large cities - all categories
        return BUSINESS_CATEGORIES
    elif population >= 200_000:
        # Medium cities - skip ultra-niche
        return [cat for cat in BUSINESS_CATEGORIES if cat[2] >= 6]
    else:
        # Smaller cities - focus on essentials
        return [cat for cat in BUSINESS_CATEGORIES if cat[2] >= 7]
