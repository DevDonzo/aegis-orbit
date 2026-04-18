# Backend Work Status

This `backend/` folder contains all implemented work completed so far.

## Completed

- FastAPI API service exposing:
  - `GET /health`
  - `GET /satellites`
  - `GET /collisions`
  - `GET /predict`
  - `GET /ml/status`
- Config-driven simulation and model settings (`core/config.py`).
- TTL cache utility and endpoint-level caching for expensive simulation calls (`core/cache.py`, `api/routes.py`).
- Orbital state and conjunction simulation from TLEs using Skyfield (`ml/data_pipeline.py`).
- Feature engineering for ML inference:
  - Relative position/velocity
  - Relative speed magnitude
  - XY separation
  - Radial closure rate (`ml/feature_engineering.py`).
- RandomForest-based regression training to predict closest approach distance with serialized artifact + metadata (`ml/training.py`, `train_model.py`).
- Runtime predictor with ML-model and heuristic-fallback modes (`ml/predictor.py`).
- Pydantic response schemas and typed risk levels (`ml/schemas.py`).
- Backend tests (`tests/`).

## ML Summary

- Target: predict minimum miss distance between satellite pairs over future timesteps.
- Training data: generated from simulated pairwise conjunction states across the configured horizon.
- Model: `RandomForestRegressor` trained on engineered orbital-relative features.
- Output: predicted miss distance (km), derived risk band, and collision probability proxy.
- Fallback behavior: if no trained model exists, `/predict` returns heuristic predictions based on simulated closest distance.
