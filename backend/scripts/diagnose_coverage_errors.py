"""
Diagnostic script to identify and fix coverage page errors.

This script checks:
1. Database connection
2. Required tables exist
3. Data integrity
4. Service initialization
5. API endpoint functionality

Run this to diagnose the 500 errors on the coverage page.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import get_settings
from core.database import get_db, AsyncSessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_database_connection():
    """Test basic database connectivity."""
    print("\n" + "="*60)
    print("1. CHECKING DATABASE CONNECTION")
    print("="*60)
    
    settings = get_settings()
    try:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            if value == 1:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection returned unexpected value")
                return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    finally:
        await engine.dispose()


async def check_required_tables():
    """Check if all required tables exist."""
    print("\n" + "="*60)
    print("2. CHECKING REQUIRED TABLES")
    print("="*60)
    
    required_tables = [
        'coverage_grid',
        'geo_strategies',
        'draft_campaigns',
        'businesses',
        'admin_users'
    ]
    
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    try:
        async with engine.connect() as conn:
            # Get list of existing tables
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            existing_tables = [row[0] for row in result]
            
            print(f"\nFound {len(existing_tables)} tables in database")
            
            missing_tables = []
            for table in required_tables:
                if table in existing_tables:
                    print(f"✅ {table}")
                else:
                    print(f"❌ {table} - MISSING!")
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
                print("\nTo fix, run migrations:")
                print("  cd backend/migrations")
                if 'geo_strategies' in missing_tables:
                    print("  psql $DATABASE_URL -f 004_add_geo_strategies.sql")
                if 'draft_campaigns' in missing_tables:
                    print("  psql $DATABASE_URL -f 005_add_draft_campaigns.sql")
                return False
            else:
                print("\n✅ All required tables exist")
                return True
                
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False
    finally:
        await engine.dispose()


async def check_table_data():
    """Check if tables have data."""
    print("\n" + "="*60)
    print("3. CHECKING TABLE DATA")
    print("="*60)
    
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    try:
        async with engine.connect() as conn:
            # Check coverage_grid
            result = await conn.execute(text("SELECT COUNT(*) FROM coverage_grid"))
            coverage_count = result.scalar()
            print(f"coverage_grid: {coverage_count} rows")
            
            # Check businesses
            result = await conn.execute(text("SELECT COUNT(*) FROM businesses"))
            business_count = result.scalar()
            print(f"businesses: {business_count} rows")
            
            # Check geo_strategies
            result = await conn.execute(text("SELECT COUNT(*) FROM geo_strategies"))
            strategy_count = result.scalar()
            print(f"geo_strategies: {strategy_count} rows")
            
            # Check draft_campaigns
            result = await conn.execute(text("SELECT COUNT(*) FROM draft_campaigns"))
            draft_count = result.scalar()
            print(f"draft_campaigns: {draft_count} rows")
            
            if coverage_count == 0 and business_count == 0:
                print("\n⚠️  No data found. This is normal for a new installation.")
            else:
                print("\n✅ Data exists in tables")
            
            return True
            
    except Exception as e:
        print(f"❌ Error checking data: {e}")
        return False
    finally:
        await engine.dispose()


async def test_coverage_stats_query():
    """Test the exact query used by /coverage/campaigns/stats endpoint."""
    print("\n" + "="*60)
    print("4. TESTING COVERAGE STATS QUERY")
    print("="*60)
    
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    try:
        async with engine.connect() as conn:
            # Test status counts
            result = await conn.execute(text("""
                SELECT status, COUNT(*) as count
                FROM coverage_grid
                GROUP BY status
            """))
            status_counts = {row[0]: row[1] for row in result}
            print(f"Status counts: {status_counts}")
            
            # Test locations count
            result = await conn.execute(text("""
                SELECT COUNT(DISTINCT CONCAT(city, ':', state)) as count
                FROM coverage_grid
            """))
            locations = result.scalar()
            print(f"Unique locations: {locations}")
            
            # Test categories count
            result = await conn.execute(text("""
                SELECT COUNT(DISTINCT industry_category) as count
                FROM coverage_grid
            """))
            categories = result.scalar()
            print(f"Unique categories: {categories}")
            
            # Test businesses count
            result = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM businesses
            """))
            businesses = result.scalar()
            print(f"Total businesses: {businesses}")
            
            print("\n✅ Coverage stats query successful")
            return True
            
    except Exception as e:
        print(f"❌ Coverage stats query failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def test_draft_campaigns_stats_query():
    """Test the exact query used by /draft-campaigns/stats endpoint."""
    print("\n" + "="*60)
    print("5. TESTING DRAFT CAMPAIGNS STATS QUERY")
    print("="*60)
    
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    try:
        async with engine.connect() as conn:
            # Test status counts
            result = await conn.execute(text("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'pending_review') as pending,
                    COUNT(*) FILTER (WHERE status = 'approved') as approved,
                    COUNT(*) FILTER (WHERE status = 'sent') as sent,
                    COUNT(*) FILTER (WHERE status = 'rejected') as rejected,
                    COUNT(*) as total
                FROM draft_campaigns
            """))
            row = result.fetchone()
            
            if row:
                print(f"Pending: {row[0]}")
                print(f"Approved: {row[1]}")
                print(f"Sent: {row[2]}")
                print(f"Rejected: {row[3]}")
                print(f"Total: {row[4]}")
            else:
                print("No draft campaigns found (this is normal)")
            
            print("\n✅ Draft campaigns stats query successful")
            return True
            
    except Exception as e:
        print(f"❌ Draft campaigns stats query failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def test_service_imports():
    """Test if services can be imported and initialized."""
    print("\n" + "="*60)
    print("6. TESTING SERVICE IMPORTS")
    print("="*60)
    
    try:
        from services.hunter.geo_strategy_service import GeoStrategyService
        print("✅ GeoStrategyService imported")
        
        from services.draft_campaign_service import DraftCampaignService
        print("✅ DraftCampaignService imported")
        
        from services.hunter.hunter_service import HunterService
        print("✅ HunterService imported")
        
        # Try to initialize with a session
        async with AsyncSessionLocal() as session:
            geo_service = GeoStrategyService(session)
            print("✅ GeoStrategyService initialized")
            
            draft_service = DraftCampaignService(session)
            print("✅ DraftCampaignService initialized")
            
            hunter_service = HunterService(session)
            print("✅ HunterService initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Service import/initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all diagnostic checks."""
    print("\n" + "="*60)
    print("COVERAGE PAGE ERROR DIAGNOSTICS")
    print("="*60)
    
    results = []
    
    # Run all checks
    results.append(("Database Connection", await check_database_connection()))
    results.append(("Required Tables", await check_required_tables()))
    results.append(("Table Data", await check_table_data()))
    results.append(("Coverage Stats Query", await test_coverage_stats_query()))
    results.append(("Draft Campaigns Stats Query", await test_draft_campaigns_stats_query()))
    results.append(("Service Imports", await test_service_imports()))
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check_name}")
    
    print(f"\nResults: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All checks passed! The backend should be working correctly.")
        print("\nIf you're still seeing 500 errors, check:")
        print("  1. API server is running (pm2 status)")
        print("  2. API logs for specific errors (pm2 logs webmagic-api)")
        print("  3. Frontend is pointing to correct API URL")
    else:
        print("\n⚠️  Some checks failed. Review the errors above.")
        print("\nCommon fixes:")
        print("  1. Run missing migrations")
        print("  2. Check DATABASE_URL in .env")
        print("  3. Restart API server (pm2 restart webmagic-api)")


if __name__ == "__main__":
    asyncio.run(main())

