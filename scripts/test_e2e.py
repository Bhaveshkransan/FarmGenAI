import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("E2E_Test")

API_BASE = "http://localhost:8000/api/v1/"
TEST_USER = {"user_id": "u-test-1", "role": "FARMER"}

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.core.security import create_access_token

async def run_tests():
    logger.info("Starting E2E Regression Tests...")
    
    token = await create_access_token({"sub": "u-test-1", "role": "FARMER"})

    async with httpx.AsyncClient(base_url=API_BASE, headers={"Authorization": f"Bearer {token}"}) as client:
        # 1. Test Health
        try:
            res = await client.get("http://localhost:8000/health")
            if res.status_code == 200:
                logger.info("✅ System Health Check: PASS")
            else:
                logger.error("❌ System Health Check: FAIL")
        except Exception as e:
            logger.error(f"❌ System Health Check: ERROR ({e})")

        # 2. Test RAG Endpoint
        try:
            res = await client.get("rag/query?q=onion&collection=market_prices&limit=1")
            if res.status_code == 200 and res.json().get("success"):
                logger.info("✅ RAG Query Endpoint: PASS")
            else:
                logger.error("❌ RAG Query Endpoint: FAIL")
        except Exception as e:
            logger.error(f"❌ RAG Query Endpoint: ERROR ({e})")

        # 3. Test Workflow Planner
        try:
            payload = {
                "crop": "Onion",
                "quantity": 1500,
                "min_price": 20,
                "location": "Nashik",
                "spoilage_days": 2
            }
            res = await client.post("workflows/plan", json=payload)
            if res.status_code == 200 and res.json().get("success"):
                logger.info("✅ Workflow Planner POST: PASS")
            else:
                logger.error(f"❌ Workflow Planner POST: FAIL ({res.text})")
        except Exception as e:
            logger.error(f"❌ Workflow Planner POST: ERROR ({e})")

        # 4. Test GET Workflow Plans (Persistence check)
        try:
            res = await client.get("workflows/")
            if res.status_code == 200 and res.json().get("success"):
                logger.info("✅ Workflow Planner GET (Persistence): PASS")
            else:
                logger.error("❌ Workflow Planner GET: FAIL")
        except Exception as e:
            logger.error(f"❌ Workflow Planner GET: ERROR ({e})")

        # 5. Test Processor Pending Offers
        try:
            res = await client.get("negotiations/?status=ESCALATED_PROCESSING")
            if res.status_code == 200:
                logger.info("✅ Processor Escalated Offers: PASS")
            else:
                logger.error("❌ Processor Escalated Offers: FAIL")
        except Exception as e:
            logger.error(f"❌ Processor Escalated Offers: ERROR ({e})")

    logger.info("E2E Tests Completed.")

if __name__ == "__main__":
    asyncio.run(run_tests())
