import numpy as np
import pandas as pd

from ml.feature_engineering import FEATURE_COLUMNS, apply_normalization, create_feature_dataframe, fit_normalizer


def test_feature_engineering_outputs_normalized_data() -> None:
    frame = pd.DataFrame(
        [
            {
                "dx": 1.0,
                "dy": 2.0,
                "dz": 3.0,
                "dvx": 0.1,
                "dvy": 0.2,
                "dvz": 0.3,
                "current_distance_km": 4.0,
                "altitude_diff_km": 5.0,
                "lead_time_minutes": 12.0,
            }
        ]
    )

    features = create_feature_dataframe(frame)
    stats = fit_normalizer(features)
    transformed = apply_normalization(features, stats)
    assert transformed.shape[1] == len(FEATURE_COLUMNS)
    assert np.isfinite(transformed.to_numpy()).all()
