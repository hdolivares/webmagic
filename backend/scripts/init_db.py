"""
Create all database tables from the SQLAlchemy models (fresh local setup).

Usage (from backend/):
    python -m scripts.init_db
"""
import asyncio

import models  # noqa: F401  (registers every model on the metadata)
import models.checkout_session  # noqa: F401
from core.database import init_db


if __name__ == "__main__":
    asyncio.run(init_db())
    print("Database tables created.")
