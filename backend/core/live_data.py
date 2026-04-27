from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from core.config import SAMPLE_TLES, settings


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_cache_fresh(fetched_at_iso: str, ttl_seconds: int) -> bool:
    try:
        fetched_at = datetime.fromisoformat(fetched_at_iso.replace("Z", "+00:00"))
    except ValueError:
        return False
    age_seconds = (datetime.now(timezone.utc) - fetched_at).total_seconds()
    return age_seconds <= ttl_seconds


def _cache_path() -> Path:
    return Path(settings.live_data_cache_file)


def _history_payload(records: list[dict[str, Any]], source: str) -> dict[str, Any]:
    return {
        "fetched_at": _utc_now_iso(),
        "source": source,
        "count": len(records),
        "records": records,
    }


def _write_cache(records: list[dict[str, Any]], source: str) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_history_payload(records, source), indent=2), encoding="utf-8")


def _read_cache() -> dict[str, Any] | None:
    path = _cache_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _normalize_record(item: dict[str, Any], fallback_name: str | None = None) -> dict[str, Any] | None:
    line1 = str(item.get("TLE_LINE1") or item.get("line1") or "").strip()
    line2 = str(item.get("TLE_LINE2") or item.get("line2") or "").strip()
    if not line1.startswith("1 ") or not line2.startswith("2 "):
        return None
    name = str(item.get("OBJECT_NAME") or item.get("name") or fallback_name or "UNKNOWN").strip()
    norad = str(item.get("NORAD_CAT_ID") or item.get("norad_id") or line1[2:7].strip())
    return {
        "name": name,
        "norad_id": norad,
        "line1": line1,
        "line2": line2,
    }


