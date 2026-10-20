import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.rag_service import rag_service

async def main():
    print("Ingesting knowledge base (documents/PDFs)...")
    rag_service.ingest_knowledge_base()
    
    print("Ingesting mandi prices and historical negotiations...")
    rag_service.ingest_mandi_prices_and_negotiations()
    
    print("Ingestion complete.")

if __name__ == "__main__":
    asyncio.run(main())
