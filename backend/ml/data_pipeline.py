from __future__ import annotations

from datetime import datetime, timedelta, timezone
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from skyfield.api import EarthSatellite, load, wgs84

from core.cache import SimpleTTLCache
from core.config import settings
from core.live_data import load_satellite_records
from ml.schemas import CollisionEvent, SatellitePosition

_TS = load.timescale()
_CONJUNCTION_CACHE = SimpleTTLCache()
_LAST_SOURCE_STATUS: dict[str, Any] = {
    "mode": "sample",
    "live_available": False,
    "cache_available": False,
    "last_fetch_at": None,
    "note": "No fetch attempted yet.",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _time_step_seconds(horizon_hours: int | None = None) -> int:
    return max(1, int(settings.simulation_step_seconds))


def _prediction_hours(horizon_hours: int | None = None) -> int:
    if horizon_hours is None:
        return max(1, int(settings.simulation_horizon_hours))
    return max(1, int(horizon_hours))


def _distance_km(a: dict[str, Any], b: dict[str, Any]) -> float:
    vec_a = np.array([a["x_km"], a["y_km"], a["z_km"]], dtype=float)
    vec_b = np.array([b["x_km"], b["y_km"], b["z_km"]], dtype=float)
    return float(max(0.0, np.linalg.norm(vec_a - vec_b)))


def _relative_speed_km_s(dx_vel: float, dy_vel: float, dz_vel: float) -> float:
    velocity_vector = np.array([dx_vel, dy_vel, dz_vel], dtype=float)
    return float(np.linalg.norm(velocity_vector))


def _future_times(start: datetime, horizon_hours: int | None = None) -> list[datetime]:
    step_seconds = _time_step_seconds(horizon_hours=horizon_hours)
    total_seconds = _prediction_hours(horizon_hours=horizon_hours) * 3600
    steps = max(1, int(total_seconds // step_seconds))
    return [start + timedelta(seconds=i * step_seconds) for i in range(steps + 1)]


def _risk_tier_from_score(score: float) -> str:
    if score >= 80:
        return "danger"
    if score >= 45:
        return "warning"
    return "safe"


def _base_score_from_distance(min_distance_km: float) -> float:
    if min_distance_km < settings.danger_distance_km:
        return 95.0
    if min_distance_km < settings.warning_distance_km:
        return 70.0
    if min_distance_km < 150:
        return 40.0
    return 10.0


def _prediction_quality(mode: str) -> str:
    if mode == "live":
        return "medium"
    if mode == "cache":
        return "medium-low"
    return "low"


def _risk_score(
    min_distance_km: float,
    relative_speed_km_s: float,
    altitude_diff_km: float,
    source_mode: str,
) -> float:
    score = _base_score_from_distance(min_distance_km)
    if altitude_diff_km <= settings.altitude_band_km:
        score += 12.0
    if relative_speed_km_s >= settings.high_relative_speed_km_s:
        score += 10.0
    elif relative_speed_km_s >= settings.moderate_relative_speed_km_s:
        score += 5.0
    if source_mode == "sample":
        score -= 5.0
    return float(max(0.0, min(100.0, score)))


def _satellite_state(satellite: EarthSatellite, when: datetime) -> dict[str, Any]:
    t = _TS.from_datetime(when)
    geocentric = satellite.at(t)
    subpoint = wgs84.subpoint(geocentric)
    xyz = geocentric.position.km
    velocity = geocentric.velocity.km_per_s
    return {
        "lat": float(subpoint.latitude.degrees),
        "lon": float(subpoint.longitude.degrees),
        "alt_km": float(subpoint.elevation.km),
        "x_km": float(xyz[0]),
        "y_km": float(xyz[1]),
        "z_km": float(xyz[2]),
        "vx_km_s": float(velocity[0]),
        "vy_km_s": float(velocity[1]),
        "vz_km_s": float(velocity[2]),
    }


def _build_satellites(
    refresh: bool = False,
    catnr_list: list[int] | None = None,
    group: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records, source_status = load_satellite_records(refresh=refresh, catnr_list=catnr_list, group=group)
    satellites: list[dict[str, Any]] = []
    for record in records:
        try:
            satellite = EarthSatellite(record["line1"], record["line2"], record["name"], _TS)
        except Exception:
            continue
        satellites.append(
            {
                "satellite": satellite,
                "name": str(record["name"]),
                "norad_id": str(record.get("norad_id", "unknown")),
                "source_type": str(record.get("source_type", source_status.get("mode", "sample"))),
                "fetched_at": str(record.get("fetched_at") or source_status.get("last_fetch_at") or ""),
            }
        )
    global _LAST_SOURCE_STATUS
    _LAST_SOURCE_STATUS = dict(source_status)
    return satellites, source_status


def get_source_status() -> dict[str, Any]:
    return dict(_LAST_SOURCE_STATUS)


def build_current_satellite_positions(
    refresh: bool = False,
    catnr_list: list[int] | None = None,
    group: str | None = None,
) -> list[SatellitePosition]:
    satellite_entries, _ = _build_satellites(refresh=refresh, catnr_list=catnr_list, group=group)
    if not satellite_entries:
        return []

    now = _utc_now()
    states: list[dict[str, Any]] = []
    for entry in satellite_entries:
        try:
            state = _satellite_state(entry["satellite"], now)
        except Exception:
            continue
        if not np.all(np.isfinite([state["lat"], state["lon"], state["alt_km"], state["x_km"], state["y_km"], state["z_km"]])):
            continue
        states.append({**entry, **state})

    out: list[SatellitePosition] = []
    for i, state_i in enumerate(states):
        nearest = float("inf")
        for j, state_j in enumerate(states):
            if i == j:
                continue
            nearest = min(nearest, _distance_km(state_i, state_j))
        score = _risk_score(
            min_distance_km=nearest,
            relative_speed_km_s=0.0,
            altitude_diff_km=0.0,
            source_mode=str(state_i["source_type"]),
        )
        out.append(
            SatellitePosition(
                name=state_i["name"],
                norad_id=state_i["norad_id"],
                lat=round(state_i["lat"], 6),
                lon=round(state_i["lon"], 6),
                alt_km=round(state_i["alt_km"], 3),
                x_km=round(state_i["x_km"], 3),
                y_km=round(state_i["y_km"], 3),
                z_km=round(state_i["z_km"], 3),
                risk=_risk_tier_from_score(score),
                source_type=state_i["source_type"],
                fetched_at=state_i["fetched_at"],
            )
        )
    return out


def compute_collision_candidates(
    horizon_hours: int | None = None,
    limit: int | None = None,
    risk: str | None = None,
    name_filter: str | None = None,
    refresh: bool = False,
    catnr_list: list[int] | None = None,
    group: str | None = None,
) -> list[CollisionEvent]:
    cache_key = (
        f"conjunction:{horizon_hours}:{limit}:{risk}:{name_filter}:"
        f"{','.join(str(v) for v in (catnr_list or []))}:{group}"
    )
    if not refresh:
        cached = _CONJUNCTION_CACHE.get(cache_key)
        if cached is not None:
            return [CollisionEvent.model_validate(item) for item in cached]

    satellite_entries, source_status = _build_satellites(refresh=refresh, catnr_list=catnr_list, group=group)
    if len(satellite_entries) < 2:
        return []

    now = _utc_now()
    times = _future_times(now, horizon_hours=horizon_hours)
    output: list[CollisionEvent] = []
    normalized_filter = (name_filter or "").strip().lower()

    for left, right in combinations(satellite_entries, 2):
        sat_a: EarthSatellite = left["satellite"]
        sat_b: EarthSatellite = right["satellite"]
        name_a = str(left["name"])
        name_b = str(right["name"])
        if normalized_filter:
            pair_text = f"{name_a} {name_b} {left['norad_id']} {right['norad_id']}".lower()
            if normalized_filter not in pair_text:
                continue

        try:
            current_a = _satellite_state(sat_a, now)
            current_b = _satellite_state(sat_b, now)
        except Exception:
            continue

        min_distance = float("inf")
        tca = now
        tca_a = current_a
        tca_b = current_b
        for step_time in times:
            try:
                step_a = _satellite_state(sat_a, step_time)
                step_b = _satellite_state(sat_b, step_time)
            except Exception:
                continue
            distance = _distance_km(step_a, step_b)
            if distance < min_distance:
                min_distance = distance
                tca = step_time
                tca_a = step_a
                tca_b = step_b

        if not np.isfinite(min_distance):
            continue

        dx = float(current_b["x_km"] - current_a["x_km"])
        dy = float(current_b["y_km"] - current_a["y_km"])
        dz = float(current_b["z_km"] - current_a["z_km"])
        dvx = float(current_b["vx_km_s"] - current_a["vx_km_s"])
        dvy = float(current_b["vy_km_s"] - current_a["vy_km_s"])
        dvz = float(current_b["vz_km_s"] - current_a["vz_km_s"])
        relative_speed = _relative_speed_km_s(
            float(tca_b["vx_km_s"] - tca_a["vx_km_s"]),
            float(tca_b["vy_km_s"] - tca_a["vy_km_s"]),
            float(tca_b["vz_km_s"] - tca_a["vz_km_s"]),
        )
        altitude_diff = abs(float(current_b["alt_km"] - current_a["alt_km"]))
        score = _risk_score(
            min_distance_km=min_distance,
            relative_speed_km_s=relative_speed,
            altitude_diff_km=altitude_diff,
            source_mode=str(source_status.get("mode", "sample")),
        )
        risk_tier = _risk_tier_from_score(score)
        if risk and risk_tier != risk:
            continue

        event = CollisionEvent(
            satellite_1=name_a,
            satellite_2=name_b,
            distance_km=round(min_distance, 3),
            min_distance_km=round(min_distance, 3),
            relative_speed_km_s=round(relative_speed, 4),
            altitude_band_match=altitude_diff <= settings.altitude_band_km,
            prediction_quality=_prediction_quality(str(source_status.get("mode", "sample"))),
            data_source=str(source_status.get("mode", "sample")),
            risk=risk_tier,
            timestamp=tca.isoformat().replace("+00:00", "Z"),
            dx=round(dx, 6),
            dy=round(dy, 6),
            dz=round(dz, 6),
            dvx=round(dvx, 6),
            dvy=round(dvy, 6),
            dvz=round(dvz, 6),
            current_distance_km=round(_distance_km(current_a, current_b), 6),
            altitude_diff_km=round(altitude_diff, 6),
        )
        output.append(event)

    output.sort(
        key=lambda item: (
            {"danger": 0, "warning": 1, "safe": 2}.get(item.risk, 3),
            item.min_distance_km,
            -item.relative_speed_km_s,
        )
    )
    if limit is not None:
        output = output[: max(1, int(limit))]

    _CONJUNCTION_CACHE.set(
        cache_key,
        [item.model_dump() for item in output],
        ttl_seconds=settings.conjunction_cache_ttl_seconds,
    )
    return output


def build_predict_rows_from_collisions(collisions: list[CollisionEvent]) -> list[dict[str, float]]:
    return [
        {
            "dx": event.dx,
            "dy": event.dy,
            "dz": event.dz,
            "dvx": event.dvx,
            "dvy": event.dvy,
            "dvz": event.dvz,
            "relative_speed_km_s": _relative_speed_km_s(event.dvx, event.dvy, event.dvz),
            "current_distance_km": event.current_distance_km,
            "altitude_diff_km": event.altitude_diff_km,
        }
        for event in collisions
    ]


def generate_training_dataframe(
    samples_per_pair: int = 12,
    offset_minutes: int = 10,
    refresh: bool = False,
) -> pd.DataFrame:
    satellite_entries, _ = _build_satellites(refresh=refresh)
    if len(satellite_entries) < 2:
        return pd.DataFrame(
            columns=[
                "satellite_1",
                "satellite_2",
                "sample_time",
                "dx",
                "dy",
                "dz",
                "dvx",
                "dvy",
                "dvz",
                "relative_speed_km_s",
                "current_distance_km",
                "altitude_diff_km",
                "label_min_distance_km",
                "label_risk_class",
            ]
        )

    base_time = _utc_now()
    rows: list[dict[str, Any]] = []
    for left, right in combinations(satellite_entries, 2):
        sat_a: EarthSatellite = left["satellite"]
        sat_b: EarthSatellite = right["satellite"]
        for idx in range(samples_per_pair):
            start_time = base_time + timedelta(minutes=idx * max(1, offset_minutes))
            current_a = _satellite_state(sat_a, start_time)
            current_b = _satellite_state(sat_b, start_time)

            min_distance = float("inf")
            for step_time in _future_times(start_time):
                step_a = _satellite_state(sat_a, step_time)
                step_b = _satellite_state(sat_b, step_time)
                min_distance = min(min_distance, _distance_km(step_a, step_b))

            dx = float(current_b["x_km"] - current_a["x_km"])
            dy = float(current_b["y_km"] - current_a["y_km"])
            dz = float(current_b["z_km"] - current_a["z_km"])
            dvx = float(current_b["vx_km_s"] - current_a["vx_km_s"])
            dvy = float(current_b["vy_km_s"] - current_a["vy_km_s"])
            dvz = float(current_b["vz_km_s"] - current_a["vz_km_s"])
            relative_speed = _relative_speed_km_s(dvx, dvy, dvz)
            current_distance = _distance_km(current_a, current_b)
            altitude_diff = abs(float(current_b["alt_km"] - current_a["alt_km"]))

            rows.append(
                {
                    "satellite_1": left["name"],
                    "satellite_2": right["name"],
                    "sample_time": start_time.isoformat().replace("+00:00", "Z"),
                    "dx": dx,
                    "dy": dy,
                    "dz": dz,
                    "dvx": dvx,
                    "dvy": dvy,
                    "dvz": dvz,
                    "relative_speed_km_s": relative_speed,
                    "current_distance_km": current_distance,
                    "altitude_diff_km": altitude_diff,
                    "label_min_distance_km": float(min_distance),
                    "label_risk_class": _risk_tier_from_score(
                        _risk_score(
                            min_distance_km=min_distance,
                            relative_speed_km_s=relative_speed,
                            altitude_diff_km=altitude_diff,
                            source_mode="live",
                        )
                    ),
                }
            )

    return pd.DataFrame(rows)
