"""
tests/test_parallel_buyer_negotiation.py

Tests proving TRUE CONCURRENT (parallel) execution of multi-buyer negotiation
in LangGraph's buyer_node using asyncio.gather rather than sequential looping.
"""

import asyncio
import time
import pytest
from unittest.mock import MagicMock, patch
from backend.agents.graph_orchestrator import buyer_node


def run(coro):
    return asyncio.run(coro)


class MockConcurrentBuyerAgent:
    """Mock buyer agent that introduces a small async delay to test concurrency."""
    def __init__(self, name: str, delay: float = 0.05, counter_price: float = 21.0):
        self.name = name
        self.id = f"buyer_{name.lower()}"
        self.delay = delay
        self.counter_price = counter_price
        self.last_ml_prediction = None

    async def respond_to_offer(self, offer_payload, context=None):
        await asyncio.sleep(self.delay)
        return {
            "type": "COUNTER",
            "price": self.counter_price,
            "message": f"Counter offer from {self.name} after {self.delay}s delay"
        }


def test_buyer_node_concurrent_execution_provenance():
    """
    Verify that buyer_node queries 5 shortlisted buyers in parallel using asyncio.gather,
    recording execution_mode='PARALLEL_ASYNCIO' and overlapping timestamps.
    """
    delay_per_buyer = 0.06
    mock_buyers = [
        MockConcurrentBuyerAgent(name=f"Buyer_{i+1}", delay=delay_per_buyer, counter_price=20.0 + i)
        for i in range(5)
    ]

    state = {
        "crop": "Onion",
        "quantity": 1000.0,
        "min_price": 18.0,
        "target_price": 24.0,
        "spoilage_days": 10,
        "location": "Nashik",
        "market_price": 22.0,
        "logs": [],
        "history": [],
        "latest_farmer_ask": 23.0,
        "round": 1,
        "market_features": {"modal_price": 22.0},
        "active_buyers": [{"id": b.id, "name": b.name} for b in mock_buyers],
        "buyer_agent_objs": mock_buyers,
    }

    # Patch external heavy services so we strictly measure buyer response concurrency
    dummy_rag = MagicMock(is_empty=True)
    with patch("backend.services.buyer_rag_service.buyer_rag_service.get_buyer_context", return_value=dummy_rag), \
         patch("backend.services.current_mandi_service.current_mandi_service.get_current_market_price", return_value={"success": False}):
        
        t0 = time.time()
        result = run(buyer_node(state))
        total_wall_time = time.time() - t0

    offers = result["current_offers"]
    assert len(offers) == 5, f"Expected 5 offers, got {len(offers)}"

    # 1. Sequential execution would take 5 * 0.06s = 300ms+ minimum.
    # Concurrent asyncio.gather completes in ~60-150ms.
    parallel_ms = result.get("parallel_eval_duration_ms", 0.0)
    assert parallel_ms < (delay_per_buyer * 1000 * 3.0), (
        f"Parallel eval duration {parallel_ms}ms indicates sequential execution (expected < {delay_per_buyer * 1000 * 3.0}ms)"
    )

    # 2. Every offer must document concurrent execution provenance
    for off in offers:
        assert off["execution_mode"] == "PARALLEL_ASYNCIO"
        assert "contacted_at" in off
        assert "responded_at" in off
        assert off["duration_ms"] > 0
        assert off["responded_at"] >= off["contacted_at"]

    # 3. All buyers were contacted simultaneously in the same event-loop batch
    contact_times = [off["contacted_at"] for off in offers]
    assert max(contact_times) - min(contact_times) < 0.05, (
        f"Contact initiation times differed by {max(contact_times) - min(contact_times)}s; not concurrent"
    )


def test_deterministic_parallel_vs_sequential_speedup():
    """
    Deterministic mathematical proof of concurrency:
    5 buyers each execute a deliberate 100ms async sleep.
    Sequential execution takes >= 500ms.
    Concurrent asyncio.gather takes ~100-180ms (< 300ms).
    """
    sleep_delay = 0.10  # 100ms per buyer
    mock_buyers = [
        MockConcurrentBuyerAgent(name=f"Deliberate_Buyer_{i+1}", delay=sleep_delay, counter_price=21.0 + i)
        for i in range(5)
    ]

    state = {
        "crop": "Onion",
        "quantity": 1000.0,
        "min_price": 18.0,
        "target_price": 24.0,
        "spoilage_days": 10,
        "location": "Nashik",
        "market_price": 22.0,
        "logs": [],
        "history": [],
        "latest_farmer_ask": 23.0,
        "round": 1,
        "market_features": {"modal_price": 22.0},
        "active_buyers": [{"id": b.id, "name": b.name} for b in mock_buyers],
        "buyer_agent_objs": mock_buyers,
    }

    dummy_rag = MagicMock(is_empty=True)
    with patch("backend.services.buyer_rag_service.buyer_rag_service.get_buyer_context", return_value=dummy_rag), \
         patch("backend.services.current_mandi_service.current_mandi_service.get_current_market_price", return_value={"success": False}):
        
        t_start = time.time()
        result = run(buyer_node(state))
        elapsed_parallel = time.time() - t_start

    sequential_minimum = sleep_delay * 5  # 0.50 seconds
    assert len(result["current_offers"]) == 5
    # Strict assertion: parallel execution MUST be substantially faster than sequential minimum
    assert elapsed_parallel < (sequential_minimum * 0.65), (
        f"Concurrent execution took {elapsed_parallel:.3f}s; expected < {sequential_minimum * 0.65:.3f}s for 5x100ms buyers"
    )
    print(f"\nEmpirical Concurrency Benchmark: Sequential minimum={sequential_minimum*1000:.0f}ms | Parallel observed={elapsed_parallel*1000:.1f}ms")
