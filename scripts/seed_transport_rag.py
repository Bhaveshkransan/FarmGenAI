import os
import chromadb
from datetime import datetime

# Connect to ChromaDB (Assuming it runs on localhost:8000 in dev, or direct if embedded)
try:
    client = chromadb.HttpClient(host='localhost', port=8000)
    print("Connected to ChromaDB via HTTP")
except Exception as e:
    print(f"HTTP Client failed: {e}")
    # Fallback to local
    client = chromadb.PersistentClient(path="./node_storage/chroma_db")

market_collection = client.get_or_create_collection("market_prices")
strategy_collection = client.get_or_create_collection("reflection_memory")
knowledge_collection = client.get_or_create_collection("crop_knowledge")

# Seed Market Prices for Produce / Freight
market_docs = [
    "Average freight rates for Produce in Maharashtra have increased by 2% due to rising diesel costs. Current average is ₹6.50/kg for a 100km trip.",
    "Latur to Pune standard logistics rate for bulk agricultural goods stands at roughly ₹5.80/kg.",
    "Refrigerated transport commands a 15-20% premium. Current rates for cold chain transport are ₹8.00/kg."
]
market_metas = [{"crop": "Produce", "type": "Freight Rate"}, {"crop": "Produce", "type": "Freight Rate"}, {"crop": "Produce", "type": "Cold Chain"}]
market_ids = ["freight_m1", "freight_m2", "freight_m3"]
market_collection.upsert(documents=market_docs, metadatas=market_metas, ids=market_ids)

# Seed Strategy
strategy_docs = [
    "When Stakeholders push for rates below ₹5.00/kg, Transporters should highlight vehicle wear and tear and non-negotiable toll costs.",
    "If a Transporter's initial quote is rejected, they should drop the price by exactly 5% in the first counter to show goodwill without collapsing the margin.",
    "Always stand firm on the floor price. Accepting below floor price ruins fleet sustainability."
]
strategy_metas = [{"crop": "Produce", "agent": "Transporter"}, {"crop": "Produce", "agent": "Transporter"}, {"crop": "Produce", "agent": "Transporter"}]
strategy_ids = ["strat_t1", "strat_t2", "strat_t3"]
strategy_collection.upsert(documents=strategy_docs, metadatas=strategy_metas, ids=strategy_ids)

# Seed Knowledge
knowledge_docs = [
    "Produce transportation requires specialized handling. Loading and unloading times can exceed 3 hours for 1000kg.",
    "Maharashtra APMC regulations mandate that transport vehicles used for agricultural produce must have valid e-way bills if crossing districts.",
    "During monsoon season, tarpaulin covers are mandatory for open trucks carrying perishable produce."
]
knowledge_metas = [{"crop": "Produce", "topic": "Handling"}, {"crop": "Produce", "topic": "Regulations"}, {"crop": "Produce", "topic": "Weather"}]
knowledge_ids = ["know_t1", "know_t2", "know_t3"]
knowledge_collection.upsert(documents=knowledge_docs, metadatas=knowledge_metas, ids=knowledge_ids)

print("Successfully seeded Transport RAG contexts into ChromaDB!")
