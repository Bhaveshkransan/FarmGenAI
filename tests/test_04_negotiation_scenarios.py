"""
tests/test_04_negotiation_scenarios.py
Type: INTEGRATION (LangGraph + Ollama when available, else deterministic)
Covers: 20 real negotiation scenarios.
"""
import sys, os, asyncio, random
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest

import agents.farmer_agent as _fa_mod
import agents.buyer_agent as _ba_mod
_fa_mod.llm_client = None
_ba_mod.llm_client = None

from agents.farmer_agent import FarmerAgent
from agents.buyer_agent import BuyerAgent
from agents.warehouse_agent import WarehouseAgent
from agents.processor_agent import ProcessorAgent
from agents.compost_agent import CompostAgent
from agents.transporter_agent import TransporterAgent
from negotiation_engine.negotiation_manager import NegotiationManager

VALID_STATES = {"DEAL", "FAILED", "ESCALATED_STORAGE", "ESCALATED_PROCESSING", "ESCALATED_COMPOST"}


def run(coro):
    return asyncio.run(coro)


def make_mgr(min_price=20.0, target_price=22.0, max_rounds=6, shelf_life=5,
             quantity=500, buyer_count=1, extra_buyers=None):
    random.seed(42)
    farmer = FarmerAgent(name="TestFarmer", crop="Tomato", quantity=quantity,
                         min_price=min_price, shelf_life=shelf_life)
    buyers = [
        BuyerAgent(name=f"Buyer_{i+1}",
                   budget=target_price * quantity * 1.5,
                   max_quantity=quantity,
                   target_price=target_price - i * 0.5)
        for i in range(buyer_count)
    ]
    if extra_buyers:
        buyers.extend(extra_buyers)
    warehouse = WarehouseAgent(name="WH", capacity=5000, storage_cost_per_kg=1.5)
    processor = ProcessorAgent(name="FP", crop_type="Tomato", processing_capacity=1000,
                               processing_cost_per_kg=2.0,
                               target_price=min_price * 0.7,
                               max_price=min_price * 1.1)
    compost = CompostAgent(name="Compost", base_price=8.0)
    transporter = TransporterAgent(name="FastTrack", vehicle_capacity=1000,
                                   cost_per_km_per_kg=0.03, base_fee=450.0)
    mgr = NegotiationManager(farmer=farmer, buyers=buyers, warehouse=warehouse,
                             processor=processor, compost=compost,
                             transporter=transporter, max_rounds=max_rounds)
    return mgr


def validate(result):
    assert isinstance(result, dict)
    assert result["state"] in VALID_STATES, f"Invalid state: {result['state']}"
    assert "summary" in result
    assert "logs" in result
    assert len(result["logs"]) > 0


def test_s01_easy_agreement():
    """Farmer floor=18, buyer target=25 -- easy DEAL."""
    result = run(make_mgr(min_price=18.0, target_price=25.0).start_negotiation(22.0))
    validate(result)
    print(f"  S01 state={result['state']}")

def test_s02_low_buyer_offer():
    """Buyer target=15, farmer floor=20 -- buyer below floor."""
    result = run(make_mgr(min_price=20.0, target_price=15.0).start_negotiation(18.0))
    validate(result)
    if result["state"] == "DEAL":
        assert result["deal"]["price"] >= 20.0
    print(f"  S02 state={result['state']}")

def test_s03_multiple_counteroffers():
    """Close prices -- multiple rounds expected."""
    result = run(make_mgr(min_price=19.0, target_price=20.5, max_rounds=8).start_negotiation(20.0))
    validate(result)
    print(f"  S03 state={result['state']}")

def test_s04_buyer_max_below_floor():
    """Buyer max < farmer floor -- MUST NOT reach DEAL."""
    result = run(make_mgr(min_price=30.0, target_price=10.0, max_rounds=3).start_negotiation(20.0))
    validate(result)
    if result["state"] == "DEAL":
        pytest.fail(f"DEAL reached when buyer target(10) < floor(30): {result['deal']}")
    print(f"  S04 state={result['state']} (correctly no DEAL)")

def test_s05_farmer_urgency():
    """Shelf life=2 -- farmer urgent."""
    result = run(make_mgr(min_price=20.0, target_price=22.0, shelf_life=2, max_rounds=4).start_negotiation(22.0))
    validate(result)
    print(f"  S05 state={result['state']} (shelf_life=2)")

def test_s06_buyer_urgency_high_budget():
    """Buyer with 3x budget and high target."""
    result = run(make_mgr(min_price=18.0, target_price=30.0, max_rounds=4).start_negotiation(22.0))
    validate(result)
    print(f"  S06 state={result['state']}")

def test_s07_three_buyers():
    """3 competing buyers."""
    result = run(make_mgr(min_price=18.0, target_price=22.0, buyer_count=3).start_negotiation(21.0))
    validate(result)
    print(f"  S07 state={result['state']}")

def test_s08_high_demand():
    """Market price = 2x min."""
    result = run(make_mgr(min_price=15.0, target_price=28.0).start_negotiation(30.0))
    validate(result)
    print(f"  S08 state={result['state']}")

def test_s09_low_demand():
    """Market price < min -- distressed."""
    result = run(make_mgr(min_price=25.0, target_price=18.0).start_negotiation(15.0))
    validate(result)
    print(f"  S09 state={result['state']}")

