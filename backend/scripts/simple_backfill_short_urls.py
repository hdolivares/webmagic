"""
Backfill short_url for legacy generated sites that have none.

Strategy:
  - Load raw (id, subdomain, business_id) tuples — NOT ORM objects — so
    that per-site commits cannot trigger async lazy-reload errors.
  - Join with businesses to get the business name for readable slugs.
  - Uses ShortLinkServiceV2 with business_name for human-readable slugs
    (e.g. "redwx7k" for "Redwood Plumbing").
"""
import asyncio
import logging
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from services.shortener.short_link_service_v2 import ShortLinkServiceV2
from services.shortener.slug_generator import generate_business_slug

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SITE_BASE_URL = "https://sites.lavish.solutions"


def _build_full_url(subdomain: str) -> str:
    return f"{SITE_BASE_URL}/{subdomain}"


async def main() -> None:
    # Load DATABASE_URL from env or .env file
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
        db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    engine = create_async_engine(db_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    logger.info("=" * 60)
    logger.info("Starting short URL backfill for legacy sites")
    logger.info("=" * 60)

    success, errors = 0, 0

    async with AsyncSessionLocal() as db:
        # Load raw rows — tuples, not ORM objects — immune to expire_on_commit
        rows_result = await db.execute(text("""
            SELECT gs.id, gs.subdomain, gs.business_id, b.name AS business_name
            FROM generated_sites gs
            LEFT JOIN businesses b ON b.id = gs.business_id
            WHERE gs.short_url IS NULL
              AND gs.status = 'completed'
            ORDER BY gs.created_at ASC
        """))
        rows = rows_result.fetchall()

    total = len(rows)
    if total == 0:
        logger.info("✅ All sites already have short URLs — nothing to do.")
        await engine.dispose()
        return

    logger.info(f"Found {total} sites needing short links\n")

    for i, row in enumerate(rows, 1):
        site_id = row.id
        subdomain = row.subdomain
        business_id = row.business_id
        business_name = row.business_name

        logger.info(f"[{i}/{total}] {subdomain} ({business_name}) …")

        try:
            # Each site gets its own session so a commit doesn't bleed into others
            async with AsyncSessionLocal() as db:
                full_url = _build_full_url(subdomain)
                short_url = await ShortLinkServiceV2.get_or_create_short_link(
                    db=db,
                    destination_url=full_url,
                    link_type="site_preview",
                    business_id=business_id,
                    site_id=site_id,
                    business_name=business_name,
                )
                await db.execute(
                    text("UPDATE generated_sites SET short_url = :u WHERE id = :id"),
                    {"u": short_url, "id": str(site_id)},
                )
                await db.commit()

            logger.info(f"  ✅  → {short_url}")
            success += 1

        except Exception as exc:
            logger.error(f"  ❌  {subdomain}: {exc}")
            errors += 1

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Done — ✅ {success} succeeded, ❌ {errors} failed out of {total}")
    logger.info("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
