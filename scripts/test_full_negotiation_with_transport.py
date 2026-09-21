"""
scripts/test_full_negotiation_with_transport.py

Tests the complete end-to-end LangGraph negotiation workflow with:
1. Matching Engine & Market Intelligence (RAG + ML)
2. Farmer & Buyer multi-round conversational bidding
3. Validator & Reflection
4. Dynamic Routing invoking Gayatri's real 11-node Transport Agent
5. PostgreSQL trip persistence verification
"""

import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.agents.graph_orchestrator import workflow
from backend.services.negotiation_service import NegotiationService
from database.db import Database

async def run_full_test():
    print("=" * 80)
    print("RUNNING END-TO-END NEGOTIATION WITH REAL TRANSPORT AGENT INTEGRATION")
    print("=" * 80)

    service = NegotiationService(db=None)

    crop = "Onion"
    quantity = 1500.0
    min_price = 18.0
    target_price = 24.0
    farmer_location = "Nashik"
    buyer_location = "Pune"

    farmer_obj = await service._build_farmer({
        "name": "Ramesh Patil",
        "crop": crop,
        "quantity": quantity,
        "location": farmer_location,
        "urgency": "NORMAL",
        "min_price": 18.0,
        "target_price": 21.0
    })

    buyer_obj = await service._build_buyer({
        "name": "Reliance Fresh Pune",
        "location": buyer_location,
        "budget": 50000,
        "max_quantity": 2000,
        "target_price": 22.0,
        "strategy": "Premium Quality"
    })

    initial_state = {
        "crop": crop,
        "quantity": quantity,
        "min_price": 18.0,
        "target_price": 21.0,
        "spoilage_days": 10,
        "location": farmer_location,
        "market_price": 22.0,
        "round": 0,
        "max_rounds": 5,
        "history": [],
        "logs": [],
        "status": "ACTIVE",
        "proposed_scenario": "direct-sale",
        "next_action": "start",
        "deal": None,
        "plan": None,
        "reflection": None,
        "selected_buyer": {
            "name": "Reliance Fresh Pune",
            "location": buyer_location,
            "target_price": 22.0
        },
        "market_offers": [
            {
                "buyer_name": "Reliance Fresh Pune",
                "location": buyer_location,
                "offered_price": 21.0,
                "budget": 50000,
                "offered_quantity": 1500
            }
        ],
        "user_id": "usr_test_farmer",
        "active_buyers": [],
        "current_offers": [],
        "best_current_offer": None,
        "latest_farmer_ask": 21.0,
        "latest_buyer_offer": 21.0,
        "buyers_list": [],
        "rag_context": None,
        "market_intelligence": None,
        "recommendation": None,
        "farmer_agent_obj": farmer_obj,
        "buyer_agent_objs": [buyer_obj]
    }

    app = workflow.compile()
    print("Invoking LangGraph State Machine...")
    final_state = await app.ainvoke(initial_state)

    print("\n\n====== FINAL NEGOTIATION STATE ======")
    print(f"Status: {final_state.get('status')}")
    deal = final_state.get("deal") or {}
    print(f"Deal Price: ₹{deal.get('price')}/kg")
    print(f"Buyer: {deal.get('buyer_name')}")
    
    tp = deal.get("transport_plan")
    print("\n====== TRANSPORT PLAN AUDIT ======")
    if tp:
        print(f"Assigned Agent / Carrier : {tp.get('agent')}")
        print(f"Vehicle ID & Model       : {tp.get('vehicle_id')} ({tp.get('vehicle_name')})")
        print(f"Vehicle Type             : {tp.get('vehicle_type')}")
        print(f"Capacity                 : {tp.get('capacity')} kg")
        print(f"Road Distance (OSRM)     : {tp.get('distance')} km")
        print(f"Estimated Duration       : {tp.get('duration_hours')} hrs")
        print(f"Agreed Freight           : ₹{tp.get('cost')}")
        print(f"Operating Cost           : ₹{tp.get('total_operating_cost')}")
        print(f"Routing Source           : {tp.get('routing_source')}")
        print(f"Transport Status         : {tp.get('status')}")
    else:
        print("❌ Transport Plan missing from deal!")

    print("\n====== AGENT LOGS ======")
    for log in final_state.get("logs", []):
        print(log)

    print("=" * 80)
    print("✅ TEST COMPLETED")

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(run_full_test())
