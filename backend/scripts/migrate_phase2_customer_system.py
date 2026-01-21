"""
Phase 2: Customer Purchase System - Database Migration

Creates tables for:
- Customer sites (with purchase and subscription tracking)
- Customer users (authentication and profiles)
- Site versions (version history)
- Edit requests (AI-powered edits)
- Domain verification records

Run this once to set up Phase 2 infrastructure.

Author: WebMagic Team
Date: January 21, 2026
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from core.config import get_settings

settings = get_settings()


async def migrate_up():
    """Run Phase 2 migrations."""
    engine = create_async_engine(settings.DATABASE_URL)
    
    print("=" * 70)
    print("Phase 2: Customer Purchase System - Database Migration")
    print("=" * 70)
    print()
    
    async with engine.begin() as conn:
        # 1. Create sites table (main customer site tracking)
        print("📋 Creating sites table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sites (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                slug VARCHAR(255) UNIQUE NOT NULL,
                business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,
                
                -- Status tracking
                status VARCHAR(50) DEFAULT 'preview' NOT NULL,
                
                -- Purchase info
                purchased_at TIMESTAMP WITH TIME ZONE,
                purchase_amount DECIMAL(10, 2) DEFAULT 495.00,
                purchase_transaction_id VARCHAR(255),
                
                -- Subscription info
                subscription_status VARCHAR(50),
                subscription_id VARCHAR(255),
                subscription_started_at TIMESTAMP WITH TIME ZONE,
                subscription_ends_at TIMESTAMP WITH TIME ZONE,
                monthly_amount DECIMAL(10, 2) DEFAULT 95.00,
                next_billing_date DATE,
                
                -- Custom domain
                custom_domain VARCHAR(255) UNIQUE,
                domain_verified BOOLEAN DEFAULT FALSE,
                domain_verification_token VARCHAR(255),
                domain_verified_at TIMESTAMP WITH TIME ZONE,
                ssl_provisioned BOOLEAN DEFAULT FALSE,
                ssl_certificate_path VARCHAR(500),
                ssl_provisioned_at TIMESTAMP WITH TIME ZONE,
                
                -- Site metadata
                current_version_id UUID,
                site_title VARCHAR(255),
                site_description TEXT,
                meta_tags JSONB,
                
                -- Timestamps
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        print("✅ sites table created")
        
        # Create indexes for sites
        print("📋 Creating indexes for sites...")
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sites_slug ON sites(slug)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sites_status ON sites(status)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sites_subscription_status 
            ON sites(subscription_status)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sites_custom_domain ON sites(custom_domain)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sites_business_id ON sites(business_id)
        """))
        print("✅ Indexes created for sites")
        
        # 2. Create customer_users table
        print("📋 Creating customer_users table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS customer_users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                
                -- Profile
                full_name VARCHAR(255),
                phone VARCHAR(50),
                
                -- Site ownership
                site_id UUID REFERENCES sites(id) ON DELETE SET NULL,
                
                -- Auth
                email_verified BOOLEAN DEFAULT FALSE,
                email_verification_token VARCHAR(255),
                email_verified_at TIMESTAMP WITH TIME ZONE,
                
                -- Password reset
                password_reset_token VARCHAR(255),
                password_reset_expires TIMESTAMP WITH TIME ZONE,
                
                -- Activity
                last_login TIMESTAMP WITH TIME ZONE,
                login_count INTEGER DEFAULT 0,
                
                -- Status
                is_active BOOLEAN DEFAULT TRUE,
                
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        print("✅ customer_users table created")
        
        # Create indexes for customer_users
        print("📋 Creating indexes for customer_users...")
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_customer_users_email ON customer_users(email)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_customer_users_site_id ON customer_users(site_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_customer_users_email_verification_token 
            ON customer_users(email_verification_token)
        """))
        print("✅ Indexes created for customer_users")
        
        # 3. Create site_versions table
        print("📋 Creating site_versions table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS site_versions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                site_id UUID REFERENCES sites(id) ON DELETE CASCADE NOT NULL,
                version_number INTEGER NOT NULL,
                
                -- Content
                html_content TEXT NOT NULL,
                css_content TEXT,
                js_content TEXT,
                assets JSONB,
                
                -- Metadata
                change_description TEXT,
                change_type VARCHAR(50),
                created_by_type VARCHAR(50),
                created_by_id UUID,
                
                -- Status
                is_current BOOLEAN DEFAULT FALSE,
                is_preview BOOLEAN DEFAULT FALSE,
                
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                
                UNIQUE(site_id, version_number)
            )
        """))
        print("✅ site_versions table created")
        
        # Create indexes for site_versions
        print("📋 Creating indexes for site_versions...")
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_site_versions_site_id 
            ON site_versions(site_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_site_versions_site_current 
            ON site_versions(site_id, is_current)
        """))
        print("✅ Indexes created for site_versions")
        
        # 4. Create edit_requests table
        print("📋 Creating edit_requests table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS edit_requests (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                site_id UUID REFERENCES sites(id) ON DELETE CASCADE NOT NULL,
                
                -- Request details
                request_text TEXT NOT NULL,
                request_type VARCHAR(50),
                target_section VARCHAR(100),
                
                -- Status
                status VARCHAR(50) DEFAULT 'pending',
                
                -- AI processing
                ai_interpretation JSONB,
                ai_confidence DECIMAL(3, 2),
                changes_made JSONB,
                
                -- Preview
                preview_version_id UUID REFERENCES site_versions(id),
                preview_url VARCHAR(500),
                
                -- Approval workflow
                customer_approved BOOLEAN,
                customer_feedback TEXT,
                approved_at TIMESTAMP WITH TIME ZONE,
                rejected_reason TEXT,
                
                -- Deployment
                deployed_version_id UUID REFERENCES site_versions(id),
                deployed_at TIMESTAMP WITH TIME ZONE,
                
                -- Timestamps
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                processed_at TIMESTAMP WITH TIME ZONE
            )
        """))
        print("✅ edit_requests table created")
        
        # Create indexes for edit_requests
        print("📋 Creating indexes for edit_requests...")
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_edit_requests_site_status 
            ON edit_requests(site_id, status)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_edit_requests_status 
            ON edit_requests(status)
        """))
        print("✅ Indexes created for edit_requests")
        
        # 5. Create domain_verification_records table
        print("📋 Creating domain_verification_records table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS domain_verification_records (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                site_id UUID REFERENCES sites(id) ON DELETE CASCADE NOT NULL,
                domain VARCHAR(255) NOT NULL,
                
                -- Verification method
                verification_method VARCHAR(50) NOT NULL,
                verification_token VARCHAR(255) NOT NULL,
                
                -- Status
                verified BOOLEAN DEFAULT FALSE,
                verified_at TIMESTAMP WITH TIME ZONE,
                verification_attempts INTEGER DEFAULT 0,
                last_check_at TIMESTAMP WITH TIME ZONE,
                
                -- DNS records found
                dns_records JSONB,
                
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE
            )
        """))
        print("✅ domain_verification_records table created")
        
        # Create indexes for domain_verification_records
        print("📋 Creating indexes for domain_verification_records...")
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_domain_verification_site_domain 
            ON domain_verification_records(site_id, domain)
        """))
        print("✅ Indexes created for domain_verification_records")
        
        # 6. Add foreign key constraint for sites.current_version_id
        print("📋 Adding foreign key constraints...")
        await conn.execute(text("""
            ALTER TABLE sites 
            DROP CONSTRAINT IF EXISTS fk_sites_current_version
        """))
        await conn.execute(text("""
            ALTER TABLE sites 
            ADD CONSTRAINT fk_sites_current_version 
            FOREIGN KEY (current_version_id) 
            REFERENCES site_versions(id) ON DELETE SET NULL
        """))
        print("✅ Foreign key constraints added")
    
    await engine.dispose()
    
    print()
    print("=" * 70)
    print("✅ Phase 2 Migration Complete!")
    print("=" * 70)
    print()
    print("📊 Tables Created:")
    print("   ✅ sites")
    print("   ✅ customer_users")
    print("   ✅ site_versions")
    print("   ✅ edit_requests")
    print("   ✅ domain_verification_records")
    print()
    print("🎯 Next Steps:")
    print("   1. Run: python backend/scripts/migrate_existing_sites.py")
    print("   2. Test customer registration")
    print("   3. Test site purchase flow")
    print()


async def migrate_down():
    """Rollback Phase 2 migrations (use with caution!)."""
    engine = create_async_engine(settings.DATABASE_URL)
    
    print("⚠️  WARNING: This will drop all Phase 2 tables!")
    response = input("Are you sure? Type 'yes' to confirm: ")
    
    if response.lower() != 'yes':
        print("Cancelled.")
        await engine.dispose()
        return
    
    print()
    print("🗑️  Rolling back Phase 2 migration...")
    
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS domain_verification_records CASCADE"))
        print("✅ Dropped domain_verification_records")
        
        await conn.execute(text("DROP TABLE IF EXISTS edit_requests CASCADE"))
        print("✅ Dropped edit_requests")
        
        await conn.execute(text("DROP TABLE IF EXISTS site_versions CASCADE"))
        print("✅ Dropped site_versions")
        
        await conn.execute(text("DROP TABLE IF EXISTS customer_users CASCADE"))
        print("✅ Dropped customer_users")
        
        await conn.execute(text("DROP TABLE IF EXISTS sites CASCADE"))
        print("✅ Dropped sites")
    
    await engine.dispose()
    print()
    print("✅ Rollback complete")


async def main():
    """Main execution."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'down':
        await migrate_down()
    else:
        await migrate_up()


if __name__ == "__main__":
    asyncio.run(main())
