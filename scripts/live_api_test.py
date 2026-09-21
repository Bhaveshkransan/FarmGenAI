"""Live HTTP API end-to-end test - tests all frontend-facing endpoints."""
import requests
import json

BASE = "http://localhost:8000"

def check(name, r, key=None):
    if r.status_code == 200:
        if key:
            val = r.json().get(key, '?')
            print(f"[OK] {name}: {key}={val}")
        else:
            print(f"[OK] {name}: HTTP 200")
    else:
        print(f"[FAIL] {name}: HTTP {r.status_code} - {r.text[:80]}")

# 1. Health check
r = requests.get(f"{BASE}/")
check("API Root", r, "message")

# 2. Nodes
r = requests.get(f"{BASE}/api/nodes")
check("P2P Nodes", r)
if r.ok:
    n = len(r.json().get("nodes", []))
    print(f"       -> {n} nodes active")

# 3. Ledger
r = requests.get(f"{BASE}/api/ledger")
check("Audit Ledger", r)

# 4. Buyers list
r = requests.get(f"{BASE}/api/v1/buyers/")
check("Buyer Registry", r)
if r.ok:
    data = r.json()
    buyers = data.get("buyers", data if isinstance(data, list) else [])
    print(f"       -> {len(buyers)} registered buyers")

# 5. Agents directory
r = requests.get(f"{BASE}/api/v1/agents/")
check("Agent Directory", r)
if r.ok:
    data = r.json()
    agents = data.get("agents", data if isinstance(data, list) else [])
    roles = [a.get("role", str(a)) for a in agents if isinstance(a, dict)]
    print(f"       -> Roles: {', '.join(roles[:5])}")

# 6. Produce listings
r = requests.get(f"{BASE}/api/v1/listings/")
check("Farmer Produce", r)

# 7. Past negotiations
r = requests.get(f"{BASE}/api/v1/negotiations/")
check("Negotiations History", r)
if r.ok:
    data = r.json()
    negs = data.get("negotiations", data if isinstance(data, list) else [])
    print(f"       -> {len(negs)} past negotiations")

# 8. Transport fleet
r = requests.get(f"{BASE}/api/v1/transport/fleet")
check("Logistics Fleet", r)

# 9. Warehouse list
r = requests.get(f"{BASE}/api/v1/warehouse/")
check("Warehouse Inventory", r)

# 10. Run a real simulation (direct-sale)
print("\n[TEST] Running direct-sale simulation...")
try:
    r = requests.post(f"{BASE}/run-simulation", json={
        "scenario": "direct-sale",
        "user_id": "audit_e2e",
        "farmer_name": "Ramesh",
        "crop": "Tomato",
        "quantity": 200,
        "min_price": 18,
        "shelf_life": 5,
        "location": "Nashik"
    }, timeout=30)
    if r.ok:
        data = r.json()
        buyer = data.get("selected_buyer", {})
        print(f"[OK] Simulation: status={data.get('status')} | buyer={buyer.get('buyer_name','?')} | price=Rs.{data.get('final_price')} | score={data.get('score')}")
    else:
        print(f"[FAIL] Simulation: HTTP {r.status_code} - {r.text[:100]}")
except Exception as e:
        print(f"[FAIL] Simulation Exception: {e}")

# 11. Run "all" scenario
print("\n[TEST] Running all-scenarios simulation...")
try:
    r = requests.post(f"{BASE}/run-simulation", json={
        "scenario": "all",
        "user_id": "audit_e2e"
    }, timeout=60)
    if r.ok:
        data = r.json()
        scenarios = data.get("scenarios", [])
        best = data.get("best_scenario", "?")
        print(f"[OK] All-scenarios: {len(scenarios)} scenarios | best={best}")
        for s in scenarios:
            print(f"     -> {s.get('scenario_type')}: status={s.get('status')} score={s.get('score')}")
    else:
        print(f"[FAIL] All-scenarios: HTTP {r.status_code} - {r.text[:100]}")
except Exception as e:
    print(f"[FAIL] All-scenarios Exception: {e}")

print("\n" + "="*50)
print("Frontend Web App Dashboard: http://localhost:8080")
print("Backend API Swagger Docs:   http://localhost:8000/docs")
print("="*50)
