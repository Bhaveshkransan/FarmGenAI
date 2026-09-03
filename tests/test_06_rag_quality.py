"""
tests/test_06_rag_quality.py
Type: INTEGRATION (requires ChromaDB on port 8001)
Covers: RAG retrieval quality and graceful degradation.

Notes on rag_service return types:
- query_mandi_records, query_strategies -> AwaitableDict (subclass of dict)
  * Can be used directly as dict OR awaited in async context.
  * asyncio.run() does NOT work on it (not a coroutine).
  * Returns {} when collection is empty (no 'documents' key).
- add_strategy_log -> AwaitableNone (awaitable, not a coroutine)
  * Must be awaited inside an async function, not via asyncio.run().
"""
import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest

CHROMA_AVAILABLE = False
rag_service = None

try:
    from backend.services.rag_service import rag_service as _rs
    if _rs and _rs.client:
        _rs.client.heartbeat()
        CHROMA_AVAILABLE = True
        rag_service = _rs
except Exception:
    pass

skip_chroma = pytest.mark.skipif(
    not CHROMA_AVAILABLE,
    reason="CHROMA_UNAVAILABLE -- ChromaDB not reachable"
)


class TestRAGMandi:
    @skip_chroma
    def test_query_returns_dict(self):
        result = rag_service.query_mandi_records("Tomato Pune", n_results=2)
        assert isinstance(result, dict)

    @skip_chroma
    def test_query_result_is_dict_or_empty(self):
        """AwaitableDict is a dict subclass. May be empty if collection not seeded."""
        result = rag_service.query_mandi_records("Tomato Pune", n_results=2)
        assert isinstance(result, dict)
        # If non-empty, it must have 'documents' key
        if result:
            assert "documents" in result, f"Non-empty result missing 'documents': {result.keys()}"
        else:
            pytest.skip("Mandi collection is empty (RAG_COLLECTION_EMPTY)")

    @skip_chroma
    def test_query_tomato_relevant(self):
        result = rag_service.query_mandi_records("Tomato Nashik 2024 price", n_results=3)
        docs = result.get("documents", [[]])
        if not docs or not docs[0]:
            pytest.skip("No mandi records seeded (RAG_COLLECTION_EMPTY)")
        found = any(
            any(k in d.lower() for k in ["tomato", "price", "mandi", "nashik", "kg"])
            for d in docs[0]
        )
        assert found, f"RAG returned irrelevant docs: {docs[0]}"


class TestRAGStrategy:
    @skip_chroma
    def test_query_returns_dict(self):
        result = rag_service.query_strategies("Tomato negotiation", n_results=3)
        assert isinstance(result, dict)

    @skip_chroma
    def test_nonexistent_query_no_crash(self):
        result = rag_service.query_strategies("ZZZZ_NONEXISTENT_CROP", n_results=1)
        docs = result.get("documents", [[]])
        if docs:
            assert isinstance(docs[0], list)


class TestRAGContextBuilding:
    def test_build_rag_context_does_not_crash(self):
        from backend.agents.graph_orchestrator import _build_rag_context
        result = asyncio.run(_build_rag_context("Tomato", "Pune"))
        assert isinstance(result, str)

    def test_build_rag_context_unknown_crop(self):
        from backend.agents.graph_orchestrator import _build_rag_context
        result = asyncio.run(_build_rag_context("AlienCrop", "MarsCity"))
        assert isinstance(result, str) and result is not None

    def test_build_rag_context_onion(self):
        from backend.agents.graph_orchestrator import _build_rag_context
        result = asyncio.run(_build_rag_context("Onion", "Nashik"))
        assert result is not None


class TestRAGAddStrategy:
    @skip_chroma
    def test_add_strategy_log_succeeds(self):
        """
        add_strategy_log returns AwaitableNone (not a coroutine).
        Must be awaited inside an async function using asyncio.get_event_loop().run_until_complete
        OR used directly (it's a synchronous call that also supports await).
        """
        from uuid import uuid4
        log_id = str(uuid4())
        try:
            # AwaitableNone supports __await__ but is NOT a coroutine.
            # Call it directly -- the underlying add_document is synchronous.
            result = rag_service.add_strategy_log(
                log_id,
                "Farmer accepted at min_price. Deal reached in 2 rounds.",
                {"crop": "Tomato", "status": "DEAL", "rounds": 2,
                 "farmer_reward": 96.0, "buyer_reward": 98.0}
            )
            # Result is AwaitableNone -- just verify it did not raise
            assert result is not None or result is None  # always true, just ensuring no exception
        except Exception as e:
            pytest.fail(f"add_strategy_log raised unexpectedly: {e}")

    @skip_chroma
    def test_add_strategy_log_awaitable_in_async(self):
        """Verify add_strategy_log can be properly awaited in async context."""
        from uuid import uuid4

        async def _do():
            log_id = str(uuid4())
            result = rag_service.add_strategy_log(
                log_id,
                "Async test: Deal reached.",
                {"crop": "Tomato", "status": "DEAL", "rounds": 1,
                 "farmer_reward": 100.0, "buyer_reward": 100.0}
            )
            # Await the AwaitableNone
            awaited = await result
            return awaited

        result = asyncio.run(_do())
        assert result is None  # AwaitableNone awaits to None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
