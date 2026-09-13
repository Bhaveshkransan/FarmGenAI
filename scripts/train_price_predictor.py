import json
import os
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.preprocessing import LabelEncoder
import pickle

def train_model():
    data_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'dataset', 'mock_historical_prices.json')
    if not os.path.exists(data_path):
        print(f"Dataset not found at {data_path}. Please run generate_mock_history.py first.")
        return

    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    
    # Feature Engineering
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.month
    df['day_of_week'] = df['date'].dt.dayofweek
    df['day_of_year'] = df['date'].dt.dayofyear
    
    # Encode categorical variables
    crop_encoder = LabelEncoder()
    district_encoder = LabelEncoder()
    
    df['crop_encoded'] = crop_encoder.fit_transform(df['crop'])
    df['district_encoded'] = district_encoder.fit_transform(df['district'])

    # Sort by date for lag features
    df = df.sort_values(by=['crop_encoded', 'district_encoded', 'date'])

    # Create lag features (e.g. price 7 days ago)
    # Since we have multiple records per crop/district, we group by them
    df['price_7d_ago'] = df.groupby(['crop_encoded', 'district_encoded'])['price_per_kg'].shift(7)
    df['price_30d_ago'] = df.groupby(['crop_encoded', 'district_encoded'])['price_per_kg'].shift(30)
    
    # Drop rows with NaN lag features (first 30 days will be dropped)
    df = df.dropna()

    features = ['crop_encoded', 'district_encoded', 'month', 'day_of_week', 'day_of_year', 'arrival_mt', 'price_7d_ago', 'price_30d_ago']
    target = 'price_per_kg'

    X = df[features]
    y = df[target]

    # Chronological split (train on past, test on recent)
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print("Training XGBoost Regressor...")
    model = xgb.XGBRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=6,
        random_state=42
    )

    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    print(f"Model trained! MSE: {mse:.2f}, MAE: {mae:.2f}")

    # Save model and encoders
    model_dir = os.path.join(os.path.dirname(__file__), '..', 'backend', 'models')
    os.makedirs(model_dir, exist_ok=True)
    
    model_path = os.path.join(model_dir, 'xgboost_price_model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'crop_encoder': crop_encoder,
            'district_encoder': district_encoder,
            'features': features
        }, f)

    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_model()
