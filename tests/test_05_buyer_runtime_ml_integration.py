"""
tests/test_05_buyer_runtime_ml_integration.py
------------------------------------------------------------------------
Test suite validating end-to-end runtime ML execution for BuyerAgent:
  1. All 7 crops auto-resolve real features and execute model.predict() with audit_status == "ML_USED"
  2. Standalone BuyerAgent get_market_valuation() auto-resolves features without manual input
  3. ML prediction anchors initial bid in make_offer()
  4. ML prediction anchors concession in respond_to_offer()
  5. Economic guardrails:
     - Case A: High market price / ask capped at reservation price P_max
     - Case B: Insufficient budget strictly bounded or rejected
     - Case C: Normal valuation within budget
  6. Unsupported crop fallback: audit_status == "FALLBACK_USED"
  7. LangGraph buyer_node: auto-resolves market_features when missing from state and logs ML anchor
  8. Thread safety under concurrent pricing service calls
"""

import math
import pytest
import asyncio
import threading
from agents.buyer_agent import BuyerAgent
from backend.services.buyer_pricing_service import (
    get_buyer_pricing_service,
    BuyerPricePredictionService,
)
from shared.crop_catalog import BUYER_SUPPORTED_CROPS
from backend.agents.graph_orchestrator import buyer_node, NegotiationState


