from dataclasses import dataclass

TIME_STEP_SECONDS: int = 300
PREDICTION_HOURS: int = 6
DANGER_DISTANCE_KM: float = 10.0
WARNING_DISTANCE_KM: float = 50.0
ALTITUDE_BAND_KM: float = 25.0
HIGH_RELATIVE_SPEED_KM_S: float = 12.0
MODERATE_RELATIVE_SPEED_KM_S: float = 8.0

LIVE_FETCH_TTL_SECONDS: int = 1800
CONJUNCTION_CACHE_TTL_SECONDS: int = 45
HISTORY_MAX_EVENTS: int = 500

CELESTRAK_BASE_URL: str = "https://celestrak.org/NORAD/elements/gp.php"
CELESTRAK_DEFAULT_GROUP: str = "stations"
CELESTRAK_DEFAULT_CATNR_LIST: tuple[int, ...] = (25544, 20580, 25338, 25994, 27424, 44713)
LIVE_DATA_CACHE_FILE: str = "models\\live_data_cache.json"
CONJUNCTION_HISTORY_FILE: str = "models\\conjunction_history.json"


@dataclass(frozen=True)
class Settings:
    api_title: str = "Satellite Collision Predictor API"
    api_version: str = "1.0.0"
    simulation_step_seconds: int = TIME_STEP_SECONDS
    simulation_horizon_hours: int = PREDICTION_HOURS
    danger_distance_km: float = DANGER_DISTANCE_KM
    warning_distance_km: float = WARNING_DISTANCE_KM
    altitude_band_km: float = ALTITUDE_BAND_KM
    high_relative_speed_km_s: float = HIGH_RELATIVE_SPEED_KM_S
    moderate_relative_speed_km_s: float = MODERATE_RELATIVE_SPEED_KM_S
    live_fetch_ttl_seconds: int = LIVE_FETCH_TTL_SECONDS
    conjunction_cache_ttl_seconds: int = CONJUNCTION_CACHE_TTL_SECONDS
    history_max_events: int = HISTORY_MAX_EVENTS
    celestrak_base_url: str = CELESTRAK_BASE_URL
    celestrak_default_group: str = CELESTRAK_DEFAULT_GROUP
    celestrak_default_catnr_list: tuple[int, ...] = CELESTRAK_DEFAULT_CATNR_LIST
    live_data_cache_file: str = LIVE_DATA_CACHE_FILE
    conjunction_history_file: str = CONJUNCTION_HISTORY_FILE
    model_file: str = "models\\collision_model.keras"
    normalizer_file: str = "models\\normalizer_stats.json"
    ml_enabled: bool = True


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
    if distance_km < DANGER_DISTANCE_KM:
        return "danger"
    if distance_km < WARNING_DISTANCE_KM:
        return "warning"
    return "safe"
