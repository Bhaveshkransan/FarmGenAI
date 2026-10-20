"""
tests/test_net_farmer_margin_ranking.py
--------------------------------------------------------------------
Unit and integration tests for Net Farmer Margin Ranking in rank_responses_node
and deal enrichment in validator_node.

Verifies:
  1. Closer buyer with higher Net Take-Home Margin is selected over a distant
     buyer with higher nominal gross price.
  2. Distant buyer is chosen when their premium outweighs logistics freight.
  3. Farmer-owned transport (has_transport=True) eliminates freight deductions.
  4. Counter-offer ranking prioritizes Net Farmer Margin.
  5. Validator node propagates net_price, net_margin, and est_transport_cost.
--------------------------------------------------------------------
"""
import pytest
from unittest.mock import patch
from backend.agents.graph_orchestrator import (
    rank_responses_node,
    validator_node,
    estimate_distance_km,
    compute_net_farmer_margin,
)


def test_estimate_distance_km_lookup():
    """Verify city road distance lookup with canonical APMC distances."""
    assert estimate_distance_km("Nashik", "Nashik") == 0.0
    assert estimate_distance_km("nashik", "pune") == 210.0
    assert estimate_distance_km("Nashik", "Nagpur") == 450.0
    assert estimate_distance_km("pune", "mumbai") == 150.0
    assert estimate_distance_km("", "Pune") == 0.0
    assert estimate_distance_km("UnknownDistrict", "AnotherDistrict") == 150.0


def test_compute_net_farmer_margin_deductions():
    """Verify freight and storage cost deductions from gross revenue."""
    state = {
        "location": "Nashik",
        "quantity": 1000.0,
        "has_transport": False,
        "storage_cost": 0.0,
        "min_price": 20.0,
        "active_buyers": [
            {"id": "b_nagpur", "name": "Nagpur Exporter", "location": "Nagpur"}
        ]
    }
    offer = {"buyer_id": "b_nagpur", "price": 26.50}
    margin = compute_net_farmer_margin(offer, state)

    # 450 km * 3.0/t-km * 1.0 tonne = 1350.0 freight
    assert margin["distance_km"] == 450.0
    assert margin["est_transport_cost"] == 1350.0
    assert margin["gross_revenue"] == 26500.0
    assert margin["net_margin"] == 25150.0
    assert margin["net_price"] == 25.15


@pytest.mark.asyncio
async def test_net_margin_ranking_prefers_closer_buyer_with_higher_net_revenue():
    """
    Scenario from Audit Report Section E:
    Farmer in Nashik selling 1,000 kg produce.
      - Buyer A (Nagpur Exporter): ₹26.50/kg (Nominal highest), 450 km away -> Net ₹25,150 (₹25.15/kg)
      - Buyer B (Local Retailer):  ₹25.50/kg, 0 km away (Local)             -> Net ₹25,500 (₹25.50/kg)
      - Buyer C (Pune Wholesaler): ₹25.80/kg, 210 km away                   -> Net ₹25,170 (₹25.17/kg)

    Ranker MUST choose Local Retailer (Net ₹25,500) over Nagpur Exporter (Net ₹25,150)
    despite Nagpur's higher nominal gross price.
    """
    state = {
        "location": "Nashik",
        "quantity": 1000.0,
        "min_price": 20.0,
        "round": 1,
        "max_rounds": 5,
        "has_transport": False,
        "active_buyers": [
            {"id": "b_nagpur", "name": "Nagpur Exporter", "location": "Nagpur"},
            {"id": "b_nashik", "name": "Local Retailer", "location": "Nashik"},
            {"id": "b_pune", "name": "Pune Wholesaler", "location": "Pune"},
        ],
        "current_offers": [
            {"buyer_id": "b_nagpur", "buyer_name": "Nagpur Exporter", "price": 26.50, "status": "ACCEPT"},
            {"buyer_id": "b_nashik", "buyer_name": "Local Retailer", "price": 25.50, "status": "ACCEPT"},
            {"buyer_id": "b_pune", "buyer_name": "Pune Wholesaler", "price": 25.80, "status": "ACCEPT"},
        ],
        "logs": [],
    }

    result = await rank_responses_node(state)

    assert result["status"] == "DEAL"
    best = result["best_current_offer"]

    # Local Retailer must win due to higher Net Take-Home Margin
    assert best["buyer_id"] == "b_nashik"
    assert best["buyer_name"] == "Local Retailer"
    assert best["price"] == 25.50
    assert best["net_price"] == 25.50
    assert best["net_margin"] == 25500.0
    assert best["est_transport_cost"] == 0.0

    # Ensure result also contains net economics
    assert result["net_price"] == 25.50
    assert result["net_margin"] == 25500.0
    assert result["est_transport_cost"] == 0.0
    assert result["selected_buyer"]["name"] == "Local Retailer"


