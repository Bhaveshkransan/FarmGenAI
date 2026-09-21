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

results = {}

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
r = requests.get(f"{BASE}/api/buyer/")
check("Buyer Registry", r)
if r.ok:
    b = len(r.json().get("buyers", []))
    print(f"       -> {b} registered buyers")

# 5. Agents directory
r = requests.get(f"{BASE}/agents")
check("Agent Directory", r)
if r.ok:
    roles = [a["role"] for a in r.json().get("agents", [])]
    print(f"       -> Roles: {', '.join(roles)}")

# 6. Produce listings
r = requests.get(f"{BASE}/api/farmer/produce")
check("Farmer Produce", r)

# 7. Past negotiations
r = requests.get(f"{BASE}/api/negotiations")
check("Negotiations History", r)
if r.ok:
    n = len(r.json().get("negotiations", []))
    print(f"       -> {n} past negotiations")

# 8. Warehouse fleet
r = requests.get(f"{BASE}/api/warehouse/fleet")
check("Logistics Fleet", r)

# 9. Warehouse list
r = requests.get(f"{BASE}/api/warehouse/")
check("Warehouse Inventory", r)

# 10. Run a real simulation (direct-sale)
print("\n[TEST] Running direct-sale simulation...")
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
    print(f"[FAIL] Simulation: HTTP {r.status_code}")

# 11. Run "all" scenario
print("\n[TEST] Running all-scenarios simulation...")
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
    print(f"[FAIL] All-scenarios: HTTP {r.status_code}")

print("\n" + "="*50)
print("Frontend URL: http://localhost:5500/dashboard.html")
print("Simulation:   http://localhost:5500/simulation.html")
print("="*50)
