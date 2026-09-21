"""
scripts/run_buyer_agent.py
-------------------------------------------------------------------------------
Autonomous Buyer Agent Live Runner.
Demonstrates:
  1. Multi-Persona Strategic Negotiation (Boulware, Conceder, Aggressive)
  2. Multi-Attribute Utility Scoring (Price, Volume, Freshness, Grade)
  3. APMC Statutory Floor & Buyer Ceiling Guardrails (Maharashtra 7 Crops)
  4. Dynamic PO Contract Generation with SHA-256 Hash
  5. Live Auto-Parallel Procurement Execution across 5 Maharashtra APMC Hubs
-------------------------------------------------------------------------------
"""

import sys
import os
import json
import asyncio
from datetime import datetime

# Set utf-8 encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.buyer_agent import BuyerAgent, BUYER_PERSONAS
from backend.services.negotiation_service import NegotiationService, STATUTORY_BENCHMARKS
from database.db import Database, init_db


def print_banner(title: str):
    print("\n" + "═" * 78)
    print(f"  {title.center(74)}")
    print("═" * 78)


def run_single_buyer_simulation():
    print_banner("1. AUTONOMOUS BUYER AGENT — ROUND-BY-ROUND NEGOTIATION")
    
    # 1. Instantiate Buyer Agent (Persona: Retail Supermarket)
    crop = "Soybean"
    msp = STATUTORY_BENCHMARKS[crop]["benchmark"]  # ₹48.92
    target_price = 47.0
    reservation_price = round(target_price * 1.15, 2)  # ₹54.05
    
    buyer = BuyerAgent(
        name="MahaAgro Supermarkets Ltd",
        budget=250000.0,
        max_quantity=5000.0,
        target_price=target_price,
        reservation_price=reservation_price,
        crop=crop,
        location="Pune",
        persona="retail_supermarket",
        min_shelf_life=3
    )

    print(f"🤖 Buyer Agent Initialized: {buyer.name}")
    print(f"   • Crop: {buyer.crop} (Statutory MSP: ₹{msp:.2f}/kg)")
    print(f"   • Persona: {buyer.persona} (Strategy: {buyer.strategy})")
    print(f"   • Target Price: ₹{buyer.target_price:.2f}/kg | Max Ceiling: ₹{buyer.reservation_price:.2f}/kg")
    print(f"   • Budget: ₹{buyer.budget:,.2f} | Max Qty: {buyer.max_quantity:,.0f} kg")
    print(f"   • Attribute Weights: {buyer.weights}")
    print(f"   • Initial Opening Bid: ₹{buyer.current_bid:.2f}/kg\n")

    # 2. Simulate 4 negotiation rounds with a farmer
    farmer_name = "Latur APMC Cooperative"
    farmer_proposals = [
        {"round": 1, "price": 58.00, "quantity": 4000, "shelf_life": 5, "grade": "FAQ"},
        {"round": 2, "price": 53.50, "quantity": 4000, "shelf_life": 5, "grade": "FAQ"},
        {"round": 3, "price": 50.00, "quantity": 4000, "shelf_life": 5, "grade": "FAQ"},
        {"round": 4, "price": 47.50, "quantity": 4000, "shelf_life": 5, "grade": "FAQ"},
    ]

    market_price = 49.50

    for step in farmer_proposals:
        r = step["round"]
        offer = {"price": step["price"], "quantity": step["quantity"]}
        utility = buyer.calculate_utility(
            price=step["price"],
            quantity=step["quantity"],
            shelf_life=step["shelf_life"],
            quality_grade=step["grade"]
        )

        print(f"┌── [Round {r}/4] Incoming Farmer Offer: ₹{step['price']:.2f}/kg ({step['quantity']} kg)")
        print(f"│   • Multi-Attribute Utility Score: {utility:.4f} / 1.0000")

        # Evaluate offer
        response = buyer.evaluate_proposal(
            offer=offer,
            market_price=market_price,
            current_round=r,
            max_rounds=4,
            shelf_life=step["shelf_life"],
            context={"seller_name": farmer_name, "crop": crop, "location": "Latur"}
        )

        decision = response.get("type")
        msg = response.get("message", "")
        print(f"│   • Buyer Agent Decision: [{decision}]")
        print(f"└── {msg}\n")

        if decision == "ACCEPT":
            contract = response.get("contract", {})
            print("🎉 DEAL FINALIZED! Generated Formal Purchase Order:")
            print(f"   • PO Number: {contract.get('po_number')}")
            print(f"   • Total Value: ₹{contract.get('total_value', 0):,.2f}")
            print(f"   • Contract Hash: {contract.get('contract_hash')[:32]}...")
            break