@pytest.mark.asyncio
async def test_net_margin_ranking_distant_buyer_wins_when_net_margin_is_higher():
    """
    If a distant buyer offers a high enough premium to outweigh freight,
    they must be selected:
      - Buyer A (Nagpur Exporter): ₹28.50/kg, 450 km -> Net ₹27,150
      - Buyer B (Local Retailer):  ₹25.50/kg, 0 km   -> Net ₹25,500
    """
    state = {
        "location": "Nashik",
        "quantity": 1000.0,
        "min_price": 20.0,
        "round": 1,
        "max_rounds": 5,
        "has_transport": False,
        "active_buyers": [
            {"id": "b_nagpur", "name": "Nagpur Exporter", "location": "Nagpur"},
            {"id": "b_nashik", "name": "Local Retailer", "location": "Nashik"},
        ],
        "current_offers": [
            {"buyer_id": "b_nagpur", "buyer_name": "Nagpur Exporter", "price": 28.50, "status": "ACCEPT"},
            {"buyer_id": "b_nashik", "buyer_name": "Local Retailer", "price": 25.50, "status": "ACCEPT"},
        ],
        "logs": [],
    }

    result = await rank_responses_node(state)

    assert result["status"] == "DEAL"
    best = result["best_current_offer"]

    assert best["buyer_id"] == "b_nagpur"
    assert best["buyer_name"] == "Nagpur Exporter"
    assert best["price"] == 28.50
    assert best["net_price"] == 27.15
    assert best["net_margin"] == 27150.0
    assert best["est_transport_cost"] == 1350.0


@pytest.mark.asyncio
async def test_net_margin_ranking_with_farmer_own_transport():
    """
    When farmer has own transport (has_transport=True), third-party freight is ₹0.
    Thus, gross revenue = net revenue.
    """
    state = {
        "location": "Nashik",
        "quantity": 1000.0,
        "min_price": 20.0,
        "round": 1,
        "max_rounds": 5,
        "has_transport": True,
        "active_buyers": [
            {"id": "b_nagpur", "name": "Nagpur Exporter", "location": "Nagpur"},
            {"id": "b_nashik", "name": "Local Retailer", "location": "Nashik"},
        ],
        "current_offers": [
            {"buyer_id": "b_nagpur", "buyer_name": "Nagpur Exporter", "price": 26.50, "status": "ACCEPT"},
            {"buyer_id": "b_nashik", "buyer_name": "Local Retailer", "price": 25.50, "status": "ACCEPT"},
        ],
        "logs": [],
    }

    result = await rank_responses_node(state)

    assert result["status"] == "DEAL"
    best = result["best_current_offer"]

    # Since transport cost is 0, Nagpur's ₹26.50 wins over Local's ₹25.50
    assert best["buyer_id"] == "b_nagpur"
    assert best["price"] == 26.50
    assert best["est_transport_cost"] == 0.0
    assert best["net_margin"] == 26500.0


@pytest.mark.asyncio
async def test_net_margin_ranking_counter_selection():
    """
    During multi-turn counter negotiation, ranker must choose the counter-offer
    that maximizes Net Farmer Margin.
    """
    state = {
        "location": "Nashik",
        "quantity": 1000.0,
        "min_price": 20.0,
        "round": 1,
        "max_rounds": 5,
        "has_transport": False,
        "active_buyers": [
            {"id": "b_nagpur", "name": "Nagpur Exporter", "location": "Nagpur"},
            {"id": "b_nashik", "name": "Local Retailer", "location": "Nashik"},
        ],
        "current_offers": [
            {"buyer_id": "b_nagpur", "buyer_name": "Nagpur Exporter", "price": 26.50, "status": "COUNTER"},
            {"buyer_id": "b_nashik", "buyer_name": "Local Retailer", "price": 25.50, "status": "COUNTER"},
        ],
        "logs": [],
    }

    result = await rank_responses_node(state)

    assert result["status"] == "ACTIVE"
    best = result["best_current_offer"]

    # Local Retailer net margin (25,500) beats Nagpur net margin (25,150)
    assert best["buyer_id"] == "b_nashik"
    assert result["latest_buyer_offer"] == 25.50
    assert result["net_margin"] == 25500.0
    assert result["selected_buyer"]["net_margin"] == 25500.0


@pytest.mark.asyncio
async def test_validator_enriches_deal_with_net_margin_and_freight():
    """
    Verify that validator_node propagates net_price, net_margin, and est_transport_cost
    to the finalized deal dictionary.
    """
    state = {
        "crop": "Onion",
        "quantity": 1000.0,
        "min_price": 20.0,
        "latest_buyer_offer": 25.50,
        "latest_farmer_ask": 25.50,
        "status": "DEAL",
        "selected_buyer": {
            "id": "b_nashik",
            "name": "Local Retailer",
            "budget": 30000.0,
            "net_price": 25.50,
            "net_margin": 25500.0,
            "est_transport_cost": 0.0,
        },
        "best_current_offer": {
            "price": 25.50,
            "net_price": 25.50,
            "net_margin": 25500.0,
            "est_transport_cost": 0.0,
        },
        "logs": [],
    }

    with patch("backend.agents.graph_orchestrator.llm_client.generate", return_value=None):
        result = await validator_node(state)

    assert result["status"] == "DEAL"
    deal = result["deal"]
    assert deal["price"] == 25.50
    assert deal["net_price"] == 25.50
    assert deal["net_margin"] == 25500.0
    assert deal["est_transport_cost"] == 0.0
    assert deal["total_value"] == 25500.0
