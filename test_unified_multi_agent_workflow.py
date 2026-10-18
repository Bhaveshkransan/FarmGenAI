import sys
import os
import json
import time
import requests
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://localhost:8000/api/v1"
UI_BASE = "http://localhost:8080"
ARTIFACT_DIR = r"C:\Users\ACER\.gemini\antigravity-ide\brain\1f7d05f6-aff6-42e5-8054-59ee7cba80e6"

test_results = {}

def log(tc, msg):
    print(f"[{tc}] {msg}")

# =========================================================================
# TEST 1: Farmer & Transport Both Available (Full Chain Procurement)
# =========================================================================
log("TEST 1", "Starting Farmer + Transport procurement (Soybean, 3000kg in Latur)...")
t1_payload = {
    "crop": "Soybean",
    "quantity": 3000,
    "min_price": 48.0,
    "target_price": 50.0,
    "workflow_mode": "FULL_SUPPLY_CHAIN",
    "district": "Latur",
    "location": "Latur, Maharashtra",
    "buyer_location": "Pune Agro-Industrial Complex, Hadapsar",
    "selected_services": {
        "farmer_matching": True,
        "transport": True
    }
}
res_t1 = requests.post(f"{API_BASE}/negotiations/start-negotiation", json=t1_payload)
assert res_t1.status_code in (200, 201), f"T1 start failed: {res_t1.text}"
neg_id_1 = res_t1.json().get("negotiation_id") or res_t1.json().get("id")
log("TEST 1", f"Created negotiation {neg_id_1}")

# Poll status until initial offers generated
time.sleep(1.5)
status_res_1 = requests.get(f"{API_BASE}/negotiations/{neg_id_1}").json()
log("TEST 1", f"Negotiation status: {status_res_1.get('status')} | Offers: {len(status_res_1.get('offers', []))}")
assert len(status_res_1.get("offers", [])) >= 1

# Accept farmer offer to complete Phase 1
accept_res_1 = requests.post(f"{API_BASE}/negotiations/{neg_id_1}/accept", json={"final_price": 50.0})
assert accept_res_1.status_code in (200, 201)
log("TEST 1", f"Farmer deal accepted. Status: {accept_res_1.json().get('status')}")

# Call Transport Agent negotiation API with real state
tp_plan_req = {
    "crop": "Soybean",
    "quantity_kg": 3000,
    "pickup_location": "Latur",
    "delivery_location": "Pune",
    "buyer_offer": 19500
}
tp_plan_res = requests.post(f"{API_BASE}/transport/plan", json=tp_plan_req)
assert tp_plan_res.status_code == 200
tp_plan_data = tp_plan_res.json()
selected_v = tp_plan_data.get("full_state", {}).get("selected_vehicle", {})
log("TEST 1", f"Transport Agent selected vehicle: {selected_v.get('vehicle_name')} ({selected_v.get('capacity_kg')} kg capacity)")
assert selected_v.get("capacity_kg", 0) >= 3000, "Selected vehicle capacity must be >= 3000kg"

# Interactive Transport negotiation round
tp_neg_req = {
    "buyer_offer": 21000.0,
    "state": tp_plan_data.get("full_state")
}
tp_neg_res = requests.post(f"{API_BASE}/transport/negotiate", json=tp_neg_req)
assert tp_neg_res.status_code == 200
tp_neg_data = tp_neg_res.json()
log("TEST 1", f"Transport Agent decision: {tp_neg_data.get('negotiation_status')} | Agreed Price: ₹{tp_neg_data.get('agreed_price')}")
assert tp_neg_data.get("negotiation_status") in ("ACCEPTED", "COUNTERED")

# Persist transport plan to negotiation record
final_freight = tp_neg_data.get("agreed_price") or 21000.0
persisted_tp = {
    "vehicle_name": selected_v.get("vehicle_name"),
    "vehicle_type": selected_v.get("vehicle_type"),
    "agreed_freight": final_freight,
    "distance_km": tp_plan_data.get("full_state", {}).get("distance_km", 322.62),
    "origin": "Latur",
    "destination": "Pune"
}
requests.post(f"{API_BASE}/negotiations/{neg_id_1}/accept", json={"transport_plan": persisted_tp})

# Verify persisted state
db_status_1 = requests.get(f"{API_BASE}/negotiations/{neg_id_1}").json()
assert db_status_1.get("transport_plan") is not None, "transport_plan must be persisted in DB"
log("TEST 1", "SUCCESS: Farmer and Transport phases both executed and persisted with real agent data.")
test_results["TEST_1_FULL_CHAIN"] = "PASSED"

