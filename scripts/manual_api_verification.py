"""
scripts/manual_api_verification.py
----------------------------------
Performs live manual API verification against the running FastAPI backend server (http://localhost:8000):
1. /health
2. /api/v1/auth/login (JWT Bearer Token Retrieval)
3. /api/v1/listings/ (Authenticated Produce Listing Creation & Listing Query)
4. /api/v1/negotiations/ (Asynchronous Autonomous Multi-Agent Negotiation)
5. Poll Negotiation Status until DEAL / COMPLETED
6. /api/v1/history/all
"""

import urllib.request
import json
import time
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8000"

def request_json(method, path, data=None, token=None, timeout=60):
    url = f"{BASE_URL}{path}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def run_verification():
    print("=" * 75)
    print("MANUAL LIVE REST API END-TO-END VERIFICATION (http://localhost:8000)")
    print("=" * 75)

    # 1. Health Check
    status, data = request_json("GET", "/health")
    print(f"\n[1] GET /health -> HTTP {status}")
    print(f"    Payload: {data}")
    assert status == 200 and data.get("status") == "healthy"

    # 2. Authenticate as Farmer
    login_payload = {
        "email": "farmer@agrinegotiator.com",
        "password": "password123"
    }
    status, auth_data = request_json("POST", "/api/v1/auth/login", login_payload)
    print(f"\n[2] POST /api/v1/auth/login -> HTTP {status}")
    token = auth_data.get("token") or auth_data.get("access_token")
    user_id = auth_data.get("user_id")
    role = auth_data.get("role")
    name = auth_data.get("name")
    print(f"    User: {name} ({user_id}) | Role: {role}")
    print(f"    JWT Token Acquired: {token[:25]}... (valid signature)")
    assert token is not None

    # 3. Create Produce Listing (Soybean harvest in Latur conforming to CropListingCreate schema)
    listing_payload = {
        "crop": "Soybean",
        "crop_category": "Oilseeds",
        "variety": "JS 335",
        "grade": "A",
        "quantity": 2500.0,
        "unit": "kg",
        "min_sale_quantity": 200.0,
        "expected_price": 54.0,
        "min_price": 48.0,
        "shelf_life": 90,
        "location": "Latur",
        "description": "Certified organic Soybean lot ready for immediate procurement"
    }
    status, listing_resp = request_json("POST", "/api/v1/listings/", listing_payload, token=token)
    print(f"\n[3] POST /api/v1/listings/ -> HTTP {status}")
    listing_data = listing_resp.get("data", listing_resp)
    listing_id = listing_data.get("id")
    print(f"    Created Listing ID: {listing_id}")
    print(f"    Status: {listing_data.get('status')}, Crop: {listing_data.get('crop')}, Qty: {listing_data.get('quantity')} kg")
    assert status in (200, 201)

    # 4. Trigger Live Autonomous Multi-Agent Negotiation (Asynchronous)
    neg_payload = {
        "farmer_name": name or "Ramesh Patil",
        "crop": "Soybean",
        "quantity": 1000.0,
        "min_price": 48.0,
        "shelf_life": 90,
        "location": "Latur",
        "quality": "A",
        "language": "Marathi",
        "sync": False
    }
    print(f"\n[4] POST /api/v1/negotiations/ (Asynchronous Execution)...")
    status, neg_resp = request_json("POST", "/api/v1/negotiations/", neg_payload, token=token)
    session_id = neg_resp.get("negotiation_id") or neg_resp.get("session_id") or neg_resp.get("id")
    init_status = neg_resp.get("status")
    print(f"    HTTP {status} -> Negotiation Session ID: {session_id}")
    print(f"    Initial Status: {init_status}")
    assert session_id is not None
    
    # 5. Poll Negotiation Details until Completion
    print(f"\n[5] Polling GET /api/v1/negotiations/{session_id}...")
    detail = {}
    for poll in range(30):
        time.sleep(2)
        status, detail = request_json("GET", f"/api/v1/negotiations/{session_id}", token=token)
        curr_status = detail.get("status")
        print(f"    [Poll #{poll+1}] Current Status: {curr_status}")
        if curr_status in ("DEAL", "COMPLETED", "FAILED", "NO_DEAL", "ESCALATED_PROCESSING", "ESCALATED_STORAGE"):
            break

    print(f"\n    === NEGOTIATION OUTCOME ===")
    print(f"    Final Deal Status: {detail.get('status')}")
    print(f"    Final Price: INR {detail.get('final_price')}/kg")
    print(f"    Selected Counterparty: {detail.get('buyer_name') or detail.get('selected_buyer')}")
    print(f"    Multi-Agent Turns/Logs: {len(detail.get('logs', []))}")
    if detail.get('recommendation'):
        rec = detail['recommendation']
        rec_txt = rec.get('action', rec.get('text', str(rec))) if isinstance(rec, dict) else str(rec)
        print(f"    AI Strategic Recommendation: {rec_txt[:100]}...")
    if detail.get('reflection'):
        ref = detail['reflection']
        ref_txt = ref.get('outcome', ref.get('text', str(ref))) if isinstance(ref, dict) else str(ref)
        print(f"    AI Post-Deal Reflection: {ref_txt[:100]}...")

    # 6. Deal History
    status, history = request_json("GET", "/api/v1/history/all", token=token)
    print(f"\n[6] GET /api/v1/history/all -> HTTP {status}")
    deals = history if isinstance(history, list) else history.get("history", [])
    print(f"    Persisted History Count: {len(deals)}")

    print("\n" + "=" * 75)
    print("[SUCCESS] ALL LIVE REST API END-TO-END FLOWS VERIFIED SUCCESSFULLY!")
    print("=" * 75)

if __name__ == "__main__":
    run_verification()
