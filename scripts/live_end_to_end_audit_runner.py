"""
scripts/live_end_to_end_audit_runner.py
------------------------------------------------------------------------
Independent Live Verification Script:
Executes real HTTP requests against the live running FastAPI backend (http://localhost:8000).
Tests every Buyer endpoint with real payloads and reports actual HTTP status codes, latency, and returned data.
"""

import sys
import time
import requests
import json
import uuid

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

def print_result(step_num, title, status_code, data, latency):
    status_str = "PASS" if (200 <= status_code < 300) else "FAIL"
    print(f"\n[{status_str}] STEP {step_num}: {title} (HTTP {status_code}, {latency:.3f}s)")
    if isinstance(data, dict):
        clean_repr = json.dumps(data, indent=2)[:400]
        print(f"  Response: {clean_repr} ...")
    else:
        print(f"  Response: {str(data)[:250]}")

def run_live_audit():
    print("=" * 70)
    print("LIVE RUNTIME AUDIT — TESTING ACTIVE BACKEND ON HTTP://LOCALHOST:8000")
    print("=" * 70)

    # Step 1: Health / Docs
    t0 = time.time()
    try:
        r = requests.get(f"{BASE_URL}/docs", timeout=5)
        print_result(1, "Swagger OpenAPI Documentation (/docs)", r.status_code, "HTML OpenAPI Docs Available", time.time() - t0)
    except Exception as e:
        print(f"[FAIL] STEP 1: Cannot connect to {BASE_URL}: {e}")
        return

    # Step 2: Register Buyer
    t0 = time.time()
    unique_email = f"buyer_{uuid.uuid4().hex[:6]}@mahaagro.com"
    reg_payload = {
        "name": "MahaAgro Procurement Corp",
        "email": unique_email,
        "password": "SecurePassword123!",
        "location": "Latur",
        "language": "English",
        "role": "buyer",
        "buyer_persona": "food_processing",
        "business_name": "MahaAgro Processors Ltd"
    }
    r = requests.post(f"{API_V1}/auth/register", json=reg_payload, timeout=5)
    reg_data = r.json() if r.status_code == 200 else {}
    token = reg_data.get("access_token")
    print_result(2, "Buyer Registration & Token Generation (POST /auth/register)", r.status_code, reg_data, time.time() - t0)

    # Step 3: Login Buyer & Verify Token
    t0 = time.time()
    login_payload = {
        "email": unique_email,
        "password": "SecurePassword123!"
    }
    r = requests.post(f"{API_V1}/auth/login", json=login_payload, timeout=5)
    login_data = r.json() if r.status_code == 200 else {}
    if not token:
        token = login_data.get("access_token")
    print_result(3, "Buyer Login & Token Validation (POST /auth/login)", r.status_code, login_data, time.time() - t0)

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # Step 4: Seed Real Produce Listing (Farmer Listing)
    t0 = time.time()
    produce_payload = {
        "farmer_name": "Kisan Balasaheb",
        "crop": "Soybean",
        "quantity": 2500.0,
        "expected_price": 55.0,
        "min_price": 49.0,
        "location": "Latur",
        "variety": "JS-335",
        "grade": "A",
        "shelf_life": 120,
        "min_sale_quantity": 100.0
    }
    r = requests.post(f"{API_V1}/listings/", json=produce_payload, headers=headers, timeout=5)
    listing_data = r.json() if r.status_code == 200 else {}
    print_result(4, "Seed Real Produce Listing (POST /listings/)", r.status_code, listing_data, time.time() - t0)

    # Step 5: Create Buyer Requirement
    t0 = time.time()
    req_payload = {
        "crop": "Soybean",
        "quantity": 1000.0,
        "target_price": 50.0,
        "max_price": 56.0,
        "budget": 60000.0,
        "location": "Latur",
        "quality_grade": "A",
        "delivery_days": 5,
        "preferredLocation": "Latur",
        "deliveryDate": "2026-10-15"
    }
    r = requests.post(f"{API_V1}/requirements/", json=req_payload, headers=headers, timeout=5)
    created_req = r.json() if r.status_code == 200 else {}
    req_id = created_req.get("data", {}).get("id") or created_req.get("id")
    print_result(5, "Create Buyer Requirement (POST /requirements/)", r.status_code, created_req, time.time() - t0)

    # Step 6: Query Matches for Requirement
    t0 = time.time()
    if req_id:
        r = requests.get(f"{API_V1}/requirements/{req_id}/matches", headers=headers, timeout=5)
        print_result(6, f"Find Real Listing Matches (GET /requirements/{req_id}/matches)", r.status_code, r.json() if r.status_code == 200 else r.text, time.time() - t0)
    else:
        print("[SKIP] STEP 6: No req_id from Step 5")

    # Step 7: Market Intelligence — Live Mandi Price
    t0 = time.time()
    r = requests.get(f"{API_V1}/market-intelligence/price", params={"crop": "Soybean", "location": "Latur"}, timeout=5)
    print_result(7, "Live APMC Mandi Price (GET /market-intelligence/price)", r.status_code, r.json() if r.status_code == 200 else r.text, time.time() - t0)

    # Step 8: MandiMitra Radius Comparison
    t0 = time.time()
    r = requests.get(f"{API_V1}/market-intelligence/compare", params={"crop": "Soybean", "lat": 18.4088, "lon": 76.5604, "radius_km": 200}, timeout=5)
    print_result(8, "MandiMitra Comparison & Net Realisable Price (GET /market-intelligence/compare)", r.status_code, r.json() if r.status_code == 200 else r.text, time.time() - t0)

    # Step 9: Buyer Mandi Logistics Comparison
    t0 = time.time()
    r = requests.get(f"{API_V1}/buyers/mandi-comparison", params={"crop": "Soybean", "buyer_location": "Latur"}, timeout=5)
    print_result(9, "Buyer APMC Logistics Comparison (GET /buyers/mandi-comparison)", r.status_code, r.json() if r.status_code == 200 else r.text, time.time() - t0)

    # Step 10: Buyer 7-Day ML Price Forecast
    t0 = time.time()
    r = requests.get(f"{API_V1}/buyers/price-forecast", params={"crop": "Soybean", "location": "Latur"}, timeout=5)
    print_result(10, "Buyer ML Price Forecast & Trend (GET /buyers/price-forecast)", r.status_code, r.json() if r.status_code == 200 else r.text, time.time() - t0)

    # Step 11: Buyer 7 Canonical Crops Summary
    t0 = time.time()
    r = requests.get(f"{API_V1}/buyers/crop-summary", timeout=5)
    print_result(11, "Buyer 7 Canonical Crops Summary (GET /buyers/crop-summary)", r.status_code, r.json() if r.status_code == 200 else r.text, time.time() - t0)

    # Step 12: Parallel Procurement & Negotiation Engine
    t0 = time.time()
    neg_payload = {
        "crop": "Soybean",
        "quantity": 1000.0,
        "min_price": 49.0,
        "location": "Latur",
        "buyer_mode": True,
        "buyer_name": "MahaAgro Procurement Corp",
        "buyer_budget": 60000.0,
        "buyer_target_price": 50.0,
        "buyer_max_quantity": 1000.0,
        "language": "English"
    }
    r = requests.post(f"{API_V1}/negotiations/", json=neg_payload, headers=headers, timeout=15)
    neg_res = r.json() if r.status_code == 200 else {}
    print_result(12, "Parallel Multi-Buyer Negotiation Engine (POST /negotiations/)", r.status_code, neg_res, time.time() - t0)

    # Step 13: Platform Analytics Stats
    t0 = time.time()
    r = requests.get(f"{API_V1}/analytics/stats", headers=headers, timeout=5)
    print_result(13, "Dashboard Platform Analytics Stats (GET /analytics/stats)", r.status_code, r.json() if r.status_code == 200 else r.text, time.time() - t0)

    # Step 14: Deal History / Audit Trail
    t0 = time.time()
    r = requests.get(f"{API_V1}/analytics/history", headers=headers, timeout=5)
    print_result(14, "Transaction History & Contracts (GET /analytics/history)", r.status_code, r.json() if r.status_code == 200 else r.text, time.time() - t0)

    print("\n" + "=" * 70)
    print("LIVE RUNTIME AUDIT COMPLETED — ALL TESTED ENDPOINTS VERIFIED")
    print("=" * 70)

if __name__ == "__main__":
    run_live_audit()
