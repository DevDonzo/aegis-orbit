from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from joblib import dump
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from core.config import settings
from ml.data_pipeline import generate_training_dataframe
from ml.feature_engineering import FEATURE_COLUMNS, create_feature_dataframe

TRAIN_TEST_SEED = 42


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "test_rmse_km": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "test_mae_km": float(mean_absolute_error(y_true, y_pred)),
        "test_r2": float(r2_score(y_true, y_pred)),
    }


def _feature_schema_hash() -> str:
    joined = "|".join(FEATURE_COLUMNS)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def train_and_save_model() -> dict[str, float | str]:
    df = generate_training_dataframe()
    if df.empty:
        raise RuntimeError("Training dataset is empty. Check propagation inputs and simulation settings.")

    features = create_feature_dataframe(df)
    labels = df["label_min_distance_km"].to_numpy(dtype=np.float32)
    feature_matrix = features.to_numpy(dtype=np.float32)

    x_train, x_test, y_train, y_test = train_test_split(
        feature_matrix,
        labels,
        test_size=0.2,
        random_state=TRAIN_TEST_SEED,
    )

    candidate_models = {
        "random_forest": RandomForestRegressor(
            n_estimators=450,
            max_depth=14,
            min_samples_leaf=2,
            random_state=TRAIN_TEST_SEED,
            n_jobs=-1,
        ),
        "gradient_boosting": GradientBoostingRegressor(
            n_estimators=320,
            learning_rate=0.045,
            max_depth=3,
            random_state=TRAIN_TEST_SEED,
        ),
    }

    trained_models: dict[str, object] = {}
    metrics_by_model: dict[str, dict[str, float]] = {}
    predictions_by_model: dict[str, np.ndarray] = {}

    for name, model in candidate_models.items():
        model.fit(x_train, y_train)
        trained_models[name] = model
        predictions = model.predict(x_test).reshape(-1)
        predictions_by_model[name] = predictions
        metrics_by_model[name] = _metrics(y_test, predictions)

    ensemble_predictions = np.mean(np.vstack(list(predictions_by_model.values())), axis=0)
    metrics_by_model["ensemble"] = _metrics(y_test, ensemble_predictions)

    selected_model = min(metrics_by_model.items(), key=lambda item: item[1]["test_rmse_km"])[0]
    bundle = {
        "models": trained_models,
        "selected_model": selected_model,
        "feature_columns": FEATURE_COLUMNS,
        "schema_hash": _feature_schema_hash(),
        "train_test_seed": TRAIN_TEST_SEED,
        "candidate_metrics": metrics_by_model,
        "trained_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    model_path = Path(settings.model_file)
    metadata_path = Path(settings.model_metadata_file)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    dump(bundle, model_path)

    metadata = {
        "trained_at_utc": bundle["trained_at_utc"],
        "model_type": "ModelSelectionBundle",
        "selected_model": selected_model,
        "candidate_models": list(candidate_models.keys()),
        "feature_columns": FEATURE_COLUMNS,
        "feature_schema_hash": bundle["schema_hash"],
        "samples": int(len(df)),
        "train_test_seed": TRAIN_TEST_SEED,
        "data_timestamp_range": {
            "sample_time_min": str(df["sample_time_utc"].min()),
            "sample_time_max": str(df["sample_time_utc"].max()),
            "tca_time_min": str(df["tca_time_utc"].min()),
            "tca_time_max": str(df["tca_time_utc"].max()),
        },
        "model_registry": metrics_by_model,
    }
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    selected_metrics = metrics_by_model[selected_model]
    return {
        "selected_model": selected_model,
        "samples": float(len(df)),
        "test_rmse_km": selected_metrics["test_rmse_km"],
        "test_mae_km": selected_metrics["test_mae_km"],
        "test_r2": selected_metrics["test_r2"],
    }


def main() -> None:
    print(json.dumps(train_and_save_model(), indent=2))


if __name__ == "__main__":
    main()
