import asyncio, json
from backend.services.supply_chain_intelligence_service import supply_chain_intelligence_service

async def main():
    print("Testing Infeasible Shelf Life (Sugarcane 14 days holding):")
    req_sugar = {
        "crop": "Sugarcane",
        "quantity": 10000.0,
        "pickup_location": "Kolhapur",
        "location": "Pune",
        "holding_days": 14, # Exceeds Sugarcane max shelf life of 4 days!
        "budget": 50000.0,
        "target_price": 3.5,
        "max_price": 3.8,
        "delivery_days": 7,
        "need_storage": True,
        "need_transport": True,
        "user_id": "usr_buyer_demo"
    }
    sci_sugar = await supply_chain_intelligence_service.optimize_supply_chain(req_sugar)
    print("Status:", sci_sugar.get("status"))
    print("Is Feasible:", sci_sugar.get("is_feasible"))
    print("Relaxation Advice:", sci_sugar.get("relaxation_advice"))
    if sci_sugar.get("all_evaluated_options"):
        print("Top Infeasibility Reasons:", sci_sugar["all_evaluated_options"][0].get("infeasibility_reasons"))

if __name__ == "__main__":
    asyncio.run(main())
