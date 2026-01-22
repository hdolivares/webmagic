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
    
    # ==========================================
    # EMERGENCY & 24/7 SERVICES (High Value)
    # ==========================================
    ("Emergency Plumbing", "emergency plumber", 9, 4000),
    ("24 Hour Plumber", "24 hour plumber", 9, 4500),
    ("Emergency Electrician", "emergency electrician", 9, 3500),
    ("Emergency Locksmith", "emergency locksmith", 8, 1500),
    ("24 Hour Locksmith", "24 hour locksmith", 8, 1800),
    ("Emergency HVAC", "emergency hvac repair", 9, 3500),
    ("24 Hour HVAC", "24 hour hvac service", 9, 4000),
    ("Emergency Towing", "emergency towing", 7, 800),
    ("24 Hour Towing", "24 hour towing service", 7, 1000),
    ("Emergency Dentist", "emergency dentist", 9, 2500),
    ("Emergency Veterinarian", "emergency vet", 8, 1500),
    
    # ==========================================
    # SPECIALIZED MEDICAL (High Value)
    # ==========================================
    ("Plastic Surgeons", "plastic surgeons", 10, 15000),
    ("Cosmetic Surgery", "cosmetic surgery", 10, 18000),
    ("Ophthalmologists", "ophthalmologists", 9, 4000),
    ("Eye Doctors", "eye doctors", 8, 2500),
    ("Optometrists", "optometrists", 8, 2000),
    ("ENT Specialists", "ent doctors", 9, 3500),
    ("Podiatrists", "podiatrists", 8, 2500),
    ("Foot Doctor", "foot doctors", 8, 2500),
    ("Pain Management", "pain management doctors", 9, 4000),
    ("Sports Medicine", "sports medicine doctors", 8, 3000),
    ("Allergists", "allergists", 8, 2500),
    ("Endocrinologists", "endocrinologists", 9, 3500),
    ("Gastroenterologists", "gastroenterologists", 9, 3500),
    ("Neurologists", "neurologists", 9, 4000),
    ("Orthopedic Surgeons", "orthopedic surgeons", 9, 8000),
    ("Urologists", "urologists", 9, 3500),
    ("OBGYN", "obgyn doctors", 8, 3000),
    ("Pediatricians", "pediatricians", 8, 2500),
    ("Sleep Specialists", "sleep doctors", 8, 3000),
    ("Fertility Clinics", "fertility clinics", 9, 8000),
    ("IVF Clinics", "ivf clinics", 9, 10000),
    
    # ==========================================
    # SPECIALIZED DENTAL (High Value)
    # ==========================================
    ("Dental Implants", "dental implants", 10, 8000),
    ("Teeth Whitening", "teeth whitening", 8, 1500),
    ("Invisalign", "invisalign dentist", 9, 6000),
    ("Periodontics", "periodontist", 9, 4000),
    ("Endodontist", "endodontist", 9, 3500),
    ("Oral Surgeons", "oral surgeons", 9, 5000),
    ("Root Canal Specialist", "root canal specialist", 8, 2500),
    ("Dental Bridges", "dental bridges", 9, 5000),
    ("Dentures", "denture specialist", 8, 3000),
    ("Sedation Dentistry", "sedation dentist", 9, 4000),
    
    # ==========================================
    # SPECIALIZED LEGAL (Very High Value)
    # ==========================================
    ("Immigration Lawyers", "immigration lawyers", 9, 5000),
    ("Criminal Defense", "criminal defense attorney", 9, 8000),
    ("DUI Lawyers", "dui lawyers", 9, 4000),
    ("Divorce Lawyers", "divorce attorneys", 9, 5000),
    ("Bankruptcy Lawyers", "bankruptcy attorneys", 8, 3500),
    ("Workers Comp Lawyers", "workers compensation attorney", 9, 6000),
    ("Medical Malpractice", "medical malpractice attorney", 10, 20000),
    ("Employment Lawyers", "employment lawyers", 8, 5000),
    ("Social Security Disability", "social security disability lawyer", 9, 6000),
    ("Car Accident Lawyers", "car accident lawyer", 10, 12000),
    ("Truck Accident Lawyers", "truck accident lawyer", 10, 18000),
    ("Motorcycle Accident Lawyers", "motorcycle accident lawyer", 9, 10000),
    ("Slip and Fall Lawyers", "slip and fall attorney", 9, 8000),
    ("Wrongful Death Lawyers", "wrongful death attorney", 10, 25000),
    ("Patent Lawyers", "patent attorneys", 9, 8000),
    ("Trademark Lawyers", "trademark attorneys", 8, 4000),
    ("Real Estate Lawyers", "real estate attorneys", 8, 4000),
    ("Probate Lawyers", "probate attorneys", 8, 4000),
    ("Tax Lawyers", "tax attorneys", 9, 6000),
    
    # ==========================================
    # SPECIALIZED HOME SERVICES (High Value)
    # ==========================================
    ("Water Damage Restoration", "water damage restoration", 9, 6000),
    ("Fire Damage Restoration", "fire damage restoration", 9, 8000),
    ("Mold Remediation", "mold remediation", 9, 5000),
    ("Mold Removal", "mold removal", 9, 5500),
    ("Foundation Repair", "foundation repair", 9, 12000),
    ("Basement Waterproofing", "basement waterproofing", 8, 6000),
    ("Sump Pump Installation", "sump pump installation", 7, 2000),
    ("Drain Cleaning", "drain cleaning", 7, 1500),
    ("Sewer Repair", "sewer repair", 8, 4000),
    ("Septic Tank Service", "septic tank service", 7, 2500),
    ("Well Pump Repair", "well pump repair", 7, 2000),
    ("Water Heater Repair", "water heater repair", 7, 1500),
    ("Tankless Water Heater", "tankless water heater installation", 8, 3500),
    ("Furnace Repair", "furnace repair", 8, 2500),
    ("AC Repair", "air conditioner repair", 8, 2000),
    ("Duct Cleaning", "duct cleaning", 6, 800),
    ("Chimney Sweep", "chimney sweep", 6, 500),
    ("Chimney Repair", "chimney repair", 7, 3000),
    ("Gutter Installation", "gutter installation", 7, 2500),
    ("Gutter Repair", "gutter repair", 6, 1000),
    ("Deck Builders", "deck builders", 8, 8000),
    ("Fence Installation", "fence installation", 7, 3000),
    ("Fence Repair", "fence repair", 6, 1000),
    ("Patio Installation", "patio installation", 8, 6000),
    ("Concrete Driveway", "concrete driveway", 8, 5000),
    ("Asphalt Paving", "asphalt paving", 8, 6000),
    ("Driveway Sealing", "driveway sealing", 6, 800),
    ("Garage Door Repair", "garage door repair", 7, 1500),
    ("Garage Door Installation", "garage door installation", 8, 3000),
    ("Insulation Installation", "insulation installation", 7, 3000),
    ("Attic Insulation", "attic insulation", 7, 2500),
    ("Drywall Repair", "drywall repair", 6, 800),
    ("Drywall Installation", "drywall installation", 6, 2000),
    ("Tile Installation", "tile installation", 7, 3000),
    ("Countertop Installation", "countertop installation", 8, 4000),
    ("Cabinet Installation", "cabinet installation", 8, 5000),
    ("Closet Organizers", "closet organizers", 7, 2000),
    
    # ==========================================
    # OUTDOOR & LANDSCAPING (Medium-High Value)
    # ==========================================
    ("Pool Installation", "pool installation", 9, 40000),
    ("Pool Maintenance", "pool maintenance", 7, 1500),
    ("Pool Repair", "pool repair", 7, 2500),
    ("Hot Tub Repair", "hot tub repair", 7, 1500),
    ("Sprinkler System", "sprinkler system installation", 7, 3000),
    ("Irrigation Systems", "irrigation systems", 7, 3500),
    ("Sod Installation", "sod installation", 7, 2000),
    ("Artificial Turf", "artificial turf installation", 8, 5000),
    ("Tree Removal", "tree removal", 8, 2500),
    ("Stump Removal", "stump removal", 7, 800),
    ("Tree Trimming", "tree trimming", 7, 1200),
    ("Arborist", "arborist", 8, 2000),
    ("Snow Removal", "snow removal", 6, 800),
    ("Outdoor Lighting", "outdoor lighting installation", 7, 2500),
    ("Hardscaping", "hardscaping", 8, 8000),
    ("Retaining Walls", "retaining wall installation", 8, 6000),
    
    # ==========================================
    # SPECIALIZED AUTOMOTIVE (Medium-High Value)
    # ==========================================
    ("Luxury Car Repair", "luxury car repair", 8, 3000),
    ("European Car Repair", "european car repair", 8, 2500),
    ("BMW Repair", "bmw repair", 8, 2500),
    ("Mercedes Repair", "mercedes repair", 8, 2800),
    ("Tesla Repair", "tesla repair", 9, 3500),
    ("Electric Car Repair", "electric vehicle repair", 8, 2500),
    ("Hybrid Car Repair", "hybrid car repair", 7, 2000),
    ("Diesel Repair", "diesel repair", 7, 2000),
    ("Truck Repair", "truck repair", 7, 2500),
    ("RV Repair", "rv repair", 8, 3000),
    ("Motorcycle Repair", "motorcycle repair", 7, 1500),
    ("Boat Repair", "boat repair", 8, 3000),
    ("Auto Upholstery", "auto upholstery", 6, 1200),
    ("Window Tinting", "window tinting", 6, 500),
    ("Paint Protection Film", "paint protection film", 7, 1500),
    ("Ceramic Coating", "ceramic coating", 7, 1200),
    ("Mobile Mechanic", "mobile mechanic", 7, 1500),
    ("Mobile Oil Change", "mobile oil change", 6, 400),
    
    # ==========================================
    # TECHNOLOGY & IT (High Value)
    # ==========================================
    ("IT Support", "it support", 8, 3000),
    ("Managed IT Services", "managed it services", 9, 5000),
    ("Computer Repair", "computer repair", 6, 800),
    ("Mac Repair", "mac repair", 7, 1000),
    ("iPhone Repair", "iphone repair", 6, 300),
    ("Phone Repair", "phone repair", 6, 200),
    ("Data Recovery", "data recovery", 8, 2000),
    ("Network Installation", "network installation", 8, 3000),
    ("Security Cameras", "security camera installation", 7, 2500),
    ("Home Automation", "home automation", 8, 4000),
    ("Smart Home Installation", "smart home installation", 8, 3500),
    
    # ==========================================
    # WELLNESS & ALTERNATIVE MEDICINE (Medium Value)
    # ==========================================
    ("Naturopathic Doctor", "naturopathic doctor", 7, 2000),
    ("Holistic Medicine", "holistic medicine", 7, 1800),
    ("Functional Medicine", "functional medicine", 8, 3000),
    ("Integrative Medicine", "integrative medicine", 8, 2500),
    ("Meditation Classes", "meditation classes", 5, 500),
    ("Reiki Healing", "reiki healing", 5, 600),
    ("Life Coach", "life coach", 6, 1500),
    ("Health Coach", "health coach", 6, 1200),
    ("Dietitian", "dietitian", 7, 1500),
    ("Sports Nutrition", "sports nutritionist", 7, 1800),
    
    # ==========================================
    # WEDDING & EVENTS (High Value)
    # ==========================================
    ("Wedding Planners", "wedding planners", 8, 4000),
    ("Event Planners", "event planners", 7, 3000),
    ("Wedding Venues", "wedding venues", 9, 8000),
    ("Wedding Photographers", "wedding photographers", 7, 3000),
    ("Wedding Videographers", "wedding videographers", 7, 2500),
    ("Wedding DJs", "wedding djs", 6, 1200),
    ("Wedding Florists", "wedding florists", 7, 2000),
    ("Wedding Cakes", "wedding cake bakery", 7, 1500),
    ("Party Rentals", "party rentals", 6, 1000),
    
    # ==========================================
    # PET SERVICES (Medium Value)
    # ==========================================
    ("Dog Grooming", "dog grooming", 6, 800),
    ("Pet Grooming", "pet grooming", 6, 700),
    ("Dog Training", "dog training", 6, 1000),
    ("Dog Walking", "dog walking", 5, 400),
    ("Pet Sitting", "pet sitting", 5, 500),
    ("Dog Boarding", "dog boarding", 6, 800),
    ("Pet Boarding", "pet boarding", 6, 900),
    ("Mobile Pet Grooming", "mobile pet grooming", 7, 1000),
    ("Emergency Vet", "24 hour emergency vet", 9, 2000),
    
    # ==========================================
    # MOVING & STORAGE (Medium Value)
    # ==========================================
    ("Moving Companies", "moving companies", 7, 2000),
    ("Local Movers", "local movers", 7, 1500),
    ("Long Distance Movers", "long distance movers", 8, 3500),
    ("Piano Movers", "piano movers", 7, 800),
    ("Storage Units", "storage units", 6, 1000),
    ("Climate Controlled Storage", "climate controlled storage", 7, 1500),
    ("Junk Removal", "junk removal", 6, 800),
    ("Estate Cleanout", "estate cleanout", 7, 1500),
    ("Hoarding Cleanup", "hoarding cleanup", 8, 3000),
    
    # ==========================================
    # SENIOR CARE (High Value)
    # ==========================================
    ("Home Care", "home care services", 8, 3000),
    ("Senior Care", "senior care", 8, 3500),
    ("Assisted Living", "assisted living", 9, 5000),
    ("Memory Care", "memory care", 9, 6000),
    ("Elder Care", "elder care", 8, 3000),
    ("Nursing Homes", "nursing homes", 8, 4000),
    ("In Home Care", "in home care", 8, 3000),
    ("Caregiver Services", "caregiver services", 7, 2500),
    
    # ==========================================
    # SPECIALIZED CONTRACTORS (High Value)
    # ==========================================
    ("Solar Installation", "solar panel installation", 9, 15000),
    ("Solar Companies", "solar companies", 9, 18000),
    ("Generator Installation", "generator installation", 8, 6000),
    ("Backup Generator", "backup generator installation", 8, 7000),
    ("Elevator Installation", "elevator installation", 9, 50000),
    ("Home Elevator", "home elevator", 9, 40000),
    ("Soundproofing", "soundproofing", 7, 3000),
    ("Home Theater Installation", "home theater installation", 8, 5000),
    ("Sauna Installation", "sauna installation", 8, 8000),
    ("Wine Cellar", "wine cellar construction", 9, 15000),
    ("Home Additions", "home additions", 9, 50000),
    ("Second Story Addition", "second story addition", 9, 80000),
    ("ADU Construction", "adu construction", 9, 100000),
    ("Garage Conversion", "garage conversion", 8, 25000),
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
