"""
scripts/run_top5_buyer_orchestration.py
------------------------------------------------------------------------
Terminal / Chat-Style Demonstration of Autonomous Top-5 Buyer Negotiation Orchestration.

Demonstrates:
  1. User Requirement Input (Crop, Quantity, Target, Reservation Price, Budget).
  2. Candidate Discovery (Top 5 eligible sellers).
  3. Parallel Multi-Round Negotiation Execution with complete state isolation.
  4. Strict Deterministic Economic Protection (Bajra Bug: Reservation ₹3000 vs Asks ₹3500+ -> NO DEAL).
  5. Multi-Criteria Landed Cost Evaluation (Base Rate + Freight + APMC Cess).
  6. Final Valid Deal Selection OR Deterministic "NO_EXECUTABLE_DEAL".
"""

import sys
import os
import asyncio

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.services.buyer_orchestrator import buyer_orchestration_service


async def run_scenario_bajra_above_reservation():
    print("\n" + "=" * 75)
    print("▶ SCENARIO A & B: BAJRA PROCUREMENT (ALL SELLERS ABOVE RESERVATION CEILING)")
    print("=" * 75)

    bajra_req = {
        "crop": "Bajra",
        "quantity": 1000.0,
        "target_price": 2700.0,
        "reservation_price": 3000.0,
        "max_price": 3000.0,
        "budget": 3000000.0,
        "location": "Ahmednagar",
        "buyer_name": "Metro Food Wholesalers",
        "persona": "bulk_wholesaler",
        "strategy": "aggressive",
        "sellers": [
            {
                "id": "seller_1",
                "name": "Dhule Millet Producer Co.",
                "crop": "Bajra",
                "quantity": 1200.0,
                "price": 3500.0,
                "floor_price": 3400.0,
                "location": "Dhule",
                "distance_km": 190.0,
                "special": "Grade A Pearl Millet",
            },
            {
                "id": "seller_2",
                "name": "Nashik Agro Grain Consortium",
                "crop": "Bajra",
                "quantity": 1000.0,
                "price": 3450.0,
                "floor_price": 3350.0,
                "location": "Nashik",
                "distance_km": 140.0,
                "special": "Cleaned Bold Grain",
            },
            {
                "id": "seller_3",
                "name": "Jalgaon Millet Pool",
                "crop": "Bajra",
                "quantity": 1500.0,
                "price": 3600.0,
                "floor_price": 3450.0,
                "location": "Jalgaon",
                "distance_km": 230.0,
                "special": "Direct APMC Lot",
            },
            {
                "id": "seller_4",
                "name": "Sangamner Farmers Union",
                "crop": "Bajra",
                "quantity": 800.0,
                "price": 3550.0,
                "floor_price": 3300.0,
                "location": "Sangamner",
                "distance_km": 80.0,
                "special": "Graded Kernel Lot",
            },
            {
                "id": "seller_5",
                "name": "Solapur Millets Co-op",
                "crop": "Bajra",
                "quantity": 1000.0,
                "price": 3500.0,
                "floor_price": 3250.0,
                "location": "Solapur",
                "distance_km": 210.0,
                "special": "Sun-Dried Stock",
            },
        ],
    }

    result = await buyer_orchestration_service.orchestrate_negotiation(bajra_req, max_candidates=5)
    print(result["chat_transcript"])
    print(f"\nFinal Execution Status: {result['status']}")
    print(f"Final Winner Selected: {result['winner']}")
    assert result["winner"] is None, "FAILURE: Winner must be None when all asks exceed reservation ceiling!"
    assert result["status"] == "NO_EXECUTABLE_DEAL", "FAILURE: Status must be NO_EXECUTABLE_DEAL!"
    print("✔ Bajra bug protection verified: 0 deals accepted above ₹3,000/kg ceiling.")


async def run_scenario_soybean_valid_deals():
    print("\n" + "=" * 75)
    print("▶ SCENARIO D: SOYBEAN PROCUREMENT (COMPETITIVE NEGOTIATIONS WITHIN ZOPA)")
    print("=" * 75)

    soybean_req = {
        "crop": "Soybean",
        "quantity": 500.0,
        "target_price": 46.0,
        "reservation_price": 52.0,
        "max_price": 52.0,
        "budget": 30000.0,
        "location": "Pune",
        "buyer_name": "Sahyadri Oil Mills",
        "persona": "bulk_wholesaler",
        "strategy": "balanced",
    }

    result = await buyer_orchestration_service.orchestrate_negotiation(soybean_req, max_candidates=5)
    print(result["chat_transcript"])
    print(f"\nFinal Execution Status: {result['status']}")
    if result["winner"]:
        print(f"✔ Deal locked with winner: {result['winner']['seller_name']} at ₹{result['winner']['final_price']}/kg")
        print(f"  True Landed Cost: ₹{result['winner']['landed_cost_per_kg']}/kg")
    else:
        print("  No executable deal reached.")


async def main():
    print("\n" + "#" * 75)
    print("# AgriNegotiator — Priority 5C Top-5 Buyer Negotiation Terminal Suite")
    print("#" * 75)

    await run_scenario_bajra_above_reservation()
    await run_scenario_soybean_valid_deals()


if __name__ == "__main__":
    asyncio.run(main())
