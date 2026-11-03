"""
Test configuration: a fixed, fake environment so tests never depend on a local
.env, a running database, or real API keys.
"""
import base64
import os
import sys
from pathlib import Path

TEST_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://test:test@127.0.0.1:1/test",
    "SECRET_KEY": "test-" + "x" * 40,
    "OUTSCRAPER_API_KEY": "test",
    "ANTHROPIC_API_KEY": "test",
    "DEBUG": "false",
    "FRONTEND_URL": "https://app.example.com",
    "SITES_BASE_URL": "https://sites.example.com",
    "RECURRENTE_WEBHOOK_SECRET": "whsec_" + base64.b64encode(b"k" * 24).decode(),
    "LABSMOBILE_WEBHOOK_TOKEN": "test-webhook-token",
    "TELNYX_PUBLIC_KEY": "",
    "CORS_ORIGINS": "",
}
os.environ.update(TEST_ENV)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
