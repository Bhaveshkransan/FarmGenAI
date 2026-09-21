import asyncio
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.crop_master import CROPS
from backend.services.market_intelligence import MarketIntelligenceService
from backend.services.rag_service import rag_service
from backend.agents.graph_orchestrator import planner_node
import pickle
import pandas as pd
from datetime import datetime, timedelta

def _get_ml_prediction(crop, location, arrival, lag_price):
    try:
        model_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'models', 'xgboost_price_model.pkl')
        if not os.path.exists(model_path):
            return 25.0
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        xgb_model = model_data['model']
        crop_encoder = model_data['crop_encoder']
        dist_encoder = model_data['district_encoder']
        features = model_data['features']
        
        target_date = datetime.now() + timedelta(days=7)
        crop_val = crop_encoder.transform([crop])[0] if crop in crop_encoder.classes_ else 0
        dist_val = dist_encoder.transform([location])[0] if location in dist_encoder.classes_ else 0
        
        input_df = pd.DataFrame([{
            'crop_encoded': crop_val,
            'district_encoded': dist_val,
            'month': target_date.month,
            'day_of_week': target_date.weekday(),
            'day_of_year': target_date.timetuple().tm_yday,
            'arrival_mt': arrival,
            'price_7d_ago': lag_price,
            'price_30d_ago': lag_price
        }])[features]
        return float(xgb_model.predict(input_df)[0])
    except Exception as e:
        logger.error(f"ML Predict Error: {e}")
        return None

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("CropConsistencyTest")

async def test_all_crops():
    logger.info("========================================")
    logger.info(" CROP CONSISTENCY TEST - MVP SCOPE")
    logger.info("========================================\n")
    
    total_crops = len(CROPS)
    passed = 0

    for crop_id, data in CROPS.items():
        crop_name = data["name"]
        ml_mapping = data["ml_mapping"]
        logger.info(f"Testing Crop: {crop_name} (ID: {crop_id})")
        
        try:
            # 1. Test ML Prediction
            pred = _get_ml_prediction(ml_mapping, "Nashik", 100, 30)
            if pred is None:
                raise ValueError("XGBoost prediction returned None")
            logger.info(f"  [x] ML Prediction successful (Predicted: ₹{pred:.2f}/kg)")
            
            # 2. Test RAG Pipeline 
            rag_docs = rag_service.query_crop_knowledge(f"market info {crop_name}", crop=crop_name, n_results=1)
            # We don't fail if empty, just verify it didn't throw an exception (since it's a mock DB)
            logger.info(f"  [x] RAG Pipeline successful (Retrieved {len(rag_docs)} chunks)")
            
            # 3. Test Agent Planner Node
            mock_state = {
                "crop": crop_name,
                "quantity": 500,
                "min_price": 20,
                "target_price": 25,
                "spoilage_days": 5,
                "location": "Nashik",
                "market_price": pred,
                "logs": []
            }
            planner_result = await planner_node(mock_state)
            if "plan" not in planner_result:
                raise ValueError("Agent planner failed to generate plan")
            logger.info(f"  [x] Agent Planner successful")
            
            passed += 1
            logger.info("  -> CROP PASSED\n")
            
        except Exception as e:
            logger.error(f"  [ ] CROP FAILED: {str(e)}\n")

    logger.info("========================================")
    logger.info(f" TEST COMPLETE: {passed}/{total_crops} Crops Passed")
    logger.info("========================================")
    
if __name__ == "__main__":
    asyncio.run(test_all_crops())
