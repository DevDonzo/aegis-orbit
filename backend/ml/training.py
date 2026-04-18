from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split

from core.config import settings
from ml.data_pipeline import generate_training_dataframe
from ml.feature_engineering import (
    apply_normalization,
    create_feature_dataframe,
    fit_normalizer,
    split_features_and_label,
)


def train_and_save_model() -> dict[str, float]:
    try:
        from tensorflow import keras
    except ImportError as exc:
        raise RuntimeError("TensorFlow is required for training. Install tensorflow.") from exc

    df = generate_training_dataframe()
    features, labels_series = split_features_and_label(df, label_column="label_min_distance_km")
    labels = labels_series.to_numpy(dtype=np.float32)
    stats = fit_normalizer(features)
    normalized_features = apply_normalization(features, stats).to_numpy(dtype=np.float32)

    x_train, x_test, y_train, y_test = train_test_split(
        normalized_features, labels, test_size=0.2, random_state=42
    )

    model = keras.Sequential(
        [
            keras.layers.Input(shape=(x_train.shape[1],)),
            keras.layers.Dense(64, activation="relu"),
            keras.layers.Dense(32, activation="relu"),
            keras.layers.Dense(1, activation="linear"),
        ]
    )
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    early_stop = keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=8,
        restore_best_weights=True,
    )
    model.fit(
        x_train,
        y_train,
        validation_split=0.2,
        epochs=80,
        batch_size=16,
        verbose=0,
        callbacks=[early_stop],
    )
    loss, mae = model.evaluate(x_test, y_test, verbose=0)

    model_path = Path(settings.model_file)
    normalizer_path = Path(settings.normalizer_file)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    model.save(model_path)
    with normalizer_path.open("w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    return {
        "test_mse": float(loss),
        "test_mae": float(mae),
        "samples": float(len(df)),
        "feature_count": float(len(create_feature_dataframe(df).columns)),
    }


def main() -> None:
    metrics = train_and_save_model()
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
