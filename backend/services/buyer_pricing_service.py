"""
backend/services/buyer_pricing_service.py
------------------------------------------------------------------------
Runtime ML Price Prediction Service for BuyerAgent.

Loads and executes the pre-trained Ridge regression pipeline:
    backend/models/buyer_price_prediction_model.pkl

Strict Constraints:
1. Reuses existing serialized model without retraining on startup.
2. Singleton in-memory caching to avoid redundant disk I/O.
3. Strictly restricts crop scope to the 7 canonical Maharashtra commodities.
4. Validates all 12 numerical features + 7 one-hot crop indicators.
5. Fails with controlled errors on missing/invalid features (no silent fabrication).
6. Returns rich prediction metadata for auditable valuation tracking.
"""

import os
import pickle
import numpy as np
from typing import Dict, Any, Optional

from shared.crop_catalog import (
    BUYER_SUPPORTED_CROPS,
    normalize_crop_name,
    is_supported_buyer_crop,
    validate_buyer_crop,
)

class BuyerPricePredictionService:
    _instance = None
    _model_pkg = None

    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            model_path = os.path.join(base_dir, "backend", "models", "buyer_price_prediction_model.pkl")
        self.model_path = model_path
        self._load_model()

    def _load_model(self) -> None:
        if BuyerPricePredictionService._model_pkg is not None:
            self.model = BuyerPricePredictionService._model_pkg["model"]
            self.model_type = BuyerPricePredictionService._model_pkg["model_type"]
            self.feature_cols = BuyerPricePredictionService._model_pkg["feature_cols"]
            self.crop_list = BuyerPricePredictionService._model_pkg["crop_list"]
            self.month_map = BuyerPricePredictionService._model_pkg["month_map"]
            return

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Buyer model artifact not found at {self.model_path}")

        with open(self.model_path, "rb") as f:
            pkg = pickle.load(f)

        BuyerPricePredictionService._model_pkg = pkg
        self.model = pkg["model"]
        self.model_type = pkg["model_type"]
        self.feature_cols = pkg["feature_cols"]
        self.crop_list = pkg["crop_list"]
        self.month_map = pkg["month_map"]

    def predict_modal_price(
        self,
        crop: str,
        features: Dict[str, Any],
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Predicts next-period modal APMC market price for a given crop and feature dictionary.
        Strictly enforces 7-crop isolation and validates required inputs.
        """
        # 1. Strict 7-crop validation
        if not is_supported_buyer_crop(crop):
            crops_str = ", ".join(BUYER_SUPPORTED_CROPS)
            raise ValueError(
                f"Unsupported crop '{crop}'. BuyerAgent strictly supports only 7 Maharashtra crops: {crops_str}"
            )
        canonical_crop = normalize_crop_name(crop)

        # 2. Input feature dictionary validation
        if not isinstance(features, dict) or not features:
            raise ValueError("Features payload must be a non-empty dictionary of numerical market metrics.")

        # 3. Check for missing required features (no silent fabrication)
        missing_features = [col for col in self.feature_cols if col not in features]
        if missing_features:
            raise ValueError(
                f"Missing required model feature(s): {missing_features}. "
                f"All 12 feature columns must be provided: {self.feature_cols}"
            )

        # 4. Extract and validate numerical values
        num_vector = []
        for col in self.feature_cols:
            val = features[col]
            if val is None or not isinstance(val, (int, float, np.number)) or np.isnan(val) or np.isinf(val):
                raise ValueError(f"Invalid non-finite or null value for feature '{col}': {val}")
            num_vector.append(float(val))

        # Check non-negative price sanity
        if num_vector[0] <= 0:
            raise ValueError(f"Invalid modal_price_kg ({num_vector[0]}): must be strictly positive.")

        # 5. Construct full 19-dimensional input vector (12 features + 7 one-hot crop indicators)
        crop_one_hot = [1.0 if canonical_crop == c else 0.0 for c in self.crop_list]
        X = np.array([num_vector + crop_one_hot], dtype=np.float32)

        # 6. Execute model prediction
        predicted_modal = float(self.model.predict(X)[0])

        return {
            "predicted_modal_price": round(predicted_modal, 2),
            "raw_predicted_price": predicted_modal,
            "crop": canonical_crop,
            "location": location or "Maharashtra APMC",
            "model_type": self.model_type,
            "features_used": dict(zip(self.feature_cols, num_vector)),
            "one_hot_crop": dict(zip(self.crop_list, crop_one_hot)),
            "is_ml_prediction": True,
        }

_default_service = None

def get_buyer_pricing_service() -> BuyerPricePredictionService:
    global _default_service
    if _default_service is None:
        _default_service = BuyerPricePredictionService()
    return _default_service
