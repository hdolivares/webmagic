"""
One-off script: validate phone line types for 45 businesses that had sites
generated before the phone validation pipeline was in place.

Calls Telnyx Number Lookup for each business and checks:
  1. line_type_intelligence.type  (requires Telnyx premium add-on; may be null)
  2. portability.line_type        (always returned for US numbers — fallback)

Updates per business:
  - phone_line_type
  - phone_validated_at
  - phone_lookup_at
  - outreach_channel  ("sms" if SMS-capable, "call_later" if landline/blocked)

Usage:
    cd /var/www/webmagic/backend
    python scripts/validate_phone_line_types.py
"""
import asyncio
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import asyncpg
import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# Telnyx portability.line_type raw values -> our internal phone_line_type
_PORTABILITY_MAP: dict[str, str] = {
    "fixed line": "landline",
    "landline": "landline",
    "mobile": "mobile",
    "voip": "voip",
    "fixed voip": "fixed_voip",
    "toll-free": "toll_free",
    "toll free": "toll_free",
    "premium rate": "premium_rate",
    "premium-rate": "premium_rate",
    "pager": "landline",
    "shared cost": "landline",
}

_BLOCKED: frozenset[str] = frozenset({"landline", "toll_free", "premium_rate"})

# 45 businesses that need retroactive phone validation.
# (id, raw_phone, display_name)
BUSINESSES: list[tuple[str, str, str]] = [
    ("c3d4e024-4430-4a5b-ab20-39daec56ff41", "+1 347-773-2875", "24/7 Plumber Mr Rooter"),
    ("2d98f4da-7225-4273-b7e8-61e2ba6e2b8d", "+1 303-629-0722", "A -1 Plumbing Co."),
    ("6c66e06f-db39-455c-8920-f50ad93a4b42", "+1 213-738-6000", "ABC CPAs"),
    ("991456a3-37b1-4e3a-81be-87e89e69a9b6", "+1 918-221-8638", "Alert Plumbing Heat and Air LLC"),
    ("d0530b7d-c4b9-462a-96a4-c911859f914f", "+1 904-888-7268", "A & M Plumbing Repair LLC"),
    ("2d98d1a8-4c7f-4015-99be-c57c938a88e1", "+1 281-277-6765", "Apple Plumbing LLC"),
    ("d9ec17d5-1c5a-4aa7-a551-3bb99d413f25", "+1 337-275-9780", "AR Plumbing Solutions LLC"),
    ("362efff0-5952-4f34-8ae5-79a3487321b5", "+1 314-942-3500", "Beetz Jos H Plumbing Co Inc"),
    ("ea4f3da7-238e-4645-ac21-2a4fd8725c54", "+1 310-500-7079", "Body Care Chiropractic"),
    ("018366de-5ff1-4ae1-95cb-4f5295a38359", "+1 213-634-8807", "Cadens Plumbers"),
    ("bf7e6d04-b14b-416c-8f32-a099f49e95aa", "+1 310-574-5555", "CAMP Clinic - Los Angeles"),
    ("7c88c2c6-2572-4288-a39f-7ce66cb79959", "+1 718-246-4095", "Einsteins Plumbing and Heating Inc"),
    ("f85c9b01-5273-48c1-aae8-aa7ed9d97f6a", "+1 323-585-6486", "Florence Pet Clinic"),
    ("c486b073-105b-4a48-ab73-7b3d978efc7c", "+1 213-984-2997", "GLOBAL FIRST ACCOUNTING GROUP"),
    ("fc96e5c6-37a2-4304-8b32-0c6b6f41ac03", "+1 317-412-7418", "Goin Plumbing"),
    ("92a3b527-20dd-4bbf-9150-d466d638d96f", "+1 410-529-3283", "Hamilton Plumbing Heating Air"),
    ("d89f3734-b970-47cf-8799-f91829d03c70", "+1 256-351-0904", "Higdon Service Heating Cooling Plumbing"),
    ("12629d91-7ceb-411a-9c62-7163e17752b1", "+1 818-765-8196", "Holiday Humane Society Clinic"),
    ("1e306b58-abe5-4fd0-b52d-93343ec6b02b", "+1 720-576-8211", "Homestead Plumbing and Heating"),
    ("3c8c75b3-ca6c-40cf-bd9f-f199afd3517f", "+1 213-761-4246", "JeongTherapy Group"),
    ("dcfac76d-68af-4312-9b41-dd35db3690c7", "+1 918-336-3200", "Lees Plumbing"),
    ("76902318-5475-423f-aaa8-3ed4b4fcdc52", "+1 337-207-5297", "Louisiana Hydro Blast Solutions LLC"),
    ("92940dee-56fb-45c2-9609-8256adf100d4", "+1 225-683-9115", "M & D Plumbing"),
    ("e6200d0e-05dc-4061-8952-7d8a7a16e607", "+1 323-514-2840", "Miguel Perez Painting Corp"),
    ("4e00a261-d142-4099-b6e8-cf0edea18f61", "+1 412-206-1038", "Mister Sewer Plumbing HVAC"),
    ("fe571459-6b71-4b0a-9857-5d79fcee2b52", "+1 310-871-9500", "Nathaniel Flatt LMFT"),
    ("fa35cfad-07fe-4762-bab4-94ee448e0af6", "+1 412-882-8183", "Nix Plumbing"),
    ("fe955ad3-9e62-4e1c-9670-509423a0cf9f", "+1 917-379-6727", "NYC Plumbing Heating Drain Cleaning"),
    ("2b73d830-b68a-4e6d-badc-cdea7f89dec7", "+1 412-563-4383", "PENASCINO PLUMBING AND HEATING Inc"),
    ("130a7992-4e23-434c-9258-e5160dcc9a08", "+1 334-875-4311", "Plumbing Contractors LLC"),
    ("f2ea1cab-c7c0-496a-8f97-062e5284e346", "+1 510-470-7703", "Plumbing The Bay"),
    ("95b7c63a-fe36-442b-8b6d-15109d3279de", "+1 332-239-4044", "Premier Plumbing Company NYC 24/7"),
    ("accdfdd4-4076-498b-9962-81438130fbe1", "+1 206-360-0078", "Puget Seattle Plumbers"),
    ("d6dfc31c-98e3-4e0c-a3cd-548b956ccbf4", "+1 303-981-1059", "Quality Plumbing"),
    ("2652dd7a-a3a1-4464-bec4-2d62bdeecd1e", "+1 412-881-3456", "R D Eikey Plumbing LLC"),
    ("701a227f-577e-467b-a545-5c0e2fd31650", "+1 520-483-9906", "Redwood Plumbing Service Repair LLC"),
    ("6f51580b-8458-44f2-a2a2-b38d50d2a9ba", "+1 718-502-9210", "RR Plumbing Roto-Rooter"),
    ("e0fc0a90-615c-4f7e-ac9a-84f8d1d8cee8", "+1 337-329-0231", "SITTIGS PLUMBING LLC"),
    ("fa20b0c6-4268-41b1-8850-ccfa4d3b9f47", "+1 740-442-4944", "Sparks plumbing and drain cleaning"),
    ("80f1af2f-dfe8-40f5-93b9-99acb082bb28", "+1 323-310-5555", "The Melrose Vet"),
    ("ad3a6003-0615-406d-b17d-ecd85d5ceed3", "+1 310-955-1352", "Thriving Center of Psychology"),
    ("3080aea0-744c-4dfa-a06c-1ae2e19fe371", "+1 213-365-1935", "Tom Kim CPA"),
    ("c15ea1bf-e2db-483e-84fb-ebbf0f2d5ff2", "+1 323-868-9266", "Trees Counseling"),
    ("1dd289fa-5a32-448f-a9e4-b7bee7706a9e", "+1 620-625-2913", "Walker Plumbing Heating"),
    ("ad5b8f04-5abf-4c2e-98b7-4876470fd8bf", "+1 646-280-5850", "West LA Paint More"),
]