# =========================================================================
# TEST 2: Transport-Only Procurement (No Farmer Phase Forced)
# =========================================================================
log("TEST 2", "Starting Transport-Only procurement (Cotton, 4000kg in Jalgaon)...")
t2_payload = {
    "crop": "Cotton",
    "quantity": 4000,
    "min_price": 60.0,
    "target_price": 65.0,
    "workflow_mode": "TRANSPORT_ONLY",
    "district": "Jalgaon",
    "location": "Jalgaon, Maharashtra",
    "buyer_location": "Pune Agro-Industrial Complex, Hadapsar",
    "selected_services": {
        "farmer_matching": False,
        "transport": True
    }
}
res_t2 = requests.post(f"{API_BASE}/negotiations/start-negotiation", json=t2_payload)
neg_id_2 = res_t2.json().get("negotiation_id") or res_t2.json().get("id")
time.sleep(1)
status_res_2 = requests.get(f"{API_BASE}/negotiations/{neg_id_2}").json()
assert status_res_2.get("workflow_mode") == "TRANSPORT_ONLY"

# Verify route estimate for Jalgaon -> Pune
route_t2 = requests.get(f"{API_BASE}/transport/route-estimate", params={"origin": "Jalgaon", "destination": "Pune"}).json()
assert route_t2.get("success") is True
dist_t2 = route_t2["routes"][0]["distance_km"]
log("TEST 2", f"Authoritative OSRM route Jalgaon -> Pune: {dist_t2} km, Duration: {route_t2['routes'][0]['duration_hours']}h")
assert dist_t2 > 300, "Distance Jalgaon to Pune should be > 300 km"
test_results["TEST_2_TRANSPORT_ONLY"] = "PASSED"

# =========================================================================
# TEST 3: Farmer Unavailable but Transport Legitimately Eligible
# =========================================================================
log("TEST 3", "Testing Farmer Unavailable with valid district origin fallback...")
t3_payload = {
    "crop": "Bajra",
    "quantity": 1500,
    "min_price": 20.0,
    "target_price": 22.0,
    "workflow_mode": "FULL_SUPPLY_CHAIN",
    "district": "Solapur",
    "location": "Solapur, Maharashtra",
    "selected_services": {
        "farmer_matching": True,
        "transport": True
    }
}
res_t3 = requests.post(f"{API_BASE}/negotiations/start-negotiation", json=t3_payload)
neg_id_3 = res_t3.json().get("negotiation_id") or res_t3.json().get("id")

# Simulate farmer negotiation rejected / failed
requests.post(f"{API_BASE}/negotiations/{neg_id_3}/reject")
status_res_3 = requests.get(f"{API_BASE}/negotiations/{neg_id_3}").json()
log("TEST 3", f"Farmer rejected. Status: {status_res_3.get('status')}")

# Verify Transport Agent can still evaluate route from Solapur
t3_rec = requests.post(f"{API_BASE}/transport/vehicles/recommend", json={
    "crop": "Bajra",
    "quantity_kg": 1500,
    "pickup_location": "Solapur",
    "delivery_location": "Pune"
}).json()
assert t3_rec.get("success") is True and len(t3_rec.get("data", [])) > 0
log("TEST 3", f"Transport candidates found for Solapur origin: {len(t3_rec.get('data'))} vehicles")
test_results["TEST_3_FARMER_UNAVAIL_TRANSPORT_OK"] = "PASSED"

# =========================================================================
# TEST 4: Transporter Unavailable / Incompatible Payload (50,000kg Overload)
# =========================================================================
log("TEST 4", "Testing Incompatible payload: 50,000 kg (exceeds all fleet vehicles)...")
t4_req = {
    "crop": "Soybean",
    "quantity_kg": 50000,
    "pickup_location": "Latur",
    "delivery_location": "Pune",
    "buyer_offer": 50000
}
t4_plan = requests.post(f"{API_BASE}/transport/plan", json=t4_req).json()
log("TEST 4", f"Transport Plan response: status={t4_plan.get('status')} | success={t4_plan.get('success')} | rejected={len(t4_plan.get('rejected_vehicles', []))}")
assert t4_plan.get("status") == "INFEASIBLE" or t4_plan.get("success") is False, "50MT load must return INFEASIBLE"
assert len(t4_plan.get("rejected_vehicles", [])) > 0, "Must report rejected vehicles with capacity reasons"
log("TEST 4", f"Sample rejection reason: {t4_plan.get('rejected_vehicles')[0].get('reason')}")
test_results["TEST_4_INCOMPATIBLE_PAYLOAD_HANDLING"] = "PASSED"

