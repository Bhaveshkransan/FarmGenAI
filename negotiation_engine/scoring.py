"""
negotiation_engine/scoring.py - Scenario Scoring Engine
Calculates scores (0-100) for different supply chain outcomes.
"""

def calculate_scenario_score(scenario_data: dict) -> dict:
    """
    Calculates a multi-dimensional score for a given negotiation outcome.
    
    Args:
        scenario_data (dict): Contains 'final_price', 'min_price', 'target_price', 
                             'status', 'scenario_type', and 'shelf_life'.
    
    Returns:
        dict: Total score and breakdown.
    """
    status = scenario_data.get("status", "FAILED")
    scenario_type = scenario_data.get("scenario_type", "direct-sale")
    final_price = scenario_data.get("final_price") or 0
    min_price = scenario_data.get("min_price") or 1  # avoid division by zero
    target_price = scenario_data.get("target_price") or final_price or min_price

    # 1. Price Satisfaction (40%)
    if status in ("CONTRACT", "DEAL") and final_price:
        if final_price >= min_price:
            price_score = min(max(((final_price / min_price) * 100), 0), 100)
        else:
            price_score = 0
    else:
        price_score = 0

    # 2. Waste Reduction / Spoilage Mitigation (20%)
    waste_map = {
        "direct-sale": 100,
        "storage": 80,
        "processing": 60,
        "compost": 30,
        "failed": 0
    }
    waste_score = waste_map.get(scenario_type if status in ("CONTRACT", "DEAL") else "failed", 0)

    # 3. Speed / Freshness (20%)
    shelf_life = scenario_data.get("shelf_life") or 1
    freshness_score = min(shelf_life * 20, 100)
    
    # 4. Quantity Fulfillment (20%)
    requested_quantity = float(scenario_data.get("quantity") or 1)
    offered_quantity = float(scenario_data.get("offered_quantity") or requested_quantity)
    quantity_score = min((offered_quantity / max(requested_quantity, 1)) * 100, 100) if status in ("CONTRACT", "DEAL") else 0

    # Weighted Average (Farmer-First Index)
    total_score = (price_score * 0.4) + (waste_score * 0.2) + (freshness_score * 0.2) + (quantity_score * 0.2)
    
    return {
        "score": round(total_score, 1),
        "breakdown": {
            "price_satisfaction": round(price_score, 1),
            "waste_reduction": round(waste_score, 1),
            "freshness": round(freshness_score, 1),
            "quantity_fulfillment": round(quantity_score, 1)
        }
    }
