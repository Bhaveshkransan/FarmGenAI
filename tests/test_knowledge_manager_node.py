"""
tests/test_knowledge_manager_node.py
--------------------------------------------------------------------
Unit tests for knowledge_manager_node and its active integration in
the LangGraph StateGraph workflow.

Verifies:
  1. knowledge_manager_node is compiled and actively wired into the graph
     between planner_agent and market_intelligence_agent.
  2. Acquires live weather and Agmarknet mandi feeds into state.
  3. Offline / API error graceful degradation (no unhandled exceptions).
  4. Preserves pre-existing state data without redundant overwrites.
--------------------------------------------------------------------
"""
import pytest
from unittest.mock import patch, AsyncMock
from backend.agents.graph_orchestrator import (
    knowledge_manager_node,
    graph_orchestrator,
    workflow,
)


def test_knowledge_manager_node_compiled_in_graph():
    """Verify that knowledge_manager_node is an active node in the compiled graph."""
    graph_obj = graph_orchestrator.get_graph()
    node_ids = set(graph_obj.nodes.keys())
    assert "knowledge_manager_node" in node_ids
    assert "planner_agent" in node_ids
    assert "market_intelligence_agent" in node_ids

    # Verify edge connectivity: planner_agent -> knowledge_manager_node -> market_intelligence_agent
    edges = [(e.source, e.target) for e in graph_obj.edges]
    assert ("planner_agent", "knowledge_manager_node") in edges
    assert ("knowledge_manager_node", "market_intelligence_agent") in edges


@pytest.mark.asyncio
async def test_knowledge_manager_acquires_weather_and_mandi():
    """Verify state enrichment with weather and mandi data."""
    state = {
        "crop": "Soybean",
        "location": "Latur",
        "quantity": 1000.0,
        "logs": [],
    }

    mock_weather = {
        "temperature_c": 28.5,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 12.0,
        "location_resolved": "Latur",
    }
    mock_mandi = {
        "mandi": "Latur APMC",
        "crop": "Soybean",
        "live_modal_price": 52.0,
        "trend": "Bullish",
        "volatility_pct": 3.2,
    }

    with patch("backend.services.external_apis.OpenMeteoClient.get_weather", new_callable=AsyncMock) as m_weather:
        m_weather.return_value = mock_weather
        with patch("backend.services.external_apis.MandiAPIClient.get_live_price", new_callable=AsyncMock) as m_mandi:
            m_mandi.return_value = mock_mandi
            updates = await knowledge_manager_node(state)

    assert "weather" in updates
    assert updates["weather"]["temperature_c"] == 28.5
    assert "live_mandi" in updates
    assert updates["live_mandi"]["live_modal_price"] == 52.0
    assert any("Weather feed active" in l for l in updates.get("logs", []))
    assert any("Mandi feed active" in l for l in updates.get("logs", []))


@pytest.mark.asyncio
async def test_knowledge_manager_offline_graceful_pass():
    """Verify that network exceptions are caught and never crash the workflow."""
    state = {
        "crop": "Cotton",
        "location": "Wardha",
        "logs": [],
    }

    with patch("backend.services.external_apis.OpenMeteoClient.get_weather", side_effect=Exception("Connection timed out")):
        with patch("backend.services.external_apis.MandiAPIClient.get_live_price", side_effect=Exception("503 Service Unavailable")):
            updates = await knowledge_manager_node(state)

    # Must return gracefully without raising
    assert isinstance(updates, dict)
    assert "logs" in updates
    assert "weather" not in updates
    assert "live_mandi" not in updates


@pytest.mark.asyncio
async def test_knowledge_manager_preserves_existing_data():
    """Verify pre-existing weather and mandi data are preserved without redundant fetches."""
    existing_weather = {"temperature_c": 22.0, "location_resolved": "Pune"}
    existing_mandi = {"live_modal_price": 45.0, "mandi": "Pune APMC"}

    state = {
        "crop": "Onion",
        "location": "Pune",
        "weather": existing_weather,
        "live_mandi": existing_mandi,
        "logs": [],
    }

    with patch("backend.services.external_apis.OpenMeteoClient.get_weather", new_callable=AsyncMock) as m_weather:
        with patch("backend.services.external_apis.MandiAPIClient.get_live_price", new_callable=AsyncMock) as m_mandi:
            updates = await knowledge_manager_node(state)

    # Pre-existing data means no external API calls were needed
    m_weather.assert_not_called()
    m_mandi.assert_not_called()
    assert "weather" not in updates
    assert "live_mandi" not in updates
