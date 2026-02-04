#!/usr/bin/env python3
"""
Telnyx SMS quick test (single file)

Prereqs:
  pip install requests python-dotenv

Env vars (recommended):
  TELNYX_API_KEY=KEY...
  TELNYX_FROM=+15551234567
  TELNYX_TO=+15559876543

Optional:
  TELNYX_MESSAGING_PROFILE_ID=...   (not required if your number is already assigned to a messaging profile)
  TELNYX_WEBHOOK_URL=https://...    (delivery receipts, etc)
  TELNYX_WEBHOOK_FAILOVER_URL=https://...
"""

import os
import sys
import argparse
import json
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependency: python-dotenv\nRun: pip install python-dotenv")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Missing dependency: requests\nRun: pip install requests")
    sys.exit(1)

# Load .env from script directory or parent directories
env_path = Path(__file__).resolve().parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"  # project root
load_dotenv(env_path)

TELNYX_API_URL = "https://api.telnyx.com/v2/messages"


def must_get(env_name: str, cli_value: str | None) -> str:
    v = cli_value or os.getenv(env_name)
    if not v:
        print(f"Missing required value for {env_name}. Set env var or pass CLI flag.")
        sys.exit(2)
    return v


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test SMS with Telnyx")
    parser.add_argument("--api-key", default=None, help="Telnyx API key (or set TELNYX_API_KEY)")
    parser.add_argument("--from", dest="from_number", default=None, help="Sender E.164 number (or TELNYX_FROM)")
    parser.add_argument("--to", dest="to_number", default=None, help="Recipient E.164 number (or TELNYX_TO)")
    parser.add_argument("--text", default="Hello from Telnyx 👋", help="SMS body text")
    parser.add_argument("--profile-id", default=None, help="Messaging profile ID (or TELNYX_MESSAGING_PROFILE_ID)")
    parser.add_argument("--webhook-url", default=None, help="Webhook URL for DLR/events (or TELNYX_WEBHOOK_URL)")
    parser.add_argument("--webhook-failover-url", default=None, help="Failover webhook URL (or TELNYX_WEBHOOK_FAILOVER_URL)")
    args = parser.parse_args()

    api_key = must_get("TELNYX_API_KEY", args.api_key)
    from_number = must_get("TELNYX_FROM", args.from_number)
    to_number = must_get("TELNYX_TO", args.to_number)

    # Optional extras
    messaging_profile_id = args.profile_id or os.getenv("TELNYX_MESSAGING_PROFILE_ID")
    webhook_url = args.webhook_url or os.getenv("TELNYX_WEBHOOK_URL")
    webhook_failover_url = args.webhook_failover_url or os.getenv("TELNYX_WEBHOOK_FAILOVER_URL")

    payload = {
        "from": from_number,
        "to": to_number,
        "text": args.text,
    }

    # These are optional; add if provided
    if messaging_profile_id:
        payload["messaging_profile_id"] = messaging_profile_id
    if webhook_url:
        payload["webhook_url"] = webhook_url
    if webhook_failover_url:
        payload["webhook_failover_url"] = webhook_failover_url

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(TELNYX_API_URL, headers=headers, json=payload)
        data = resp.json()

        if resp.status_code in (200, 201, 202):
            msg_id = data.get("data", {}).get("id", "(unknown)")
            print("✅ Sent!")
            print(f"Message ID: {msg_id}")
            print("Raw response:")
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ API Error (HTTP {resp.status_code}):")
            print(json.dumps(data, indent=2))
            sys.exit(3)

    except requests.RequestException as e:
        print("❌ Request error:")
        print(str(e))
        sys.exit(3)
    except Exception as e:
        print("❌ Unexpected error:")
        print(repr(e))
        sys.exit(4)


if __name__ == "__main__":
    main()
