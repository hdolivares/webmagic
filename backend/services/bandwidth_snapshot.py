"""
Bandwidth snapshot reader — reads and parses vnstat JSON written by cron.

Used by GET /api/v1/system/bandwidth to expose traffic data to the admin UI.
Keeps parsing and staleness logic separate from the HTTP layer for testability.
"""
from pathlib import Path
import json
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# vnstat --json structure: interfaces[].traffic has "day", "month", "total"
# each with "rx"/"tx" in bytes (or nested under "bytes" in some versions)
REASON_FILE_MISSING = "file_missing"
REASON_FILE_TOO_OLD = "file_too_old"
REASON_PARSE_ERROR = "parse_error"


def get_bandwidth_snapshot(
    snapshot_path: Path,
    stale_seconds: int,
) -> dict[str, Any]:
    """
    Read vnstat JSON snapshot and return a minimal structure for the API.

    Returns a dict with:
      - available: bool
      - reason: optional str (when available is False)
      - updated_at: optional ISO datetime string
      - interface: optional str
      - daily: optional list of {date, rx_bytes, tx_bytes}
      - monthly: optional {rx_bytes, tx_bytes}
      - total: optional {rx_bytes, tx_bytes}

    Does not raise; on any error returns available=False and reason set.
    """
    path = Path(snapshot_path)
    if not path.exists():
        logger.debug("Bandwidth snapshot file missing: %s", path)
        return {"available": False, "reason": REASON_FILE_MISSING}

    try:
        mtime = path.stat().st_mtime
        if stale_seconds > 0 and (datetime.now().timestamp() - mtime) > stale_seconds:
            logger.debug("Bandwidth snapshot too old: %s (mtime %s)", path, mtime)
            return {"available": False, "reason": REASON_FILE_TOO_OLD}
    except OSError as e:
        logger.debug("Bandwidth snapshot stat failed: %s", e)
        return {"available": False, "reason": REASON_FILE_MISSING}

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as e:
        logger.info("Bandwidth snapshot read/parse failed: %s", e)
        return {"available": False, "reason": REASON_PARSE_ERROR}

    return _parse_vnstat_json(data, mtime)


def _parse_vnstat_json(data: dict, mtime: float) -> dict[str, Any]:
    """
    Extract last 7 days daily, current month total, and grand total from vnstat JSON.

    vnstat --json typically has: interfaces: [ { name, traffic: { day: [...], month: [...], total: { rx, tx } } } ]
    Some versions use traffic.total.rx/tx or traffic.total.bytes.rx/tx.
    """
    result: dict[str, Any] = {
        "available": True,
        "updated_at": datetime.utcfromtimestamp(mtime).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "interface": "eth0",
        "daily": [],
        "monthly": None,
        "total": None,
    }

    interfaces = data.get("interfaces")
    if not isinstance(interfaces, list) or not interfaces:
        return result

    iface = interfaces[0] if isinstance(interfaces[0], dict) else None
    if not iface:
        return result

    result["interface"] = iface.get("name") or "eth0"
    traffic = iface.get("traffic") or {}
    if not traffic:
        return result

    # Daily: last 7 entries (vnstat often lists newest first or by date)
    day_list = traffic.get("day") or []
    if isinstance(day_list, list):
        for entry in (day_list[-7:] if len(day_list) > 7 else day_list):
            if not isinstance(entry, dict):
                continue
            date_str = _normalize_date(entry)
            rx = _bytes_from(entry, "rx")
            tx = _bytes_from(entry, "tx")
            if date_str:
                result["daily"].append({"date": date_str, "rx_bytes": rx, "tx_bytes": tx})
        result["daily"] = result["daily"][-7:]

    # Month: current or latest
    month_list = traffic.get("month") or []
    if isinstance(month_list, list) and month_list:
        last_month = month_list[-1] if isinstance(month_list[-1], dict) else None
        if last_month:
            result["monthly"] = {
                "rx_bytes": _bytes_from(last_month, "rx"),
                "tx_bytes": _bytes_from(last_month, "tx"),
            }

    # Total
    total_obj = traffic.get("total") or {}
    if isinstance(total_obj, dict):
        result["total"] = {
            "rx_bytes": _bytes_from(total_obj, "rx"),
            "tx_bytes": _bytes_from(total_obj, "tx"),
        }

    return result


def _normalize_date(entry: dict) -> Optional[str]:
    """Extract date as YYYY-MM-DD from vnstat day entry (date string or id.date or date sub-object)."""
    date_val = entry.get("date")
    if isinstance(date_val, str) and len(date_val) >= 10:
        return date_val[:10]
    id_obj = entry.get("id")
    if isinstance(id_obj, dict):
        d = id_obj.get("date")
        if isinstance(d, str) and len(d) >= 10:
            return d[:10]
    if isinstance(date_val, dict):
        y, m, d = date_val.get("year"), date_val.get("month"), date_val.get("day")
        if y is not None and m is not None and d is not None:
            return f"{y:04d}-{m:02d}-{d:02d}"
    return None


def _bytes_from(obj: dict, direction: str) -> int:
    """Get byte count from vnstat entry; can be under 'rx'/'tx' or 'bytes': {'rx':..., 'tx':...}."""
    val = obj.get(direction)
    if isinstance(val, (int, float)):
        return int(val)
    bytes_obj = obj.get("bytes") or obj.get("byte")
    if isinstance(bytes_obj, dict):
        v = bytes_obj.get(direction)
        if isinstance(v, (int, float)):
            return int(v)
    return 0
