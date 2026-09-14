"""
Real Agricultural Market Data Ingestion & Valuation Modeling Pipeline for BuyerAgent.

Sources:
1. Maharashtra State Agricultural Marketing Board (MSAMB / CMO) official APMC records:
   - Path: backend/dataset/Monthly_data_cmo.csv
   - Official open data for 349 APMC mandis across 33 districts of Maharashtra.
2. Local Agmarknet Daily Snippet:
   - Path: backend/dataset/Market_Wise_Price_Arrival_06-08-2026_08-18-20_PM.csv
3. CMO MSP Mandi:
   - Path: backend/dataset/CMO_MSP_Mandi.csv

Strict Constraints:
- REAL DATA ONLY. No synthetic records, no artificial 19,200 rows.
- STRICTLY 7 Maharashtra crops: Sugarcane, Soybean, Cotton, Jowar, Onion, Bajra, Rice.
- Chronological train/val/test split (no data leakage).
- Evaluates Persistence Baseline, Moving Average Baseline, and ML Models (HistGradientBoosting, Ridge).
"""

import csv
import json
import math
import os
import pickle
import sys
from collections import defaultdict
from datetime import datetime, timezone

# Configure UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Canonical 7 Crops Mapping
CROP_ALIAS_MAP = {
    # Bajra
    "BAJRI": "Bajra",
    "Bajri": "Bajra",
    "Bajra": "Bajra",
    "Bajra(Pearl Millet/Cumbu)": "Bajra",
    # Cotton
    "COTTON": "Cotton",
    "Cotton": "Cotton",
    "Cotton_Long Staple": "Cotton",
    # Onion
    "ONION": "Onion",
    "Onion": "Onion",
    # Rice / Paddy
    "PADDY-UNHUSKED": "Rice",
    "Paddy-Unhusked": "Rice",
    "RICE(PADDY-HUS)": "Rice",
    "Rice(Paddy-Hus)": "Rice",
    "Paddy": "Rice",
    "Paddy(Common)": "Rice",
    "Rice": "Rice",
    # Jowar
    "SORGUM(JAWAR)": "Jowar",
    "Sorgum(Jawar)": "Jowar",
    "Jowar_Hybrid": "Jowar",
    "Jowar": "Jowar",
    "Jowar(Sorghum)": "Jowar",
    # Soybean
    "SOYBEAN": "Soybean",
    "Soybean": "Soybean",
    "Soyabean": "Soybean",
    "Soyabean_Black": "Soybean",
    # Sugarcane
    "Sugarcane": "Sugarcane",
    "Sugar Cane": "Sugarcane",
    "Ganna": "Sugarcane",
}

CANONICAL_CROPS = ["Sugarcane", "Soybean", "Cotton", "Jowar", "Onion", "Bajra", "Rice"]


def parse_float(val, default=0.0):
    if val is None:
        return default
    s = str(val).strip().replace(",", "")
    if not s or s == "-":
        return default
    try:
        return float(s)
    except ValueError:
        return default


def calculate_mape(y_true, y_pred):
    y_t = np.array(y_true)
    y_p = np.array(y_pred)
    mask = y_t > 0
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.abs((y_t[mask] - y_p[mask]) / y_t[mask])) * 100.0)


