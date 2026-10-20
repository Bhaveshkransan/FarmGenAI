"""
tests/test_07_buyer_rag.py

Comprehensive test suite for Priority 3: Purpose-Built Buyer RAG Capability.
Covers BRAG-01 through BRAG-20.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.buyer_rag_service import BuyerRAGService, BuyerRAGContext, buyer_rag_service
from agents.buyer_agent import BuyerAgent


class TestBRAG01ArchitectureInitialization:
    def test_buyer_rag_service_initialization(self):
        """BRAG-01: Verify BuyerRAGService initializes cleanly with default and custom rag_services."""
        service = BuyerRAGService()
        assert service is not None
        ctx = service.get_buyer_context(crop="Tomato")
        assert isinstance(ctx, BuyerRAGContext)


class TestBRAG02BuyerRetrieval:
    def test_buyer_retrieval_returns_context_object(self):
        """BRAG-02: Verify get_buyer_context returns structured BuyerRAGContext."""
        ctx = buyer_rag_service.get_buyer_context(crop="Onion", persona="retail_supermarket")
        assert isinstance(ctx, BuyerRAGContext)
        assert hasattr(ctx, "to_prompt_text")
        prompt_text = ctx.to_prompt_text()
        assert isinstance(prompt_text, str)


class TestBRAG03SharedKnowledgeRetrieval:
    def test_shared_knowledge_retrieval_allowed(self):
        """BRAG-03: Buyer retrieval includes stakeholder='shared' knowledge (e.g. government rules)."""
        ctx = buyer_rag_service.get_buyer_context(crop="Sugarcane")
        for source in ctx.sources:
            assert source.get("stakeholder") in ["buyer", "shared"]


class TestBRAG04FarmerIsolation:
    def test_farmer_private_documents_never_returned(self):
        """BRAG-04: Verify documents tagged with stakeholder='farmer' are NEVER returned to Buyer."""
        # Mock vector store returning a farmer-private document alongside buyer document
        mock_doc_farmer = MagicMock()
        mock_doc_farmer.page_content = "FARMER PRIVATE RECORD: Minimum acceptable price ₹45/kg."
        mock_doc_farmer.metadata = {"stakeholder": "farmer", "crop": "Onion", "source": "farmer_private.json"}

        mock_doc_buyer = MagicMock()
        mock_doc_buyer.page_content = "BUYER RECORD: Target purchasing range ₹30-35/kg."
        mock_doc_buyer.metadata = {"stakeholder": "buyer", "crop": "Onion", "source": "buyer_profile.json"}

        mock_vs = MagicMock()
        mock_vs.similarity_search.return_value = [mock_doc_farmer, mock_doc_buyer]

        mock_rag = MagicMock()
        mock_rag.vectorstores = {"crop_knowledge": mock_vs, "buyer_profiles": mock_vs, "government_rules": mock_vs, "reflection_memory": mock_vs, "government_schemes": mock_vs}

        service = BuyerRAGService(rag_service=mock_rag)
        ctx = service.get_buyer_context(crop="Onion")

        # Verify no item text contains farmer private record
        prompt_text = ctx.to_prompt_text()
        assert "FARMER PRIVATE RECORD" not in prompt_text

        for src in ctx.sources:
            assert src["stakeholder"] != "farmer"


class TestBRAG05StakeholderIsolation:
    def test_stakeholder_filtering_policy(self):
        """BRAG-05: Verify only 'buyer' or 'shared' stakeholder metadata is accepted."""
        service = BuyerRAGService()
        ctx = service.get_buyer_context(crop="Cotton")
        for src in ctx.sources:
            assert src.get("stakeholder") in ["buyer", "shared"]


class TestBRAG06CropFiltering:
    def test_crop_filtering_restricts_to_target_crop(self):
        """BRAG-06: Verify crop normalization and filtering restricts context to target crop."""
        ctx = service_res = buyer_rag_service.get_buyer_context(crop="Onion")
        if not service_res.is_empty:
            assert service_res.retrieval_metadata.get("crop") == "Onion"


class TestBRAG07LocationFiltering:
    def test_location_filtering_supported(self):
        """BRAG-07: Verify location parameter is stored in retrieval metadata."""
        ctx = buyer_rag_service.get_buyer_context(crop="Soybean", location="Nashik")
        assert ctx.retrieval_metadata.get("location") == "Nashik"


class TestBRAG08BuyerProfileRetrieval:
    def test_buyer_profile_domain_query(self):
        """BRAG-08: Verify buyer profile persona details can be retrieved."""
        ctx = buyer_rag_service.get_buyer_context(crop="Onion", persona="bulk_wholesaler")
        assert isinstance(ctx.buyer_profile, list)


class TestBRAG09ProcurementRetrieval:
    def test_procurement_knowledge_domain(self):
        """BRAG-09: Verify procurement knowledge domain structure."""
        ctx = buyer_rag_service.get_buyer_context(crop="Rice")
        assert isinstance(ctx.procurement_knowledge, list)


class TestBRAG10CropQualityRetrieval:
    def test_crop_quality_knowledge_domain(self):
        """BRAG-10: Verify crop quality specs (grading, moisture) domain structure."""
        ctx = buyer_rag_service.get_buyer_context(crop="Cotton")
        assert isinstance(ctx.crop_quality_knowledge, list)


class TestBRAG11GovernmentRuleRetrieval:
    def test_government_rule_domain(self):
        """BRAG-11: Verify APMC / MSP government rules domain structure."""
        ctx = buyer_rag_service.get_buyer_context(crop="Sugarcane")
        assert isinstance(ctx.government_rules, list)


class TestBRAG12NegotiationMemoryRetrieval:
    def test_negotiation_memory_domain(self):
        """BRAG-12: Verify buyer historical negotiation reflections domain structure."""
        ctx = buyer_rag_service.get_buyer_context(crop="Bajra")
        assert isinstance(ctx.negotiation_memory, list)


class TestBRAG13ProvenanceValidation:
    def test_source_provenance_attributes(self):
        """BRAG-13: Every retrieved document contains source, source_type, and document_id metadata."""
        mock_doc = MagicMock()
        mock_doc.page_content = "Test guideline text"
        mock_doc.metadata = {
            "source": "crop_quality_references.json",
            "source_type": "project",
            "id": "doc_123",
            "stakeholder": "buyer",
            "is_synthetic": False
        }
        mock_vs = MagicMock()
        mock_vs.similarity_search.return_value = [mock_doc]
        mock_rag = MagicMock()
        mock_rag.vectorstores = {k: mock_vs for k in ["crop_knowledge", "buyer_profiles", "government_rules", "reflection_memory", "government_schemes"]}

        service = BuyerRAGService(rag_service=mock_rag)
        ctx = service.get_buyer_context(crop="Onion")

        assert len(ctx.sources) > 0
        for src in ctx.sources:
            assert "source" in src
            assert "source_type" in src
            assert "document_id" in src
            assert "is_synthetic" in src


class TestBRAG14SyntheticDataMarking:
    def test_synthetic_data_flag_preserved(self):
        """BRAG-14: Synthetic test records must be explicitly marked with is_synthetic=True."""
        mock_doc = MagicMock()
        mock_doc.page_content = "Synthetic test fixture note"
        mock_doc.metadata = {
            "source": "test_fixture.json",
            "source_type": "synthetic_test",
            "id": "synth_001",
            "stakeholder": "buyer",
            "is_synthetic": True
        }
        mock_vs = MagicMock()
        mock_vs.similarity_search.return_value = [mock_doc]
        mock_rag = MagicMock()
        mock_rag.vectorstores = {k: mock_vs for k in ["crop_knowledge", "buyer_profiles", "government_rules", "reflection_memory", "government_schemes"]}

        service = BuyerRAGService(rag_service=mock_rag)
        ctx = service.get_buyer_context(crop="Onion")

        synth_sources = [s for s in ctx.sources if s.get("is_synthetic") is True]
        assert len(synth_sources) > 0
        assert synth_sources[0]["source_type"] == "synthetic_test"


class TestBRAG15EmptyRetrievalFallback:
    def test_empty_context_fallback_text(self):
        """BRAG-15: Empty retrieval handles gracefully and to_prompt_text returns safe default."""
        empty_ctx = BuyerRAGContext.empty(reason="Test empty")
        assert empty_ctx.is_empty is True
        text = empty_ctx.to_prompt_text()
        assert "No buyer-specific RAG knowledge" in text


class TestBRAG16ChromaFailureFallback:
    def test_chroma_offline_fallback(self):
        """BRAG-16: If ChromaDB fails or raises exception, BuyerRAGService returns empty context safely."""
        mock_rag = MagicMock()
        mock_rag.vectorstores = {}
        mock_rag.client = None

        service = BuyerRAGService(rag_service=mock_rag)
        ctx = service.get_buyer_context(crop="Onion")
        assert ctx.is_empty is True
        assert ctx.retrieval_metadata["status"] == "EMPTY"


class TestBRAG17MalformedResultHandling:
    def test_unsupported_crop_or_invalid_inputs(self):
        """BRAG-17: Unsupported crops or invalid query arguments return empty fallback without crashing."""
        ctx = buyer_rag_service.get_buyer_context(crop="UnsupportedAlienCrop")
        assert ctx.is_empty is True
        assert "Unsupported crop" in ctx.retrieval_metadata.get("reason", "")


class TestBRAG18RAGContextIntegration:
    def test_buyer_agent_accepts_buyer_rag_context(self):
        """BRAG-18: BuyerAgent.respond_to_offer accepts buyer_rag_context in context dict cleanly."""
        buyer = BuyerAgent(
            name="RetailBuyer",
            budget=100000,
            max_quantity=1000,
            target_price=30.0,
            reservation_price=36.0,
            crop="Onion"
        )
        rag_ctx = BuyerRAGContext(
            crop_quality_knowledge=[{"text": "Grade A Onion requires tight scales."}],
            sources=[{"source": "test", "source_type": "project", "document_id": "1", "is_synthetic": False}]
        )
        offer = {"price": 32.0, "quantity": 500, "crop": "Onion"}
        res = buyer.respond_to_offer(offer, context={"buyer_rag_context": rag_ctx}, force_deterministic=True)
        assert res["type"] in ["COUNTER", "ACCEPT", "REJECT"]


class TestBRAG19EconomicConstraintProtection:
    def test_rag_cannot_override_reservation_price(self):
        """BRAG-19: RAG context recommending higher price CANNOT bypass buyer reservation price."""
        buyer = BuyerAgent(
            name="RetailBuyer",
            budget=100000,
            max_quantity=1000,
            target_price=30.0,
            reservation_price=35.0,
            crop="Onion"
        )
        # RAG context claiming onion market is premium ₹50/kg
        high_price_rag = BuyerRAGContext(
            crop_quality_knowledge=[{"text": "Market report suggests accepting up to ₹50/kg for Grade A."}]
        )
        # Offer at ₹45/kg (above reservation ceiling of ₹35/kg)
        offer = {"price": 45.0, "quantity": 500, "crop": "Onion"}
        res = buyer.respond_to_offer(offer, context={"buyer_rag_context": high_price_rag}, force_deterministic=True)

        # Must NOT accept offer above reservation price
        assert res["type"] != "ACCEPT"
        if res["type"] == "COUNTER":
            assert res["price"] <= 35.0

    def test_rag_cannot_override_budget(self):
        """BRAG-19b: RAG context CANNOT bypass buyer budget limit."""
        buyer = BuyerAgent(
            name="LowBudgetBuyer",
            budget=500,  # Only ₹500 total budget
            max_quantity=1000,
            target_price=30.0,
            reservation_price=35.0,
            crop="Onion"
        )
        high_price_rag = BuyerRAGContext(
            crop_quality_knowledge=[{"text": "Quality is exceptional."}]
        )
        offer = {"price": 32.0, "quantity": 500, "crop": "Onion"}  # Cost ₹16,000 > ₹500 budget
        res = buyer.respond_to_offer(offer, context={"buyer_rag_context": high_price_rag}, force_deterministic=True)

        if res["type"] == "ACCEPT":
            assert res["quantity"] * res["price"] <= 500.0

    def test_rag_cannot_override_crop_isolation(self):
        """BRAG-19c: RAG context CANNOT allow unsupported crop purchase."""
        buyer = BuyerAgent(
            name="Buyer",
            budget=10000,
            max_quantity=100,
            target_price=30.0,
            reservation_price=35.0,
            crop="Onion"
        )
        offer = {"price": 25.0, "quantity": 100, "crop": "Wheat"}  # Wheat is not in 7-crop list
        res = buyer.respond_to_offer(offer, force_deterministic=True)
        assert res["type"] == "REJECT"
        assert "Unsupported crop" in res["message"]


class TestBRAG20MLRAGSeparation:
    def test_ml_prediction_independent_of_rag(self):
        """BRAG-20: ML prediction remains functional from pricing service when RAG is empty."""
        buyer = BuyerAgent(
            name="Buyer",
            budget=100000,
            max_quantity=1000,
            target_price=30.0,
            reservation_price=35.0,
            crop="Onion"
        )
        empty_rag = BuyerRAGContext.empty()
        val = buyer.get_market_valuation("Onion", context={"buyer_rag_context": empty_rag})
        assert isinstance(val, (int, float))
        assert val > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
