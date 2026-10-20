"""
tests/test_topic1_buyer_matching_flow.py

Verification tests for Priority 1 / Topic 1:
Buyer Request -> Database -> requirement_id -> Matching Service -> Farmer Produce Listings
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from backend.main import app
from database.db import Database
from backend.core.security import create_access_token

client = TestClient(app)

def get_auth_headers(user_id: str = "buyer_enterprise", role: str = "buyer"):
    token = create_access_token(data={"sub": user_id, "role": role})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(autouse=True)
def reset_database_before_test():
    asyncio.run(Database.reset())
    yield


def test_requirement_creation_and_persistence():
    headers = get_auth_headers("buyer_101", "buyer")
    payload = {
        "crop": "Soybean",
        "quantity": 1000.0,
        "target_price": 48.0,
        "max_price": 52.0,
        "location": "Pune",
        "budget": 52000.0,
        "quality_grade": "Grade A"
    }
    res = client.post("/api/v1/requirements", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    req_id = data["requirement_id"]
    assert req_id.startswith("req_")

    # Verify persistence in Database
    buyers = asyncio.run(Database.list_buyers_async())
    saved = next((r for r in buyers if r.get("id") == req_id), None)
    assert saved is not None
    assert saved["crop"] == "Soybean"
    assert saved["user_id"] == "buyer_101"


def test_requirement_retrieval_by_id():
    headers = get_auth_headers("buyer_102", "buyer")
    payload = {
        "crop": "Cotton",
        "quantity": 500.0,
        "target_price": 70.0,
        "max_price": 75.0,
        "location": "Jalgaon",
        "budget": 37500.0
    }
    create_res = client.post("/api/v1/requirements", json=payload, headers=headers)
    req_id = create_res.json()["requirement_id"]

    get_res = client.get(f"/api/v1/requirements/{req_id}", headers=headers)
    assert get_res.status_code == 200
    retrieved = get_res.json()["data"]
    assert retrieved["id"] == req_id
    assert retrieved["crop"] == "Cotton"
    assert retrieved["user_id"] == "buyer_102"


def test_get_requirement_matches():
    # 1. Create produce listing
    farmer_listing = {
        "id": "prod_soya_1",
        "farmer_name": "Ramesh Farmer",
        "user_id": "farmer_88",
        "crop": "Soybean",
        "quantity": 2000.0,
        "min_price": 46.0,
        "expected_price": 48.0,
        "location": "Latur",
        "status": "ACTIVE"
    }
    asyncio.run(Database.upsert_produce_async(farmer_listing))

    # 2. Create buyer requirement
    headers = get_auth_headers("buyer_103", "buyer")
    req_payload = {
        "crop": "Soybean",
        "quantity": 800.0,
        "target_price": 48.0,
        "max_price": 52.0,
        "location": "Pune",
        "budget": 41600.0
    }
    req_id = client.post("/api/v1/requirements", json=req_payload, headers=headers).json()["requirement_id"]

    # 3. GET matches
    res = client.get(f"/api/v1/requirements/{req_id}/matches", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["count"] >= 1
    matched = data["data"][0]
    assert matched["crop"] == "Soybean"
    assert matched["listing_id"] == "prod_soya_1"


def test_post_requirement_to_listings_by_id():
    # 1. Create produce listing
    farmer_listing = {
        "id": "prod_onion_1",
        "farmer_name": "Nashik Farmer",
        "user_id": "farmer_99",
        "crop": "Onion",
        "quantity": 1500.0,
        "min_price": 22.0,
        "location": "Nashik",
        "status": "ACTIVE"
    }
    asyncio.run(Database.upsert_produce_async(farmer_listing))

    # 2. Create buyer requirement
    headers = get_auth_headers("buyer_104", "buyer")
    req_payload = {
        "crop": "Onion",
        "quantity": 500.0,
        "target_price": 25.0,
        "max_price": 28.0,
        "location": "Nashik",
        "budget": 14000.0
    }
    req_id = client.post("/api/v1/requirements", json=req_payload, headers=headers).json()["requirement_id"]

    # 3. POST matching by requirement_id
    res = client.post("/api/v1/matching/requirement-to-listings", json={"requirement_id": req_id}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["crop"] == "Onion"
    assert len(data["data"]) >= 1
    assert data["data"][0]["listing_id"] == "prod_onion_1"


def test_canonical_crop_matching_aliases():
    # Farmer listed produce as "Soya" (alias)
    farmer_listing = {
        "id": "prod_soya_alias",
        "farmer_name": "Kisan Patel",
        "user_id": "farmer_55",
        "crop": "Soya",
        "quantity": 1000.0,
        "min_price": 47.0,
        "location": "Latur",
        "status": "ACTIVE"
    }
    asyncio.run(Database.upsert_produce_async(farmer_listing))

    # Buyer requirement specifies "Soybean" (canonical)
    headers = get_auth_headers("buyer_105", "buyer")
    req_payload = {
        "crop": "Soybean",
        "quantity": 500.0,
        "target_price": 49.0,
        "max_price": 53.0,
        "location": "Latur",
        "budget": 26500.0
    }
    req_id = client.post("/api/v1/requirements", json=req_payload, headers=headers).json()["requirement_id"]

    res = client.get(f"/api/v1/requirements/{req_id}/matches", headers=headers)
    assert res.status_code == 200
    matches = res.json()["data"]
    assert len(matches) == 1
    assert matches[0]["listing_id"] == "prod_soya_alias"


def test_nonexistent_requirement_returns_404():
    headers = get_auth_headers("buyer_106", "buyer")
    res_get = client.get("/api/v1/requirements/req_missing999/matches", headers=headers)
    assert res_get.status_code == 404
    assert "not found" in res_get.json()["detail"].lower()

    res_post = client.post("/api/v1/matching/requirement-to-listings", json={"requirement_id": "req_missing999"}, headers=headers)
    assert res_post.status_code == 404
    assert "not found" in res_post.json()["detail"].lower()


def test_unauthorized_buyer_returns_403():
    # Buyer 1 creates requirement
    headers_owner = get_auth_headers("buyer_owner", "buyer")
    req_payload = {
        "crop": "Jowar",
        "quantity": 400.0,
        "target_price": 32.0,
        "location": "Solapur",
        "budget": 12800.0
    }
    req_id = client.post("/api/v1/requirements", json=req_payload, headers=headers_owner).json()["requirement_id"]

    # Buyer 2 attempts to get matches for Buyer 1's requirement
    headers_other = get_auth_headers("buyer_other", "buyer")
    res_get = client.get(f"/api/v1/requirements/{req_id}/matches", headers=headers_other)
    assert res_get.status_code == 403

    res_post = client.post("/api/v1/matching/requirement-to-listings", json={"requirement_id": req_id}, headers=headers_other)
    assert res_post.status_code == 403


def test_no_matching_listings_returns_empty_result():
    # Create farmer listing for Sugarcane
    farmer_listing = {
        "id": "prod_cane_1",
        "farmer_name": "Kolhapur Farmer",
        "user_id": "farmer_12",
        "crop": "Sugarcane",
        "quantity": 5000.0,
        "min_price": 3.4,
        "location": "Kolhapur",
        "status": "ACTIVE"
    }
    asyncio.run(Database.upsert_produce_async(farmer_listing))

    # Buyer creates requirement for Rice
    headers = get_auth_headers("buyer_107", "buyer")
    req_payload = {
        "crop": "Rice",
        "quantity": 1000.0,
        "target_price": 24.0,
        "location": "Gondia",
        "budget": 24000.0
    }
    req_id = client.post("/api/v1/requirements", json=req_payload, headers=headers).json()["requirement_id"]

    res = client.get(f"/api/v1/requirements/{req_id}/matches", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["count"] == 0
    assert data["data"] == []


def test_client_cannot_override_stored_requirement_values():
    # Create farmer listing for Soybean
    farmer_listing = {
        "id": "prod_soya_override",
        "farmer_name": "Latur Farmer",
        "user_id": "farmer_77",
        "crop": "Soybean",
        "quantity": 1000.0,
        "min_price": 45.0,
        "location": "Latur",
        "status": "ACTIVE"
    }
    asyncio.run(Database.upsert_produce_async(farmer_listing))

    # Create requirement for Soybean
    headers = get_auth_headers("buyer_108", "buyer")
    req_payload = {
        "crop": "Soybean",
        "quantity": 500.0,
        "target_price": 48.0,
        "location": "Latur",
        "budget": 24000.0
    }
    req_id = client.post("/api/v1/requirements", json=req_payload, headers=headers).json()["requirement_id"]

    # Client attempts to pass requirement_id WITH override parameters ("Rice", target_price=10.0)
    override_payload = {
        "requirement_id": req_id,
        "crop": "Rice",
        "target_price": 10.0
    }
    res = client.post("/api/v1/matching/requirement-to-listings", json=override_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    # It must use stored requirement ("Soybean"), NOT client override ("Rice")
    assert data["crop"] == "Soybean"
    assert len(data["data"]) == 1
    assert data["data"][0]["listing_id"] == "prod_soya_override"
