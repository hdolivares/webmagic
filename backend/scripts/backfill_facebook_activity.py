"""
One-time backfill script: queue fetch_facebook_activity for all businesses
that have a Facebook URL in their scrapingdog_discovery organic results
but have never had their Facebook activity checked.

Usage (run from /var/www/webmagic/backend):
    python scripts/backfill_facebook_activity.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from core.database import get_db_session_sync
from models.business import Business
from services.activity import extract_facebook_url_from_raw
from tasks.activity_tasks import fetch_facebook_activity

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def main() -> None:
    queued = 0
    skipped = 0

    with get_db_session_sync() as db:
        businesses = (
            db.query(Business)
            .filter(Business.last_facebook_post_date.is_(None))
            .filter(Business.raw_data.has_key("scrapingdog_discovery"))
            .all()
        )
        print(f"Candidates (has scrapingdog_discovery, no FB post date): {len(businesses)}")

        for biz in businesses:
            fb_url = extract_facebook_url_from_raw(biz.raw_data or {})
            if fb_url:
                fetch_facebook_activity.delay(str(biz.id))
                queued += 1
            else:
                skipped += 1

    print(f"Done — queued={queued}  no_facebook_url={skipped}  total={queued + skipped}")


if __name__ == "__main__":
    main()
