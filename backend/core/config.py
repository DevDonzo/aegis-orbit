from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

TIME_STEP_SECONDS: int = 300
PREDICTION_HOURS: int = 6
DANGER_DISTANCE_KM: float = 10.0
WARNING_DISTANCE_KM: float = 50.0

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    values = [value.strip() for value in raw.split(",")]
    return [value for value in values if value]


@dataclass(frozen=True)
class Settings:
    api_title: str = os.getenv("SAT_API_TITLE", "Satellite Collision Predictor API")
    api_version: str = os.getenv("SAT_API_VERSION", "2.0.0")
    environment: Literal["development", "staging", "production"] = os.getenv(
        "SAT_ENVIRONMENT", "development"
    )  # type: ignore[assignment]
    simulation_step_seconds: int = field(default_factory=lambda: max(60, _env_int("SAT_TIME_STEP_SECONDS", TIME_STEP_SECONDS)))
    simulation_horizon_hours: int = field(
        default_factory=lambda: max(1, _env_int("SAT_PREDICTION_HOURS", PREDICTION_HOURS))
    )
    danger_distance_km: float = field(default_factory=lambda: _env_float("SAT_DANGER_DISTANCE_KM", DANGER_DISTANCE_KM))
    warning_distance_km: float = field(
        default_factory=lambda: _env_float("SAT_WARNING_DISTANCE_KM", WARNING_DISTANCE_KM)
    )
    model_file: str = os.getenv("SAT_MODEL_FILE", str(PROJECT_ROOT / "models" / "collision_model.joblib"))
    model_metadata_file: str = os.getenv(
        "SAT_MODEL_METADATA_FILE", str(PROJECT_ROOT / "models" / "collision_model.meta.json")
    )
    user_store_file: str = os.getenv("SAT_USER_STORE_FILE", str(PROJECT_ROOT / "models" / "users.json"))
    ml_enabled: bool = _env_bool("SAT_ML_ENABLED", True)
    auth_required: bool = _env_bool("SAT_AUTH_REQUIRED", False)
    jwt_secret: str = os.getenv("SAT_JWT_SECRET", "change-me-before-production")
    jwt_algorithm: str = "HS256"
    token_expiration_minutes: int = field(default_factory=lambda: max(5, _env_int("SAT_TOKEN_EXP_MINUTES", 45)))
    demo_username: str = os.getenv("SAT_DEMO_USERNAME", "operator")
    demo_password: str = os.getenv("SAT_DEMO_PASSWORD", "orbit-demo-2026")
    demo_role: str = os.getenv("SAT_DEMO_ROLE", "operator")
    satellites_cache_ttl_seconds: int = field(default_factory=lambda: max(5, _env_int("SAT_SATELLITES_CACHE_TTL", 20)))
    collisions_cache_ttl_seconds: int = field(default_factory=lambda: max(5, _env_int("SAT_COLLISIONS_CACHE_TTL", 20)))
    predictions_cache_ttl_seconds: int = field(default_factory=lambda: max(5, _env_int("SAT_PREDICTIONS_CACHE_TTL", 30)))
    dashboard_cache_ttl_seconds: int = field(default_factory=lambda: max(5, _env_int("SAT_DASHBOARD_CACHE_TTL", 15)))
    websocket_refresh_seconds: int = field(default_factory=lambda: max(2, _env_int("SAT_WS_REFRESH_SECONDS", 6)))
    cache_url: str | None = os.getenv("SAT_REDIS_URL")
    cache_namespace: str = os.getenv("SAT_CACHE_NAMESPACE", "scp")
    frontend_origins: list[str] = field(
        default_factory=lambda: _env_list(
            "SAT_FRONTEND_ORIGINS",
            [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ],
        )
    )
    propagation_mode: Literal["skyfield"] = "skyfield"


SAMPLE_TLES: list[dict[str, str]] = [
    {
        "name": "ISS (ZARYA)",
        "line1": "1 25544U 98067A   26099.56018519  .00016717  00000+0  30207-3 0  9993",
        "line2": "2 25544  51.6412  84.8135 0003393  79.7696  22.6530 15.50021028447946",
    },
    {
        "name": "HUBBLE",
        "line1": "1 20580U 90037B   26099.30715278  .00001368  00000+0  70764-4 0  9996",
        "line2": "2 20580  28.4693 209.6719 0002349  28.8030 331.3154 15.09343824513356",
    },
    {
        "name": "NOAA 15",
        "line1": "1 25338U 98030A   26099.53446065  .00000077  00000+0  70181-4 0  9996",
        "line2": "2 25338  98.7485 126.8179 0011710 161.4428 198.7346 14.25831498318259",
    },
    {
        "name": "TERRA",
        "line1": "1 25994U 99068A   26099.51284311  .00000093  00000+0  32922-4 0  9992",
        "line2": "2 25994  98.2054 177.0857 0001128  93.3299 266.8005 14.57109192410702",
    },
    {
        "name": "AQUA",
        "line1": "1 27424U 02022A   26099.48803241  .00000103  00000+0  35748-4 0  9993",
        "line2": "2 27424  98.2138 176.5090 0001089 102.3235 257.8065 14.57124007176366",
    },
    {
        "name": "STARLINK-1007",
        "line1": "1 44713U 19074A   26099.54170139  .00001841  00000+0  13761-3 0  9999",
        "line2": "2 44713  53.0524  15.8435 0001493  86.6912 273.4248 15.06405299363948",
    },
]


settings = Settings()


def classify_risk(distance_km: float) -> str:
    if distance_km < settings.danger_distance_km:
        return "danger"
    if distance_km < settings.warning_distance_km:
        return "warning"
    return "safe"


def distance_to_risk_score(distance_km: float) -> float:
    clamped = max(0.0, float(distance_km))
    if clamped <= settings.danger_distance_km:
        return 1.0
    span = max(settings.warning_distance_km - settings.danger_distance_km, 1.0)
    score = 1.0 - ((clamped - settings.danger_distance_km) / span)
    return round(max(0.0, min(1.0, score)), 6)
