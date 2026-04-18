from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "dx",
    "dy",
    "dz",
    "dvx",
    "dvy",
    "dvz",
    "current_distance_km",
    "altitude_diff_km",
    "relative_speed_km_s",
    "relative_xy_distance_km",
    "radial_closure_rate_km_s",
    "vertical_separation_ratio",
    "time_to_closest_approach_min",
]


def create_feature_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    features = df[
        [
            "dx",
            "dy",
            "dz",
            "dvx",
            "dvy",
            "dvz",
            "current_distance_km",
            "altitude_diff_km",
            "lead_time_minutes",
        ]
    ].copy()

    features["relative_speed_km_s"] = np.sqrt(features["dvx"] ** 2 + features["dvy"] ** 2 + features["dvz"] ** 2)
    features["relative_xy_distance_km"] = np.sqrt(features["dx"] ** 2 + features["dy"] ** 2)

    denominator = features["current_distance_km"].replace(0.0, 1.0)
    dot_product = features["dx"] * features["dvx"] + features["dy"] * features["dvy"] + features["dz"] * features["dvz"]
    features["radial_closure_rate_km_s"] = (-dot_product / denominator).clip(-20.0, 20.0)
    features["vertical_separation_ratio"] = (features["altitude_diff_km"] / denominator).clip(0.0, 1.5)
    features["time_to_closest_approach_min"] = features["lead_time_minutes"].clip(lower=0.0)

    return features[FEATURE_COLUMNS]


def fit_normalizer(features: pd.DataFrame) -> dict[str, dict[str, float]]:
    means = features.mean().to_dict()
    stds = features.std(ddof=0).replace(0.0, 1.0).to_dict()
    return {"mean": {key: float(value) for key, value in means.items()}, "std": {key: float(value) for key, value in stds.items()}}


def apply_normalization(features: pd.DataFrame, stats: dict[str, dict[str, float]]) -> pd.DataFrame:
    normalized = features.copy()
    for column in FEATURE_COLUMNS:
        normalized[column] = (normalized[column] - stats["mean"][column]) / stats["std"][column]
    return normalized
