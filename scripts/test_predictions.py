import pickle, pandas as pd
from datetime import datetime, timedelta
import os
model_path = os.path.join(os.path.dirname(__file__), "..", "backend", "models", "maharashtra_price_model.pkl")
if not os.path.exists(model_path):
    model_path = "/app/backend/models/maharashtra_price_model.pkl"

d = pickle.load(open(model_path, 'rb'))
models = d['models']
crop_enc = d['crop_encoder']
dist_enc = d['district_encoder']
features = d['features']

MSP  = {'Bajra':27.75,'Cotton':66.20,'Jowar':36.99,'Onion':0.0,'Rice':23.69,'Soybean':53.28,'Sugarcane':3.40}
BASE = {'Bajra':35.58,'Cotton':65.0,'Jowar':60.0,'Onion':22.0,'Rice':34.71,'Soybean':69.64,'Sugarcane':3.75}

t = datetime.now() + timedelta(days=7)
month = t.month
season = 1 if month in [6,7,8,9,10] else (2 if month in [11,12,1,2,3] else 3)

print("7-Day XGBoost Forecasts | Maharashtra Crops")
print("="*60)

for crop in ['Sugarcane','Soybean','Cotton','Jowar','Onion','Bajra','Rice']:
    cur = BASE[crop]
    msp = MSP[crop]
    cv = crop_enc.transform([crop])[0]
    dv = dist_enc.transform(['Nashik'])[0]
    row = {
        'crop_encoded': cv, 'district_encoded': dv,
        'month': month, 'day_of_week': t.weekday(),
        'day_of_year': t.timetuple().tm_yday,
        'quarter': (month-1)//3+1, 'season': season, 'year': t.year,
        'msp_per_kg': msp, 'arrival_mt': 100.0, 'arrival_7d_avg': 100.0,
        'price_7d_ago': cur, 'price_14d_ago': cur, 'price_30d_ago': cur,
        'price_7d_rolling_avg': cur, 'price_30d_rolling_avg': cur
    }
    pred = float(models[crop].predict(pd.DataFrame([row])[features])[0])
    chg = (pred - cur) / cur * 100
    sig = "HOLD" if pred > cur else "SELL"
    print(f"{crop:<12} Now: Rs.{cur:>6.2f}  Forecast: Rs.{pred:>6.2f}  ({chg:+.1f}%)  [{sig}]")