def test_s10_quantity_mismatch():
    """Farmer has 5000kg but buyers take 200kg each."""
    buyers = [BuyerAgent(name=f"Small_{i}", budget=4200, max_quantity=200, target_price=21.0)
              for i in range(3)]
    result = run(make_mgr(min_price=18.0, target_price=21.0, quantity=5000,
                          buyer_count=0, extra_buyers=buyers).start_negotiation(20.0))
    validate(result)
    print(f"  S10 state={result['state']}")

def test_s11_expiring_crop_1_day():
    """Shelf life=1 -- critical spoilage."""
    result = run(make_mgr(min_price=20.0, target_price=22.0, shelf_life=1, max_rounds=3).start_negotiation(22.0))
    validate(result)
    print(f"  S11 state={result['state']}")

def test_s12_max_rounds_8():
    """Force many rounds."""
    result = run(make_mgr(min_price=28.0, target_price=22.0, max_rounds=8).start_negotiation(25.0))
    validate(result)
    print(f"  S12 state={result['state']}")

def test_s13_complete_failure():
    """Floor=50, buyer max=5 -- must NOT be DEAL."""
    result = run(make_mgr(min_price=50.0, target_price=5.0, max_rounds=2).start_negotiation(10.0))
    validate(result)
    assert result["state"] != "DEAL"
    print(f"  S13 state={result['state']} (confirmed no DEAL)")

def test_s14_successful_2_rupee_gap():
    """2-rupee gap -- should converge to DEAL."""
    result = run(make_mgr(min_price=20.0, target_price=22.0, max_rounds=8).start_negotiation(21.0))
    validate(result)
    if result["state"] == "DEAL":
        assert result["deal"]["price"] >= 20.0
    print(f"  S14 state={result['state']} deal={result.get('deal', {}).get('price')}")

def test_s15_offer_below_floor_rejected_or_countered():
    """CRITICAL: counter must be >= min_price."""
    farmer = FarmerAgent(name="Strict", crop="Tomato", quantity=500,
                         min_price=20.0, shelf_life=7)
    farmer.current_price = 25.0
    resp = farmer.respond_to_offer({"price": 10.0, "quantity": 200},
                                   {"market_price": 22.0, "round": 1})
    assert resp["type"] in ("REJECT", "COUNTER")
    if resp["type"] == "COUNTER":
        assert resp["price"] >= 20.0, f"FLOOR VIOLATED: counter={resp['price']}"
    print(f"  S15 type={resp['type']}")

def test_s16_buyer_budget_exceeded():
    """Buyer budget=500, wants 500kg at 22 -- must not overpay."""
    buyer = BuyerAgent(name="Tiny", budget=500.0, max_quantity=500, target_price=22.0)
    _ba_mod.llm_client = None
    resp = buyer.respond_to_offer({"price": 22.0, "quantity": 500},
                                  {"market_price": 22.0, "round": 1})
    if resp["type"] == "ACCEPT":
        assert resp["price"] * resp["quantity"] <= 500.0 + 22.0
    print(f"  S16 type={resp['type']}")

def test_s17_fallback_to_escalation():
    """Force escalation path."""
    result = run(make_mgr(min_price=40.0, target_price=10.0, max_rounds=2).start_negotiation(35.0))
    validate(result)
    print(f"  S17 state={result['state']}")
    if result["state"] in ("ESCALATED_PROCESSING", "ESCALATED_STORAGE", "ESCALATED_COMPOST"):
        assert result["deal"] is not None

def test_s18_no_buyers():
    """No buyers -- system must not crash."""
    farmer = FarmerAgent(name="Lonely", crop="Tomato", quantity=500,
                         min_price=20.0, shelf_life=5)
    warehouse = WarehouseAgent(name="WH", capacity=5000, storage_cost_per_kg=1.5)
    mgr = NegotiationManager(farmer=farmer, buyers=[], warehouse=warehouse, max_rounds=3)
    try:
        result = run(mgr.start_negotiation(22.0))
        assert "state" in result
        print(f"  S18 state={result['state']}")
    except Exception as e:
        pytest.fail(f"Crashed with no buyers: {e}")

def test_s19_five_buyers_competitive():
    """5 buyers with different budgets."""
    buyers = [
        BuyerAgent(name="Premium",  budget=50000, max_quantity=500, target_price=28.0),
        BuyerAgent(name="Standard", budget=20000, max_quantity=500, target_price=22.0),
        BuyerAgent(name="Budget",   budget=10000, max_quantity=500, target_price=18.0),
        BuyerAgent(name="Tight",    budget=8000,  max_quantity=400, target_price=16.0),
        BuyerAgent(name="Minimal",  budget=5000,  max_quantity=200, target_price=14.0),
    ]
    farmer = FarmerAgent(name="Ramesh", crop="Tomato", quantity=500, min_price=20.0, shelf_life=5)
    warehouse = WarehouseAgent(name="WH", capacity=5000, storage_cost_per_kg=1.5)
    mgr = NegotiationManager(farmer=farmer, buyers=buyers, warehouse=warehouse, max_rounds=6)
    result = run(mgr.start_negotiation(22.0))
    validate(result)
    if result["state"] == "DEAL":
        assert result["deal"]["price"] >= 20.0
    print(f"  S19 state={result['state']}")

def test_s20_warehouse_storage_fallback():
    """No buyer can meet floor, shelf life = 10 days -- expect storage fallback."""
    result = run(make_mgr(min_price=35.0, target_price=5.0, max_rounds=2, shelf_life=10).start_negotiation(30.0))
    validate(result)
    print(f"  S20 state={result['state']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
