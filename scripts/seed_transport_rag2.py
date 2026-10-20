import os
import asyncio
import sys

# Ensure backend path is recognized
sys.path.append("/app")

from backend.services.rag_service import RAGService

async def main():
    rag = RAGService()
    # Wait for init
    await asyncio.sleep(2)
    
    market_docs = [
        "Average freight rates for Produce in Maharashtra have increased by 2% due to rising diesel costs. Current average is ₹6.50/kg for a 100km trip.",
        "Latur to Pune standard logistics rate for bulk agricultural goods stands at roughly ₹5.80/kg.",
        "Refrigerated transport commands a 15-20% premium. Current rates for cold chain transport are ₹8.00/kg."
    ]
    market_metas = [{"crop": "Produce", "type": "Freight Rate"}, {"crop": "Produce", "type": "Freight Rate"}, {"crop": "Produce", "type": "Cold Chain"}]
    
    strategy_docs = [
        "When Stakeholders push for rates below ₹5.00/kg, Transporters should highlight vehicle wear and tear and non-negotiable toll costs.",
        "If a Transporter's initial quote is rejected, they should drop the price by exactly 5% in the first counter to show goodwill without collapsing the margin.",
        "Always stand firm on the floor price. Accepting below floor price ruins fleet sustainability."
    ]
    strategy_metas = [{"crop": "Produce", "agent": "Transporter"}, {"crop": "Produce", "agent": "Transporter"}, {"crop": "Produce", "agent": "Transporter"}]

    # We will use rag_service's client to insert
    rag.mandi_collection.add(
        documents=market_docs,
        metadatas=market_metas,
        ids=["freight_m1", "freight_m2", "freight_m3"]
    )
    
    rag.strategies_collection.add(
        documents=strategy_docs,
        metadatas=strategy_metas,
        ids=["strat_t1", "strat_t2", "strat_t3"]
    )
    print("Seeded successfully with BGE-M3 embeddings!")

asyncio.run(main())