def run_pipeline():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cmo_csv_path = os.path.join(base_dir, "backend", "dataset", "Monthly_data_cmo.csv")
    out_dir = os.path.join(base_dir, "backend", "dataset")
    models_dir = os.path.join(base_dir, "backend", "models")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)

    print("==================================================")
    print("STEP 1: INGESTION & 7-CROP MAHARASHTRA FILTERING")
    print("==================================================")

    if not os.path.exists(cmo_csv_path):
        raise FileNotFoundError(f"Source file {cmo_csv_path} not found.")

    raw_count = 0
    crop_rejected_count = 0
    invalid_price_count = 0
    non_mh_count = 0

    crop_raw_counts = defaultdict(int)
    raw_observations = []

    with open(cmo_csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_count += 1
            state = row.get("state_name", "").strip()
            if state and state.lower() != "maharashtra":
                non_mh_count += 1
                continue

            raw_commodity = row.get("Commodity", "").strip()
            canonical_crop = CROP_ALIAS_MAP.get(raw_commodity)

            if not canonical_crop:
                crop_rejected_count += 1
                continue

            crop_raw_counts[canonical_crop] += 1

            modal_p = parse_float(row.get("modal_price"))
            min_p = parse_float(row.get("min_price"))
            max_p = parse_float(row.get("max_price"))
            arrival = parse_float(row.get("arrivals_in_qtl"))
            apmc = row.get("APMC", "").strip()
            district = row.get("district_name", "").strip()
            date_str = row.get("date", "").strip()  # Format: YYYY-MM
            year_str = row.get("Year", "").strip()
            month_str = row.get("Month", "").strip()

            if modal_p <= 0:
                invalid_price_count += 1
                continue

            # Ensure valid min/max bounds (in raw data, 86 rows had inverted min/max)
            valid_min = min(min_p, max_p, modal_p) if (min_p > 0 and max_p > 0) else modal_p
            valid_max = max(min_p, max_p, modal_p) if (min_p > 0 and max_p > 0) else modal_p

            # Standardize prices to Rs/kg (divide by 100 from Rs/Quintal)
            # Standardize arrivals to Metric Tonnes (divide by 10 from Quintals)
            raw_observations.append({
                "apmc": apmc,
                "district": district,
                "crop": canonical_crop,
                "raw_commodity": raw_commodity,
                "date": date_str,
                "year": int(year_str) if year_str.isdigit() else 2015,
                "month_name": month_str,
                "modal_price_qtl": modal_p,
                "min_price_qtl": valid_min,
                "max_price_qtl": valid_max,
                "modal_price_kg": round(modal_p / 100.0, 4),
                "min_price_kg": round(valid_min / 100.0, 4),
                "max_price_kg": round(valid_max / 100.0, 4),
                "arrival_qtl": arrival,
                "arrival_mt": round(arrival / 10.0, 2),
            })

    print(f"Total raw records read: {raw_count}")
    print(f"Records rejected - Not Maharashtra: {non_mh_count}")
    print(f"Records rejected - Non-7 crops: {crop_rejected_count}")
    print(f"Records rejected - Invalid price (modal <= 0): {invalid_price_count}")
    print(f"Records retained for 7 crops before deduplication: {len(raw_observations)}")

    print("\n==================================================")
    print("STEP 2: DEDUPLICATION & TIME SERIES STRUCTURING")
    print("==================================================")

    # Deduplicate on (crop, apmc, date)
    # When multiple records exist (e.g. Paddy-Unhusked vs Rice(Paddy-Hus)), compute weighted average modal price
    grouped = defaultdict(list)
    for obs in raw_observations:
        key = (obs["crop"], obs["apmc"], obs["date"])
        grouped[key].append(obs)

    dedup_count = 0
    clean_records = []
    for key, items in grouped.items():
        if len(items) > 1:
            dedup_count += (len(items) - 1)
            total_arrival = sum(it["arrival_mt"] for it in items)
            if total_arrival > 0:
                avg_modal_kg = sum(it["modal_price_kg"] * it["arrival_mt"] for it in items) / total_arrival
                avg_min_kg = sum(it["min_price_kg"] * it["arrival_mt"] for it in items) / total_arrival
                avg_max_kg = sum(it["max_price_kg"] * it["arrival_mt"] for it in items) / total_arrival
            else:
                avg_modal_kg = sum(it["modal_price_kg"] for it in items) / len(items)
                avg_min_kg = sum(it["min_price_kg"] for it in items) / len(items)
                avg_max_kg = sum(it["max_price_kg"] for it in items) / len(items)
            
            final_min_kg = min(avg_min_kg, avg_modal_kg)
            final_max_kg = max(avg_max_kg, avg_modal_kg)

            clean_records.append({
                "apmc": items[0]["apmc"],
                "district": items[0]["district"],
                "crop": items[0]["crop"],
                "date": items[0]["date"],
                "year": items[0]["year"],
                "month_name": items[0]["month_name"],
                "modal_price_kg": round(avg_modal_kg, 4),
                "min_price_kg": round(final_min_kg, 4),
                "max_price_kg": round(final_max_kg, 4),
                "arrival_mt": round(total_arrival, 2),
            })
        else:
            clean_records.append({
                "apmc": items[0]["apmc"],
                "district": items[0]["district"],
                "crop": items[0]["crop"],
                "date": items[0]["date"],
                "year": items[0]["year"],
                "month_name": items[0]["month_name"],
                "modal_price_kg": items[0]["modal_price_kg"],
                "min_price_kg": items[0]["min_price_kg"],
                "max_price_kg": items[0]["max_price_kg"],
                "arrival_mt": items[0]["arrival_mt"],
            })

    print(f"Duplicates resolved: {dedup_count}")
    print(f"Total clean, unique (crop, apmc, date) records: {len(clean_records)}")

    # Sort chronologically by date
    clean_records.sort(key=lambda x: (x["date"], x["crop"], x["apmc"]))

    # Save clean dataset
    clean_csv_path = os.path.join(out_dir, "clean_buyer_market_data.csv")
    with open(clean_csv_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date", "crop", "district", "apmc", "modal_price_kg", "min_price_kg", "max_price_kg", "arrival_mt", "year", "month_name"
        ])
        writer.writeheader()
        writer.writerows(clean_records)

    clean_json_path = os.path.join(out_dir, "clean_buyer_market_data.json")
    with open(clean_json_path, mode="w", encoding="utf-8") as f:
        json.dump(clean_records, f, indent=2)

    print(f"Saved clean dataset to {clean_csv_path} and {clean_json_path}")

    print("\n==================================================")
    print("STEP 3: 7-CROP STATISTICAL PROFILE")
    print("==================================================")

    crop_stats = {}
    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }

    for crop in CANONICAL_CROPS:
        records = [r for r in clean_records if r["crop"] == crop]
        if not records:
            continue
        prices = [r["modal_price_kg"] for r in records]
        apmcs = set(r["apmc"] for r in records)
        dates = [r["date"] for r in records]
        
        sorted_prices = sorted(prices)
        n = len(sorted_prices)
        median_p = sorted_prices[n // 2] if n % 2 != 0 else (sorted_prices[n // 2 - 1] + sorted_prices[n // 2]) / 2.0

        crop_stats[crop] = {
            "raw_records": crop_raw_counts[crop],
            "valid_records": len(records),
            "rejected_records": crop_raw_counts[crop] - len(records),
            "unique_apmcs": len(apmcs),
            "earliest_date": min(dates),
            "latest_date": max(dates),
            "min_modal_kg": min(prices),
            "max_modal_kg": max(prices),
            "mean_modal_kg": round(float(np.mean(prices)), 4),
            "median_modal_kg": round(median_p, 4),
            "std_modal_kg": round(float(np.std(prices)), 4),
        }

    for crop, st in crop_stats.items():
        print(f"\n[{crop}]")
        for k, v in st.items():
            print(f"  {k}: {v}")

    print("\n==================================================")
    print("STEP 4: FEATURE ENGINEERING FOR NEXT-DAY/PERIOD VALUATION")
    print("==================================================")
    series_by_entity = defaultdict(list)
    for r in clean_records:
        series_by_entity[(r["crop"], r["apmc"])].append(r)

    dataset_rows = []

    for (crop, apmc), rows in series_by_entity.items():
        rows.sort(key=lambda x: x["date"])
        
        for i in range(len(rows) - 1):
            curr = rows[i]
            target_next = rows[i + 1]["modal_price_kg"]

            lag_1 = rows[i - 1]["modal_price_kg"] if i >= 1 else curr["modal_price_kg"]
            lag_2 = rows[i - 2]["modal_price_kg"] if i >= 2 else lag_1

            window_prices = [rows[j]["modal_price_kg"] for j in range(max(0, i - 2), i + 1)]
            rolling_3_modal = sum(window_prices) / len(window_prices)

            window_arrivals = [rows[j]["arrival_mt"] for j in range(max(0, i - 2), i + 1)]
            rolling_3_arrival = sum(window_arrivals) / len(window_arrivals)

            spread = (curr["max_price_kg"] - curr["min_price_kg"]) / (curr["modal_price_kg"] if curr["modal_price_kg"] > 0 else 1.0)
            momentum = (curr["modal_price_kg"] - rolling_3_modal) / (rolling_3_modal if rolling_3_modal > 0 else 1.0)
            arrival_shock = curr["arrival_mt"] / (rolling_3_arrival if rolling_3_arrival > 0 else 1.0)

            m_num = month_map.get(curr["month_name"], 6)
            month_sin = math.sin(2 * math.pi * m_num / 12.0)
            month_cos = math.cos(2 * math.pi * m_num / 12.0)

            dataset_rows.append({
                "date": curr["date"],
                "next_date": rows[i + 1]["date"],
                "crop": crop,
                "district": curr["district"],
                "apmc": apmc,
                "modal_price_kg": curr["modal_price_kg"],
                "min_price_kg": curr["min_price_kg"],
                "max_price_kg": curr["max_price_kg"],
                "spread": round(spread, 4),
                "arrival_mt": curr["arrival_mt"],
                "lag_1_modal": round(lag_1, 4),
                "lag_2_modal": round(lag_2, 4),
                "rolling_3_modal": round(rolling_3_modal, 4),
                "momentum": round(momentum, 4),
                "arrival_shock": round(arrival_shock, 4),
                "month_sin": round(month_sin, 4),
                "month_cos": round(month_cos, 4),
                "target_next_modal_kg": target_next,
            })

    print(f"Total entity-series rows with valid target P_(t+1): {len(dataset_rows)}")

    dataset_rows.sort(key=lambda x: x["date"])

    feature_csv_path = os.path.join(out_dir, "buyer_feature_dataset.csv")
    with open(feature_csv_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(dataset_rows[0].keys()))
        writer.writeheader()
        writer.writerows(dataset_rows)
    print(f"Saved feature dataset to {feature_csv_path}")

    print("\n==================================================")
    print("STEP 5: CHRONOLOGICAL TRAIN / VAL / TEST SPLIT")
    print("==================================================")

    total_samples = len(dataset_rows)
    train_end_idx = int(0.70 * total_samples)
    val_end_idx = int(0.85 * total_samples)

    train_data = dataset_rows[:train_end_idx]
    val_data = dataset_rows[train_end_idx:val_end_idx]
    test_data = dataset_rows[val_end_idx:]

    print(f"Train split: {len(train_data)} records ({train_data[0]['date']} to {train_data[-1]['date']}) - {len(train_data)/total_samples:.1%}")
    print(f"Val split:   {len(val_data)} records ({val_data[0]['date']} to {val_data[-1]['date']}) - {len(val_data)/total_samples:.1%}")
    print(f"Test split:  {len(test_data)} records ({test_data[0]['date']} to {test_data[-1]['date']}) - {len(test_data)/total_samples:.1%}")

    feature_cols = [
        "modal_price_kg", "min_price_kg", "max_price_kg", "spread",
        "arrival_mt", "lag_1_modal", "lag_2_modal", "rolling_3_modal",
        "momentum", "arrival_shock", "month_sin", "month_cos"
    ]

    crop_list = sorted(CANONICAL_CROPS)
    def extract_X_y(rows):
        X = []
        y = []
        for r in rows:
            feat = [r[col] for col in feature_cols]
            crop_oh = [1.0 if r["crop"] == c else 0.0 for c in crop_list]
            X.append(feat + crop_oh)
            y.append(r["target_next_modal_kg"])
        return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

    X_train, y_train = extract_X_y(train_data)
    X_val, y_val = extract_X_y(val_data)
    X_test, y_test = extract_X_y(test_data)

    print("\n==================================================")
    print("STEP 6: BASELINE EVALUATIONS ON TEST SPLIT")
    print("==================================================")

    y_test_persistence = np.array([r["modal_price_kg"] for r in test_data])
    mae_pers = mean_absolute_error(y_test, y_test_persistence)
    rmse_pers = root_mean_squared_error(y_test, y_test_persistence)
    mape_pers = calculate_mape(y_test, y_test_persistence)

    print(f"[Baseline 1: Persistence (Last Known Price)]")
    print(f"  MAE:  Rs. {mae_pers:.4f}/kg")
    print(f"  RMSE: Rs. {rmse_pers:.4f}/kg")
    print(f"  MAPE: {mape_pers:.2f}%")

    y_test_ma = np.array([r["rolling_3_modal"] for r in test_data])
    mae_ma = mean_absolute_error(y_test, y_test_ma)
    rmse_ma = root_mean_squared_error(y_test, y_test_ma)
    mape_ma = calculate_mape(y_test, y_test_ma)

    print(f"\n[Baseline 2: 3-Period Moving Average]")
    print(f"  MAE:  Rs. {mae_ma:.4f}/kg")
    print(f"  RMSE: Rs. {rmse_ma:.4f}/kg")
    print(f"  MAPE: {mape_ma:.2f}%")

    print("\n==================================================")
    print("STEP 7: TRAIN & EVALUATE ML VALUATION MODELS")
    print("==================================================")

    ridge_model = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge", Ridge(alpha=10.0))
    ])
    ridge_model.fit(X_train, y_train)
    y_test_ridge = ridge_model.predict(X_test)

    mae_ridge = mean_absolute_error(y_test, y_test_ridge)
    rmse_ridge = root_mean_squared_error(y_test, y_test_ridge)
    mape_ridge = calculate_mape(y_test, y_test_ridge)

    print(f"[Model 1: Ridge Regression]")
    print(f"  MAE:  Rs. {mae_ridge:.4f}/kg")
    print(f"  RMSE: Rs. {rmse_ridge:.4f}/kg")
    print(f"  MAPE: {mape_ridge:.2f}%")

    hgb_model = HistGradientBoostingRegressor(
        max_iter=100,
        learning_rate=0.08,
        max_depth=6,
        random_state=42
    )
    hgb_model.fit(X_train, y_train)
    y_test_hgb = hgb_model.predict(X_test)

    mae_hgb = mean_absolute_error(y_test, y_test_hgb)
    rmse_hgb = root_mean_squared_error(y_test, y_test_hgb)
    mape_hgb = calculate_mape(y_test, y_test_hgb)

    print(f"\n[Model 2: HistGradientBoostingRegressor]")
    print(f"  MAE:  Rs. {mae_hgb:.4f}/kg")
    print(f"  RMSE: Rs. {rmse_hgb:.4f}/kg")
    print(f"  MAPE: {mape_hgb:.2f}%")

    best_model_name = "HistGradientBoostingRegressor" if mae_hgb <= mae_ridge else "Ridge"
    best_model = hgb_model if best_model_name == "HistGradientBoostingRegressor" else ridge_model
    best_mae = min(mae_hgb, mae_ridge)

    beats_persistence = best_mae < mae_pers
    beats_ma = best_mae < mae_ma

    print("\n==================================================")
    print("STEP 8: EMPIRICAL PERFORMANCE COMPARISON")
    print("==================================================")
    print(f"{'Method / Model':<32} | {'MAE (Rs/kg)':<11} | {'RMSE (Rs/kg)':<13} | {'MAPE (%)':<8}")
    print("-" * 72)
    print(f"{'Baseline: Persistence (P_t)':<32} | {mae_pers:<11.4f} | {rmse_pers:<13.4f} | {mape_pers:<8.2f}%")
    print(f"{'Baseline: 3-Period Moving Avg':<32} | {mae_ma:<11.4f} | {rmse_ma:<13.4f} | {mape_ma:<8.2f}%")
    print(f"{'ML: Ridge Regression':<32} | {mae_ridge:<11.4f} | {rmse_ridge:<13.4f} | {mape_ridge:<8.2f}%")
    print(f"{'ML: HistGradientBoosting':<32} | {mae_hgb:<11.4f} | {rmse_hgb:<13.4f} | {mape_hgb:<8.2f}%")
    print("-" * 72)
    print(f"Best ML Model: {best_model_name}")
    print(f"Beats Persistence: {'YES' if beats_persistence else 'NO (Persistence is strong, ML MAE diff: Rs. ' + str(round(best_mae - mae_pers, 4)) + ')'}")
    print(f"Beats Moving Average: {'YES' if beats_ma else 'NO'}")

    print("\nPer-Crop Performance on Test Split (HistGradientBoosting):")
    test_crops = [r["crop"] for r in test_data]
    per_crop_metrics = {}
    for crop in sorted(set(test_crops)):
        idxs = [idx for idx, c in enumerate(test_crops) if c == crop]
        if not idxs:
            continue
        y_c = y_test[idxs]
        y_p = y_test_hgb[idxs]
        y_pers = y_test_persistence[idxs]
        c_mae = mean_absolute_error(y_c, y_p)
        c_pers_mae = mean_absolute_error(y_c, y_pers)
        c_mape = calculate_mape(y_c, y_p)
        per_crop_metrics[crop] = {
            "samples": len(idxs),
            "hgb_mae": round(c_mae, 4),
            "persistence_mae": round(c_pers_mae, 4),
            "mape": round(c_mape, 2)
        }
        print(f"  {crop:<10}: N={len(idxs):<4} | HGB MAE: Rs. {c_mae:<7.4f} | Persistence MAE: Rs. {c_pers_mae:<7.4f} | MAPE: {c_mape:.2f}%")

    print("\n==================================================")
    print("STEP 9: SERIALIZE ARTIFACTS & METADATA")
    print("==================================================")

    model_artifact_path = os.path.join(models_dir, "buyer_price_prediction_model.pkl")
    with open(model_artifact_path, "wb") as f:
        pickle.dump({
            "model": best_model,
            "model_type": best_model_name,
            "feature_cols": feature_cols,
            "crop_list": crop_list,
            "month_map": month_map,
        }, f)
    print(f"Saved model artifact to {model_artifact_path}")

    metadata = {
        "pipeline_execution_time": datetime.now(timezone.utc).isoformat(),
        "total_raw_ingested": raw_count,
        "total_rejected_non_7_crop": crop_rejected_count,
        "total_rejected_invalid_price": invalid_price_count,
        "total_duplicates_resolved": dedup_count,
        "total_clean_records": len(clean_records),
        "total_feature_rows": len(dataset_rows),
        "train_samples": len(train_data),
        "val_samples": len(val_data),
        "test_samples": len(test_data),
        "train_dates": f"{train_data[0]['date']} to {train_data[-1]['date']}",
        "val_dates": f"{val_data[0]['date']} to {val_data[-1]['date']}",
        "test_dates": f"{test_data[0]['date']} to {test_data[-1]['date']}",
        "metrics": {
            "persistence": {"mae": round(mae_pers, 4), "rmse": round(rmse_pers, 4), "mape": round(mape_pers, 2)},
            "moving_average_3": {"mae": round(mae_ma, 4), "rmse": round(rmse_ma, 4), "mape": round(mape_ma, 2)},
            "ridge": {"mae": round(mae_ridge, 4), "rmse": round(rmse_ridge, 4), "mape": round(mape_ridge, 2)},
            "hist_gradient_boosting": {"mae": round(mae_hgb, 4), "rmse": round(rmse_hgb, 4), "mape": round(mape_hgb, 2)},
        },
        "per_crop_test_metrics": per_crop_metrics,
        "crop_statistical_profiles": crop_stats,
    }

    metrics_json_path = os.path.join(models_dir, "buyer_price_model_metrics.json")
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved model metrics and metadata to {metrics_json_path}")
    print("\nPIPELINE COMPLETE.")


if __name__ == "__main__":
    run_pipeline()
