"""
scripts/manual_buyer_rag_verification.py
------------------------------------------------------------------------
Manual Verification Demonstration for Priority 5B: Buyer RAG Knowledge Base.
"""

import sys
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

sys.stdout.reconfigure(encoding="utf-8")

from backend.services.buyer_rag_service import buyer_rag_service, BuyerRAGContext
from agents.buyer_agent import BuyerAgent


def run_manual_verification():
    print("================================================================")
    print("MANUAL BUYER RAG VERIFICATION DEMONSTRATION")
    print("================================================================\n")

    # 1. Query specification
    crop = "Soybean"
    location = "Maharashtra"
    persona = "bulk_wholesaler"
    query_text = "Soybean procurement Maharashtra quality freshness bulk buyer persona"

    print("1. QUERY PARAMETERS:")
    print(f"   Crop: {crop}")
    print(f"   Location: {location}")
    print(f"   Persona: {persona}")
    print(f"   Query: {query_text}\n")

    # 2. Retrieve Buyer RAG Context
    ctx = buyer_rag_service.get_buyer_context(crop=crop, location=location, persona=persona, query=query_text)

    print("2. RETRIEVAL STATUS & METADATA:")
    print(f"   Status: {ctx.retrieval_metadata.get('status')}")
    print(f"   Isolation Policy: {ctx.retrieval_metadata.get('isolation_policy')}")
    print(f"   Retrieved Count: {ctx.retrieval_metadata.get('retrieved_count')} documents\n")

    print("3. RETRIEVED SOURCES & PROVENANCE:")
    for i, s in enumerate(ctx.sources, 1):
        print(f"   [{i}] Source: {s.get('source')} | Domain: {s.get('domain')} | Stakeholder: {s.get('stakeholder')} | Synthetic: {s.get('is_synthetic')}")
    print()

    print("4. RETRIEVED DOMAINS BREAKDOWN:")
    print(f"   - Buyer Profile Items: {len(ctx.buyer_profile)}")
    print(f"   - Procurement Knowledge Items: {len(ctx.procurement_knowledge)}")
    print(f"   - Crop Quality Knowledge Items: {len(ctx.crop_quality_knowledge)}")
    print(f"   - Government Rules Items: {len(ctx.government_rules)}")
    print(f"   - Negotiation Memory Items: {len(ctx.negotiation_memory)}")
    print(f"   - Shared Knowledge Items: {len(ctx.shared_knowledge)}\n")

    # 3. Instantiate Buyer Agent and execute negotiation turn WITH RAG
    buyer = BuyerAgent(
        name="MaharashtraBulkBuyer",
        budget=150000.0,
        max_quantity=2000.0,
        target_price=46.0,
        reservation_price=52.0,
        crop="Soybean",
        persona="bulk_wholesaler",
    )

    incoming_offer = {"price": 49.0, "quantity": 500.0, "crop": "Soybean"}
    response_with_rag = buyer.respond_to_offer(
        incoming_offer,
        context={"buyer_rag_context": ctx, "location": "Maharashtra"},
        force_deterministic=True
    )

    print("5. BUYER BEHAVIOR WITH RAG CONTEXT:")
    print(f"   Incoming Offer: Rs {incoming_offer['price']}/kg for {incoming_offer['quantity']} kg")
    print(f"   Buyer Target: Rs {buyer.target_price}/kg | Reservation: Rs {buyer.reservation_price}/kg")
    print(f"   Decision: {response_with_rag.get('type')}")
    print(f"   Counter/Accept Price: Rs {response_with_rag.get('price')}/kg")
    print(f"   Accepted Quantity: {response_with_rag.get('quantity')} kg")
    print(f"   Message: {response_with_rag.get('message')}\n")

    # 4. Execute negotiation turn WITHOUT RAG (RAG Unavailable / Offline)
    empty_ctx = BuyerRAGContext.empty(reason="ChromaDB offline simulation")
    response_without_rag = buyer.respond_to_offer(
        incoming_offer,
        context={"buyer_rag_context": empty_ctx, "location": "Maharashtra"},
        force_deterministic=True
    )

    print("6. BUYER BEHAVIOR WITHOUT RAG (RAG UNAVAILABLE):")
    print(f"   Incoming Offer: Rs {incoming_offer['price']}/kg for {incoming_offer['quantity']} kg")
    print(f"   Decision: {response_without_rag.get('type')}")
    print(f"   Counter/Accept Price: Rs {response_without_rag.get('price')}/kg")
    print(f"   Accepted Quantity: {response_without_rag.get('quantity')} kg")
    print(f"   Message: {response_without_rag.get('message')}\n")

    print("================================================================")
    print("MANUAL VERIFICATION COMPLETED SUCCESSFULLY!")
    print("================================================================")


if __name__ == "__main__":
    run_manual_verification()
