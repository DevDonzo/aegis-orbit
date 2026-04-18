from __future__ import annotations

import pandas as pd

FEATURE_COLUMNS = [
    "dx",
    "dy",
    "dz",
    "dvx",
    "dvy",
    "dvz",
    "relative_speed_km_s",
    "current_distance_km",
    "altitude_diff_km",
]


def create_feature_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    features = df[FEATURE_COLUMNS].copy()
    return features.apply(pd.to_numeric, errors="coerce").fillna(0.0)


def split_features_and_label(
    df: pd.DataFrame,
    label_column: str = "label_min_distance_km",
) -> tuple[pd.DataFrame, pd.Series]:
    features = create_feature_dataframe(df)
    label = pd.to_numeric(df[label_column], errors="coerce").fillna(0.0)
    return features, label


def fit_normalizer(features: pd.DataFrame) -> dict[str, dict[str, float]]:
    means = features.mean().to_dict()
    stds = features.std(ddof=0).replace(0.0, 1.0).to_dict()
    return {"mean": {k: float(v) for k, v in means.items()}, "std": {k: float(v) for k, v in stds.items()}}


def apply_normalization(features: pd.DataFrame, stats: dict[str, dict[str, float]]) -> pd.DataFrame:
    normalized = features.copy()
    for col in FEATURE_COLUMNS:
        normalized[col] = (normalized[col] - stats["mean"][col]) / stats["std"][col]
    return normalized
