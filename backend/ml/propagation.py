from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from skyfield.api import EarthSatellite, load, wgs84

_TIMESCALE = load.timescale()


@dataclass(frozen=True)
class PropagationState:
    timestamp: str
    lat: float
    lon: float
    alt_km: float
    x_km: float
    y_km: float
    z_km: float
    vx_km_s: float
    vy_km_s: float
    vz_km_s: float


class Propagator(Protocol):
    def propagate_many(self, timestamps: list[datetime]) -> list[PropagationState]:
        ...


class SkyfieldPropagator:
    def __init__(self, name: str, line1: str, line2: str) -> None:
        self.name = name
        self._satellite = EarthSatellite(line1, line2, name, _TIMESCALE)

    def propagate_many(self, timestamps: list[datetime]) -> list[PropagationState]:
        states: list[PropagationState] = []
        for timestamp in timestamps:
            t = _TIMESCALE.from_datetime(timestamp)
            geocentric = self._satellite.at(t)
            subpoint = wgs84.subpoint(geocentric)
            position = geocentric.position.km
            velocity = geocentric.velocity.km_per_s
            states.append(
                PropagationState(
                    timestamp=timestamp.isoformat().replace("+00:00", "Z"),
                    lat=float(subpoint.latitude.degrees),
                    lon=float(subpoint.longitude.degrees),
                    alt_km=float(subpoint.elevation.km),
                    x_km=float(position[0]),
                    y_km=float(position[1]),
                    z_km=float(position[2]),
                    vx_km_s=float(velocity[0]),
                    vy_km_s=float(velocity[1]),
                    vz_km_s=float(velocity[2]),
                )
            )
        return states


def build_propagator(name: str, line1: str, line2: str) -> Propagator:
    return SkyfieldPropagator(name=name, line1=line1, line2=line2)
