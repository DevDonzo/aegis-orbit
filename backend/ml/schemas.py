from pydantic import BaseModel


class SatellitePosition(BaseModel):
    name: str
    norad_id: str
    lat: float
    lon: float
    alt_km: float
    x_km: float
    y_km: float
    z_km: float
    risk: str
    source_type: str
    fetched_at: str


class SatelliteSummary(BaseModel):
    name: str
    norad_id: str
    lat: float
    lon: float
    alt_km: float
    risk: str
    source_type: str
    fetched_at: str


class CollisionEvent(BaseModel):
    satellite_1: str
    satellite_2: str
    distance_km: float  # backward-compatible alias of min_distance_km
    min_distance_km: float
    relative_speed_km_s: float
    altitude_band_match: bool
    prediction_quality: str
    data_source: str
    risk: str
    timestamp: str
    dx: float
    dy: float
    dz: float
    dvx: float
    dvy: float
    dvz: float
    current_distance_km: float
    altitude_diff_km: float


class CollisionSummary(BaseModel):
    satellite_1: str
    satellite_2: str
    distance_km: float
    min_distance_km: float
    relative_speed_km_s: float
    risk: str
    timestamp: str
    data_source: str
    prediction_quality: str
    ml_available: bool
    ml_predicted_min_distance_km: float | None = None
    ml_risk_score: float | None = None


class MLPrediction(BaseModel):
    satellite_1: str
    satellite_2: str
    predicted_min_distance_km: float
    predicted_risk: str
    ml_available: bool


class SourceStatus(BaseModel):
    mode: str
    live_available: bool
    cache_available: bool
    last_fetch_at: str | None
    note: str


class HistoryResponse(BaseModel):
    events: list[CollisionSummary]
