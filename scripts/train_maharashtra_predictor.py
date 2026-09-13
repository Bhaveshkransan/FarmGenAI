"""
train_maharashtra_predictor.py
Trains an XGBoost price predictor on the realistic Maharashtra historical dataset.
Includes MSP as a feature and uses real crop-district data.
"""
import json, os, pickle
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.preprocessing import LabelEncoder

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'dataset', 'maharashtra_historical_prices.json')
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'models', 'maharashtra_price_model.pkl')

def train():
    print("Loading dataset...")
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    print(f"Loaded {len(df)} records for {df['crop'].nunique()} crops, {df['district'].nunique()} districts")

    # ── Feature Engineering ──────────────────────────────────────────────────
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['day_of_week'] = df['date'].dt.dayofweek
    df['day_of_year'] = df['date'].dt.dayofyear
    df['quarter'] = df['date'].dt.quarter

    # Season encoding: 1=Kharif(Jun-Oct), 2=Rabi(Nov-Mar), 3=Zaid(Apr-May)
    def get_season(m):
        if m in [6,7,8,9,10]: return 1
        elif m in [11,12,1,2,3]: return 2
        else: return 3
    df['season'] = df['month'].apply(get_season)

    # Encode categoricals
    crop_enc = LabelEncoder()
    dist_enc = LabelEncoder()
    df['crop_encoded'] = crop_enc.fit_transform(df['crop'])
    df['district_encoded'] = dist_enc.fit_transform(df['district'])

    # Fill MSP (Sugarcane and Onion have None)
    df['msp_per_kg'] = df['msp_per_kg'].fillna(0.0)

    # Sort for lag features
    df = df.sort_values(['crop_encoded', 'district_encoded', 'date']).reset_index(drop=True)

    # Lag features
    grp = df.groupby(['crop_encoded', 'district_encoded'])['price_per_kg']
    df['price_7d_ago']  = grp.shift(7)
    df['price_14d_ago'] = grp.shift(14)
    df['price_30d_ago'] = grp.shift(30)
    df['price_7d_rolling_avg'] = grp.transform(lambda x: x.shift(1).rolling(7, min_periods=1).mean())
    df['price_30d_rolling_avg'] = grp.transform(lambda x: x.shift(1).rolling(30, min_periods=5).mean())

    # Arrival lag
    grp_arr = df.groupby(['crop_encoded', 'district_encoded'])['arrival_mt']
    df['arrival_7d_avg'] = grp_arr.transform(lambda x: x.shift(1).rolling(7, min_periods=1).mean())

    df = df.dropna()

    features = [
        'crop_encoded', 'district_encoded',
        'month', 'day_of_week', 'day_of_year', 'quarter', 'season', 'year',
        'msp_per_kg',
        'arrival_mt', 'arrival_7d_avg',
        'price_7d_ago', 'price_14d_ago', 'price_30d_ago',
        'price_7d_rolling_avg', 'price_30d_rolling_avg'
    ]
    target = 'price_per_kg'

    X = df[features]
    y = df[target]

    # Chronological train/test split (80/20)
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print(f"\nTraining set: {len(X_train)} samples | Test set: {len(X_test)} samples")

    # ── XGBoost Model: Train one per crop for better accuracy ────────────────
    crop_models = {}
    print("\nTraining per-crop XGBoost models...")
    print(f"{'Crop':<25} {'MAE':>8} {'RMSE':>8} {'MAPE':>8} {'Records':>8}")
    print("-" * 65)
    
    for crop_name in sorted(df['crop'].unique()):
        cdf = df[df['crop'] == crop_name].copy()
        cX = cdf[features]
        cy = cdf['price_per_kg']
        
        split = int(len(cdf) * 0.8)
        cX_train, cX_test = cX.iloc[:split], cX.iloc[split:]
        cy_train, cy_test = cy.iloc[:split], cy.iloc[split:]
        
        m = xgb.XGBRegressor(
            n_estimators=200, learning_rate=0.05, max_depth=6,
            subsample=0.8, colsample_bytree=0.8, random_state=42, verbosity=0
        )
        m.fit(cX_train, cy_train)
        cy_pred = m.predict(cX_test)
        
        c_mae  = mean_absolute_error(cy_test, cy_pred)
        c_rmse = np.sqrt(mean_squared_error(cy_test, cy_pred))
        c_mape = np.mean(np.abs((cy_test.values - cy_pred) / cy_test.values)) * 100
        print(f"  {crop_name:<23} {c_mae:>7.2f}  {c_rmse:>7.2f}  {c_mape:>6.1f}%  {len(cdf):>6}")
        
        crop_models[crop_name] = m

    # ── Save per-crop model bundle ────────────────────────────────────────────
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    model_bundle = {
        'models': crop_models,          # dict: crop_name -> XGBRegressor
        'crop_encoder': crop_enc,
        'district_encoder': dist_enc,
        'features': features,
        'crops': list(crop_enc.classes_),
        'districts': list(dist_enc.classes_),
    }
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model_bundle, f)

    print(f"\nModel bundle saved to {MODEL_PATH}")
    print(f"Supported crops: {list(crop_enc.classes_)}")

if __name__ == "__main__":
    train()
