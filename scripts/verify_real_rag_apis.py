import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'TestClient'})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return resp.status, json.loads(resp.read().decode())

print("=== 1. SYSTEM HEALTH ===")
s, h = get("http://localhost:8000/health")
print(f"Health: {s}, {h}")

print("\n=== 2. LIVE APMC MARKET PRICES FOR 7 CROPS ===")
for crop in ["Soybean", "Cotton", "Sugarcane", "Onion", "Bajra", "Jowar", "Rice"]:
    s, p = get(f"http://localhost:8000/api/v1/market-intelligence/price?crop={crop}&location=Maharashtra")
    pdata = p.get("data", {}).get("price_data", {})
    print(f"  {crop:10s} -> Modal: Rs {pdata.get('modal_price')}/kg (Mandi: {pdata.get('mandi')}, Source: {pdata.get('source')})")

print("\n=== 3. MANDIMITRA COMPARISON ===")
s, comp = get("http://localhost:8000/api/v1/market-intelligence/compare?crop=Soybean&lat=18.4088&lon=76.5604&radius_km=300")
data = comp.get("data", {})
best = data.get("best_option", {})
print(f"Mandis found: {len(data.get('mandis', []))}")
print(f"Best APMC: {best.get('mandi_name')} | Modal: Rs {best.get('modal_price')}/kg | Transport: Rs {best.get('transport_cost')}/kg | Net: Rs {best.get('net_realization')}/kg")
print(f"Data source: {data.get('data_source')}")

print("\n=== 4. REAL RAG + ML MARKET INSIGHTS ===")
s, ins = get("http://localhost:8000/api/v1/market-intelligence/insights?crop=Soybean&location=Latur")
idata = ins.get("data", {})
print(f"Crop: {idata.get('crop')} in {idata.get('location')}")
print(f"Live Price: Rs {idata.get('live_price')}/kg | Trend: {idata.get('trend')}")
print(f"ML Forecast: {idata.get('ml_prediction')}")
print(f"Recommendation: {idata.get('recommendation')[:160]}...")

chart = idata.get("chart_data", [])
print(f"\nChart Data Points: {len(chart)}")
historical = [p for p in chart if p.get("type") == "Historical"]
live = [p for p in chart if p.get("type") == "Live"]
forecast = [p for p in chart if p.get("type") == "Forecast"]
print(f"  Historical points ({len(historical)}): {historical}")
print(f"  Live point: {live}")
print(f"  Forecast points ({len(forecast)}): {forecast}")
