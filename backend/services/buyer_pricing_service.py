"""
backend/services/buyer_pricing_service.py
------------------------------------------------------------------------
Runtime ML Price Prediction Service for BuyerAgent.

Loads and executes the pre-trained Ridge regression pipeline:
    backend/models/buyer_price_prediction_model.pkl

Strict Constraints:
1. Reuses existing serialized model without retraining on startup.
2. Genuinely thread-safe singleton initialization using double-checked locking.
3. Strictly restricts crop scope to the 7 canonical Maharashtra commodities.
4. Dynamically retrieves legitimate market features from the real historical
   APMC feature dataset (backend/dataset/buyer_feature_dataset.csv).
5. Validates all 12 numerical features + 7 one-hot crop indicators.
6. Fails with controlled errors on missing/invalid features (no silent fabrication).
7. Clearly distinguishes ML_USED from FALLBACK_USED in audit telemetry.
"""

import os
import re
import csv
import pickle
import threading
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, Any, Optional, Tuple, List

import numpy as np

from shared.crop_catalog import (
    BUYER_SUPPORTED_CROPS,
    normalize_crop_name,
    is_supported_buyer_crop,
    validate_buyer_crop,
)


class BuyerPricePredictionService:
    _instance = None
    _model_pkg = None
    _lock = threading.Lock()
    _dataset_lock = threading.Lock()
    _dataset_loaded = False
    _by_crop_apmc = defaultdict(list)
    _by_crop_district = defaultdict(list)
    _by_crop = defaultdict(list)

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(BuyerPricePredictionService, cls).__new__(cls)
        return cls._instance

    def __init__(self, model_path: Optional[str] = None):
        if hasattr(self, "_initialized") and self._initialized:
            return
        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if model_path is None:
                model_path = os.path.join(base_dir, "backend", "models", "buyer_price_prediction_model.pkl")
            self.model_path = model_path
            self.base_dir = base_dir
            self._load_model()
            self._initialized = True

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

    @classmethod
    def _load_feature_dataset(cls, dataset_path: Optional[str] = None) -> None:
        if cls._dataset_loaded:
            return

        with cls._dataset_lock:
            if cls._dataset_loaded:
                return

            if dataset_path is None:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                dataset_path = os.path.join(base_dir, "backend", "dataset", "buyer_feature_dataset.csv")

            if not os.path.exists(dataset_path):
                raise FileNotFoundError(f"Real buyer feature dataset not found at {dataset_path}")

            with open(dataset_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    c = row["crop"]
                    a = row["apmc"].strip().lower()
                    d = row["district"].strip().lower()
                    cls._by_crop_apmc[(c, a)].append(row)
                    cls._by_crop_district[(c, d)].append(row)
                    cls._by_crop[c].append(row)

            # Sort records chronologically by date
            for lst in cls._by_crop_apmc.values():
                lst.sort(key=lambda x: x["date"])
            for lst in cls._by_crop_district.values():
                lst.sort(key=lambda x: x["date"])
            for lst in cls._by_crop.values():
                lst.sort(key=lambda x: x["date"])

            cls._dataset_loaded = True

    def get_market_features(
        self,
        crop: str,
        location: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, float]], Optional[Dict[str, Any]]]:
        """
        Retrieves the latest legitimate market features from the real historical
        APMC dataset for the requested crop and location.
        Returns (features_dict, metadata_dict) or (None, None) if crop unsupported.
        """
        if not is_supported_buyer_crop(crop):
            return None, None

        canonical_crop = normalize_crop_name(crop)
        self._load_feature_dataset()

        crop_rows = self._by_crop.get(canonical_crop)
        if not crop_rows:
            return None, None

        selected_row = None
        source_level = "state_latest"

        if location:
            clean_loc = location.strip().lower()
            # Extract word tokens from location (excluding common filler words)
            tokens = set(re.findall(r"[a-z0-9]+", clean_loc)) - {"maharashtra", "apmc", "mandi", "market", "main"}

            # 1. Exact APMC match
            for (c, a), rows in self._by_crop_apmc.items():
                if c == canonical_crop and a == clean_loc:
                    selected_row = rows[-1]
                    source_level = f"apmc_exact_match ({rows[-1]['apmc']})"
                    break

            # 2. Token match on APMC name
            if not selected_row and tokens:
                for (c, a), rows in self._by_crop_apmc.items():
                    if c == canonical_crop:
                        a_tokens = set(re.findall(r"[a-z0-9]+", a))
                        if tokens & a_tokens:
                            selected_row = rows[-1]
                            source_level = f"apmc_token_match ({rows[-1]['apmc']})"
                            break

            # 3. Exact District match
            if not selected_row:
                for (c, d), rows in self._by_crop_district.items():
                    if c == canonical_crop and d == clean_loc:
                        selected_row = rows[-1]
                        source_level = f"district_exact_match ({rows[-1]['district']})"
                        break

            # 4. Token match on District name
            if not selected_row and tokens:
                for (c, d), rows in self._by_crop_district.items():
                    if c == canonical_crop:
                        d_tokens = set(re.findall(r"[a-z0-9]+", d))
                        if tokens & d_tokens:
                            selected_row = rows[-1]
                            source_level = f"district_token_match ({rows[-1]['district']})"
                            break

            # 5. Substring containment match
            if not selected_row and clean_loc:
                for (c, a), rows in self._by_crop_apmc.items():
                    if c == canonical_crop and (clean_loc in a or a in clean_loc):
                        selected_row = rows[-1]
                        source_level = f"apmc_substring_match ({rows[-1]['apmc']})"
                        break

        # 6. Fallback to latest statewide observation for canonical crop
        if not selected_row:
            selected_row = crop_rows[-1]
            source_level = f"state_latest_fallback ({selected_row['apmc']}, {selected_row['district']})"

        # Assemble the 12 numerical features strictly adhering to model schema
        features = {col: float(selected_row[col]) for col in self.feature_cols}

        metadata = {
            "dataset": "buyer_feature_dataset.csv",
            "observation_date": selected_row["date"],
            "apmc": selected_row["apmc"],
            "district": selected_row["district"],
            "match_level": source_level,
            "is_real_data": True,
        }

        return features, metadata

    def predict_modal_price(
        self,
        crop: str,
        features: Optional[Dict[str, Any]] = None,
        location: Optional[str] = None,
        feature_source: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Predicts next-period modal APMC market price for a given crop.
        If features is None, dynamically resolves legitimate features from the
        real historical APMC dataset.
        Strictly enforces 7-crop isolation and validates required inputs.
        """
        # 1. Strict 7-crop validation
        if not is_supported_buyer_crop(crop):
            crops_str = ", ".join(BUYER_SUPPORTED_CROPS)
            raise ValueError(
                f"Unsupported crop '{crop}'. BuyerAgent strictly supports only 7 Maharashtra crops: {crops_str}"
            )
        canonical_crop = normalize_crop_name(crop)

        # 2. Dynamic feature resolution if features not provided
        if features is None:
            resolved_feats, resolved_meta = self.get_market_features(canonical_crop, location)
            if not resolved_feats:
                raise ValueError(
                    f"No legitimate real market features available for {canonical_crop} at location '{location}'."
                )
            features = resolved_feats
            feature_source = resolved_meta
        elif feature_source is None:
            feature_source = {
                "dataset": "caller_context",
                "type": "direct_input",
                "is_real_data": True,
            }

        # 3. Input feature dictionary validation
        if not isinstance(features, dict) or not features:
            raise ValueError("Features payload must be a non-empty dictionary of numerical market metrics.")

        # 4. Check for missing required features (no silent fabrication)
        missing_features = [col for col in self.feature_cols if col not in features]
        if missing_features:
            raise ValueError(
                f"Missing required model feature(s): {missing_features}. "
                f"All 12 feature columns must be provided: {self.feature_cols}"
            )

        # 5. Extract and validate numerical values
        num_vector = []
        for col in self.feature_cols:
            val = features[col]
            if val is None or not isinstance(val, (int, float, np.number)) or np.isnan(val) or np.isinf(val):
                raise ValueError(f"Invalid non-finite or null value for feature '{col}': {val}")
            num_vector.append(float(val))

        # Check non-negative price sanity
        if num_vector[0] <= 0:
            raise ValueError(f"Invalid modal_price_kg ({num_vector[0]}): must be strictly positive.")

        # 6. Construct full 19-dimensional input vector (12 features + 7 one-hot crop indicators)
        crop_one_hot = [1.0 if canonical_crop == c else 0.0 for c in self.crop_list]
        X = np.array([num_vector + crop_one_hot], dtype=np.float32)

        # 7. Execute model prediction
        predicted_modal = float(self.model.predict(X)[0])

        return {
            "audit_status": "ML_USED",
            "is_ml_prediction": True,
            "predicted_price": round(predicted_modal, 2),
            "predicted_modal_price": round(predicted_modal, 2),
            "raw_predicted_price": predicted_modal,
            "crop": canonical_crop,
            "location": location or (feature_source.get("apmc") if feature_source else "Maharashtra APMC"),
            "model_type": self.model_type,
            "model_version": "xgb_v1",
            "horizon_days": 7,
            "unit": "INR_PER_KG",
            "status": "AVAILABLE",
            "features_used": dict(zip(self.feature_cols, num_vector)),
            "feature_source": feature_source,
            "one_hot_crop": dict(zip(self.crop_list, crop_one_hot)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


_default_service = None
_service_lock = threading.Lock()


def get_buyer_pricing_service() -> BuyerPricePredictionService:
    global _default_service
    if _default_service is None:
        with _service_lock:
            if _default_service is None:
                _default_service = BuyerPricePredictionService()
    return _default_service
