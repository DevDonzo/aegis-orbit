from ml.data_pipeline import (
    build_current_satellite_positions,
    compute_collision_candidates,
    generate_training_dataframe,
)


def test_satellite_positions_exist() -> None:
    positions = build_current_satellite_positions()
    assert len(positions) >= 5
    assert positions[0].name != ""


def test_collision_events_exist() -> None:
    events = compute_collision_candidates()
    assert len(events) > 0
    assert events[0].distance_km >= 0
    assert events[0].min_distance_km >= 0
    assert events[0].relative_speed_km_s >= 0
    assert events[0].data_source in {"live", "cache", "sample"}
    assert events[0].risk in {"danger", "warning", "safe"}


def test_training_dataframe_shape() -> None:
    df = generate_training_dataframe(samples_per_pair=2, offset_minutes=5)
    assert "label_min_distance_km" in df.columns
    assert "relative_speed_km_s" in df.columns
    assert "label_risk_class" in df.columns
    assert len(df) > 0
