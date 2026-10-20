"""
tests/test_adaptive_candidate_expansion.py
--------------------------------------------------------------------
Test Adaptive Candidate Expansion in AgriNegotiator LangGraph Orchestrator
--------------------------------------------------------------------
Verifies:
1. When the initial 5 candidates reject, the orchestrator automatically expands to candidates 6-10.
2. If a candidate in the expanded batch accepts or counters, negotiation succeeds.
3. If all candidates across expanded batches reject, the pool exhausts cleanly.
"""

import pytest
import asyncio
from backend.agents.graph_orchestrator import rank_responses_node, route_after_rank

@pytest.mark.asyncio
async def test_adaptive_expansion_triggers_when_first_batch_rejects():
    """Verify that when top 5 candidates reject, rank_responses_node expands to next batch."""
    
    # 10 candidate offers in market_offers
    market_offers = [
        {"buyer_id": f"buyer_{i:02d}", "buyer_name": f"Corp {i}", "offered_price": 20.0 + i, "status": "VIABLE"}
        for i in range(10)
    ]
    raw_buyers = [
        {"id": f"buyer_{i:02d}", "name": f"Corp {i}", "target_price": 20.0 + i, "budget": 50000}
        for i in range(10)
    ]
    
    # First batch (0 to 4) all rejected
    first_batch_offers = [
        {"buyer_id": f"buyer_{i:02d}", "buyer_name": f"Corp {i}", "price": 18.0, "status": "REJECT"}
        for i in range(5)
    ]
    
    state = {
        "round": 1,
        "max_rounds": 5,
        "min_price": 20.0,
        "quantity": 1000,
        "current_offers": first_batch_offers,
        "active_buyers": raw_buyers[:5],
        "market_offers": market_offers,
        "raw_buyers": raw_buyers,
        "contacted_buyer_ids": [f"buyer_{i:02d}" for i in range(5)],
        "expansion_count": 0,
        "max_candidate_expansions": 3,
        "logs": []
    }
    
    # Execute rank_responses_node
    result = await rank_responses_node(state)
    
    # Assertions
    assert result["status"] == "ACTIVE", f"Expected ACTIVE status on expansion, got {result['status']}"
    assert result["expansion_count"] == 1, "Expected expansion_count to be incremented to 1"
    assert len(result["active_buyers"]) == 5, f"Expected 5 new active buyers, got {len(result['active_buyers'])}"
    
    # Verify the new active buyers are candidates 5 to 9!
    new_ids = [b["id"] for b in result["active_buyers"]]
    assert new_ids == ["buyer_05", "buyer_06", "buyer_07", "buyer_08", "buyer_09"], f"Wrong expanded buyers: {new_ids}"
    
    # Verify route_after_rank routes back to farmer_agent for continuing negotiation
    route = await route_after_rank(result)
    assert route == "farmer_agent", f"Expected route_after_rank to return 'farmer_agent', got '{route}'"


@pytest.mark.asyncio
async def test_adaptive_expansion_exhaustion_halts_cleanly():
    """Verify that when all available candidates across all batches reject, the pool halts with REJECT."""
    
    # Only 5 candidates total
    market_offers = [
        {"buyer_id": f"buyer_{i:02d}", "buyer_name": f"Corp {i}", "offered_price": 20.0 + i, "status": "VIABLE"}
        for i in range(5)
    ]
    raw_buyers = [
        {"id": f"buyer_{i:02d}", "name": f"Corp {i}", "target_price": 20.0 + i, "budget": 50000}
        for i in range(5)
    ]
    
    # All 5 rejected
    first_batch_offers = [
        {"buyer_id": f"buyer_{i:02d}", "buyer_name": f"Corp {i}", "price": 18.0, "status": "REJECT"}
        for i in range(5)
    ]
    
    state = {
        "round": 1,
        "max_rounds": 5,
        "min_price": 20.0,
        "quantity": 1000,
        "current_offers": first_batch_offers,
        "active_buyers": raw_buyers[:5],
        "market_offers": market_offers,
        "raw_buyers": raw_buyers,
        "contacted_buyer_ids": [f"buyer_{i:02d}" for i in range(5)],
        "expansion_count": 0,
        "max_candidate_expansions": 3,
        "logs": []
    }
    
    result = await rank_responses_node(state)
    
    # Assertions
    assert result["status"] == "REJECT", f"Expected REJECT when pool is exhausted, got {result['status']}"
    assert any("Candidate pool exhausted" in log for log in result["logs"]), "Expected exhaustion log message"


@pytest.mark.asyncio
async def test_expanded_candidate_accept_leads_to_deal():
    """Verify that if an expanded candidate accepts, rank_responses_node moves to DEAL."""
    
    # Expanded batch offers where one accepted
    expanded_offers = [
        {"buyer_id": "buyer_05", "buyer_name": "Corp 5", "price": 19.0, "status": "COUNTER"},
        {"buyer_id": "buyer_06", "buyer_name": "Corp 6", "price": 24.5, "status": "ACCEPT"},
        {"buyer_id": "buyer_07", "buyer_name": "Corp 7", "price": 18.5, "status": "REJECT"}
    ]
    
    state = {
        "round": 1,
        "max_rounds": 5,
        "min_price": 20.0,
        "quantity": 1000,
        "current_offers": expanded_offers,
        "active_buyers": [{"id": f"buyer_{i:02d}", "name": f"Corp {i}"} for i in range(5, 8)],
        "expansion_count": 1,
        "logs": []
    }
    
    result = await rank_responses_node(state)
    
    assert result["status"] == "DEAL"
    assert result["best_current_offer"]["buyer_id"] == "buyer_06"
    assert result["latest_buyer_offer"] == 24.5
    
    route = await route_after_rank(result)
    assert route == "validator_agent", f"Expected route to validator_agent, got {route}"
