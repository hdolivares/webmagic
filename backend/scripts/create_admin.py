"""
Create (or reset the password of) an admin dashboard user.

Usage (from backend/):
    python -m scripts.create_admin admin@example.com --name "Jane Doe"

The password is prompted for interactively and never echoed or logged.
"""
import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select

from core.database import AsyncSessionLocal
from core.security import hash_password
from models.user import AdminUser

MIN_PASSWORD_LENGTH = 12


async def upsert_admin(email: str, full_name: str | None, password: str) -> bool:
    """Create the admin, or reset its password if it exists. Returns True if created."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AdminUser).where(AdminUser.email == email))
        user = result.scalar_one_or_none()
        created = user is None
        if created:
            user = AdminUser(email=email, full_name=full_name, role="super_admin", is_active=True)
            db.add(user)
        user.password_hash = hash_password(password)
        await db.commit()
        return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("email")
    parser.add_argument("--name", default=None, help="Full name")
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", file=sys.stderr)
        return 1
    if password != getpass.getpass("Confirm password: "):
        print("Passwords do not match.", file=sys.stderr)
        return 1

    created = asyncio.run(upsert_admin(args.email.strip().lower(), args.name, password))
    print(f"Admin {'created' if created else 'password updated'}: {args.email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
