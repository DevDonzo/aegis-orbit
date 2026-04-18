from ml.data_pipeline import (
    build_current_satellite_positions,
    build_dashboard_snapshot,
    compute_collision_candidates,
    generate_training_dataframe,
)


def test_satellite_positions_include_tracks() -> None:
    positions = build_current_satellite_positions()
    assert len(positions) >= 5
    assert positions[0].telemetry
    assert positions[0].norad_id != ""


def test_collision_events_have_operational_metrics() -> None:
    events = compute_collision_candidates()
    assert len(events) > 0
    assert events[0].distance_km >= 0
    assert events[0].relative_velocity_km_s > 0


def test_dashboard_snapshot_is_consistent() -> None:
    snapshot = build_dashboard_snapshot()
    assert snapshot.satellites
    assert snapshot.collisions


def test_training_dataframe_shape() -> None:
    df = generate_training_dataframe(samples_per_pair=2, offset_minutes=5)
    assert "label_min_distance_km" in df.columns
    assert "lead_time_minutes" in df.columns
    assert len(df) > 0