class TestBuyerRuntimeMLIntegration:
    """Rigorous end-to-end verification of runtime ML prediction flow."""

    def test_01_all_seven_crops_auto_resolve_and_predict(self):
        """Verify all 7 crops auto-resolve real features from APMC dataset and run ML predict."""
        service = get_buyer_pricing_service()
        assert service is not None

        for crop in list(BUYER_SUPPORTED_CROPS.keys()):
            pred_res = service.predict_modal_price(crop)
            assert pred_res["audit_status"] == "ML_USED"
            assert pred_res["is_ml_prediction"] is True
            assert pred_res["crop"] == crop
            assert pred_res["predicted_modal_price"] > 0
            assert pred_res["feature_source"]["is_real_data"] is True
            assert "apmc" in pred_res["feature_source"]
            assert len(pred_res["features_used"]) == 12

    def test_02_buyer_agent_standalone_valuation_auto_resolves(self):
        """Verify BuyerAgent.get_market_valuation() auto-resolves without context features."""
        buyer = BuyerAgent(
            name="ValuationTester",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=30.0,
            reservation_price=40.0,
            crop="Soybean",
            location="Latur"
        )
        val = buyer.get_market_valuation("Soybean", "Latur")
        assert val > 0
        pred = buyer.last_ml_prediction
        assert pred is not None
        assert pred["audit_status"] == "ML_USED"
        assert pred["is_ml_prediction"] is True
        assert pred["predicted_modal_price"] == val
        assert "Latur" in pred["feature_source"]["match_level"]

    def test_03_make_offer_anchored_by_ml_prediction(self):
        """Verify make_offer() invokes ML prediction and uses it to anchor opening bid."""
        buyer = BuyerAgent(
            name="OpeningBidTester",
            budget=50000.0,
            max_quantity=500.0,
            target_price=45.0,
            reservation_price=55.0,
            crop="Cotton",
            location="Nagpur"
        )
        offer = buyer.make_offer()
        assert offer["price"] > 0
        assert offer["quantity"] > 0
        pred = buyer.last_ml_prediction
        assert pred is not None
        assert pred["audit_status"] == "ML_USED"
        assert pred["crop"] == "Cotton"

    def test_04_respond_to_offer_anchored_by_ml(self):
        """Verify respond_to_offer() executes ML model and anchors concession."""
        buyer = BuyerAgent(
            name="ConcessionTester",
            budget=100000.0,
            max_quantity=500.0,
            target_price=28.0,
            reservation_price=35.0,
            crop="Soybean",
            location="Latur"
        )
        resp = buyer.respond_to_offer({"price": 42.0, "quantity": 500.0, "crop": "Soybean"})
        assert resp["type"] in ["COUNTER", "REJECT"]
        pred = buyer.last_ml_prediction
        assert pred is not None
        assert pred["audit_status"] == "ML_USED"
        assert resp["price"] <= buyer.reservation_price

    def test_05_economic_guardrail_case_a_reservation_ceiling(self):
        """Case A: When seller ask and ML price are high, counter is strictly capped at P_max."""
        buyer = BuyerAgent(
            name="CeilingTester",
            budget=100000.0,
            max_quantity=500.0,
            target_price=22.0,
            reservation_price=26.0,
            crop="Soybean",
            location="Latur"
        )
        resp = buyer.respond_to_offer({"price": 60.0, "quantity": 500.0, "crop": "Soybean"})
        if resp["type"] == "COUNTER":
            assert resp["price"] <= buyer.reservation_price
        else:
            assert resp["type"] == "REJECT"

    def test_06_economic_guardrail_case_b_budget_protection(self):
        """Case B: When budget is tightly constrained, order cost never exceeds budget."""
        buyer = BuyerAgent(
            name="BudgetTester",
            budget=300.0,
            max_quantity=100.0,
            target_price=12.0,
            reservation_price=15.0,
            crop="Bajra",
            location="Pune"
        )
        resp = buyer.respond_to_offer({"price": 14.0, "quantity": 100.0, "crop": "Bajra"})
        if resp["type"] in ["ACCEPT", "COUNTER"]:
            total_commitment = resp["price"] * resp["quantity"]
            assert total_commitment <= buyer.budget
        else:
            assert resp["type"] == "REJECT"

    def test_07_economic_guardrail_case_c_normal_anchored_bid(self):
        """Case C: Realistic market conditions anchor reasonable counter-offer."""
        buyer = BuyerAgent(
            name="NormalBidTester",
            budget=50000.0,
            max_quantity=500.0,
            target_price=30.0,
            reservation_price=36.0,
            crop="Soybean",
            location="Latur"
        )
        resp = buyer.respond_to_offer({"price": 34.0, "quantity": 500.0, "crop": "Soybean"})
        assert resp["type"] in ["ACCEPT", "COUNTER"]
        assert resp["price"] <= buyer.reservation_price
        assert resp["price"] * resp["quantity"] <= buyer.budget

    def test_08_unsupported_crop_fallback_audit_status(self):
        """Verify unsupported crop cleanly falls back with audit_status == 'FALLBACK_USED'."""
        buyer = BuyerAgent(
            name="FallbackTester",
            budget=50000.0,
            max_quantity=100.0,
            target_price=50.0
        )
        val = buyer.get_market_valuation("Mango", context={"market_price": 55.0})
        assert val == 55.0
        pred = buyer.last_ml_prediction
        assert pred is not None
        assert pred["audit_status"] == "FALLBACK_USED"
        assert pred["is_ml_prediction"] is False

    def test_09_thread_safe_pricing_service(self):
        """Verify thread-safety: concurrent predictions execute without race conditions."""
        service = get_buyer_pricing_service()
        results = []
        errors = []

        def worker(crop):
            try:
                res = service.predict_modal_price(crop)
                results.append(res)
            except Exception as e:
                errors.append(e)

        crop_list = list(BUYER_SUPPORTED_CROPS.keys()) * 3  # 21 concurrent requests
        threads = [
            threading.Thread(target=worker, args=(crop,))
            for crop in crop_list
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors encountered: {errors}"
        assert len(results) == 21
        assert all(r["audit_status"] == "ML_USED" for r in results)

    def test_10_langgraph_buyer_node_auto_resolves_and_logs(self):
        """Verify LangGraph buyer_node auto-resolves features, updates state, and logs ML anchor."""
        state: NegotiationState = {
            "crop": "Soybean",
            "quantity": 500.0,
            "min_price": 25.0,
            "target_price": 32.0,
            "spoilage_days": 15,
            "location": "Latur",
            "market_price": 30.0,
            "round": 1,
            "max_rounds": 5,
            "history": [],
            "buyer_profile": {
                "name": "AgriCorp Latur",
                "budget": 50000.0,
                "max_quantity": 500.0,
                "target_price": 32.0,
                "location": "Latur",
                "strategy": "balanced"
            },
            "logs": [],
            "status": "ACTIVE",
            "proposed_scenario": "",
            "next_action": "",
            "deal": None,
            "plan": None,
            "reflection": None,
            "selected_buyer": None,
            "market_offers": [],
            "user_id": None,
            "active_buyers": [],
            "current_offers": [],
            "best_current_offer": None,
            "latest_farmer_ask": 44.0,
            "latest_buyer_offer": None,
            "buyers_list": [],
            "rag_context": None,
            "market_intelligence": None,
            "recommendation": None,
            "farmer_agent_obj": None,
            "buyer_agent_objs": None,
            "market_features": None,  # Omitted: must be dynamically resolved
        }

        result = asyncio.run(buyer_node(state))
        assert "market_features" in result
        assert result["market_features"] is not None
        assert "modal_price_kg" in result["market_features"]
        assert len(result["buyer_agent_objs"]) > 0
        b_agent = result["buyer_agent_objs"][0]
        assert b_agent.last_ml_prediction is not None
        assert b_agent.last_ml_prediction["audit_status"] == "ML_USED"
        assert any("ML Market Anchor" in log for log in result["logs"])

    def test_11_real_model_artifact_structure_and_prediction(self):
        """Verify the actual serialized .pkl artifact without mocks."""
        import os
        import pickle
        import numpy as np

        model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "backend", "models", "buyer_price_prediction_model.pkl"
        )
        assert os.path.exists(model_path), f"Artifact {model_path} missing"

        with open(model_path, "rb") as f:
            art = pickle.load(f)

        assert "model" in art
        assert "feature_cols" in art
        assert "crop_list" in art
        assert len(art["feature_cols"]) == 12
        assert len(art["crop_list"]) == 7

        # 19-dimensional input schema
        x = np.ones((1, 19), dtype=np.float32)
        pred = art["model"].predict(x)
        assert isinstance(pred, np.ndarray)
        assert pred.shape == (1,)
        assert not np.isnan(pred[0])

    def test_12_dataset_provenance_and_no_target_leakage(self):
        """Verify buyer_feature_dataset.csv provenance, record count, and zero target leakage."""
        import os
        import csv

        ds_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "backend", "dataset", "buyer_feature_dataset.csv"
        )
        assert os.path.exists(ds_path), f"Dataset {ds_path} missing"

        rows = []
        with open(ds_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        assert len(rows) == 13179
        unique_crops = set(r["crop"] for r in rows)
        assert len(unique_crops) == 7
        assert unique_crops == set(BUYER_SUPPORTED_CROPS.keys())

        # Zero chronological target leakage
        for r in rows:
            assert r["date"] < r["next_date"], f"Target leakage anomaly: {r['date']} >= {r['next_date']}"

    def test_13_runtime_location_hierarchy_all_levels(self):
        """Verify the 6-level hierarchical location matcher and fallback audit reporting."""
        service = get_buyer_pricing_service()

        cases = [
            ("Latur", "apmc_exact_match"),
            ("latur mandi apmc", "apmc_token_match"),
            ("Pune", "district_exact_match"),
            ("pune district maharashtra", "district_token_match"),
            ("lat", "apmc_substring_match"),
            ("", "state_latest_fallback"),
            ("Atlantis Unknown Mandi", "state_latest_fallback"),
        ]

        for loc, expected_level in cases:
            feats, meta = service.get_market_features("Soybean", loc)
            assert len(feats) == 12
            assert meta["is_real_data"] is True
            assert meta["dataset"] == "buyer_feature_dataset.csv"
            assert expected_level in meta["match_level"], f"Expected {expected_level} in {meta['match_level']}"

    def test_14_purchase_scenarios_a_through_j(self):
        """Verify Buyer purchase scenarios A through J."""
        # TEST A: Normal purchase within reservation
        ba = BuyerAgent(name="BA", budget=50000, max_quantity=500, target_price=41.0, reservation_price=45.0, crop="Soybean", location="Latur")
        ra = ba.respond_to_offer({"price": 41.6, "quantity": 500.0, "crop": "Soybean"})
        assert ra["type"] == "ACCEPT"
        assert ra["price"] == 41.6
        assert "contract" in ra

        # TEST B: Seller price above reservation
        bb = BuyerAgent(name="BB", budget=50000, max_quantity=500, target_price=35.0, reservation_price=40.0, crop="Soybean")
        rb = bb.respond_to_offer({"price": 55.0, "quantity": 500.0, "crop": "Soybean"})
        assert rb["type"] in ["COUNTER", "REJECT"]
        assert rb.get("price", 0) <= 40.0

        # TEST C: Seller price within reservation
        bc = BuyerAgent(name="BC", budget=50000, max_quantity=500, target_price=38.0, reservation_price=45.0, crop="Soybean")
        rc = bc.respond_to_offer({"price": 42.0, "quantity": 500.0, "crop": "Soybean"})
        assert rc["type"] in ["ACCEPT", "COUNTER"]
        assert rc["price"] <= 45.0

        # TEST D: Quantity exceeds budget -> capped or rejected
        bd = BuyerAgent(name="BD", budget=500.0, max_quantity=100, target_price=10.0, reservation_price=15.0, crop="Bajra", location="Pune")
        rd = bd.respond_to_offer({"price": 12.0, "quantity": 100.0, "crop": "Bajra"})
        assert rd.get("price", 0) * rd.get("quantity", 0) <= 500.0

        # TEST E: Full quantity affordable
        be = BuyerAgent(name="BE", budget=50000, max_quantity=500, target_price=41.0, reservation_price=45.0, crop="Soybean")
        re = be.respond_to_offer({"price": 41.6, "quantity": 500.0, "crop": "Soybean"})
        assert re["type"] == "ACCEPT"
        assert re["quantity"] == 500.0

        # TEST F: Unsupported crop rejected
        bf = BuyerAgent(name="BF", budget=50000, max_quantity=500, target_price=30.0)
        rf = bf.respond_to_offer({"price": 20.0, "quantity": 100.0, "crop": "Tomato"})
        assert rf["type"] == "REJECT"
        assert "Unsupported crop" in rf["message"]

        # TEST G: Alias crop "soya" normalizes to Soybean
        bg = BuyerAgent(name="BG", budget=50000, max_quantity=500, target_price=41.0, reservation_price=45.0, crop="soya", location="Latur")
        assert bg.crop == "Soybean"
        rg = bg.respond_to_offer({"price": 41.6, "quantity": 500.0, "crop": "soya"})
        assert rg["type"] == "ACCEPT"

        # TEST H: Invalid quantity rejected
        bh = BuyerAgent(name="BH", budget=50000, max_quantity=500, target_price=30.0)
        rh1 = bh.respond_to_offer({"price": 30.0, "quantity": -50.0, "crop": "Soybean"})
        rh2 = bh.respond_to_offer({"price": 30.0, "quantity": float("nan"), "crop": "Soybean"})
        assert rh1["type"] == "REJECT" and rh2["type"] == "REJECT"

        # TEST I: Invalid price rejected
        bi = BuyerAgent(name="BI", budget=50000, max_quantity=500, target_price=30.0)
        ri1 = bi.respond_to_offer({"price": -10.0, "quantity": 100.0, "crop": "Soybean"})
        ri2 = bi.respond_to_offer({"price": float("inf"), "quantity": 100.0, "crop": "Soybean"})
        assert ri1["type"] == "REJECT" and ri2["type"] == "REJECT"

        # TEST J: Unknown location triggers statewide fallback and ML prediction
        bj = BuyerAgent(name="BJ", budget=50000, max_quantity=500, target_price=30.0, reservation_price=40.0, crop="Soybean", location="Atlantis Unknown")
        val_j = bj.get_market_valuation("Soybean", "Atlantis Unknown")
        pred_j = bj.last_ml_prediction
        assert pred_j["audit_status"] == "ML_USED"
        assert "state_latest_fallback" in pred_j["feature_source"]["match_level"]

    def test_15_ml_trace_anchor_versus_reservation(self):
        """Verify ML prediction serves as a market valuation anchor without forcing bid equality."""
        buyer = BuyerAgent(
            name="TraceBuyer",
            budget=50000.0,
            max_quantity=500.0,
            target_price=41.0,
            reservation_price=45.0,
            crop="Soybean",
            location="Latur",
            strategy="balanced"
        )
        val = buyer.get_market_valuation("Soybean", "Latur")
        assert val > 0
        offer = buyer.make_offer()
        counter = buyer.respond_to_offer({"price": 43.5, "quantity": 500.0, "crop": "Soybean"})

        # ML prediction anchors the bid, but is NOT the bid price or reservation ceiling
        assert offer["price"] != val or counter["price"] != val
        assert offer["price"] <= buyer.reservation_price
        assert counter["price"] <= buyer.reservation_price

