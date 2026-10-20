"""Quick integration check for the three new features."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import agents.buyer_agent as bm
import agents.farmer_agent as fm
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.negotiation_service import service
from database.db import Database

import asyncio
import time
from unittest.mock import patch

bm.llm_client = None
fm.llm_client = None

try:
    asyncio.run(Database.reset())
except Exception:
    pass

service.active_negotiations.clear()
try:
    asyncio.run(service.ensure_default_buyers())
except Exception:
    pass

# Override JWT auth for testing
from backend.services.security import get_current_user
app.dependency_overrides[get_current_user] = lambda: {"sub": "admin_001", "role": "admin"}

client = TestClient(app)


payload = {
    "farmer_name": "Ramesh",
    "crop": "Onion",
    "quantity": 800,
    "min_price": 20,
    "shelf_life": 5,
    "location": "Nashik",
    "quality": "A",
    "language": "Marathi",
    "sync": True,
}

with patch("backend.services.external_apis._http_get", return_value=None):
    from llm.llm_client import client as global_llm_client
    global_llm_client.enabled = False

    # 1. POST returns status immediately
    r = client.post("/api/v1/negotiations/", json=payload)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    initial = r.json()
    print("[1] Immediate response status:", initial.get("status"))
    assert initial.get("status") in ("RUNNING", "COMPLETED", "DEAL", "FAILED", "NO_DEAL")

    # 2. Poll for final result
    neg_id = initial.get("negotiation_id")
    status = initial
    if initial.get("status") == "RUNNING" and neg_id:
        for _ in range(60):
            res = client.get(f"/api/v1/negotiations/{neg_id}")
            if res.status_code == 200:
                s = res.json()
                if s.get("status") != "RUNNING":
                    status = s
                    break
            time.sleep(1)
    print("[2] Polled final status:", status.get("status"))
    assert status.get("status") != "RUNNING"

# 3. Multiple buyer offers present
offers = status.get("market_offers", [])
print("[3] market_offers count:", len(offers))
assert len(offers) >= 1

# 4. Selected buyer set
buyer = status.get("selected_buyer") or {}
print("[4] selected_buyer:", buyer.get("buyer_name"))
assert buyer.get("buyer_name")

# 5. Logs present
logs = status.get("logs", [])
print("[5] logs count:", len(logs))
assert len(logs) > 0

# 6. History saved
hist_resp = client.get("/api/v1/history/all")
print("[6] /api/v1/history/all status:", hist_resp.status_code)
assert hist_resp.status_code == 200
hist_data = hist_resp.json()
print("[6] history items:", len(hist_data.get("history", [])))
assert len(hist_data.get("history", [])) >= 1

# 7. Negotiations list endpoint
negs_resp = client.get("/api/v1/negotiations/")
assert negs_resp.status_code == 200
negs_raw = negs_resp.json()
negs = negs_raw if isinstance(negs_raw, list) else negs_raw.get("negotiations", [])
print("[7] /api/v1/negotiations count:", len(negs))
assert len(negs) >= 1

# 8. Negotiation row has created_at timestamp
assert negs[0].get("created_at"), "no created_at in negotiation row"
print("[8] created_at:", negs[0]["created_at"])

print("\n[SUCCESS] All integration checks passed!")

