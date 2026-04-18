from __future__ import annotations

import asyncio
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status

from core.auth import (
    authenticate_user,
    decode_access_token,
    register_user,
    require_authenticated_user,
    token_response,
)
from core.cache import CacheBackend
from core.config import settings
from ml.data_pipeline import build_dashboard_snapshot, build_predict_rows_from_collisions
from ml.predictor import OptionalMLPredictor
from ml.schemas import (
    AuthTokenResponse,
    DashboardSnapshot,
    HealthResponse,
    CollisionEvent,
    MLPrediction,
    MLStatus,
    SatelliteSummary,
    SourceStatusResponse,
    UserRegistrationRequest,
    UserRegistrationResponse,
)

router = APIRouter()
cache = CacheBackend()


def _cached_dashboard_snapshot() -> DashboardSnapshot:
    cached = cache.get("dashboard-snapshot")
    if cached is not None:
        return DashboardSnapshot.model_validate(cached)

    snapshot = build_dashboard_snapshot()
    cache.set("dashboard-snapshot", snapshot.model_dump(mode="json"), ttl_seconds=settings.dashboard_cache_ttl_seconds)
    return snapshot


async def _parse_token_request(request: Request) -> tuple[str, str]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()

    if content_type == "application/x-www-form-urlencoded":
        raw = (await request.body()).decode("utf-8")
        parsed = parse_qs(raw)
        username = (parsed.get("username") or [""])[0]
        password = (parsed.get("password") or [""])[0]
    else:
        payload = await request.json()
        username = str(payload.get("username", ""))
        password = str(payload.get("password", ""))

    username = username.strip()
    password = password.strip()
    if not username or not password:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Username and password required.")
    return username, password


def _prediction_payload() -> list[MLPrediction]:
    snapshot = _cached_dashboard_snapshot()
    collisions = snapshot.collisions
    predictor = OptionalMLPredictor()

    if predictor.available:
        results = predictor.predict_distances(build_predict_rows_from_collisions(collisions))
        predictions = [
            MLPrediction(
                id=event.id,
                satellite_1=event.satellite_1,
                satellite_2=event.satellite_2,
                predicted_min_distance_km=round(float(result["predicted_distance_km"]), 4),
                predicted_risk=predictor.distance_to_risk(float(result["predicted_distance_km"])),
                collision_probability=round(
                    predictor.distance_to_probability(
                        float(result["predicted_distance_km"]),
                        float(result["uncertainty_km"]),
                    ),
                    6,
                ),
                uncertainty_km=round(float(result["uncertainty_km"]), 4),
                prediction_source=result["prediction_source"],  # type: ignore[arg-type]
                model_name=str(result["model_name"]),
                ml_available=True,
            )
            for event, result in zip(collisions, results)
        ]
    else:
        predictions = [
            MLPrediction(
                id=event.id,
                satellite_1=event.satellite_1,
                satellite_2=event.satellite_2,
                predicted_min_distance_km=event.distance_km,
                predicted_risk=event.risk,
                collision_probability=event.collision_probability_proxy,
                uncertainty_km=0.0,
                prediction_source="heuristic-fallback",
                model_name="heuristic",
                ml_available=False,
            )
            for event in collisions
        ]

    return predictions


def _source_mode() -> str:
    return "sample"


def _normalized_satellites(limit: int | None = None) -> list[SatelliteSummary]:
    satellites = [
        item.model_copy(update={"source_type": _source_mode()})
        for item in _cached_dashboard_snapshot().satellites
    ]
    return satellites[:limit] if limit is not None else satellites


def _normalized_collisions(limit: int | None = None) -> list[CollisionEvent]:
    collisions = [
        item.model_copy(
            update={
                "min_distance_km": item.distance_km,
                "relative_speed_km_s": item.relative_velocity_km_s,
                "data_source": _source_mode(),
            }
        )
        for item in _cached_dashboard_snapshot().collisions
    ]
    return collisions[:limit] if limit is not None else collisions


