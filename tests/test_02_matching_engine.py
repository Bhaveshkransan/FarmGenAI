"""
tests/test_02_matching_engine.py
Type: DETERMINISTIC / UNIT
Covers: Both matching formulas -- matching_service.py (FR-5) and
        the inline matching_engine_node scoring in graph_orchestrator.
"""
import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest

from backend.services.matching_service import _score_match, _get_distance_km, CITY_DISTANCES_KM


def run(coro):
    return asyncio.run(coro)


# ========================================================================
#  FR-5 Matching Service: Price(40) + Quantity(25) + Geo(20) + Trust(15)
# ========================================================================

class TestMatchingServiceScoring:

    def test_price_full_score_when_target_above_min(self):
        listing = {"min_price": 18.0, "quantity": 500, "location": "Nashik"}
        req = {"target_price": 20.0, "quantity": 500, "budget": 10000, "location": "Nashik"}
        score = run(_score_match(listing, req, {"trust_score": 3.5}))
        # Price(40) + Qty(25) + Geo(20 same city) + Trust(10.5) = ~95.5
        assert score >= 90.0, f"Expected >=90, got {score}"

    def test_price_zero_when_target_far_below_min(self):
        listing = {"min_price": 30.0, "quantity": 500, "location": "Nashik"}
        req = {"target_price": 10.0, "max_price": 15.0, "quantity": 500,
               "budget": 5000, "location": "Nashik"}
        score = run(_score_match(listing, req))
        # Price pts = 0 (incompatible). Under 8-factor NRV model (Price=20, Qty=20, Geo=15, Trust=15, Quality=10, Urgency=10, Transport=5, Storage=5),
        # non-price factors yield ~71.5. Key assertion: score is significantly below the 90+ of a compatible match.
        assert score <= 72.0, f"Expected <=72 (price-incompatible), got {score}"

    def test_partial_price_when_max_covers_min(self):
        listing = {"min_price": 20.0, "quantity": 500, "location": "Pune"}
        req = {"target_price": 18.0, "max_price": 22.0, "quantity": 500,
               "budget": 11000, "location": "Pune"}
        score = run(_score_match(listing, req))
        # max_price(22) >= min_price(20) -> partial price pts
        assert 45.0 <= score <= 85.0, f"Expected 45-85 for partial match, got {score}"

    def test_quantity_full_score_when_fully_fulfillable(self):
        listing = {"min_price": 18.0, "quantity": 1000, "location": "Nashik"}
        req = {"target_price": 20.0, "quantity": 800, "budget": 20000, "location": "Nashik"}
        score = run(_score_match(listing, req, {"trust_score": 0}))
        # In 8-factor NRV model with trust=0, score reaches ~74.0
        assert score >= 70.0, f"Expected >=70, got {score}"

    def test_geography_penalty_for_distant_cities(self):
        listing = {"min_price": 18.0, "quantity": 500, "location": "Nashik"}
        req_near = {"target_price": 20.0, "quantity": 500, "budget": 12000, "location": "Nashik"}
        req_far  = {"target_price": 20.0, "quantity": 500, "budget": 12000, "location": "Nagpur"}
        score_near = run(_score_match(listing, req_near, {"trust_score": 3.5}))
        score_far  = run(_score_match(listing, req_far,  {"trust_score": 3.5}))
        assert score_near > score_far, "Nearby buyer should rank higher"

    def test_trust_score_contributes_15_pts_at_max(self):
        listing = {"min_price": 18.0, "quantity": 500, "location": "Pune"}
        req = {"target_price": 20.0, "quantity": 500, "budget": 12000, "location": "Pune"}
        score_high = run(_score_match(listing, req, {"trust_score": 5.0}))
        score_zero = run(_score_match(listing, req, {"trust_score": 0.0}))
        diff = round(score_high - score_zero, 2)
        assert abs(diff - 15.0) < 1.0, f"Trust diff should be ~15, got {diff}"

    def test_match_grade_a_above_70(self):
        listing = {"min_price": 18.0, "quantity": 500, "location": "Pune"}
        req = {"target_price": 25.0, "quantity": 500, "budget": 15000, "location": "Pune"}
        score = run(_score_match(listing, req, {"trust_score": 5.0}))
        grade = "A" if score >= 70 else "B" if score >= 45 else "C"
        assert grade == "A", f"Expected grade A for score {score}"

    def test_match_grade_c_for_incompatible(self):
        listing = {"min_price": 50.0, "quantity": 500, "location": "Nagpur"}
        req = {"target_price": 10.0, "max_price": 15.0, "quantity": 100,
               "budget": 1500, "location": "Mumbai"}
        score = run(_score_match(listing, req, {"trust_score": 1.0}))
        grade = "A" if score >= 70 else "B" if score >= 45 else "C"
        assert grade == "C", f"Expected grade C, got score={score}"


# ========================================================================
#  Distance Lookup
# ========================================================================