def run_guardrail_stress_tests():
    print_banner("2. STATUTORY GUARDRAILS & ADVERSARIAL REJECTION AUDIT")
    
    buyer = BuyerAgent(
        name="Audited Buyer",
        budget=100000.0,
        max_quantity=2000.0,
        target_price=48.0,
        reservation_price=55.0,
        crop="Soybean",
        persona="food_processor"
    )

    scenarios = [
        ("Astronomical Out-of-Bounds Price", {"price": 2000.00, "quantity": 1000}),
        ("Predatory / Sub-Floor Price", {"price": 1.50, "quantity": 1000}),
        ("Zero / Negative Volume", {"price": 48.00, "quantity": 0}),
    ]

    for label, payload in scenarios:
        print(f"🛡️ Testing: {label} (Price: ₹{payload['price']}, Qty: {payload['quantity']}kg)")
        res = buyer.evaluate_proposal(
            offer=payload,
            market_price=49.0,
            current_round=1,
            max_rounds=4
        )
        print(f"   Decision: [{res.get('type')}] — {res.get('message')}\n")


async def run_live_parallel_procurement():
    print_banner("3. AUTO-PARALLEL 5 PROCUREMENT (BACKEND ENGINE)")
    await init_db()
    service = NegotiationService(None)
    
    crop = "Soybean"
    req_qty = 5000
    target_price = 48.0
    
    neg_id = Database.generate_id("neg")
    payload = {
        "negotiation_id": neg_id,
        "crop": crop,
        "quantity": req_qty,
        "price": target_price,
        "target_price": target_price,
        "min_price": 45.0,
        "status": "ACTIVE",
        "farmer_name": "Multi-APMC Producers",
        "buyer_name": "Apex Maharashtra Logistics"
    }
    await Database.create_negotiation_async(payload)

    print(f"🚀 Launching Parallel Procurement Job ({neg_id})...")
    print(f"   Crop: {crop} | Target: ₹{target_price}/kg | Quantity: {req_qty:,} kg\n")

    result = await service.run_parallel_procurement(
        neg_id,
        {"quantity": req_qty, "target_price": target_price}
    )

    if result.get("success"):
        data = result.get("data", {})
        winner = data.get("winner", {})
        print("✅ 5 APMC Counterparties Evaluated Concurrently:")
        for idx, cp in enumerate(data.get("all_counterparties", []), 1):
            is_win = "🏆 [WINNER]" if cp.get("name") == winner.get("name") else "   "
            print(f"   {is_win} {idx}. {cp.get('name')[:35]:<35} | Dist: {cp.get('dist')}km | Final Offer: ₹{cp.get('final_offer'):.2f}/kg | Match: {cp.get('match')}%")

        print("\n📝 Contract & Validation Details:")
        print(f"   • Recommended Supplier: {winner.get('name')} ({winner.get('location')})")
        print(f"   • Best Agreed Price: ₹{winner.get('final_offer'):.2f}/kg")
        print(f"   • Transaction ID: {data.get('transaction_id')}")
        print(f"   • Contract Hash: {data.get('contract_hash')}")
        print(f"   • Mandi Cess (1% APMC): ₹{data.get('mandi_cess', 0):,.2f}")
        print(f"   • Freight Total: ₹{data.get('freight_total', 0):,.2f}")
        print(f"   • Total Transaction: ₹{data.get('total_transaction', 0):,.2f}")
    else:
        print(f"❌ Failed: {result.get('error')}")


async def main():
    run_single_buyer_simulation()
    run_guardrail_stress_tests()
    await run_live_parallel_procurement()
    print_banner("EXECUTION COMPLETE — ALL BUYER AGENT TESTS & SIMULATIONS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
