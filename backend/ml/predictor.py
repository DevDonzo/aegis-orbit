from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from core.config import classify_risk, settings
from ml.feature_engineering import FEATURE_COLUMNS, apply_normalization


class OptionalMLPredictor:
    def __init__(self) -> None:
        self.model_path = Path(settings.model_file)
        self.normalizer_path = Path(settings.normalizer_file)
        self.available = False
        self.model = None
        self.stats: dict[str, dict[str, float]] | None = None
        self.load_error: str | None = None
        self._load_if_possible()

    def _load_if_possible(self) -> None:
        if not settings.ml_enabled or not self.model_path.exists() or not self.normalizer_path.exists():
            self.load_error = "model_or_normalizer_missing"
            return
        try:
            from tensorflow import keras
        except ImportError:
            self.load_error = "tensorflow_not_installed"
            return
        try:
            with self.normalizer_path.open("r", encoding="utf-8") as f:
                self.stats = json.load(f)
            self.model = keras.models.load_model(self.model_path)
        except Exception as exc:
            self.load_error = str(exc)
            self.available = False
            return
        self.load_error = None
        self.available = True

    def predict_min_distance(self, rows: list[dict[str, float]]) -> list[float]:
        if not self.available or self.model is None or self.stats is None:
            return [float("nan")] * len(rows)
        features = pd.DataFrame(rows)[FEATURE_COLUMNS]
        normalized = apply_normalization(features, self.stats)
        predictions = self.model.predict(normalized.to_numpy(dtype=np.float32), verbose=0).reshape(-1)
        return [max(0.0, float(v)) for v in predictions]

    def enrich_collision(
        self,
        row: dict[str, float],
    ) -> dict[str, Any]:
        prediction = self.predict_min_distance([row])[0]
        if not np.isfinite(prediction):
            return {
                "ml_available": False,
                "ml_predicted_min_distance_km": None,
                "ml_risk_score": None,
            }
        capped = max(0.0, float(prediction))
        ml_risk_score = float(max(0.0, min(1.0, 1.0 - (capped / 100.0))))
        return {
            "ml_available": True,
            "ml_predicted_min_distance_km": round(capped, 3),
            "ml_risk_score": round(ml_risk_score, 4),
            "ml_predicted_risk": self.distance_to_risk(capped),
        }

    @staticmethod
    def distance_to_risk(distance_km: float) -> str:
        return classify_risk(distance_km)