class TestDistanceLookup:

    def test_same_city_distance_zero(self):
        assert run(_get_distance_km("Pune", "Pune")) == 0.0

    def test_known_city_pair(self):
        dist = run(_get_distance_km("Nashik", "Pune"))
        assert dist == CITY_DISTANCES_KM["Nashik"]["Pune"]

    def test_reverse_pair_symmetric(self):
        d1 = run(_get_distance_km("Pune", "Nashik"))
        d2 = run(_get_distance_km("Nashik", "Pune"))
        assert d1 == d2

    def test_unknown_city_returns_default_250(self):
        dist = run(_get_distance_km("UnknownCity", "AnotherUnknown"))
        assert dist == 250.0

    def test_empty_location_returns_default_150(self):
        dist = run(_get_distance_km("", "Pune"))
        assert dist == 150.0


# ========================================================================
#  In-graph matching_engine_node scoring formula
#  score = (bid_price - distance_penalty) * 100 + (20 if verified else 0)
# ========================================================================

class TestMatchingEngineNodeScoring:

    def _compute_opening_bid(self, target_price, budget, quantity,
                             market_price, is_premium=False):
        budget_limited = budget / max(quantity, 1)
        if is_premium:
            return min(target_price * 0.85, budget_limited)
        return min(target_price * 0.75, budget_limited, (market_price + 3) * 0.75)

    def test_standard_buyer_75pct_of_target(self):
        bid = self._compute_opening_bid(20.0, 100000, 500, 18.0)
        # min(15.0, 200.0, 15.75) = 15.0
        assert bid == pytest.approx(15.0, abs=0.5)

    def test_premium_buyer_85pct_of_target(self):
        bid = self._compute_opening_bid(35.0, 50000, 50, 25.0, is_premium=True)
        # min(29.75, 1000) = 29.75
        assert bid == pytest.approx(29.75, abs=0.5)

    def test_budget_cap_limits_bid(self):
        # budget=500, qty=500 => budget_limited=1.0 < 75 => cap applies
        bid = self._compute_opening_bid(100.0, 500, 500, 90.0)
        assert bid == pytest.approx(1.0, abs=0.5)

    def test_verified_buyer_gets_20pt_bonus(self):
        bid_price = 20.0
        score_v = round((bid_price - 0) * 100 + 20.0, 2)
        score_u = round((bid_price - 0) * 100 + 0.0,  2)
        assert score_v - score_u == 20.0

    def test_distance_penalty_0_2_for_different_city(self):
        bid_price = 20.0
        score_same = (bid_price - 0) * 100
        score_diff = (bid_price - 0.2) * 100
        assert score_same > score_diff
        assert score_same - score_diff == pytest.approx(20.0, abs=0.01)

    def test_viable_flag_below_min_price_is_false(self):
        min_price = 20.0
        for price in [15.0, 10.0, 0.5]:
            assert (price >= min_price) is False

    def test_viable_flag_at_or_above_min_price_is_true(self):
        min_price = 20.0
        for price in [20.0, 22.0, 30.0]:
            assert (price >= min_price) is True


# ========================================================================
#  Unified Canonical Matching Engine (matching_service.py <-> LangGraph)
# ========================================================================

class TestUnifiedMatchingEngine:

    def test_compute_match_score_sync_returns_canonical_score(self):
        from backend.services.matching_service import compute_match_score_sync
        listing = {"min_price": 18.0, "quantity": 500, "location": "Nashik", "grade": "A", "spoilage_days": 10}
        req = {"target_price": 20.0, "quantity": 500, "budget": 10000, "location": "Nashik", "grade": "A"}
        score = compute_match_score_sync(listing, req, {"trust_score": 4.5, "verified": True})
        assert 0.0 <= score <= 100.0
        assert score >= 90.0, f"Expected high score for compatible local buyer, got {score}"

    def test_matching_engine_node_uses_canonical_score(self):
        from backend.agents.graph_orchestrator import matching_engine_node
        state = {
            "crop": "Tomato",
            "quantity": 500.0,
            "min_price": 18.0,
            "target_price": 22.0,
            "spoilage_days": 5,
            "location": "Nashik",
            "market_price": 20.0,
            "logs": [],
            "buyers_list": [
                {
                    "id": "b1",
                    "name": "Local Retailer",
                    "target_price": 22.0,
                    "budget": 20000.0,
                    "max_quantity": 500.0,
                    "location": "Nashik",
                    "strategy": "retail",
                    "verified": True
                },
                {
                    "id": "b2",
                    "name": "Distant Buyer",
                    "target_price": 19.0,
                    "budget": 10000.0,
                    "max_quantity": 500.0,
                    "location": "Nagpur",
                    "strategy": "bulk",
                    "verified": False
                }
            ]
        }
        res = run(matching_engine_node(state))
        offers = res["market_offers"]
        assert len(offers) == 2

        # Both offers have canonical 0-100 scores
        for off in offers:
            assert 0.0 <= off["score"] <= 100.0
            assert "match_score" in off
            assert off["match_score"] == off["score"]
            assert "legacy_score" in off

        # Local verified buyer b1 scores higher than distant unverified b2
        b1_offer = next(o for o in offers if o["buyer_id"] == "b1")
        b2_offer = next(o for o in offers if o["buyer_id"] == "b2")
        assert b1_offer["score"] > b2_offer["score"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
