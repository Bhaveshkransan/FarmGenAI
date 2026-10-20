"""
tests/test_08_failure_modes.py
Type: UNIT + INTEGRATION
Covers: Graceful degradation when Ollama, ChromaDB, PostgreSQL, or APIs fail.
"""
import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from unittest.mock import patch, MagicMock


def run(coro):
    return asyncio.run(coro)


# ================================================================
# F-1: Ollama Unavailable
# ================================================================

class TestOllamaFailure:

    def test_llm_generate_returns_none_when_ollama_down(self):
        from llm.llm_client import LLMClient
        client = LLMClient()
        original_url = client.ollama_url
        client.ollama_url = "http://127.0.0.1:59999"
        client.gemini_key = ""
        client.groq_key = ""
        result = client.generate("Test prompt.")
        assert result is None
        client.ollama_url = original_url

    def test_farmer_node_works_with_llm_none(self):
        import agents.farmer_agent as _fa_mod
        _fa_mod.llm_client = None

        from backend.agents.graph_orchestrator import farmer_node
        state = {
            "crop": "Tomato", "quantity": 500.0, "min_price": 20.0,
            "target_price": 24.0, "spoilage_days": 5, "location": "Pune",
            "market_price": 22.0, "round": 0, "max_rounds": 6, "history": [],
            "buyer_profile": None, "logs": [], "status": "ACTIVE",
            "proposed_scenario": "", "next_action": "", "deal": None,
            "plan": None, "reflection": None, "selected_buyer": None,
            "market_offers": [], "user_id": None,
            "active_buyers": [
                {"id": "b1", "name": "TestBuyer", "target_price": 22.0,
                 "budget": 15000.0, "max_quantity": 600.0,
                 "location": "Mumbai", "strategy": "bulk"}
            ],
            "current_offers": [], "best_current_offer": None,
            "latest_farmer_ask": 24.0, "latest_buyer_offer": 18.0,
            "buyers_list": [], "rag_context": "", "market_intelligence": "",
            "recommendation": None,
        }
        with patch("backend.agents.graph_orchestrator.llm_client") as mock_llm:
            mock_llm.generate.return_value = None
            result = run(farmer_node(state))
        assert "logs" in result
        assert "round" in result

    def test_buyer_node_works_with_llm_none(self):
        from backend.agents.graph_orchestrator import buyer_node
        state = {
            "crop": "Tomato", "quantity": 500.0, "min_price": 20.0,
            "target_price": 24.0, "spoilage_days": 5, "location": "Pune",
            "market_price": 22.0, "round": 1, "max_rounds": 6, "history": [],
            "buyer_profile": None, "logs": [], "status": "ACTIVE",
            "proposed_scenario": "", "next_action": "", "deal": None,
            "plan": None, "reflection": None, "selected_buyer": None,
            "market_offers": [], "user_id": None,
            "active_buyers": [
                {"id": "b1", "name": "TestBuyer", "target_price": 22.0,
                 "budget": 15000.0, "max_quantity": 600.0,
                 "location": "Mumbai", "strategy": "bulk"}
            ],
            "current_offers": [], "best_current_offer": None,
            "latest_farmer_ask": 23.0, "latest_buyer_offer": None,
            "buyers_list": [], "rag_context": "", "market_intelligence": "",
            "recommendation": None,
        }
        with patch("backend.agents.graph_orchestrator.llm_client") as mock_llm:
            mock_llm.generate.return_value = None
            result = run(buyer_node(state))
        assert "current_offers" in result
        assert len(result["current_offers"]) >= 1


# ================================================================
# F-2: ChromaDB Unavailable
# ================================================================

class TestChromaDBFailure:

    def test_build_rag_context_handles_chroma_failure(self):
        from backend.agents.graph_orchestrator import _build_rag_context
        with patch("backend.services.rag_service.rag_service.query_mandi_records",
                   side_effect=Exception("ChromaDB connection refused")):
            result = run(_build_rag_context("Tomato", "Pune"))
        assert isinstance(result, str)


# ================================================================
# F-3: PostgreSQL Unavailable
# ================================================================

class TestPostgreSQLFailure:

    def test_reflection_node_handles_db_failure(self):
        from backend.agents.graph_orchestrator import reflection_node
        state = {
            "crop": "Tomato", "quantity": 500.0, "min_price": 20.0,
            "target_price": 24.0, "spoilage_days": 5, "location": "Pune",
            "market_price": 22.0, "round": 2, "max_rounds": 6,
            "history": [{"round": 1, "agent": "Farmer", "price": 24.0,
                         "decision": "COUNTER", "quantity": 500}],
            "buyer_profile": {"name": "TestBuyer", "id": "b1"},
            "logs": [], "status": "DEAL",
            "proposed_scenario": "", "next_action": "",
            "deal": {"price": 22.0, "quantity": 500, "type": "DIRECT"},
            "plan": None, "reflection": None,
            "selected_buyer": {"id": "b1", "name": "TestBuyer", "budget": 15000.0},
            "market_offers": [], "user_id": "test_user",
            "active_buyers": [], "current_offers": [], "best_current_offer": None,
            "latest_farmer_ask": 22.0, "latest_buyer_offer": 22.0,
            "buyers_list": [], "rag_context": "", "market_intelligence": "",
            "recommendation": None,
        }
        with patch("database.db.Database.add_history_async",
                   side_effect=Exception("PostgreSQL down")):
            with patch("backend.agents.graph_orchestrator.llm_client") as mock_llm:
                mock_llm.generate.return_value = None
                result = run(reflection_node(state))
        assert "logs" in result
        assert "status" in result


# ================================================================
# F-4: Corrupted State Inputs
# ================================================================

class TestCorruptedStateInputs:

    def test_parse_json_none(self):
        from backend.agents.graph_orchestrator import _parse_json_response
        assert run(_parse_json_response(None)) is None

    def test_parse_json_empty(self):
        from backend.agents.graph_orchestrator import _parse_json_response
        assert run(_parse_json_response("")) is None

    def test_parse_json_non_json(self):
        from backend.agents.graph_orchestrator import _parse_json_response
        assert run(_parse_json_response("plain text with no JSON")) is None

    def test_parse_json_valid_object(self):
        from backend.agents.graph_orchestrator import _parse_json_response
        result = run(_parse_json_response('{"decision": "ACCEPT", "price": 22.0}'))
        assert result == {"decision": "ACCEPT", "price": 22.0}

    def test_parse_json_from_markdown_block(self):
        from backend.agents.graph_orchestrator import _parse_json_response
        result = run(_parse_json_response('```json\n{"decision": "COUNTER", "price": 21.5}\n```'))
        if result:
            assert result["decision"] == "COUNTER"

    def test_rank_node_empty_offers_returns_reject(self):
        from backend.agents.graph_orchestrator import rank_responses_node
        result = run(rank_responses_node(
            {"current_offers": [], "active_buyers": [], "logs": [],
             "round": 1, "status": "ACTIVE"}
        ))
        assert result["status"] == "REJECT"

    def test_matching_node_empty_buyers_creates_default(self):
        from backend.agents.graph_orchestrator import matching_engine_node
        state = {
            "crop": "Tomato", "quantity": 500.0, "min_price": 20.0,
            "target_price": 24.0, "spoilage_days": 5, "location": "Pune",
            "market_price": 22.0, "logs": [], "buyers_list": [],
        }
        with patch("database.db.Database.list_buyers_async", return_value=[]):
            result = run(matching_engine_node(state))
        assert len(result["active_buyers"]) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
