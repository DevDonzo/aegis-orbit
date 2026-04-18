from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import load

from core.config import classify_risk, settings
from ml.feature_engineering import FEATURE_COLUMNS, create_feature_dataframe


class OptionalMLPredictor:
    def __init__(self) -> None:
        self.model_path = Path(settings.model_file)
        self.metadata_path = Path(settings.model_metadata_file)
        self.available = False
        self.bundle: dict[str, object] | None = None
        self.metadata: dict[str, object] = {}
        self._load_if_possible()

    def _load_if_possible(self) -> None:
        if not settings.ml_enabled or not self.model_path.exists():
            return
        loaded = load(self.model_path)
        if isinstance(loaded, dict) and "models" in loaded:
            self.bundle = loaded
        else:  # Legacy single-model compatibility
            self.bundle = {
                "models": {"legacy": loaded},
                "selected_model": "legacy",
                "feature_columns": FEATURE_COLUMNS,
            }
        if self.metadata_path.exists():
            with self.metadata_path.open("r", encoding="utf-8") as handle:
                self.metadata = json.load(handle)
        self.available = True

    def _candidate_predictions(self, rows: list[dict[str, float]]) -> dict[str, np.ndarray]:
        if not self.available or self.bundle is None:
            raise RuntimeError("Model bundle is not available.")
        features = create_feature_dataframe(pd.DataFrame(rows))[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
        predictions: dict[str, np.ndarray] = {}
        for name, model in (self.bundle["models"] or {}).items():
            predictions[str(name)] = np.asarray(model.predict(features), dtype=np.float32).reshape(-1)
        return predictions

    def predict_distances(self, rows: list[dict[str, float]]) -> list[dict[str, float | str]]:
        if not self.available or self.bundle is None:
            raise RuntimeError("Model bundle is not available.")

        predictions = self._candidate_predictions(rows)
        if not predictions:
            raise RuntimeError("No candidate models available.")

        matrix = np.vstack(list(predictions.values()))
        ensemble = matrix.mean(axis=0)
        spread = matrix.std(axis=0)
        selected_model = str(self.bundle.get("selected_model", "legacy"))

        results: list[dict[str, float | str]] = []
        for index in range(ensemble.shape[0]):
            if selected_model == "ensemble":
                predicted = float(ensemble[index])
                source = "ensemble"
            else:
                predicted = float(predictions.get(selected_model, ensemble)[index])
                source = "selected-model"

            results.append(
                {
                    "predicted_distance_km": max(0.0, predicted),
                    "uncertainty_km": max(0.0, float(spread[index])),
                    "prediction_source": source,
                    "model_name": selected_model,
                }
            )
        return results

    @staticmethod
    def distance_to_risk(distance_km: float) -> str:
        return classify_risk(distance_km)

    @staticmethod
    def distance_to_probability(distance_km: float, uncertainty_km: float = 0.0) -> float:
        return float(np.exp(-max(0.0, distance_km) / max(22.0, 48.0 + uncertainty_km * 6.0)))

    def status(self) -> dict[str, object]:
        candidate_models = []
        selected_model = None
        if self.bundle is not None:
            candidate_models = list((self.bundle.get("models") or {}).keys())
            selected_model = str(self.bundle.get("selected_model")) if self.bundle.get("selected_model") else None
        return {
            "available": self.available,
            "model_path": str(self.model_path),
            "metadata": self.metadata if self.metadata else None,
            "source": "selected-model" if self.available else "heuristic-fallback",
            "candidate_models": candidate_models,
            "selected_model": selected_model,
        }
