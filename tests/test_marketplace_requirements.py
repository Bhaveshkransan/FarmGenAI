import unittest

from fastapi.testclient import TestClient

import agents.buyer_agent as buyer_agent_module
import agents.farmer_agent as farmer_agent_module
from backend.main import app
from backend.services.negotiation_service import service
from database.db import Database


class MarketplaceRequirementsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        import asyncio
        asyncio.run(Database.reset())
        service.active_negotiations.clear()
        asyncio.run(service.ensure_default_buyers())
        buyer_agent_module.llm_client = None
        farmer_agent_module.llm_client = None
        
        # Override JWT auth for testing REST routes
        from backend.services.security import get_current_user
        app.dependency_overrides[get_current_user] = lambda: {"sub": "test_user_001", "role": "farmer"}

    def tearDown(self):
        app.dependency_overrides.clear()

    def _start_negotiation(self, farmer_name="Farmer One", crop="Soybean", quantity=900, min_price=68):
        payload = {
            "farmer_name": farmer_name,
            "crop": crop,
            "quantity": quantity,
            "min_price": min_price,
            "shelf_life": 4,
            "location": "Latur",
            "quality": "A",
            "language": "English",
        }
        response = self.client.post("/api/v1/negotiations/", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()

        # With background tasks the endpoint returns RUNNING immediately.
        # The TestClient completes background tasks before returning, so a
        # single status poll is enough to retrieve the real result.
        if result.get("status") == "RUNNING":
            neg_id = result["negotiation_id"]
            status_resp = self.client.get(f"/api/v1/negotiations/{neg_id}")
            if status_resp.status_code == 200:
                result = status_resp.json()

        return result

    def test_farmer_listing_gets_multiple_buyer_offers(self):
        result = self._start_negotiation()
        self.assertGreaterEqual(len(result.get("market_offers", [])), 3)
        self.assertIsNotNone(result.get("selected_buyer"))
        self.assertIn("Marketplace scan", "\n".join(result.get("logs", [])))

    def test_best_ranked_buyer_is_selected(self):
        result = self._start_negotiation(min_price=70)

        market_offers = result.get("market_offers", [])
        self.assertTrue(market_offers)
        self.assertEqual(result["selected_buyer"]["buyer_id"], market_offers[0]["buyer_id"])
        self.assertGreaterEqual(market_offers[0]["offered_price"], market_offers[-1]["offered_price"])

    def test_buyer_dashboard_has_many_farmer_listings_and_buyers(self):
        self._start_negotiation(farmer_name="Farmer Alpha", crop="Soybean", quantity=1000, min_price=68)
        self._start_negotiation(farmer_name="Farmer Beta", crop="Onion", quantity=700, min_price=22)

        produce_response = self.client.get("/api/v1/listings/")
        buyers_response = self.client.get("/api/v1/buyers/")

        self.assertEqual(produce_response.status_code, 200)
        self.assertEqual(buyers_response.status_code, 200)
        self.assertGreaterEqual(len(produce_response.json().get("data", [])), 2)
        self.assertGreaterEqual(len(buyers_response.json().get("buyers", [])), 3)


if __name__ == "__main__":
    unittest.main()