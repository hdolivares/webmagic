"""Quick campaign initialization - inserts directly into database."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_settings

settings = get_settings()

# Top 20 US Cities for demo
CITIES = [
    ("New York", "NY", 8478072),
    ("Los Angeles", "CA", 3878704),
    ("Chicago", "IL", 2721308),
    ("Houston", "TX", 2390125),
    ("Phoenix", "AZ", 1673164),
    ("Philadelphia", "PA", 1573916),
    ("San Antonio", "TX", 1526656),
    ("San Diego", "CA", 1404452),
    ("Dallas", "TX", 1326087),
    ("San Jose", "CA", 997368),
    ("Austin", "TX", 993588),
    ("Jacksonville", "FL", 1009833),
    ("Fort Worth", "TX", 1008106),
    ("Columbus", "OH", 933263),
    ("Charlotte", "NC", 943476),
    ("Indianapolis", "IN", 891484),
    ("San Francisco", "CA", 827526),
    ("Seattle", "WA", 780995),
    ("Denver", "CO", 729019),
    ("Boston", "MA", 673458),
]

# Top 20 High-Value Categories
CATEGORIES = [
    ("lawyers", 9),
    ("dentists", 9),
    ("orthodontists", 10),
    ("cosmetic dentists", 10),
    ("financial advisors", 9),
    ("wealth management", 10),
    ("real estate agents", 8),
    ("insurance agents", 7),
    ("accountants", 8),
    ("chiropractors", 7),
    ("plumbers", 7),
    ("electricians", 7),
    ("hvac companies", 8),
    ("roofers", 8),
    ("general contractors", 9),
    ("home remodeling", 9),
    ("veterinarians", 8),
    ("physical therapists", 7),
    ("auto repair shops", 7),
    ("restaurants", 6),
]


async def quick_init():
    """Initialize with top 20 cities × top 20 categories."""
    from sqlalchemy.ext.asyncio import create_async_engine
    
    print("=" * 70)
    print("WebMagic Campaign Quick Initialization")
    print("=" * 70)
    print(f"Cities: {len(CITIES)}")
    print(f"Categories: {len(CATEGORIES)}")
    print(f"Total: {len(CITIES) * len(CATEGORIES)} grids")
    print(f"Estimated Cost: ${len(CITIES) * len(CATEGORIES) * 0.50:.2f}")
    print("=" * 70)
    print()
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        created = 0
        for city, state, population in CITIES:
            for category, priority in CATEGORIES:
                # Check if exists
                result = await conn.execute(
                    """
                    SELECT id FROM coverage_grid 
                    WHERE city = $1 AND state = $2 AND industry = $3
                    """,
                    city, state, category
                )
                if result.first():
                    continue
                
                # Insert
                await conn.execute(
                    """
                    INSERT INTO coverage_grid 
                    (id, city, state, country, industry, status, priority, population, 
                     lead_count, qualified_count, site_count, conversion_count,
                     created_at, updated_at)
                    VALUES 
                    (gen_random_uuid(), $1, $2, 'US', $3, 'pending', $4, $5, 
                     0, 0, 0, 0, NOW(), NOW())
                    """,
                    city, state, category, priority, population
                )
                created += 1
                
                if created % 50 == 0:
                    print(f"Created: {created}...")
        
        print()
        print("=" * 70)
        print(f"SUCCESS! Created {created} coverage grids")
        print("=" * 70)
        print()
        print("Next: Visit http://localhost:3000/coverage to view campaign")
        print()


if __name__ == "__main__":
    asyncio.run(quick_init())
