"""
Migrate Existing Sites to New System

Imports existing generated sites into the new Phase 2 database structure.
Creates Site and SiteVersion records for existing filesystem sites.

Run: python backend/scripts/migrate_existing_sites.py

Author: WebMagic Team
Date: January 21, 2026
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import get_settings
from models.site_models import Site, SiteVersion
from services.site_service import get_site_service

settings = get_settings()


async def migrate_sites():
    """Migrate existing sites to database."""
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("=" * 70)
    print("Migrating Existing Sites to Database")
    print("=" * 70)
    print()
    
    site_service = get_site_service()
    sites_base_path = Path(settings.SITES_BASE_PATH)
    
    if not sites_base_path.exists():
        print(f"❌ Sites directory not found: {sites_base_path}")
        await engine.dispose()
        return
    
    # Find all site directories
    site_dirs = [
        d for d in sites_base_path.iterdir()
        if d.is_dir() and not d.name.startswith('.')
    ]
    
    if not site_dirs:
        print("No sites found to migrate.")
        await engine.dispose()
        return
    
    print(f"Found {len(site_dirs)} site(s) to migrate:")
    for site_dir in site_dirs:
        print(f"  - {site_dir.name}")
    print()
    
    async with AsyncSessionLocal() as session:
        migrated = 0
        skipped = 0
        
        for site_dir in site_dirs:
            slug = site_dir.name
            
            # Check if site already exists in database
            result = await session.execute(
                select(Site).where(Site.slug == slug)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"⏭️  Skipping {slug} (already in database)")
                skipped += 1
                continue
            
            # Read HTML content
            index_path = site_dir / "index.html"
            if not index_path.exists():
                print(f"⚠️  Skipping {slug} (no index.html found)")
                skipped += 1
                continue
            
            try:
                html_content = index_path.read_text(encoding='utf-8')
                
                # Detect site title from HTML
                import re
                title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
                site_title = title_match.group(1) if title_match else slug.replace('-', ' ').title()
                
                # Create site record
                site = Site(
                    slug=slug,
                    site_title=site_title,
                    site_description=f"Generated website for {site_title}",
                    status="preview",  # All existing sites start as preview
                    business_id=None  # Can be linked later
                )
                
                session.add(site)
                await session.flush()  # Get site.id
                
                # Create initial version
                version = SiteVersion(
                    site_id=site.id,
                    version_number=1,
                    html_content=html_content,
                    css_content=None,
                    js_content=None,
                    change_description="Initial site generation (migrated from filesystem)",
                    change_type="initial",
                    created_by_type="admin",
                    is_current=True
                )
                
                session.add(version)
                await session.flush()
                
                # Update site's current_version_id
                site.current_version_id = version.id
                
                await session.commit()
                
                # Generate URL
                site_url = site_service.generate_site_url(slug)
                
                print(f"✅ Migrated {slug}")
                print(f"   Title: {site_title}")
                print(f"   URL: {site_url}")
                print(f"   Status: {site.status}")
                print()
                
                migrated += 1
            
            except Exception as e:
                print(f"❌ Error migrating {slug}: {e}")
                await session.rollback()
                skipped += 1
                continue
    
    await engine.dispose()
    
    print()
    print("=" * 70)
    print("Migration Complete!")
    print("=" * 70)
    print(f"Migrated: {migrated} sites ✅")
    print(f"Skipped:  {skipped} sites")
    print()
    
    if migrated > 0:
        print("🎯 Next Steps:")
        print("   1. Test site API: curl http://localhost:8000/api/v1/sites/<slug>")
        print("   2. Test purchase: POST /api/v1/sites/<slug>/purchase")
        print("   3. Check admin dashboard for site list")
    print()


async def main():
    """Main execution."""
    try:
        await migrate_sites()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