def normalize_phone(raw: str) -> str:
    """'+1 303-629-0722'  ->  '+13036290722'"""
    digits = re.sub(r"[^\d+]", "", raw)
    if not digits.startswith("+"):
        digits = "+" + digits
    return digits


def classify(data: dict) -> tuple[str, bool]:
    """
    Return (internal_line_type, is_sms_capable).

    Prefers line_type_intelligence (Telnyx premium add-on) and falls back to
    portability.line_type which is always present for US numbers.
    """
    lti = data.get("line_type_intelligence") or {}
    lti_type = (lti.get("type") or "").lower().replace("-", "_")
    if lti_type and lti_type != "unknown":
        return lti_type, lti_type not in _BLOCKED

    portability = data.get("portability") or {}
    p_raw = (portability.get("line_type") or "").lower().strip()
    p_type = _PORTABILITY_MAP.get(p_raw, "unknown")
    return p_type, p_type not in _BLOCKED


async def telnyx_lookup(session: httpx.AsyncClient, phone_e164: str) -> tuple[str, bool]:
    """Call Telnyx number lookup. Returns (line_type, is_sms_capable). Never raises."""
    try:
        r = await session.get(
            f"https://api.telnyx.com/v2/number_lookup/{phone_e164}",
            headers={"Authorization": f"Bearer {TELNYX_API_KEY}"},
            timeout=10.0,
        )
        if r.status_code != 200:
            log.warning("  Telnyx HTTP %s for %s -- defaulting to unknown", r.status_code, phone_e164)
            return "unknown", True
        return classify(r.json().get("data", {}))
    except Exception as exc:
        log.warning("  Lookup error for %s: %s -- defaulting to unknown", phone_e164, exc)
        return "unknown", True


async def main() -> None:
    if not TELNYX_API_KEY:
        sys.exit("ERROR: TELNYX_API_KEY not set in .env")
    if not DATABASE_URL:
        sys.exit("ERROR: DATABASE_URL not set in .env")

    log.info("Connecting to database...")
    conn = await asyncpg.connect(DB_URL)
    results: dict[str, list[str]] = {"sms": [], "call_later": [], "unknown": []}
    now = datetime.utcnow()

    log.info("Running Telnyx number lookup for %d businesses...\n", len(BUSINESSES))

    async with httpx.AsyncClient() as http:
        for biz_id, raw_phone, name in BUSINESSES:
            phone = normalize_phone(raw_phone)
            line_type, is_sms_capable = await telnyx_lookup(http, phone)
            channel = "sms" if is_sms_capable else "call_later"

            await conn.execute(
                """
                UPDATE businesses
                   SET phone_line_type    = $1,
                       phone_validated_at = $2,
                       phone_lookup_at    = $2,
                       outreach_channel   = $3
                 WHERE id = $4
                """,
                line_type, now, channel, biz_id,
            )

            tag = "[sms]      " if channel == "sms" else "[CALL_LATER]"
            log.info("  %s  %-12s  %s  %s", tag, line_type, phone, name[:45])
            results[channel if channel in results else "unknown"].append(name)

    await conn.close()

    log.info("\n=== SUMMARY ===")
    log.info("  sms        : %d", len(results["sms"]))
    log.info("  call_later : %d", len(results["call_later"]))
    log.info("  unknown    : %d", len(results.get("unknown", [])))
    if results["call_later"]:
        log.info("\n  Businesses flagged as call_later:")
        for name in results["call_later"]:
            log.info("    CALL: %s", name)
    log.info("================")


if __name__ == "__main__":
    asyncio.run(main())
