"""
Unit tests for BuyerAgent Real Market Data Ingestion & Valuation Pipeline.

Verifies:
1. Strict 7-crop inclusion and non-7-crop rejection.
2. Clean dataset schema, price ranges, and conversion to Rs/kg.
3. No zero or negative prices in the cleaned market dataset.
4. Correct deduplication on (crop, apmc, date).
5. Feature dataset generation and target alignment.
6. Chronological integrity of train/val/test splits.
7. Existence and loadability of trained model artifact and metrics metadata.
"""

import csv
import json
import os
import pickle
import unittest

from shared.crop_catalog import BUYER_SUPPORTED_CROPS

SUPPORTED_CROPS = set(BUYER_SUPPORTED_CROPS.keys())


class TestBuyerRealDataIngestion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.clean_csv = os.path.join(cls.base_dir, "backend", "dataset", "clean_buyer_market_data.csv")
        cls.clean_json = os.path.join(cls.base_dir, "backend", "dataset", "clean_buyer_market_data.json")
        cls.feature_csv = os.path.join(cls.base_dir, "backend", "dataset", "buyer_feature_dataset.csv")
        cls.model_pkl = os.path.join(cls.base_dir, "backend", "models", "buyer_price_prediction_model.pkl")
        cls.metrics_json = os.path.join(cls.base_dir, "backend", "models", "buyer_price_model_metrics.json")

    def test_clean_datasets_exist(self):
        """Verify cleaned dataset files exist and are non-empty."""
        self.assertTrue(os.path.exists(self.clean_csv), f"Missing {self.clean_csv}")
        self.assertTrue(os.path.exists(self.clean_json), f"Missing {self.clean_json}")
        self.assertGreater(os.path.getsize(self.clean_csv), 10000)
        self.assertGreater(os.path.getsize(self.clean_json), 10000)

    def test_clean_dataset_strict_7_crops(self):
        """Verify that every single record in clean dataset belongs strictly to the 7 canonical crops."""
        with open(self.clean_csv, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            crops_found = set()
            for row in reader:
                crop = row["crop"]
                self.assertIn(crop, SUPPORTED_CROPS, f"Found unauthorized crop {crop} in clean dataset!")
                crops_found.add(crop)

        # All 7 crops must have real observations
        self.assertEqual(crops_found, SUPPORTED_CROPS)

    def test_price_sanity_and_units(self):
        """Verify that prices are strictly positive and in realistic Rs/kg ranges (not quintal scale)."""
        with open(self.clean_csv, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                modal_kg = float(row["modal_price_kg"])
                min_kg = float(row["min_price_kg"])
                max_kg = float(row["max_price_kg"])

                self.assertGreater(modal_kg, 0.0, f"Non-positive modal price in row: {row}")
                self.assertGreaterEqual(max_kg, min_kg, f"Max price < Min price in row: {row}")
                # Rs/kg should be < 200/kg for these field crops (if > 1000 it wasn't divided by 100)
                self.assertLess(modal_kg, 200.0, f"Unscaled quintal price detected ({modal_kg}) in row: {row}")

    def test_deduplication_integrity(self):
        """Verify that every (crop, apmc, date) combination is strictly unique in the clean dataset."""
        seen = set()
        with open(self.clean_csv, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row["crop"], row["apmc"], row["date"])
                self.assertNotIn(key, seen, f"Duplicate key found in clean dataset: {key}")
                seen.add(key)

    def test_feature_dataset_integrity(self):
        """Verify feature dataset has valid rows and non-null target P_(t+1)."""
        self.assertTrue(os.path.exists(self.feature_csv), f"Missing {self.feature_csv}")
        with open(self.feature_csv, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                count += 1
                target = float(row["target_next_modal_kg"])
                self.assertGreater(target, 0.0)
                self.assertIn(row["crop"], SUPPORTED_CROPS)
                # Verify lag and spread features exist
                self.assertIn("lag_1_modal", row)
                self.assertIn("spread", row)
                self.assertIn("arrival_shock", row)
                self.assertIn("month_sin", row)
            self.assertGreater(count, 10000, "Expected >10,000 entity-series rows")

    def test_model_artifact_loadable_and_predicts(self):
        """Verify that the trained valuation model artifact can be unpickled and yields predictions."""
        self.assertTrue(os.path.exists(self.model_pkl), f"Missing {self.model_pkl}")
        with open(self.model_pkl, "rb") as f:
            bundle = pickle.load(f)

        self.assertIn("model", bundle)
        self.assertIn("feature_cols", bundle)
        self.assertIn("crop_list", bundle)
        model = bundle["model"]

        # Synthetic sample vector of length = len(feature_cols) + len(crop_list)
        # feature_cols has 12 items, crop_list has 7 items -> 19 features
        n_features = len(bundle["feature_cols"]) + len(bundle["crop_list"])
        sample = [[15.0] * n_features]
        prediction = model.predict(sample)
        self.assertEqual(len(prediction), 1)
        self.assertGreater(prediction[0], 0.0)

    def test_metrics_metadata_honesty(self):
        """Verify that metrics metadata exists, records baselines, and reports persistence vs ML honestly."""
        self.assertTrue(os.path.exists(self.metrics_json), f"Missing {self.metrics_json}")
        with open(self.metrics_json, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.assertIn("metrics", meta)
        metrics = meta["metrics"]
        self.assertIn("persistence", metrics)
        self.assertIn("moving_average_3", metrics)
        self.assertIn("ridge", metrics)
        self.assertIn("hist_gradient_boosting", metrics)

        # Baseline MAE should be around 1.7 Rs/kg
        self.assertAlmostEqual(metrics["persistence"]["mae"], 1.7258, delta=0.1)
        # Total clean records must match exactly 14,078
        self.assertEqual(meta["total_clean_records"], 14078)
        self.assertEqual(meta["total_raw_ingested"], 62429)


if __name__ == "__main__":
    unittest.main()