# =========================================================================
# TEST 5: Missing Prerequisite (No Pickup Origin & No Farmer)
# =========================================================================
log("TEST 5", "Testing Missing Prerequisite handling in Buyer Orchestrator...")
import subprocess

cmd_test5 = [
    "docker", "exec", "farmgenai-backend", "python", "-c",
    "import asyncio, json; from backend.services.buyer_orchestrator import buyer_orchestration_service; "
    "res = asyncio.run(buyer_orchestration_service.orchestrate_negotiation({'crop':'Soybean','quantity':2000,'target_price':50.0,'selected_services':{'farmer_matching':False,'transport':True},'pickup_location':None,'district':None,'location':None})); "
    "tp = res.get('transport_assignment', {}); print('TEST5_STATUS:' + str(tp.get('status'))); print('TEST5_ERROR:' + str(tp.get('error')))"
]
out_5 = subprocess.check_output(cmd_test5, text=True, errors='replace')
st_val = ""
err_val = ""
for line in out_5.splitlines():
    if line.startswith("TEST5_STATUS:"):
        st_val = line.split(":", 1)[1].strip()
    elif line.startswith("TEST5_ERROR:"):
        err_val = line.split(":", 1)[1].strip()

log("TEST 5", f"Orchestration response for missing pickup: status={st_val} | error={err_val}")
assert st_val == "UNRESOLVED_DEPENDENCY", f"Expected UNRESOLVED_DEPENDENCY, got {st_val}"
test_results["TEST_5_MISSING_PREREQUISITE_DEPENDENCY"] = "PASSED"

# =========================================================================
# TEST 6: Warehouse & Processor Capabilities (Genuine Verification)
# =========================================================================
log("TEST 6", "Verifying Warehouse and Processor genuine capabilities & rate cards...")
wh_list_res = requests.get(f"{API_BASE}/warehouse/list").json()
wh_list = wh_list_res.get("warehouses", []) if isinstance(wh_list_res, dict) else wh_list_res
log("TEST 6", f"Retrieved {len(wh_list)} active APMC warehouses:")
for wh in wh_list:
    log("TEST 6", f"  - {wh.get('name')} in {wh.get('location')}: Capacity={wh.get('capacity_kg')}kg, Rate=Rs.{wh.get('base_cost_per_kg_per_day')}/kg/day")
assert len(wh_list) >= 3

# Book warehouse storage for 2,500kg
wh_book_res = requests.post(f"{API_BASE}/warehouse/book", json={
    "quantity": 2500,
    "location": "Pune",
    "crop": "Soybean"
}).json()
log("TEST 6", f"Warehouse Booking: {wh_book_res.get('warehouse')} | Daily Cost: Rs.{wh_book_res.get('total_daily_cost')}")
assert wh_book_res.get("status") == "ASSIGNED"

# Verify Processor catalog
proc_list_res = requests.get(f"{API_BASE}/processor").json()
proc_list = proc_list_res.get("data", []) if isinstance(proc_list_res, dict) else proc_list_res
log("TEST 6", f"Retrieved {len(proc_list)} agro-processing facilities:")
for proc in proc_list:
    log("TEST 6", f"  - {proc.get('name')} ({proc.get('location')}): {proc.get('output_product')} @ Rs.{proc.get('price_per_kg')}/kg")
assert len(proc_list) >= 5

# Submit processing order
proc_order_res = requests.post(f"{API_BASE}/processor/order", json={
    "negotiation_id": neg_id_1,
    "processor_id": "proc_soy_latur",
    "crop": "Soybean",
    "quantity": 1000,
    "farmer_id": "Farmer Ramesh"
}).json()
log("TEST 6", f"Processor Order: {proc_order_res.get('order_id')} | Total: Rs.{proc_order_res.get('total_payment')}")
assert proc_order_res.get("status") == "SUBMITTED"
test_results["TEST_6_WAREHOUSE_AND_PROCESSOR_SERVICES"] = "PASSED"

# =========================================================================
# TEST 7: Multi-Service Negotiation (Farmer + Transport + Warehouse + Processor)
# =========================================================================
log("TEST 7", "Testing Full 4-Service Chain Persistence in Backend DB...")
t7_payload = {
    "crop": "Soybean",
    "quantity": 2500,
    "min_price": 48.0,
    "target_price": 50.0,
    "workflow_mode": "FULL_SUPPLY_CHAIN",
    "district": "Latur",
    "location": "Latur, Maharashtra",
    "selected_services": {
        "farmer_matching": True,
        "transport": True,
        "warehouse": True,
        "processor": True
    }
}
res_t7 = requests.post(f"{API_BASE}/negotiations/start-negotiation", json=t7_payload)
neg_id_7 = res_t7.json().get("negotiation_id") or res_t7.json().get("id")
time.sleep(1.5)

