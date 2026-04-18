from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["safe", "warning", "danger"]
PredictionSource = Literal["selected-model", "ensemble", "heuristic-fallback"]


class TelemetryPoint(BaseModel):
    timestamp: str
    lat: float
    lon: float
    alt_km: float
    velocity_km_s: float


class VectorEnvelope(BaseModel):
    lat: float
    lon: float
    alt_km: float


class SatelliteSummary(BaseModel):
    id: str
    name: str
    norad_id: str
    status: Literal["active", "inactive", "maneuvering"] = "active"
    risk: RiskLevel
    risk_score: float
    lat: float
    lon: float
    alt_km: float
    velocity_km_s: float
    inclination_deg: float
    orbital_period_minutes: float
    updated_at: str
    telemetry: list[TelemetryPoint]


class CollisionEvent(BaseModel):
    id: str
    satellite_1: str
    satellite_2: str
    distance_km: float
    current_distance_km: float
    risk: RiskLevel
    risk_score: float
    timestamp: str
    lead_time_minutes: float
    relative_velocity_km_s: float
    collision_probability_proxy: float
    risk_zone_radius_km: float
    vector_start: VectorEnvelope
    vector_end: VectorEnvelope
    dx: float
    dy: float
    dz: float
    dvx: float
    dvy: float
    dvz: float
    altitude_diff_km: float
    current_altitude_primary_km: float
    current_altitude_secondary_km: float


class MLPrediction(BaseModel):
    id: str
    satellite_1: str
    satellite_2: str
    predicted_min_distance_km: float
    predicted_risk: RiskLevel
    collision_probability: float
    uncertainty_km: float
    prediction_source: PredictionSource
    model_name: str


class MLStatus(BaseModel):
    available: bool
    source: PredictionSource
    model_path: str
    metadata: dict[str, Any] | None
    candidate_models: list[str] = Field(default_factory=list)
    selected_model: str | None = None


class DashboardSnapshot(BaseModel):
    generated_at: str
    propagation_mode: str
    satellites: list[SatelliteSummary]
    collisions: list[CollisionEvent]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    environment: str
    auth_required: bool
    cache_backend: str
    ml_enabled: bool
    websocket_refresh_seconds: int


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int
    username: str
    role: str


class UserRegistrationRequest(BaseModel):
    username: str
    password: str
    role: Literal["operator", "analyst", "viewer"] = "operator"


class UserRegistrationResponse(BaseModel):
    username: str
    role: str
    created: bool = True
