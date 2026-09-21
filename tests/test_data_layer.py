import unittest
import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db import Database
from backend.services.rag_service import rag_service
from backend.agents.graph_orchestrator import _build_rag_context

class TestDataLayer(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        import asyncio
        from database.db import init_db
        from scripts.seed_real_database import seed as seed_data
        
        async def _setup():
            await init_db()
            await seed_data()
            
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            
        if loop and loop.is_running():
            import threading
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(_setup())
                new_loop.close()
            t = threading.Thread(target=run_in_thread)
            t.start()
            t.join()
        else:
            asyncio.run(_setup())

        # Ingest RAG data to ensure the vector store has the required documents for testing
        rag_service.ingest_knowledge_base()
        rag_service.ingest_mandi_prices_and_negotiations()
    
    def test_database_helpers(self):
        """Test structured facts lookups from the database."""
        # 1. MSP Price
        soybean_msp = Database.get_msp_price("Soybean")
        self.assertIsNotNone(soybean_msp)
        self.assertGreater(soybean_msp, 0)
        print(f"Verified Soybean MSP: Rs.{soybean_msp}/quintal")
        
        # 2. Market Mapping
        nashik_markets = Database.get_market_mappings("Nashik")
        self.assertIsInstance(nashik_markets, list)
        self.assertGreater(len(nashik_markets), 0)
        self.assertEqual(nashik_markets[0]["district"], "Nashik")
        print(f"Verified Nashik APMC mappings: {[m['market_name'] for m in nashik_markets]}")

        # 3. Crop Quality
        quality = Database.get_crop_quality_reference("Soybean")
        self.assertIsInstance(quality, list)
        self.assertGreater(len(quality), 0)
        print(f"Verified Soybean Quality reference (Grade {quality[0]['grade']})")

        # 4. Seasonal Calendar
        events = Database.get_seasonal_calendar()
        self.assertIsInstance(events, list)
        self.assertGreater(len(events), 0)
        print(f"Verified Seasonal Calendar events: {[e['event_name'] for e in events]}")

    def test_embeddings_and_rag(self):
        """Test RAG service search & configurable embeddings."""
        # Test vector stores are bound
        self.assertIsNotNone(rag_service.vector_store_crop_knowledge)
        self.assertIsNotNone(rag_service.vector_store_mandi)
        
        # Test custom similarity queries
        onion_notes = rag_service.query_crop_knowledge("kharif onion seeding water", crop="Onion", n_results=1)
        self.assertIsInstance(onion_notes, list)
        self.assertGreater(len(onion_notes), 0)
        self.assertIn("crop", onion_notes[0]["metadata"])
        print(f"Verified RAG Crop Knowledge retrieval: {onion_notes[0]['text'][:100]}...")

        # Test mandi semantic query wrapper
        mandi_results = rag_service.query_mandi_records("Soybean market price", n_results=1)
        self.assertIn("documents", mandi_results)
        self.assertGreater(len(mandi_results["documents"][0]), 0)
        raw_mandi_text = mandi_results['documents'][0][0]
        safe_mandi_text = raw_mandi_text.encode('ascii', errors='replace').decode('ascii')
        print(f"Verified RAG Mandi price search: {safe_mandi_text}")

    def test_e2e_rag_context_weather(self):
        """Test weather API call and E2E context building."""
        # This calls Open-Meteo live API and connects RAG
        import asyncio
        context = asyncio.run(_build_rag_context(crop="Soybean", location="Latur"))
        self.assertIsNotNone(context)
        self.assertIn("MSP", context)
        self.assertIn("Weather", context)
        self.assertIn("Soybean", context)
        self.assertIn("Mandi", context)
        print("Verified E2E Agent RAG Context Building successfully!")
        print("\n=== Context Snippet ===")
        print(context[:400].encode('ascii', errors='replace').decode('ascii'))
        print("=======================")

if __name__ == "__main__":
    unittest.main()
