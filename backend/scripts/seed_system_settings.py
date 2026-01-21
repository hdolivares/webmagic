"""
Seed system settings including AI model configuration.
Run this once to initialize system settings table.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text
from core.config import get_settings
from models.system_settings import SystemSetting
from services.system_settings_service import SystemSettingsService

settings = get_settings()


async def create_table():
    """Create system_settings table if it doesn't exist."""
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        # Create table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                key VARCHAR(100) UNIQUE NOT NULL,
                value TEXT,
                value_type VARCHAR(20) NOT NULL DEFAULT 'string',
                category VARCHAR(50) NOT NULL,
                label VARCHAR(200) NOT NULL,
                description TEXT,
                options JSONB,
                is_secret BOOLEAN DEFAULT FALSE NOT NULL,
                is_required BOOLEAN DEFAULT FALSE NOT NULL,
                default_value TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        
        # Create indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(key)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_system_settings_category ON system_settings(category)
        """))
    
    await engine.dispose()
    print("✅ system_settings table created")


async def seed_settings():
    """Seed default system settings."""
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        print("=" * 70)
        print("Seeding System Settings")
        print("=" * 70)
        print()
        
        # Check if settings already exist
        result = await session.execute(select(SystemSetting))
        existing = result.scalars().all()
        
        if existing:
            print("⚠️  Settings already exist.")
            print(f"   Found {len(existing)} settings")
            
            # Show AI settings
            print("\n📊 Current AI Settings:")
            for s in existing:
                if s.category == "ai":
                    print(f"   {s.label}: {s.value}")
            
            response = input("\nUpdate AI settings? (y/n): ")
            if response.lower() != 'y':
                await engine.dispose()
                return
        
        # Seed AI defaults
        await SystemSettingsService.seed_ai_defaults(session)
        
        print("\n✅ System settings seeded successfully!")
        print()
        print("📋 AI Configuration:")
        print("   LLM Provider: anthropic (Anthropic Claude)")
        print("   LLM Model: claude-3-5-sonnet-20240620")
        print("   Image Provider: google (Google Imagen)")
        print("   Image Model: imagen-3.0-generate-001")
        print()
        print("💡 You can change these in the Admin Settings UI")
        
        await engine.dispose()


async def main():
    """Main execution."""
    try:
        await create_table()
        await seed_settings()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
