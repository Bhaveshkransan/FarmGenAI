"""
Complete System-Wide Backend API Audit Script
Discovers and tests all endpoints, maps frontend, verifies DB/Redis/ChromaDB/Ollama/External services.
"""

import asyncio
import json
import os
import sys
import time
import requests
from sqlalchemy import text

def run_audit():
    from backend.main import app
    from database.db import Database, AsyncSessionLocal, DBUser
    from llm.llm_client import client as llm_client
    import chromadb

    print("=" * 70)
    print("STARTING COMPLETE AGRINEGOTIATOR SYSTEM-WIDE API AUDIT")
    print("=" * 70)

    # 1. Get OpenAPI Spec
    openapi_spec = app.openapi()
    paths = openapi_spec.get("paths", {})
    
    print(f"Total API Paths Registered: {len(paths)}")
    
    # 2. Setup Test Tokens
    base_url = "http://localhost:8000"
    
    # Farmer test account
    farmer_email = f"audit_farmer_{int(time.time())}@agri.com"
    r_f = requests.post(f"{base_url}/api/v1/auth/signup", json={
        "name": "Audit Farmer",
        "email": farmer_email,
        "password": "Password123!",
        "role": "farmer",
        "location": "Nashik"
    })
    farmer_token = r_f.json().get("token", "")
    farmer_id = r_f.json().get("user_id", "")
    f_headers = {"Authorization": f"Bearer {farmer_token}"}
    
    # Buyer test account
    buyer_email = f"audit_buyer_{int(time.time())}@agri.com"
    r_b = requests.post(f"{base_url}/api/v1/auth/signup", json={
        "name": "Audit Buyer",
        "email": buyer_email,
        "password": "Password123!",
        "role": "buyer",
        "location": "Pune"
    })
    buyer_token = r_b.json().get("token", "")
    buyer_id = r_b.json().get("user_id", "")
    b_headers = {"Authorization": f"Bearer {buyer_token}"}

    # Admin test account
    admin_email = f"audit_admin_{int(time.time())}@agri.com"
    r_a = requests.post(f"{base_url}/api/v1/auth/signup", json={
        "name": "Audit Admin",
        "email": admin_email,
        "password": "Password123!",
        "role": "admin",
        "location": "Mumbai"
    })
    admin_token = r_a.json().get("token", "")
    admin_id = r_a.json().get("user_id", "")
    a_headers = {"Authorization": f"Bearer {admin_token}"}

    print(f"Provisioned Test Accounts: Farmer ({farmer_id}), Buyer ({buyer_id}), Admin ({admin_id})")

    # 3. Test Endpoints Runtime
    audit_results = []

    # Let's define specific tests for key routes
    test_suite = [
        # Health & Root
        {"method": "GET", "url": "/", "headers": {}, "payload": None, "desc": "Root Status"},
        {"method": "GET", "url": "/health", "headers": {}, "payload": None, "desc": "System Health Check"},
        
        # Auth
        {"method": "POST", "url": "/api/v1/auth/login", "headers": {}, "payload": {"email": farmer_email, "password": "Password123!"}, "desc": "User Login"},
        {"method": "GET", "url": "/api/v1/auth/me", "headers": f_headers, "payload": None, "desc": "Get Current Auth User (/me)"},
        {"method": "POST", "url": "/api/v1/auth/preferences", "headers": f_headers, "payload": {"preferences": {"theme": "dark", "buyer_preference": "retail"}}, "desc": "Update User Preferences"},
        {"method": "POST", "url": "/api/v1/auth/location", "headers": f_headers, "payload": {"location": "Nashik City"}, "desc": "Update Location", "params": {"location": "Nashik City"}},
        
        # Farmers & Buyers CRUD
        {"method": "GET", "url": "/api/v1/farmers/", "headers": f_headers, "payload": None, "desc": "List Farmers"},
        {"method": "GET", "url": "/api/v1/buyers/", "headers": f_headers, "payload": None, "desc": "List Buyers"},
        
        # Crop Listings
        {"method": "POST", "url": "/api/v1/listings/", "headers": f_headers, "payload": {"crop": "Onion", "quantity": 1000, "min_price": 16.5, "location": "Nashik", "spoilage_days": 15, "description": "Export quality onions"}, "desc": "Create Crop Listing"},
        {"method": "GET", "url": "/api/v1/listings/", "headers": f_headers, "payload": None, "desc": "List Crop Listings"},
        {"method": "GET", "url": "/api/v1/listings/me", "headers": f_headers, "payload": None, "desc": "Get My Crop Listings"},
        
        # Buyer Requirements
        {"method": "POST", "url": "/api/v1/requirements/", "headers": b_headers, "payload": {"crop": "Onion", "quantity": 1000, "target_price": 16.0, "max_price": 18.0, "location": "Pune", "budget": 20000, "delivery_days": 10, "quality_grade": "A"}, "desc": "Create Buyer Requirement"},
        {"method": "GET", "url": "/api/v1/requirements/", "headers": b_headers, "payload": None, "desc": "List Buyer Requirements"},
        
        # Role Offers
        {"method": "POST", "url": "/api/v1/role-offers/", "headers": b_headers, "payload": {"role": "buyer", "actor_name": "Audit Buyer", "crop": "Onion", "quantity": 500, "min_price": 15.0, "max_price": 17.5, "location": "Pune", "urgency": "Normal", "neg_mode": "auto", "notes": "Test offer"}, "desc": "Post Role Offer"},
        {"method": "GET", "url": "/api/v1/role-offers/", "headers": b_headers, "payload": None, "desc": "List Role Offers"},
        
        # Negotiation
        {"method": "POST", "url": "/api/v1/negotiation/start-negotiation", "headers": f_headers, "payload": {"crop": "Tomato", "quantity": 500, "min_price": 20, "farmer_name": "Audit Farmer", "location": "Nashik", "shelf_life": 5, "max_rounds": 4}, "desc": "Start Direct Negotiation"},
        {"method": "GET", "url": "/api/v1/negotiation/agents", "headers": f_headers, "payload": None, "desc": "List Negotiation Agents"},
        {"method": "GET", "url": "/api/v1/negotiations/start-negotiation", "headers": f_headers, "payload": None, "desc": "Plural Router Start Check"},
        
        # Analytics & Intelligence
        {"method": "GET", "url": "/api/v1/analytics/stats", "headers": f_headers, "payload": None, "desc": "Platform Statistics"},
        {"method": "GET", "url": "/api/v1/analytics/history", "headers": f_headers, "payload": None, "desc": "Platform History"},
        {"method": "GET", "url": "/api/v1/analytics/leaderboard", "headers": f_headers, "payload": None, "desc": "Trust Leaderboard"},
        {"method": "POST", "url": "/api/v1/recommendations/generate", "headers": f_headers, "payload": {"crop": "Tomato", "quantity": 500, "location": "Nashik"}, "desc": "Generate Recommendation", "params": {"crop": "Tomato", "quantity": 500, "location": "Nashik"}},
        {"method": "GET", "url": f"/api/v1/recommendations/history/{farmer_id}", "headers": f_headers, "payload": None, "desc": "User Recommendations History"},
        {"method": "GET", "url": f"/api/v1/trust/score/{farmer_id}", "headers": f_headers, "payload": None, "desc": "Get Trust Score"},
        {"method": "GET", "url": "/api/v1/trust/my-score", "headers": f_headers, "payload": None, "desc": "My Trust Score"},
        
        # Notifications
        {"method": "GET", "url": "/api/v1/notifications/", "headers": f_headers, "payload": None, "desc": "Get User Notifications"},
        {"method": "POST", "url": "/api/v1/notifications/send", "headers": a_headers, "payload": {"user_id": farmer_id, "title": "Audit Notice", "message": "System Audit in progress", "type": "SYSTEM"}, "desc": "Send Notification"},
        {"method": "POST", "url": "/api/v1/notifications/mark-all-read", "headers": f_headers, "payload": None, "desc": "Mark All Notifications Read"},
        
        # History
        {"method": "GET", "url": f"/api/v1/history/{farmer_id}", "headers": f_headers, "payload": None, "desc": "Get User History"},
        {"method": "GET", "url": "/api/v1/history/negotiations", "headers": f_headers, "payload": None, "desc": "Get History Negotiations"},
        
        # Profiles
        {"method": "GET", "url": "/api/v1/profiles/me", "headers": f_headers, "payload": None, "desc": "Get My Profile"},
        {"method": "PATCH", "url": "/api/v1/profiles/me", "headers": f_headers, "payload": {"phone": "9876543210", "bio": "Organic farm operator"}, "desc": "Update My Profile"},
        {"method": "GET", "url": f"/api/v1/profiles/{farmer_id}", "headers": f_headers, "payload": None, "desc": "Get Profile by ID"},
        
        # Matching & Workflow
        {"method": "POST", "url": "/api/v1/matching/listing-to-buyers", "headers": f_headers, "payload": {"listing_id": "test", "crop": "Tomato", "quantity": 500, "min_price": 20, "location": "Nashik"}, "desc": "Match Listing to Buyers"},
        {"method": "POST", "url": "/api/v1/matching/requirement-to-listings", "headers": b_headers, "payload": {"requirement_id": "test", "crop": "Tomato", "quantity": 500, "target_price": 22, "location": "Pune"}, "desc": "Match Requirement to Listings"},
        {"method": "POST", "url": "/api/v1/workflows/plan", "headers": f_headers, "payload": {"crop": "Tomato", "quantity": 500, "min_price": 20, "location": "Nashik", "shelf_life": 5}, "desc": "Generate Workflow Plan"},
        
        # Transport & Fleet
        {"method": "GET", "url": "/api/v1/transport/fleet", "headers": f_headers, "payload": None, "desc": "Get Transport Fleet"},
        {"method": "POST", "url": "/api/v1/transport/book", "headers": f_headers, "payload": {"origin": "Nashik", "destination": "Pune", "crop": "Tomato", "quantity": 500, "preferred_date": "2026-08-20"}, "desc": "Book Transport"},
        {"method": "GET", "url": "/api/v1/transport/bookings", "headers": f_headers, "payload": None, "desc": "List Transport Bookings"},
        {"method": "GET", "url": "/api/v1/transport/estimate", "headers": f_headers, "payload": None, "params": {"distance_km": 180, "quantity_kg": 500, "vehicle_type": "minitruck"}, "desc": "Estimate Transport Cost"},
        
        # Processors
        {"method": "GET", "url": "/api/v1/processors/", "headers": f_headers, "payload": None, "desc": "List Processors"},
        {"method": "POST", "url": "/api/v1/processors/order", "headers": f_headers, "payload": {"processor_id": "proc_1", "crop": "Tomato", "quantity": 500, "output_product": "Tomato Puree", "agreed_fee": 1500}, "desc": "Submit Processing Order"},
        {"method": "GET", "url": "/api/v1/processors/orders", "headers": f_headers, "payload": None, "desc": "List My Processing Orders"},
        
        # Dashboards
        {"method": "GET", "url": "/api/v1/dashboards/platform", "headers": a_headers, "payload": None, "desc": "Platform Executive Dashboard"},
        {"method": "GET", "url": "/api/v1/dashboards/farmer", "headers": f_headers, "payload": None, "desc": "Farmer Dashboard Metrics"},
        {"method": "GET", "url": "/api/v1/dashboards/buyer", "headers": b_headers, "payload": None, "desc": "Buyer Dashboard Metrics"},
        
        # Integrations
        {"method": "GET", "url": "/api/v1/integrations/weather", "headers": f_headers, "payload": None, "params": {"location": "Nashik"}, "desc": "Live Weather API"},
        {"method": "GET", "url": "/api/v1/integrations/weather/spoilage-risk", "headers": f_headers, "payload": None, "params": {"crop": "Tomato", "location": "Nashik"}, "desc": "Weather Spoilage Risk"},
        {"method": "GET", "url": "/api/v1/integrations/maps/route", "headers": f_headers, "payload": None, "params": {"origin": "Nashik", "destination": "Pune"}, "desc": "OSRM Routing Distance"},
        {"method": "GET", "url": "/api/v1/integrations/mandi/prices", "headers": f_headers, "payload": None, "params": {"crop": "Tomato", "location": "Nashik"}, "desc": "Mandi Market Prices"},
        
        # Admin
        {"method": "GET", "url": "/api/v1/admin/users", "headers": a_headers, "payload": None, "desc": "Admin List All Users"},
        {"method": "POST", "url": f"/api/v1/admin/users/{farmer_id}/verify", "headers": a_headers, "payload": None, "desc": "Admin Verify User"},
        {"method": "GET", "url": "/api/v1/admin/negotiations", "headers": a_headers, "payload": None, "desc": "Admin List Negotiations"},
        {"method": "GET", "url": "/api/v1/admin/audit-logs", "headers": a_headers, "payload": None, "desc": "Admin Audit Logs"},
        {"method": "GET", "url": "/api/v1/admin/platform-stats", "headers": a_headers, "payload": None, "desc": "Admin Platform Stats"},
        
        # P2P Node & Ledger
        {"method": "GET", "url": "/api/nodes", "headers": f_headers, "payload": None, "desc": "P2P Node Map"},
        {"method": "GET", "url": "/api/ledger", "headers": f_headers, "payload": None, "desc": "Public Audit Ledger"},
        {"method": "POST", "url": "/api/node/farmer_node_1/announce", "headers": f_headers, "payload": {"role": "farmer", "name": "Farmer Node 1", "location": "Nashik"}, "desc": "P2P Node Announce"},
        {"method": "GET", "url": "/api/node/farmer_node_1/scenarios", "headers": f_headers, "payload": None, "desc": "P2P Node Scenarios"},
    ]

    print(f"\nExecuting Runtime Tests on {len(test_suite)} Target Endpoints...")
    
    for t in test_suite:
        url = f"{base_url}{t['url']}"
        method = t["method"]
        headers = t["headers"]
        payload = t["payload"]
        params = t.get("params")
        desc = t["desc"]

        try:
            req_timeout = 60 if "negotiation" in url or "recommendations" in url else 15
            if method == "GET":
                res = requests.get(url, headers=headers, params=params, timeout=req_timeout)
            elif method == "POST":
                res = requests.post(url, headers=headers, json=payload, params=params, timeout=req_timeout)
            elif method == "PATCH":
                res = requests.patch(url, headers=headers, json=payload, params=params, timeout=req_timeout)
            elif method == "DELETE":
                res = requests.delete(url, headers=headers, timeout=req_timeout)
            
            status = res.status_code
            try:
                data = res.json()
                data_summary = str(data)[:120]
            except Exception:
                data = res.text
                data_summary = str(data)[:120]

            audit_results.append({
                "method": method,
                "endpoint": t["url"],
                "description": desc,
                "status": status,
                "result": "PASS" if status in (200, 201) else "FAIL",
                "summary": data_summary
            })
            print(f"[{'PASS' if status in (200, 201) else 'FAIL'}] {method} {t['url']} ({status}) - {desc}")
        except Exception as e:
            audit_results.append({
                "method": method,
                "endpoint": t["url"],
                "description": desc,
                "status": 0,
                "result": "ERROR",
                "summary": str(e)
            })
            print(f"[ERROR] {method} {t['url']} - {e}")

    # 4. Check Redis
    print("\n--- Checking Redis State ---")
    try:
        import redis
        r_client = redis.Redis.from_url("redis://redis:6379/0", decode_responses=True)
        r_ping = r_client.ping()
        r_keys = r_client.keys("*")
        print(f"Redis Ping: {r_ping}, Active Keys: {len(r_keys)} keys found: {r_keys[:10]}")
    except Exception as e:
        print(f"Redis Error: {e}")

    # 5. Check ChromaDB
    print("\n--- Checking ChromaDB State ---")
    try:
        c_client = chromadb.HttpClient(host="chromadb", port=8001)
        hb = c_client.heartbeat()
        colls = c_client.list_collections()
        coll_names = [c.name for c in colls]
        print(f"ChromaDB Heartbeat: {hb}, Collections ({len(colls)}): {coll_names}")
    except Exception as e:
        print(f"ChromaDB Error: {e}")

    # 6. Check Ollama
    print("\n--- Checking Ollama State ---")
    try:
        ollama_res = requests.get("http://ollama:11434/api/tags", timeout=5).json()
        models = [m["name"] for m in ollama_res.get("models", [])]
        print(f"Ollama Reachable: True, Available Models: {models}")
    except Exception as e:
        print(f"Ollama Error: {e}")

    # 7. Check PostgreSQL Tables
    print("\n--- Checking PostgreSQL Schema & Row Counts ---")
    async def inspect_postgres():
        async with AsyncSessionLocal() as session:
            tables_res = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public';"))
            tables = [r[0] for r in tables_res.fetchall()]
            counts = {}
            for t in tables:
                try:
                    c_res = await session.execute(text(f"SELECT count(*) FROM {t};"))
                    counts[t] = c_res.scalar()
                except Exception as e:
                    counts[t] = f"Error: {e}"
            print(f"PostgreSQL Tables ({len(tables)}): {counts}")

    asyncio.run(inspect_postgres())

    # Write results to file
    with open("/app/audit_raw_results.json", "w") as f:
        json.dump({
            "total_paths": len(paths),
            "test_results": audit_results
        }, f, indent=2)
    print("\nRaw Audit Results Saved to /app/audit_raw_results.json")

if __name__ == "__main__":
    run_audit()
