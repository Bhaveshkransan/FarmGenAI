import os
import sys
import json
import time
import requests

BASE_URL = "http://localhost:8000"

def run_bulk_verification():
    print(f"Connecting to {BASE_URL} for comprehensive bulk verification...")
    
    # 1. Fetch OpenAPI schema to discover all routes
    try:
        openapi_res = requests.get(f"{BASE_URL}/openapi.json", timeout=10)
        openapi = openapi_res.json()
        paths = openapi.get("paths", {})
        print(f"Discovered {len(paths)} registered route paths in OpenAPI specification.")
    except Exception as e:
        print(f"Error fetching OpenAPI schema: {e}")
        return

    # 2. Provision Auth Tokens
    print("\n--- Provisioning Test Auth Tokens ---")
    users = {}
    
    # Farmer
    f_res = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
        "name": "Bulk Farmer Test",
        "email": "farmer_bulk_verify@agri.com",
        "password": "Password123!",
        "role": "farmer",
        "location": "Nashik"
    }, timeout=10).json()
    f_token = f_res.get("token")
    f_id = f_res.get("user_id")
    users["farmer"] = {"token": f_token, "id": f_id, "headers": {"Authorization": f"Bearer {f_token}"}}

    # Buyer
    b_res = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
        "name": "Bulk Buyer Test",
        "email": "buyer_bulk_verify@agri.com",
        "password": "Password123!",
        "role": "buyer",
        "location": "Pune"
    }, timeout=10).json()
    b_token = b_res.get("token")
    b_id = b_res.get("user_id")
    users["buyer"] = {"token": b_token, "id": b_id, "headers": {"Authorization": f"Bearer {b_token}"}}

    # Admin
    a_res = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
        "name": "Bulk Admin Test",
        "email": "admin_bulk_verify@agri.com",
        "password": "Password123!",
        "role": "admin",
        "location": "Mumbai"
    }, timeout=10).json()
    a_token = a_res.get("token")
    a_id = a_res.get("user_id")
    users["admin"] = {"token": a_token, "id": a_id, "headers": {"Authorization": f"Bearer {a_token}"}}

    print(f"Farmer ID: {f_id}, Buyer ID: {b_id}, Admin ID: {a_id}")

    # 3. Create prerequisite entities for dependent routes
    print("\n--- Setting Up Prerequisite Entities ---")
    entities = {}

    # Produce / Listing
    listing_res = requests.post(f"{BASE_URL}/api/v1/listings/", json={
        "crop": "Tomato",
        "quantity": 500.0,
        "min_price": 20.0,
        "location": "Nashik",
        "spoilage_days": 5,
        "description": "Bulk Test Listing"
    }, headers=users["farmer"]["headers"], timeout=10).json()
    entities["listing_id"] = listing_res.get("listing_id") or listing_res.get("data", {}).get("listing_id")
    print(f"Created Listing ID: {entities['listing_id']}")

    # Buyer Requirement
    req_res = requests.post(f"{BASE_URL}/api/v1/requirements/", json={
        "crop": "Tomato",
        "quantity": 500.0,
        "target_price": 24.0,
        "max_price": 26.0,
        "budget": 13000.0,
        "location": "Pune",
        "delivery_days": 5
    }, headers=users["buyer"]["headers"], timeout=10).json()
    entities["requirement_id"] = req_res.get("requirement_id") or req_res.get("data", {}).get("requirement_id")
    print(f"Created Requirement ID: {entities['requirement_id']}")

    # Role Offer
    offer_res = requests.post(f"{BASE_URL}/api/v1/role-offers/", json={
        "role": "farmer",
        "actor_name": "Bulk Farmer Test",
        "crop": "Tomato",
        "quantity": 500.0,
        "min_price": 20.0,
        "max_price": 25.0,
        "location": "Nashik"
    }, headers=users["farmer"]["headers"], timeout=10).json()
    entities["offer_id"] = offer_res.get("id")
    print(f"Created Role Offer ID: {entities['offer_id']}")

    # Transport Booking
    book_res = requests.post(f"{BASE_URL}/api/v1/transport/book", json={
        "negotiation_id": "neg_bulk_prereq",
        "crop": "Tomato",
        "quantity": 500.0,
        "origin_location": "Nashik",
        "destination_location": "Pune",
        "distance_km": 210.0,
        "shelf_life": 5
    }, headers=users["farmer"]["headers"], timeout=10).json()
    entities["booking_id"] = book_res.get("data", {}).get("booking_id")
    print(f"Created Transport Booking ID: {entities['booking_id']}")

    # Processor Order
    proc_res = requests.post(f"{BASE_URL}/api/v1/processors/order", json={
        "processor_id": "proc_agro_industrial_01",
        "crop": "Tomato",
        "quantity": 500.0,
        "notes": "Bulk test conversion"
    }, headers=users["farmer"]["headers"], timeout=10).json()
    entities["processor_order_id"] = proc_res.get("data", {}).get("order_id")
    print(f"Created Processor Order ID: {entities['processor_order_id']}")

    # Negotiation ID
    neg_res = requests.post(f"{BASE_URL}/api/v1/negotiation/start-negotiation", json={
        "farmer_name": "Bulk Farmer Test",
        "crop": "Tomato",
        "quantity": 500.0,
        "min_price": 20.0,
        "shelf_life": 5,
        "location": "Nashik",
        "max_rounds": 2
    }, timeout=120).json()
    entities["negotiation_id"] = neg_res.get("negotiation_id")
    print(f"Created Negotiation ID: {entities['negotiation_id']}")

    # 4. Construct Full Endpoint Test Cases
    test_cases = [
        # Root & Health
        {"num": 1, "method": "GET", "path": "/", "auth": "NO", "payload": None, "params": None},
        {"num": 2, "method": "GET", "path": "/health", "auth": "NO", "payload": None, "params": None},
        {"num": 3, "method": "GET", "path": "/metrics", "auth": "NO", "payload": None, "params": None},
        {"num": 4, "method": "GET", "path": "/docs", "auth": "NO", "payload": None, "params": None},
        {"num": 5, "method": "GET", "path": "/openapi.json", "auth": "NO", "payload": None, "params": None},
        
        # Auth Routes
        {"num": 6, "method": "POST", "path": "/api/v1/auth/signup", "auth": "NO", "payload": {"name": "Test User", "email": "test_unique_123@agri.com", "password": "Pass123!", "role": "farmer", "location": "Pune"}},
        {"num": 7, "method": "POST", "path": "/api/v1/auth/register", "auth": "NO", "payload": {"name": "Test Reg User", "email": "test_unique_reg@agri.com", "password": "Pass123!", "role": "buyer", "location": "Mumbai"}},
        {"num": 8, "method": "POST", "path": "/api/v1/auth/login", "auth": "NO", "payload": {"email": "farmer_bulk_verify@agri.com", "password": "Password123!"}},
        {"num": 9, "method": "GET", "path": "/api/v1/auth/me", "auth": "YES_FARMER", "payload": None},
        {"num": 10, "method": "GET", "path": "/api/v1/auth/me", "auth": "UNAUTHENTICATED", "payload": None},
        {"num": 11, "method": "POST", "path": "/api/v1/auth/preferences", "auth": "YES_FARMER", "payload": {"language": "en", "notifications_enabled": True}},
        {"num": 12, "method": "POST", "path": "/api/v1/auth/location", "auth": "YES_FARMER", "params": {"location": "Nashik"}},
        {"num": 13, "method": "POST", "path": "/api/v1/auth/verify", "auth": "YES_FARMER", "payload": {"user_id": f_id, "docs": ["kisan_credit_card.pdf"]}},
        
        # Farmers & Buyers
        {"num": 14, "method": "GET", "path": "/api/v1/farmers/", "auth": "YES_FARMER", "payload": None},
        {"num": 15, "method": "GET", "path": "/api/v1/farmers/produce", "auth": "YES_FARMER", "payload": None},
        {"num": 16, "method": "GET", "path": "/api/v1/buyers/", "auth": "YES_FARMER", "payload": None},
        {"num": 17, "method": "GET", "path": "/api/v1/buyers/offers", "auth": "YES_FARMER", "payload": None},
        {"num": 18, "method": "POST", "path": "/api/v1/buyers/offers", "auth": "YES_BUYER", "payload": {"crop": "Tomato", "quantity": 500, "max_price": 25, "min_price": 20, "location": "Pune", "buyer_name": "Bulk Buyer Test"}},
        
        # Crop Listings
        {"num": 19, "method": "POST", "path": "/api/v1/listings/", "auth": "YES_FARMER", "payload": {"crop": "Onion", "quantity": 1000.0, "min_price": 18.0, "location": "Nashik", "spoilage_days": 10, "description": "Fresh Red Onion"}},
        {"num": 20, "method": "GET", "path": "/api/v1/listings/", "auth": "YES_FARMER", "payload": None},
        {"num": 21, "method": "GET", "path": "/api/v1/listings/me", "auth": "YES_FARMER", "payload": None},
        {"num": 22, "method": "GET", "path": f"/api/v1/listings/{entities['listing_id']}", "auth": "YES_FARMER", "payload": None},
        {"num": 23, "method": "PATCH", "path": f"/api/v1/listings/{entities['listing_id']}", "auth": "YES_FARMER", "payload": {"min_price": 21.0, "description": "Updated lot price"}},
        {"num": 24, "method": "DELETE", "path": f"/api/v1/listings/{entities['listing_id']}", "auth": "YES_FARMER", "payload": None},
        
        # Buyer Requirements
        {"num": 25, "method": "POST", "path": "/api/v1/requirements/", "auth": "YES_BUYER", "payload": {"crop": "Potato", "quantity": 2000.0, "target_price": 15.0, "max_price": 18.0, "budget": 36000.0, "location": "Pune", "delivery_days": 7}},
        {"num": 26, "method": "GET", "path": "/api/v1/requirements/", "auth": "YES_BUYER", "payload": None},
        {"num": 27, "method": "GET", "path": "/api/v1/requirements/me", "auth": "YES_BUYER", "payload": None},
        {"num": 28, "method": "GET", "path": f"/api/v1/requirements/{entities['requirement_id']}", "auth": "YES_BUYER", "payload": None},
        {"num": 29, "method": "PATCH", "path": f"/api/v1/requirements/{entities['requirement_id']}", "auth": "YES_BUYER", "payload": {"target_price": 16.0}},
        {"num": 30, "method": "DELETE", "path": f"/api/v1/requirements/{entities['requirement_id']}", "auth": "YES_BUYER", "payload": None},
        
        # Role Offers
        {"num": 31, "method": "POST", "path": "/api/v1/role-offers/", "auth": "YES_FARMER", "payload": {"role": "farmer", "actor_name": "Bulk Farmer", "crop": "Wheat", "quantity": 1000.0, "min_price": 22.0, "max_price": 26.0, "location": "Indore"}},
        {"num": 32, "method": "GET", "path": "/api/v1/role-offers/", "auth": "YES_FARMER", "payload": None},
        {"num": 33, "method": "GET", "path": "/api/v1/role-offers/?role=farmer", "auth": "YES_FARMER", "payload": None},
        
        # Negotiation Endpoints
        {"num": 34, "method": "POST", "path": "/api/v1/negotiation/start-negotiation", "auth": "NO", "payload": {"farmer_name": "Bulk Farmer Test", "crop": "Tomato", "quantity": 500.0, "min_price": 20.0, "shelf_life": 5, "location": "Nashik", "max_rounds": 2}},
        {"num": 35, "method": "GET", "path": "/api/v1/negotiation/agents", "auth": "NO", "payload": None},
        {"num": 36, "method": "GET", "path": f"/api/v1/negotiation/negotiation-status/{entities['negotiation_id']}", "auth": "NO", "payload": None},
        {"num": 37, "method": "POST", "path": "/api/v1/negotiations/start-negotiation", "auth": "NO", "payload": {"farmer_name": "Plural Router Test", "crop": "Tomato", "quantity": 500.0, "min_price": 20.0, "shelf_life": 5, "location": "Nashik", "max_rounds": 2}},
        
        # History Endpoints
        {"num": 38, "method": "GET", "path": f"/api/v1/history/{f_id}", "auth": "YES_FARMER", "payload": None},
        {"num": 39, "method": "GET", "path": "/api/v1/history/negotiations", "auth": "YES_ADMIN", "payload": None},
        {"num": 40, "method": "GET", "path": "/api/v1/history/negotiations", "auth": "YES_FARMER", "payload": None},
        
        # Dashboards
        {"num": 41, "method": "GET", "path": "/api/v1/dashboards/platform", "auth": "YES_ADMIN", "payload": None},
        {"num": 42, "method": "GET", "path": "/api/v1/dashboards/farmer", "auth": "YES_FARMER", "payload": None},
        {"num": 43, "method": "GET", "path": "/api/v1/dashboards/buyer", "auth": "YES_BUYER", "payload": None},
        {"num": 44, "method": "GET", "path": f"/api/v1/dashboards/user/{f_id}", "auth": "YES_FARMER", "payload": None},
        
        # Analytics & Intelligence
        {"num": 45, "method": "GET", "path": "/api/v1/analytics/stats", "auth": "YES_FARMER", "payload": None},
        {"num": 46, "method": "GET", "path": "/api/v1/analytics/history", "auth": "YES_FARMER", "payload": None},
        {"num": 47, "method": "GET", "path": "/api/v1/analytics/leaderboard", "auth": "YES_FARMER", "payload": None},
        
        # Recommendations
        {"num": 48, "method": "POST", "path": "/api/v1/recommendations/generate", "auth": "YES_FARMER", "payload": {"crop": "Tomato", "quantity": 500.0, "min_price": 20.0, "location": "Nashik", "spoilage_days": 5, "market_price": 24.0}},
        {"num": 49, "method": "GET", "path": f"/api/v1/recommendations/history/{f_id}", "auth": "YES_FARMER", "payload": None},
        
        # Trust Scores
        {"num": 50, "method": "GET", "path": f"/api/v1/trust/score/{f_id}", "auth": "YES_FARMER", "payload": None},
        {"num": 51, "method": "GET", "path": "/api/v1/trust/my-score", "auth": "YES_FARMER", "payload": None},
        {"num": 52, "method": "POST", "path": "/api/v1/trust/record-outcome", "auth": "YES_ADMIN", "payload": {"user_id": f_id, "deal_success": True, "delivery_ontime": True, "quality_met": True}},
        
        # Notifications
        {"num": 53, "method": "GET", "path": "/api/v1/notifications/", "auth": "YES_FARMER", "payload": None},
        {"num": 54, "method": "POST", "path": "/api/v1/notifications/send", "auth": "YES_ADMIN", "payload": {"user_id": f_id, "title": "Bulk Test Alert", "message": "Bulk verification test", "notif_type": "INFO"}},
        {"num": 55, "method": "POST", "path": "/api/v1/notifications/mark-all-read", "auth": "YES_FARMER", "payload": None},
        
        # Profiles
        {"num": 56, "method": "GET", "path": "/api/v1/profiles/me", "auth": "YES_FARMER", "payload": None},
        {"num": 57, "method": "PATCH", "path": "/api/v1/profiles/me", "auth": "YES_FARMER", "payload": {"location": "Nashik West", "language": "Marathi"}},
        {"num": 58, "method": "GET", "path": f"/api/v1/profiles/{f_id}", "auth": "YES_FARMER", "payload": None},
        
        # Matching Engine
        {"num": 59, "method": "POST", "path": "/api/v1/matching/listing-to-buyers", "auth": "YES_FARMER", "payload": {"crop": "Tomato", "quantity": 500.0, "min_price": 20.0, "location": "Nashik", "spoilage_days": 5, "quality": "A"}},
        {"num": 60, "method": "POST", "path": "/api/v1/matching/requirement-to-listings", "auth": "YES_BUYER", "payload": {"crop": "Tomato", "quantity": 500.0, "target_price": 22.0, "budget": 12000.0, "location": "Pune"}},
        {"num": 61, "method": "GET", "path": f"/api/v1/matching/auto/{entities['listing_id']}", "auth": "YES_FARMER", "payload": None},
        
        # Workflow Planning
        {"num": 62, "method": "POST", "path": "/api/v1/workflows/plan", "auth": "YES_FARMER", "payload": {"crop": "Tomato", "quantity": 500.0, "min_price": 20.0, "location": "Nashik", "spoilage_days": 5, "market_price": 24.0}},
        {"num": 63, "method": "GET", "path": f"/api/v1/workflows/plan/{entities['listing_id']}", "auth": "YES_FARMER", "payload": None},
        
        # Transport & Logistics
        {"num": 64, "method": "GET", "path": "/api/v1/transport/fleet", "auth": "YES_FARMER", "payload": None},
        {"num": 65, "method": "POST", "path": "/api/v1/transport/book", "auth": "YES_FARMER", "payload": {"negotiation_id": "neg_bulk_01", "crop": "Tomato", "quantity": 500.0, "origin_location": "Nashik", "destination_location": "Pune", "distance_km": 210.0, "shelf_life": 5}},
        {"num": 66, "method": "GET", "path": "/api/v1/transport/bookings", "auth": "YES_FARMER", "payload": None},
        {"num": 67, "method": "GET", "path": f"/api/v1/transport/track/{entities['booking_id']}", "auth": "YES_FARMER", "payload": None},
        {"num": 68, "method": "PATCH", "path": f"/api/v1/transport/status/{entities['booking_id']}", "auth": "YES_FARMER", "payload": {"status": "IN_TRANSIT"}},
        {"num": 69, "method": "GET", "path": "/api/v1/transport/estimate", "auth": "YES_FARMER", "params": {"distance_km": 180, "quantity": 500, "shelf_life": 5}},
        
        # Processors & Industrial Escalation
        {"num": 70, "method": "GET", "path": "/api/v1/processors/", "auth": "YES_FARMER", "payload": None},
        {"num": 71, "method": "GET", "path": "/api/v1/processors/?crop=Tomato", "auth": "YES_FARMER", "payload": None},
        {"num": 72, "method": "POST", "path": "/api/v1/processors/order", "auth": "YES_FARMER", "payload": {"processor_id": "proc_agro_industrial_01", "crop": "Tomato", "quantity": 500.0, "notes": "Puree batch"}},
        {"num": 73, "method": "GET", "path": f"/api/v1/processors/order/{entities['processor_order_id']}", "auth": "YES_FARMER", "payload": None},
        {"num": 74, "method": "GET", "path": "/api/v1/processors/orders", "auth": "YES_FARMER", "payload": None},
        
        # Warehouses
        {"num": 75, "method": "GET", "path": "/api/v1/warehouse/list", "auth": "YES_FARMER", "payload": None},
        {"num": 76, "method": "POST", "path": "/api/v1/warehouse/book", "auth": "YES_FARMER", "payload": {"warehouse_id": "wh_1", "crop": "Tomato", "quantity": 500.0, "duration_days": 7}},
        
        # External Integrations
        {"num": 77, "method": "GET", "path": "/api/v1/integrations/weather", "auth": "YES_FARMER", "params": {"location": "Nashik"}},
        {"num": 78, "method": "GET", "path": "/api/v1/integrations/weather/spoilage-risk", "auth": "YES_FARMER", "params": {"crop": "Tomato", "location": "Nashik"}},
        {"num": 79, "method": "GET", "path": "/api/v1/integrations/maps/route", "auth": "YES_FARMER", "params": {"origin": "Nashik", "destination": "Pune"}},
        {"num": 80, "method": "GET", "path": "/api/v1/integrations/mandi/prices", "auth": "YES_FARMER", "params": {"crop": "Tomato", "location": "Nashik"}},
        
        # Admin Endpoints
        {"num": 81, "method": "GET", "path": "/api/v1/admin/users", "auth": "YES_ADMIN", "payload": None},
        {"num": 82, "method": "GET", "path": "/api/v1/admin/users", "auth": "YES_FARMER", "payload": None}, # Expected 403
        {"num": 83, "method": "POST", "path": f"/api/v1/admin/users/{f_id}/verify", "auth": "YES_ADMIN", "payload": None},
        {"num": 84, "method": "GET", "path": "/api/v1/admin/negotiations", "auth": "YES_ADMIN", "payload": None},
        {"num": 85, "method": "GET", "path": "/api/v1/admin/audit-logs", "auth": "YES_ADMIN", "payload": None},
        {"num": 86, "method": "GET", "path": "/api/v1/admin/platform-stats", "auth": "YES_ADMIN", "payload": None},
        
        # P2P Node Network & Public Ledger
        {"num": 87, "method": "GET", "path": "/api/nodes", "auth": "NO", "payload": None},
        {"num": 88, "method": "GET", "path": "/api/ledger", "auth": "NO", "payload": None},
        {"num": 89, "method": "POST", "path": "/api/node/farmer_node_1/announce", "auth": "NO", "payload": {"crop": "Tomato", "quantity": 500.0, "min_price": 20.0}},
        {"num": 90, "method": "GET", "path": "/api/node/farmer_node_1/scenarios", "auth": "NO", "params": {"crop": "Tomato"}},
        {"num": 91, "method": "POST", "path": "/api/node/farmer_node_1/select", "auth": "NO", "payload": {"crop": "Tomato", "peer_node": "node_b_bigstore"}},
        
        # Agents & Simulation
        {"num": 92, "method": "GET", "path": "/api/v1/agents/list", "auth": "NO", "payload": None},
        {"num": 93, "method": "POST", "path": "/api/v1/agents/simulate", "auth": "NO", "payload": {"crop": "Tomato", "quantity": 500.0, "farmer_price": 20.0, "buyer_price": 25.0, "rounds": 2}},
    ]

    print(f"\n--- Executing Bulk Verification across {len(test_cases)} Concrete API Operations ---")
    results = []

    for tc in test_cases:
        method = tc["method"]
        path = tc["path"]
        url = f"{BASE_URL}{path}"
        auth_type = tc["auth"]
        payload = tc.get("payload")
        params = tc.get("params")
        
        # Select headers
        headers = {}
        if auth_type == "YES_FARMER":
            headers = users["farmer"]["headers"]
        elif auth_type == "YES_BUYER":
            headers = users["buyer"]["headers"]
        elif auth_type == "YES_ADMIN":
            headers = users["admin"]["headers"]
        elif auth_type == "UNAUTHENTICATED":
            headers = {}
        
        headers["Content-Type"] = "application/json"
        
        timeout = 120 if "negotiation" in path or "recommendations" in path or "simulate" in path else 15
        
        start_t = time.time()
        try:
            if method == "GET":
                res = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method == "POST":
                res = requests.post(url, headers=headers, json=payload, params=params, timeout=timeout)
            elif method == "PATCH":
                res = requests.patch(url, headers=headers, json=payload, params=params, timeout=timeout)
            elif method == "DELETE":
                res = requests.delete(url, headers=headers, timeout=timeout)
            
            elapsed = round((time.time() - start_t) * 1000, 1)
            status = res.status_code
            
            try:
                body = res.json()
            except Exception:
                body = res.text[:200]
                
            # Determine PASS/FAIL/EXPECTED_REJECTION
            is_expected_auth_rejection = (auth_type == "UNAUTHENTICATED" and status == 401) or (path == "/api/v1/admin/users" and auth_type == "YES_FARMER" and status == 403)
            
            if status in [200, 201] or is_expected_auth_rejection:
                test_result = "PASS"
            elif status in [400, 404, 422, 500]:
                test_result = "FAIL"
            else:
                test_result = f"STATUS_{status}"
                
            summary_note = ""
            if is_expected_auth_rejection:
                summary_note = f"Correctly rejected with HTTP {status}"
            elif isinstance(body, dict):
                keys = list(body.keys())[:4]
                summary_note = f"Keys: {keys} ({elapsed}ms)"
            elif isinstance(body, list):
                summary_note = f"List count: {len(body)} ({elapsed}ms)"
            else:
                summary_note = f"Text response ({elapsed}ms)"
                
            results.append({
                "num": tc["num"],
                "method": method,
                "endpoint": path,
                "auth": auth_type,
                "status": status,
                "result": test_result,
                "elapsed_ms": elapsed,
                "note": summary_note,
                "response_preview": str(body)[:150]
            })
            
            status_tag = f"[\033[92mPASS\033[0m]" if test_result == "PASS" else f"[\033[91m{test_result}\033[0m]"
            print(f"#{tc['num']:02d} {status_tag} {method:6s} {path:45s} -> {status} ({elapsed}ms) | {summary_note}")

        except Exception as ex:
            elapsed = round((time.time() - start_t) * 1000, 1)
            results.append({
                "num": tc["num"],
                "method": method,
                "endpoint": path,
                "auth": auth_type,
                "status": "TIMEOUT_OR_ERR",
                "result": "FAIL",
                "elapsed_ms": elapsed,
                "note": f"Exception: {str(ex)[:80]}",
                "response_preview": str(ex)
            })
            print(f"#{tc['num']:02d} [\033[91mFAIL\033[0m] {method:6s} {path:45s} -> EXCEPTION ({ex})")

    # Save to JSON
    with open("backend/scratch/bulk_verification_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved full bulk verification results to backend/scratch/bulk_verification_results.json")

if __name__ == "__main__":
    run_bulk_verification()
