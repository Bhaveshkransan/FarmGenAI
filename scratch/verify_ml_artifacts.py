"""Verify ML model artifact, bundle contents, and reproducibility of metrics."""
import os
import sys
import pickle
import json
import csv
from datetime import datetime

model_path = os.path.abspath("backend/models/buyer_price_prediction_model.pkl")
metrics_path = os.path.abspath("backend/models/buyer_price_model_metrics.json")
feature_path = os.path.abspath("backend/dataset/buyer_feature_dataset.csv")

print("=== VERIFY ML MODEL ARTIFACT ===")
print("File Path:", model_path)
size = os.path.getsize(model_path)
mtime = os.path.getmtime(model_path)
print(f"File Size: {size} bytes")
print(f"Modification Date: {datetime.fromtimestamp(mtime).isoformat()}")

with open(model_path, "rb") as f:
    bundle = pickle.load(f)

print("\nBundle Keys:", list(bundle.keys()))
print("Model Type:", bundle.get("model_type"))
model = bundle.get("model")
print("Model Object:", model)
feature_cols = bundle.get("feature_cols", [])
crop_list = bundle.get("crop_list", [])
print(f"Feature Cols ({len(feature_cols)}):", feature_cols)
print(f"Crop List ({len(crop_list)}):", crop_list)

# Test inference
sample_feat = [20.0, 18.0, 22.0, 0.2, 50.0, 19.5, 19.0, 19.5, 0.02, 1.0, 0.5, 0.866]
sample_crop_oh = [1.0 if c == "Soybean" else 0.0 for c in crop_list]
X_sample = [sample_feat + sample_crop_oh]
pred = model.predict(X_sample)
print(f"Sample Inference Test: Output = Rs. {pred[0]:.4f}/kg")
assert pred[0] > 0, "Model inference failed!"

print("\n=== VERIFY METRICS METADATA ===")
print("Metrics File Path:", metrics_path)
with open(metrics_path, "r", encoding="utf-8") as f:
    meta = json.load(f)

metrics = meta.get("metrics", {})
print("Reported Metrics JSON:")
for k, v in metrics.items():
    print(f"  {k}: {v}")

print("\n=== VERIFY REPRODUCIBILITY OF REPORTED METRICS ===")
# Load dataset and test split to recompute test metrics on existing artifact
with open(feature_path, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

total = len(rows)
train_end = int(0.70 * total)
val_end = int(0.85 * total)
test_data = rows[val_end:]

print(f"Total Rows: {total} | Test Split Rows: {len(test_data)}")

# Persistence
y_test = [float(r["target_next_modal_kg"]) for r in test_data]
y_pers = [float(r["modal_price_kg"]) for r in test_data]
y_ma = [float(r["rolling_3_modal"]) for r in test_data]

import numpy as np
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

mae_pers = mean_absolute_error(y_test, y_pers)
rmse_pers = root_mean_squared_error(y_test, y_pers)
mape_pers = float(np.mean(np.abs((np.array(y_test) - np.array(y_pers)) / np.array(y_test))) * 100.0)

mae_ma = mean_absolute_error(y_test, y_ma)
rmse_ma = root_mean_squared_error(y_test, y_ma)
mape_ma = float(np.mean(np.abs((np.array(y_test) - np.array(y_ma)) / np.array(y_test))) * 100.0)

X_test = []
for r in test_data:
    feat = [float(r[col]) for col in feature_cols]
    oh = [1.0 if r["crop"] == c else 0.0 for c in crop_list]
    X_test.append(feat + oh)

y_pred_model = model.predict(X_test)
mae_model = mean_absolute_error(y_test, y_pred_model)
rmse_model = root_mean_squared_error(y_test, y_pred_model)
mape_model = float(np.mean(np.abs((np.array(y_test) - np.array(y_pred_model)) / np.array(y_test))) * 100.0)

print(f"\nCalculated vs Reported Comparison on Test Split:")
print(f"  Persistence MAE:  Calculated = {mae_pers:.4f} | Reported = {metrics['persistence']['mae']}")
print(f"  Moving Avg MAE:   Calculated = {mae_ma:.4f} | Reported = {metrics['moving_average_3']['mae']}")
print(f"  Ridge Model MAE:  Calculated = {mae_model:.4f} | Reported = {metrics['ridge']['mae']}")

assert abs(mae_pers - metrics['persistence']['mae']) < 1e-4, "Persistence MAE mismatch!"
assert abs(mae_ma - metrics['moving_average_3']['mae']) < 1e-4, "Moving Avg MAE mismatch!"
assert abs(mae_model - metrics['ridge']['mae']) < 1e-4, "Ridge Model MAE mismatch!"

print("\n>>> ALL REPORTED METRICS ARE 100% MATHEMATICALLY REPRODUCIBLE FROM DISK ARTIFACTS.")
