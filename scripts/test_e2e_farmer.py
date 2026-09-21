import httpx
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

BASE_URL = "http://localhost:8000/api/v1"

def test_farmer_e2e():
    try:
        logging.info("Testing Market Intelligence (MandiMitra)...")
        res = httpx.get(f"{BASE_URL}/market-intelligence/compare?crop=Soybean&lat=19.99&lon=73.78", timeout=5)
        if res.status_code == 200:
            logging.info("  [x] Market Intelligence successful")
        else:
            logging.error(f"  [ ] Market Intelligence failed: {res.status_code} - {res.text}")

        res = httpx.get(f"{BASE_URL}/market-intelligence/insights?crop=Cotton&location=Nashik", timeout=10)
        if res.status_code == 200:
            logging.info("  [x] Market Insights successful")
        else:
            logging.error(f"  [ ] Market Insights failed: {res.status_code} - {res.text}")

        payload = {
            "user_id": "test-farmer",
            "farmer_name": "Test Farmer",
            "crop": "Sugarcane",
            "quantity": 500,
            "min_price": 40,
            "shelf_life": 5,
            "location": "Nashik",
            "quality": "A",
            "language": "English"
        }
        logging.info("Testing Start Negotiation...")
        res = httpx.post(f"{BASE_URL}/negotiations/", json=payload, timeout=20)
        if res.status_code == 200:
            logging.info(f"  [x] Negotiation Started successfully! ID: {res.json().get('negotiation_id')}")
        else:
            logging.error(f"  [ ] Negotiation failed: {res.status_code} - {res.text}")

    except Exception as e:
        logging.error(f"Test failed: {e}")

if __name__ == "__main__":
    test_farmer_e2e()
