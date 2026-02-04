#!/usr/bin/env python3
"""
Seed default admin user.

Usage: python scripts/seed_admin.py

Default credentials:
- Email: admin@webmagic.com
- Password: admin123
- Role: super_admin
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import get_settings
from core.security import hash_password

settings = get_settings()

# Default admin credentials
ADMIN_EMAIL = "admin@webmagic.com"
ADMIN_PASSWORD = "admin123"
ADMIN_NAME = "Admin User"
ADMIN_ROLE = "super_admin"


async def seed_admin():
    """Create default admin user if not exists."""
    print("=" * 50)
    print("🔐 Seeding Admin User")
    print("=" * 50)
    
    # Hash the password
    password_hash = hash_password(ADMIN_PASSWORD)
    print(f"✅ Password hashed")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # Check if admin already exists
        result = await conn.execute(
            text("SELECT id FROM admin_users WHERE email = :email"),
            {"email": ADMIN_EMAIL}
        )
        existing = result.fetchone()
        
        if existing:
            print(f"⚠️  Admin user already exists: {ADMIN_EMAIL}")
            print("   Skipping creation.")
        else:
            # Insert admin user
            await conn.execute(
                text("""
                    INSERT INTO admin_users (id, email, password_hash, full_name, role, is_active, created_at, updated_at)
                    VALUES (gen_random_uuid(), :email, :password_hash, :full_name, :role, true, NOW(), NOW())
                """),
                {
                    "email": ADMIN_EMAIL,
                    "password_hash": password_hash,
                    "full_name": ADMIN_NAME,
                    "role": ADMIN_ROLE
                }
            )
            print(f"✅ Admin user created: {ADMIN_EMAIL}")
    
    await engine.dispose()
    
    print()
    print("=" * 50)
    print("🎉 Admin seeding complete!")
    print("=" * 50)
    print()
    print("Login credentials:")
    print(f"  Email:    {ADMIN_EMAIL}")
    print(f"  Password: {ADMIN_PASSWORD}")
    print(f"  Role:     {ADMIN_ROLE}")
    print()


if __name__ == "__main__":
    asyncio.run(seed_admin())