def _fetch_json(url: str) -> list[dict[str, Any]]:
    with urlopen(url, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _fetch_live_records(catnr_list: list[int] | None, group: str | None) -> list[dict[str, Any]]:
    """Fetch live TLE data from CelesTrak.

    When ``catnr_list`` is provided we attempt to fetch individual satellite TLEs
    (JSON format) – this path is unchanged. If no ``catnr_list`` is given we fetch
    the full active‑set TLE text (``FORMAT=tle``) and parse it into the same record
    shape used elsewhere.
    """
    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    if catnr_list:
        # Existing JSON path (unchanged)
        for catnr in catnr_list:
            query = urlencode({"CATNR": str(catnr), "FORMAT": "JSON"})
            url = f"{settings.celestrak_base_url}?{query}"
            for item in _fetch_json(url):
                normalized = _normalize_record(item)
                if normalized is None:
                    continue
                key = normalized["norad_id"]
                if key in seen:
                    continue
                seen.add(key)
                records.append(normalized)
    else:
        # Fetch plain‑text TLE data for the whole group (default "active")
        grp = group or settings.celestrak_default_group
        query = urlencode({"GROUP": grp, "FORMAT": "tle"})
        url = f"{settings.celestrak_base_url}?{query}"
        try:
            with urlopen(url, timeout=15) as response:
                raw = response.read().decode("utf-8")
        except Exception:
            return []
        # Parse lines: name, line1, line2 repeating
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        for i in range(0, len(lines), 3):
            if i + 2 >= len(lines):
                break
            name_line, line1, line2 = lines[i], lines[i + 1], lines[i + 2]
            if not line1.startswith("1 ") or not line2.startswith("2 "):
                continue
            normalized = {
                "name": name_line,
                "norad_id": line1[2:7].strip(),
                "line1": line1,
                "line2": line2,
            }
            key = normalized["norad_id"]
            if key in seen:
                continue
            seen.add(key)
            records.append(normalized)

    fetched_at = _utc_now_iso()
    for record in records:
        record["fetched_at"] = fetched_at
        record["source_type"] = "live"
    return records


def _sample_records() -> list[dict[str, Any]]:
    fetched_at = _utc_now_iso()
    records: list[dict[str, Any]] = []
    for item in SAMPLE_TLES:
        normalized = _normalize_record(item, fallback_name=str(item.get("name", "UNKNOWN")))
        if normalized is None:
            continue
        normalized["fetched_at"] = fetched_at
        normalized["source_type"] = "sample"
        records.append(normalized)
    return records


# In‑memory cache for TLE data (process‑wide)
_memory_cache: dict[str, Any] = {}
_MEMORY_TTL_SECONDS = 3600  # 1 hour

def _memory_cache_valid() -> bool:
    ts = _memory_cache.get("fetched_at")
    if not ts:
        return False
    try:
        fetched_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return False
    age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
    return age <= _MEMORY_TTL_SECONDS

def load_satellite_records(
    refresh: bool = False,
    catnr_list: list[int] | None = None,
    group: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load satellite TLE records.

    - Uses an in‑memory cache (1 h TTL) to avoid hitting CelesTrak on every request.
    - Falls back to file cache, then sample data.
    - ``refresh=True`` forces a fresh live fetch.
    """
    catnr = catnr_list if catnr_list is not None else list(settings.celestrak_default_catnr_list)
    source_status: dict[str, Any] = {
        "mode": "sample",
        "live_available": False,
        "cache_available": False,
        "last_fetch_at": None,
        "note": "Using sample data.",
    }

    # 1️⃣ Check in‑memory cache first
    if _memory_cache_valid() and not refresh:
        records = _memory_cache.get("records", [])
        if records:
            for r in records:
                r["source_type"] = "cache"
            source_status.update({
                "mode": "cache",
                "cache_available": True,
                "last_fetch_at": _memory_cache["fetched_at"],
                "note": "Using cached live data (in‑memory).",
                "live_available": True,
            })
            return records, source_status

    # 2️⃣ Try file cache (fallback if memory missed or expired)
    cache_payload = _read_cache()
    if cache_payload and isinstance(cache_payload.get("records"), list):
        source_status["cache_available"] = True
        source_status["last_fetch_at"] = cache_payload.get("fetched_at")
        if not refresh and _is_cache_fresh(str(cache_payload.get("fetched_at", "")), settings.live_fetch_ttl_seconds):
            records = [r for r in cache_payload["records"] if isinstance(r, dict)]
            for record in records:
                record["source_type"] = "cache"
            # Populate in‑memory cache for next calls
            _memory_cache.clear()
            _memory_cache.update({"records": records, "fetched_at": cache_payload.get("fetched_at")})
            source_status.update({
                "mode": "cache",
                "note": "Using cached live data (disk).",
                "live_available": True,
            })
            return records, source_status

    # 3️⃣ Attempt live fetch from CelesTrak
    try:
        live_records = _fetch_live_records(catnr_list=catnr, group=group)
        if live_records:
            # Update both caches
            _write_cache(live_records, source="live")
            _memory_cache.clear()
            _memory_cache.update({"records": live_records, "fetched_at": live_records[0].get("fetched_at")})
            source_status.update({
                "mode": "live",
                "live_available": True,
                "last_fetch_at": live_records[0].get("fetched_at"),
                "note": "Using live CelesTrak data.",
            })
            return live_records, source_status
    except Exception:
        source_status["live_available"] = False
        source_status["note"] = "Live fetch failed."

    # 4️⃣ Fallback: use file cache if we have it (even if stale)
    if cache_payload and isinstance(cache_payload.get("records"), list):
        records = [r for r in cache_payload["records"] if isinstance(r, dict)]
        for record in records:
            record["source_type"] = "cache"
        # Populate in‑memory cache with stale data as a last resort
        _memory_cache.clear()
        _memory_cache.update({"records": records, "fetched_at": cache_payload.get("fetched_at")})
        source_status.update({
            "mode": "cache",
            "note": "Live fetch failed; using cached data.",
            "live_available": True,
        })
        return records, source_status

    # 5️⃣ Finally, fall back to sample data
    sample = _sample_records()
    source_status.update({
        "mode": "sample",
        "note": "Live and cache unavailable; using sample data.",
    })
    return sample, source_status
