from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Query

from core.history import history_store
from ml.data_pipeline import (
    build_current_satellite_positions,
    build_predict_rows_from_collisions,
    compute_collision_candidates,
    get_source_status,
)
from ml.predictor import OptionalMLPredictor
from ml.schemas import CollisionSummary, HistoryResponse, MLPrediction, SatelliteSummary, SourceStatus

router = APIRouter()


def _to_collision_summary(
    event,
    predictor: OptionalMLPredictor,
    feature_row: dict[str, float],
) -> CollisionSummary:
    ml_fields = predictor.enrich_collision(feature_row)
    return CollisionSummary(
        satellite_1=event.satellite_1,
        satellite_2=event.satellite_2,
        distance_km=float(event.distance_km),
        min_distance_km=float(event.min_distance_km),
        relative_speed_km_s=float(event.relative_speed_km_s),
        risk=event.risk,
        timestamp=event.timestamp,
        data_source=event.data_source,
        prediction_quality=event.prediction_quality,
        ml_available=bool(ml_fields.get("ml_available", False)),
        ml_predicted_min_distance_km=ml_fields.get("ml_predicted_min_distance_km"),
        ml_risk_score=ml_fields.get("ml_risk_score"),
    )


@router.get("/health")
def health() -> dict[str, object]:
    predictor = OptionalMLPredictor()
    return {
        "status": "ok",
        "server_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ml_available": predictor.available,
        "source_status": get_source_status(),
    }


@router.get("/source-status", response_model=SourceStatus)
def source_status() -> SourceStatus:
    status = get_source_status()
    return SourceStatus.model_validate(status)


@router.get("/satellites", response_model=list[SatelliteSummary])
def get_satellites(
    refresh: Annotated[bool, Query(description="Force live data refresh")] = False,
) -> list[SatelliteSummary]:
    positions = build_current_satellite_positions(refresh=refresh)
    return [
        SatelliteSummary(
            name=item.name,
            norad_id=item.norad_id,
            lat=float(item.lat),
            lon=float(item.lon),
            alt_km=float(item.alt_km),
            risk=item.risk,
            source_type=item.source_type,
            fetched_at=item.fetched_at,
        )
        for item in positions
    ]


@router.get("/collisions", response_model=list[CollisionSummary])
def get_collisions(
    horizon_hours: Annotated[int | None, Query(ge=1, le=48)] = None,
    limit: Annotated[int | None, Query(ge=1, le=500)] = None,
    risk: Annotated[str | None, Query(pattern="^(danger|warning|safe)$")] = None,
    satellite: Annotated[str | None, Query(description="Filter by satellite name or NORAD text")] = None,
    refresh: Annotated[bool, Query(description="Force live refresh and cache bypass")] = False,
) -> list[CollisionSummary]:
    predictor = OptionalMLPredictor()
    events = compute_collision_candidates(
        horizon_hours=horizon_hours,
        limit=limit,
        risk=risk,
        name_filter=satellite,
        refresh=refresh,
    )
    feature_rows = build_predict_rows_from_collisions(events)
    summaries = [
        _to_collision_summary(event=event, predictor=predictor, feature_row=row)
        for event, row in zip(events, feature_rows)
    ]
    history_store.add_events([item.model_dump() for item in summaries])
    return summaries


@router.get("/top-risks", response_model=list[CollisionSummary])
def get_top_risks(
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    refresh: Annotated[bool, Query(description="Force live refresh")] = False,
    horizon_hours: Annotated[int | None, Query(ge=1, le=48)] = None,
) -> list[CollisionSummary]:
    predictor = OptionalMLPredictor()
    events = compute_collision_candidates(
        horizon_hours=horizon_hours,
        limit=limit,
        risk=None,
        name_filter=None,
        refresh=refresh,
    )
    feature_rows = build_predict_rows_from_collisions(events)
    ranked = [
        _to_collision_summary(event=event, predictor=predictor, feature_row=row)
        for event, row in zip(events, feature_rows)
    ]
    ranked.sort(
        key=lambda item: (
            {"danger": 0, "warning": 1, "safe": 2}.get(item.risk, 3),
            item.min_distance_km,
            -item.relative_speed_km_s,
        )
    )
    top = ranked[:limit]
    history_store.add_events([item.model_dump() for item in top])
    return top


@router.get("/history", response_model=HistoryResponse)
def get_history(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    risk: Annotated[str | None, Query(pattern="^(danger|warning|safe)$")] = None,
) -> HistoryResponse:
    events = [
        CollisionSummary.model_validate(item)
        for item in history_store.get_recent(limit=limit, risk=risk)
    ]
    return HistoryResponse(events=events)


@router.get("/predict", response_model=list[MLPrediction])
def get_optional_predictions(
    horizon_hours: Annotated[int | None, Query(ge=1, le=48)] = None,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    refresh: Annotated[bool, Query(description="Force live refresh")] = False,
) -> list[MLPrediction]:
    predictor = OptionalMLPredictor()
    events = compute_collision_candidates(
        horizon_hours=horizon_hours,
        limit=limit,
        refresh=refresh,
    )
    rows = build_predict_rows_from_collisions(events)
    predictions = predictor.predict_min_distance(rows)
    output: list[MLPrediction] = []
    for event, prediction in zip(events, predictions):
        ml_available = predictor.available and prediction == prediction  # NaN check
        predicted_distance = float(prediction) if ml_available else float(event.min_distance_km)
        output.append(
            MLPrediction(
                satellite_1=event.satellite_1,
                satellite_2=event.satellite_2,
                predicted_min_distance_km=round(max(0.0, predicted_distance), 3),
                predicted_risk=predictor.distance_to_risk(max(0.0, predicted_distance)),
                ml_available=ml_available,
            )
        )
    return output
