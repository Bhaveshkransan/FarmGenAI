import os
import asyncio
import sys
import hashlib

sys.path.append("/app")
from backend.services.rag_service import RAGService

# Transport Logistics Knowledge
logistics_docs = [
    {
        "content": "Sugarcane transportation requires heavy trucks due to high density and weight. Moisture loss during transit is minimal, but loading and unloading require mechanical assistance or significant manual labor.",
        "meta": {"crop": "Sugarcane", "topic": "handling", "category": "crop_logistics"}
    },
    {
        "content": "Soybean is relatively hardy but must be protected from moisture. Covered trucks are recommended during monsoon. Standard bulk handling is acceptable.",
        "meta": {"crop": "Soybean", "topic": "handling", "category": "crop_logistics"}
    },
    {
        "content": "Cotton is extremely lightweight and bulky. Volumetric capacity of the vehicle is more important than weight capacity. High risk of fire; avoid exposure to sparks during transport.",
        "meta": {"crop": "Cotton", "topic": "vehicle_selection", "category": "crop_logistics"}
    },
    {
        "content": "Onion bulbs require careful handling and ventilation during long-distance road transport. Lack of ventilation causes heat buildup, sprouting, and spoilage. Do not pack in airtight containers. Use open trucks with netting or well-ventilated vehicles.",
        "meta": {"crop": "Onion", "topic": "handling", "category": "crop_logistics"}
    },
    {
        "content": "Jowar (Sorghum) should be transported in dry conditions. Grain bags must be secured to prevent shifting. Relatively low perishability risk.",
        "meta": {"crop": "Jowar", "topic": "handling", "category": "crop_logistics"}
    },
    {
        "content": "Bajra requires standard dry bulk transport considerations. Protect from rain.",
        "meta": {"crop": "Bajra", "topic": "handling", "category": "crop_logistics"}
    },
    {
        "content": "Rice transport requires protection from moisture. Polished rice is susceptible to breakage if handled roughly during loading. Covered vehicles are essential.",
        "meta": {"crop": "Rice", "topic": "handling", "category": "crop_logistics"}
    },
    {
        "content": "Agricultural Freight Guidelines: When calculating profitability, deadhead distance (empty return trips) must be factored in. For perishable crops, delivery deadlines are strict, and vehicle reliability is paramount.",
        "meta": {"topic": "freight_negotiation", "category": "transport_knowledge"}
    },
    {
        "content": "Refrigerated transport (cold chain) is typically NOT required for standard onion, cotton, or grains, but may be necessary for highly perishable exotics or dairy. Heavy trucks (10-15 tons) are most efficient for distances over 300km.",
        "meta": {"topic": "vehicle_selection", "category": "transport_knowledge"}
    },
    {
        "content": "Mini trucks and pickups (1-2 tons) are optimal for short hauls (under 100km) or highly perishable goods needing urgent farm-to-mandi delivery.",
        "meta": {"topic": "vehicle_selection", "category": "transport_knowledge"}
    }
]

# Historical Negotiation Memory (Strategy)
strategy_docs = [
    {
        "content": "Transport negotiation: When the stakeholder offer is below operating cost, always reject or counter firmly. Highlight the actual fuel and toll costs to justify the floor price.",
        "meta": {"topic": "freight_negotiation_strategy", "category": "transport_strategy"}
    },
    {
        "content": "When transporting highly perishable goods like Onions over long distances (e.g., Nashik to Mumbai), transporters can command a slight premium due to the urgency and careful handling required.",
        "meta": {"crop": "Onion", "topic": "freight_negotiation_strategy", "category": "transport_strategy"}
    },
    {
        "content": "Never accept a deal below the minimum acceptable price. A truck standing idle is better than a trip that loses money.",
        "meta": {"topic": "freight_negotiation_strategy", "category": "transport_strategy"}
    }
]

def generate_id(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]

async def main():
    rag = RAGService()
    # Ensure Chroma is loaded
    await asyncio.sleep(2)
    
    print(f"Using Embedding Model: {os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')}")
    print(f"Connected to Client: {rag.client.__class__.__name__}")

    tk_col = rag.collections.get("transport_knowledge")
    sm_col = rag.collections.get("reflection_memory")  # We reuse reflection_memory for strategy
    
    if not tk_col or not sm_col:
        print("Failed to access required collections!")
        return
        
    print("Ingesting Transport Knowledge...")
    for doc in logistics_docs:
        doc_id = generate_id(doc["content"])
        doc["meta"]["source_id"] = doc_id
        # We manually embed to ensure we use the explicit model configured in RAGService
        embedding = rag.langchain_embeddings.embed_documents([doc["content"]])[0]
        
        tk_col.upsert(
            documents=[doc["content"]],
            metadatas=[doc["meta"]],
            ids=[doc_id],
            embeddings=[embedding]
        )
        
    print("Ingesting Transport Strategy Memory...")
    for doc in strategy_docs:
        doc_id = generate_id(doc["content"])
        doc["meta"]["source_id"] = doc_id
        embedding = rag.langchain_embeddings.embed_documents([doc["content"]])[0]
        
        sm_col.upsert(
            documents=[doc["content"]],
            metadatas=[doc["meta"]],
            ids=[doc_id],
            embeddings=[embedding]
        )
        
    print("="*40)
    print("TRANSPORT RAG INGESTION COMPLETE")
    print("="*40)
    print(f"transport_knowledge count: {tk_col.count()}")
    print(f"reflection_memory count: {sm_col.count()}")
    
    # Test semantic query
    print("\nRunning Semantic Test: 'How should onions be handled during transportation?'")
    results = tk_col.query(
        query_embeddings=[rag.langchain_embeddings.embed_query("How should onions be handled during transportation?")],
        n_results=2
    )
    print(f"Results: {results['documents'][0]}")

if __name__ == '__main__':
    asyncio.run(main())