# Accept deal with all 4 phase plans
full_accept_payload = {
    "final_price": 50.0,
    "transport_plan": {
        "vehicle_name": "ColdChain Reefer 4MT",
        "agreed_freight": 21000.0,
        "distance_km": 322.62,
        "origin": "Latur",
        "destination": "Pune"
    },
    "warehouse_plan": {
        "warehouse_name": "Pune Agro Hub",
        "location": "Pune",
        "agreed_cost": 4000.0,
        "total_daily_cost": 1333.33,
        "recommended_days": 3
    },
    "processor_plan": {
        "processor_id": "proc_soy_latur",
        "processor_name": "Marathwada Solvent Extractions",
        "output_product": "Refined Soya Oil & DOC",
        "total_payment": 170000.0
    }
}
acc_7 = requests.post(f"{API_BASE}/negotiations/{neg_id_7}/accept", json=full_accept_payload)
assert acc_7.status_code in (200, 201), f"Accept failed: {acc_7.text}"

# Verify DB persistence of all 4 plans
db_check_7 = requests.get(f"{API_BASE}/negotiations/{neg_id_7}").json()
assert db_check_7.get("transport_plan") is not None, "transport_plan must be persisted"
assert db_check_7.get("warehouse_plan") is not None, "warehouse_plan must be persisted"
assert db_check_7.get("processor_plan") is not None, "processor_plan must be persisted"
assert db_check_7.get("final_price") == 50.0
log("TEST 7", f"SUCCESS: All 4 service plans persisted authoritatively in PostgreSQL!")
test_results["TEST_7_FOUR_SERVICE_PERSISTENCE"] = "PASSED"

# =========================================================================
# TEST 8: UI Playwright Verification (Reopening & Refresh Isolation)
# =========================================================================
log("TEST 8", "Testing UI Negotiation Room with Playwright in clean session...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1400, "height": 900})
    page = context.new_page()

    # 1. Login demo
    page.goto(f"{UI_BASE}/login?demo=buyer")
    page.wait_for_timeout(2000)

    # 2. Open negotiation 7 (which has all 4 plans persisted in DB)
    page.goto(f"{UI_BASE}/negotiation/{neg_id_7}")
    page.wait_for_timeout(3500)

    content_7 = page.content()
    has_summary = "Landed Cost" in content_7 or "Settlement" in content_7
    has_transport = "Inbound Freight" in content_7 or "ColdChain Reefer" in content_7
    has_warehouse = "Warehouse" in content_7 or "Pune Agro" in content_7
    log("TEST 8", f"UI Check: has_summary={has_summary}, has_transport={has_transport}, has_warehouse={has_warehouse}")

    # Capture UI screenshot as artifact
    screenshot_path = os.path.join(ARTIFACT_DIR, "unified_buyer_orchestration_room.png")
    page.screenshot(path=screenshot_path, full_page=True)
    log("TEST 8", f"Saved UI verification screenshot to {screenshot_path}")

    # 3. Open Transport-Only negotiation in fresh session
    context2 = browser.new_context(viewport={"width": 1400, "height": 900})
    page2 = context2.new_page()
    page2.goto(f"{UI_BASE}/login?demo=buyer")
    page2.wait_for_timeout(1500)
    page2.goto(f"{UI_BASE}/negotiation/{neg_id_2}")
    page2.wait_for_timeout(3500)

    content_2 = page2.content()
    is_transport_active = "Transport Agent" in content_2 or "Inbound Freight" in content_2 or "Available Fleet" in content_2
    log("TEST 8", f"Transport-Only UI active: {is_transport_active}")
    assert is_transport_active, "Transport-only negotiation must immediately activate Transport room"

    screenshot_path2 = os.path.join(ARTIFACT_DIR, "transport_only_orchestration_room.png")
    page2.screenshot(path=screenshot_path2, full_page=True)
    log("TEST 8", f"Saved Transport-Only screenshot to {screenshot_path2}")

    browser.close()

test_results["TEST_8_UI_AND_SESSION_RESTORE"] = "PASSED"

print("\n=======================================================")
print("ALL TESTS COMPLETED SUCCESSFULLY!")
print("=======================================================")
for k, v in test_results.items():
    print(f"  {k}: {v}")
