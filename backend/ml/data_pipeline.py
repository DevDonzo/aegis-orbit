from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import combinations
from math import exp
from typing import Any

import numpy as np
import pandas as pd

from core.config import SAMPLE_TLES, classify_risk, distance_to_risk_score, settings
from ml.propagation import PropagationState, build_propagator
from ml.schemas import CollisionEvent, DashboardSnapshot, SatelliteSummary, TelemetryPoint, VectorEnvelope


@dataclass(frozen=True)
class SatelliteTrack:
    id: str
    name: str
    norad_id: str
    inclination_deg: float
    orbital_period_minutes: float
    states: list[PropagationState]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _future_times(start: datetime) -> list[datetime]:
    total_seconds = settings.simulation_horizon_hours * 3600
    steps = max(1, int(total_seconds // settings.simulation_step_seconds))
    return [start + timedelta(seconds=index * settings.simulation_step_seconds) for index in range(steps + 1)]


def _parse_norad_id(line1: str) -> str:
    return line1[2:7].strip()


def _parse_inclination_deg(line2: str) -> float:
    try:
        return float(line2.split()[2])
    except Exception:
        return 0.0


def _parse_orbital_period_minutes(line2: str) -> float:
    try:
        mean_motion = float(line2.split()[-1])
    except Exception:
        return 0.0
    if mean_motion <= 0:
        return 0.0
    return round((24 * 60) / mean_motion, 3)


def _distance_km(state_a: PropagationState, state_b: PropagationState) -> float:
    return float(
        np.linalg.norm(
            np.array([state_a.x_km, state_a.y_km, state_a.z_km], dtype=float)
            - np.array([state_b.x_km, state_b.y_km, state_b.z_km], dtype=float)
        )
    )


def _relative_velocity_km_s(state_a: PropagationState, state_b: PropagationState) -> float:
    return float(
        np.linalg.norm(
            np.array([state_a.vx_km_s, state_a.vy_km_s, state_a.vz_km_s], dtype=float)
            - np.array([state_b.vx_km_s, state_b.vy_km_s, state_b.vz_km_s], dtype=float)
        )
    )


def _collision_probability(distance_km: float, relative_velocity_km_s: float, uncertainty_km: float = 0.0) -> float:
    distance_term = exp(-max(0.0, distance_km) / max(18.0, 42.0 + uncertainty_km * 6.0))
    velocity_term = min(1.25, max(0.45, relative_velocity_km_s / 8.0))
    return round(max(0.0, min(1.0, distance_term * velocity_term)), 6)


def _build_tracks(timestamps: list[datetime]) -> list[SatelliteTrack]:
    tracks: list[SatelliteTrack] = []
    for entry in SAMPLE_TLES:
        propagator = build_propagator(name=entry["name"], line1=entry["line1"], line2=entry["line2"])
        states = propagator.propagate_many(timestamps)
        if not states:
            continue
        tracks.append(
            SatelliteTrack(
                id=entry["name"],
                name=entry["name"],
                norad_id=_parse_norad_id(entry["line1"]),
                inclination_deg=_parse_inclination_deg(entry["line2"]),
                orbital_period_minutes=_parse_orbital_period_minutes(entry["line2"]),
                states=states,
            )
        )
    return tracks


def build_current_satellite_positions() -> list[SatelliteSummary]:
    tracks = _build_tracks(_future_times(_utc_now()))
    if not tracks:
        return []

    summaries: list[SatelliteSummary] = []
    for primary in tracks:
        current = primary.states[0]
        nearest_distance = min(
            (_distance_km(current, secondary.states[0]) for secondary in tracks if secondary.id != primary.id),
            default=float("inf"),
        )
        summaries.append(
            SatelliteSummary(
                id=primary.id,
                name=primary.name,
                norad_id=primary.norad_id,
                risk=classify_risk(nearest_distance),
                risk_score=distance_to_risk_score(nearest_distance),
                lat=round(current.lat, 6),
                lon=round(current.lon, 6),
                alt_km=round(current.alt_km, 3),
                velocity_km_s=round(
                    float(np.linalg.norm([current.vx_km_s, current.vy_km_s, current.vz_km_s])),
                    4,
                ),
                inclination_deg=primary.inclination_deg,
                orbital_period_minutes=primary.orbital_period_minutes,
                updated_at=current.timestamp,
                telemetry=[
                    TelemetryPoint(
                        timestamp=state.timestamp,
                        lat=round(state.lat, 6),
                        lon=round(state.lon, 6),
                        alt_km=round(state.alt_km, 3),
                        velocity_km_s=round(
                            float(np.linalg.norm([state.vx_km_s, state.vy_km_s, state.vz_km_s])),
                            4,
                        ),
                    )
                    for state in primary.states
                ],
            )
        )

    return sorted(summaries, key=lambda item: (-item.risk_score, item.name))


def compute_collision_candidates() -> list[CollisionEvent]:
    timestamps = _future_times(_utc_now())
    tracks = _build_tracks(timestamps)
    collisions: list[CollisionEvent] = []

    for primary, secondary in combinations(tracks, 2):
        current_primary = primary.states[0]
        current_secondary = secondary.states[0]
        current_distance = _distance_km(current_primary, current_secondary)

        min_index = 0
        min_distance = float("inf")
        for index, (state_a, state_b) in enumerate(zip(primary.states, secondary.states)):
            distance = _distance_km(state_a, state_b)
            if distance < min_distance:
                min_distance = distance
                min_index = index

        closest_primary = primary.states[min_index]
        closest_secondary = secondary.states[min_index]
        relative_velocity = _relative_velocity_km_s(current_primary, current_secondary)
        lead_minutes = min_index * settings.simulation_step_seconds / 60
        risk = classify_risk(min_distance)
        collisions.append(
            CollisionEvent(
                id=f"{primary.id}:{secondary.id}:{min_index}",
                satellite_1=primary.id,
                satellite_2=secondary.id,
                distance_km=round(min_distance, 4),
                current_distance_km=round(current_distance, 4),
                risk=risk,
                risk_score=distance_to_risk_score(min_distance),
                timestamp=closest_primary.timestamp,
                lead_time_minutes=round(lead_minutes, 3),
                relative_velocity_km_s=round(relative_velocity, 4),
                collision_probability_proxy=_collision_probability(min_distance, relative_velocity),
                risk_zone_radius_km=round(max(18.0, min(140.0, min_distance * 7.5 + 12.0)), 3),
                vector_start=VectorEnvelope(
                    lat=round(closest_primary.lat, 6),
                    lon=round(closest_primary.lon, 6),
                    alt_km=round(closest_primary.alt_km, 3),
                ),
                vector_end=VectorEnvelope(
                    lat=round(closest_secondary.lat, 6),
                    lon=round(closest_secondary.lon, 6),
                    alt_km=round(closest_secondary.alt_km, 3),
                ),
                dx=round(current_secondary.x_km - current_primary.x_km, 6),
                dy=round(current_secondary.y_km - current_primary.y_km, 6),
                dz=round(current_secondary.z_km - current_primary.z_km, 6),
                dvx=round(current_secondary.vx_km_s - current_primary.vx_km_s, 6),
                dvy=round(current_secondary.vy_km_s - current_primary.vy_km_s, 6),
                dvz=round(current_secondary.vz_km_s - current_primary.vz_km_s, 6),
                altitude_diff_km=round(abs(current_secondary.alt_km - current_primary.alt_km), 6),
                current_altitude_primary_km=round(current_primary.alt_km, 6),
                current_altitude_secondary_km=round(current_secondary.alt_km, 6),
            )
        )

    collisions.sort(key=lambda item: (-item.risk_score, -item.collision_probability_proxy, item.distance_km))
    return collisions


def build_predict_rows_from_collisions(collisions: list[CollisionEvent]) -> list[dict[str, float]]:
    return [
        {
            "dx": event.dx,
            "dy": event.dy,
            "dz": event.dz,
            "dvx": event.dvx,
            "dvy": event.dvy,
            "dvz": event.dvz,
            "current_distance_km": event.current_distance_km,
            "altitude_diff_km": event.altitude_diff_km,
            "lead_time_minutes": event.lead_time_minutes,
        }
        for event in collisions
    ]


def build_dashboard_snapshot() -> DashboardSnapshot:
    satellites = build_current_satellite_positions()
    collisions = compute_collision_candidates()
    return DashboardSnapshot(
        generated_at=_utc_now().isoformat().replace("+00:00", "Z"),
        propagation_mode=settings.propagation_mode,
        satellites=satellites,
        collisions=collisions,
    )


def generate_training_dataframe(samples_per_pair: int = 16, offset_minutes: int = 15) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    base_time = _utc_now()

    for sample_index in range(samples_per_pair):
        timestamps = _future_times(base_time + timedelta(minutes=sample_index * offset_minutes))
        tracks = _build_tracks(timestamps)
        for primary, secondary in combinations(tracks, 2):
            current_primary = primary.states[0]
            current_secondary = secondary.states[0]
            min_index = 0
            min_distance = float("inf")

            for index, (state_a, state_b) in enumerate(zip(primary.states, secondary.states)):
                distance = _distance_km(state_a, state_b)
                if distance < min_distance:
                    min_distance = distance
                    min_index = index

            rows.append(
                {
                    "dx": current_secondary.x_km - current_primary.x_km,
                    "dy": current_secondary.y_km - current_primary.y_km,
                    "dz": current_secondary.z_km - current_primary.z_km,
                    "dvx": current_secondary.vx_km_s - current_primary.vx_km_s,
                    "dvy": current_secondary.vy_km_s - current_primary.vy_km_s,
                    "dvz": current_secondary.vz_km_s - current_primary.vz_km_s,
                    "current_distance_km": _distance_km(current_primary, current_secondary),
                    "altitude_diff_km": abs(current_secondary.alt_km - current_primary.alt_km),
                    "lead_time_minutes": min_index * settings.simulation_step_seconds / 60,
                    "label_min_distance_km": min_distance,
                    "sample_time_utc": current_primary.timestamp,
                    "tca_time_utc": primary.states[min_index].timestamp,
                }
            )

    return pd.DataFrame(rows)