@router.post("/auth/register", response_model=UserRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_operator(payload: UserRegistrationRequest) -> UserRegistrationResponse:
    try:
        user = register_user(payload.username, payload.password, payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserRegistrationResponse(username=user.username, role=user.role)


@router.post("/auth/token", response_model=AuthTokenResponse)
async def issue_token(request: Request) -> AuthTokenResponse:
    username, password = await _parse_token_request(request)
    user = authenticate_user(username, password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    return AuthTokenResponse(**token_response(user))


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    cache_health = cache.health()
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        auth_required=settings.auth_required,
        cache_backend=cache_health.backend,
        ml_enabled=settings.ml_enabled,
        websocket_refresh_seconds=settings.websocket_refresh_seconds,
        source_status={"mode": _source_mode(), "cache_backend": cache_health.backend},
    )


@router.get("/dashboard", response_model=DashboardSnapshot)
def get_dashboard() -> DashboardSnapshot:
    return _cached_dashboard_snapshot()


@router.get("/satellites", response_model=list[SatelliteSummary])
def get_satellites(limit: int | None = Query(default=None, ge=1, le=500)) -> list[SatelliteSummary]:
    return _normalized_satellites(limit)


@router.get("/collisions", response_model=list[CollisionEvent])
def get_collisions(limit: int | None = Query(default=None, ge=1, le=500)) -> list[CollisionEvent]:
    return _normalized_collisions(limit)


@router.get("/top-risks", response_model=list[CollisionEvent])
def get_top_risks(limit: int = Query(default=5, ge=1, le=100)) -> list[CollisionEvent]:
    return _normalized_collisions(limit)


@router.get("/history")
def get_history(limit: int = Query(default=10, ge=1, le=200)) -> dict[str, object]:
    snapshot = _cached_dashboard_snapshot()
    return {
        "generated_at": snapshot.generated_at,
        "events": [item.model_dump(mode="json") for item in _normalized_collisions(limit)],
    }


@router.get("/source-status", response_model=SourceStatusResponse)
def get_source_status() -> SourceStatusResponse:
    cache_health = cache.health()
    return SourceStatusResponse(
        mode=_source_mode(),  # type: ignore[arg-type]
        cache_backend=cache_health.backend,
        propagation_mode=settings.propagation_mode,
    )


@router.get("/ml/status", response_model=MLStatus)
def get_ml_status(_: object = Depends(require_authenticated_user)) -> MLStatus:
    predictor = OptionalMLPredictor()
    return MLStatus(**predictor.status())


@router.get("/predict", response_model=list[MLPrediction])
def get_predictions(
    _: object = Depends(require_authenticated_user),
    limit: int | None = Query(default=None, ge=1, le=500),
) -> list[MLPrediction]:
    cache_key = "ml-predictions"
    cached = cache.get(cache_key)
    if cached is not None:
        predictions = [MLPrediction.model_validate(item) for item in cached]
        return predictions[:limit] if limit is not None else predictions

    predictions = _prediction_payload()
    cache.set(cache_key, [item.model_dump(mode="json") for item in predictions], ttl_seconds=settings.predictions_cache_ttl_seconds)
    return predictions[:limit] if limit is not None else predictions


@router.websocket("/ws/alerts")
async def alerts_socket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if settings.auth_required:
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        try:
            decode_access_token(token)
        except HTTPException:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    await websocket.accept()
    try:
        while True:
            snapshot = _cached_dashboard_snapshot()
            await websocket.send_json(
                {
                    "type": "alerts",
                    "generated_at": snapshot.generated_at,
                    "collisions": [item.model_dump(mode="json") for item in snapshot.collisions[:8]],
                }
            )
            await asyncio.sleep(settings.websocket_refresh_seconds)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/system-status")
async def system_status_socket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if settings.auth_required:
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        try:
            decode_access_token(token)
        except HTTPException:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    await websocket.accept()
    try:
        while True:
            predictor = OptionalMLPredictor()
            snapshot = _cached_dashboard_snapshot()
            await websocket.send_json(
                {
                    "type": "system-status",
                    "generated_at": snapshot.generated_at,
                    "tracked_objects": len(snapshot.satellites),
                    "collision_events": len(snapshot.collisions),
                    "ml_available": predictor.available,
                    "source": predictor.status()["source"],
                }
            )
            await asyncio.sleep(settings.websocket_refresh_seconds)
    except WebSocketDisconnect:
        return
