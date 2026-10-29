from backend.services.price_prediction_service import predict_price_xgboost

print("=== XGBOOST 7-CROP INFERENCE TEST ===")
crops = ["Sugarcane", "Soybean", "Cotton", "Jowar", "Onion", "Bajra", "Rice"]
for crop in crops:
    res = predict_price_xgboost(crop=crop, location="Latur", current_modal_price=50.0, days_ahead=7)
    fp = res.get('forecast_price') or res.get('predicted_price')
    print(f"  [{crop}]: forecast_price={fp} | direction={res.get('direction')} | pct_change={res.get('pct_change')}% | model={res.get('model_type')}")
    assert fp is not None and fp > 0, f"Failed prediction for {crop}"

print("\nALL 7 CROPS PREDICTED SUCCESSFULLY VIA XGBOOST!")
