import asyncio
import httpx
from database.db import Database, AsyncSessionLocal, DBProduce
from sqlalchemy import select

async def run_e2e_farmer_audit():
    print("=" * 60)
    print("STARTING FARMER AGENT END-TO-END FORENSIC VERIFICATION")
    print("=" * 60)

    # 1. Login as Farmer
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        login_res = await client.post("/api/v1/auth/login", json={
            "email": "farmer@agrinegotiator.com",
            "password": "password123"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        farmer_data = login_res.json()
        token = farmer_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        farmer_id = farmer_data["user"]["id"]
        print(f"✅ 1. Authenticated as Farmer: {farmer_data['user']['name']} (ID: {farmer_id})")

        # 2. Farmer Listing Creation
        create_payload = {
            "crop": "Onion",
            "variety": "Nashik Red",
            "grade": "A",
            "quantity": 2500.0,
            "unit": "kg",
            "min_sale_quantity": 200.0,
            "expected_price": 32.0,
            "min_price": 28.0,
            "price_unit": "per_kg",
            "shelf_life": 21,
            "location": "Nashik APMC Hub",
            "description": "Premium export-quality red onions from Dindori farm"
        }
        create_res = await client.post("/api/v1/listings", json=create_payload, headers=headers)
        assert create_res.status_code == 200, f"Create listing failed: {create_res.text}"
        created = create_res.json()
        listing_id = created["listing_id"]
        print(f"✅ 2. Created Listing: ID {listing_id}, Crop: {created['data']['crop']}, Qty: {created['data']['quantity']} kg")

        # 3. Verify PostgreSQL Persistence
        async with AsyncSessionLocal() as session:
            db_row = await session.get(DBProduce, listing_id)
            assert db_row is not None, f"Listing {listing_id} not found in PostgreSQL DBProduce!"
            assert db_row.crop == "Onion"
            assert float(db_row.expected_price) == 32.0
            print(f"✅ 3. Verified PostgreSQL DBProduce Row: ID {db_row.id}, Crop: {db_row.crop}, Status: {db_row.status}")

        # 4. Buyer Matching Discovery
        from backend.services.matching_service import match_requirement_to_listings
        buyer_req = {
            "crop": "Onion",
            "quantity": 2000.0,
            "location": "Pune",
            "user_id": "usr_buyer_demo"
        }
        matches = await match_requirement_to_listings(buyer_req)
        matched_ids = [m["listing_id"] for m in matches]
        assert listing_id in matched_ids, f"Created listing {listing_id} not discovered in buyer matching! Found: {matched_ids}"
        match_item = next(m for m in matches if m["listing_id"] == listing_id)
        print(f"✅ 4. Buyer Matching Discovery: Found listing {listing_id} with score {match_item['compatibility_score']} (Grade: {match_item['match_grade']})")

        # 5. Farmer Edits Listing
        patch_payload = {
            "expected_price": 34.0,
            "min_price": 30.0,
            "quantity": 2800.0
        }
        patch_res = await client.patch(f"/api/v1/listings/{listing_id}", json=patch_payload, headers=headers)
        assert patch_res.status_code == 200, f"Patch listing failed: {patch_res.text}"
        print(f"✅ 5. Updated Listing {listing_id}: Expected Price ₹34/kg, Min Price ₹30/kg, Qty 2800 kg")

        # Re-verify PostgreSQL DBProduce
        async with AsyncSessionLocal() as session:
            updated_row = await session.get(DBProduce, listing_id)
            assert float(updated_row.expected_price) == 34.0
            assert float(updated_row.quantity) == 2800.0
            print(f"✅ 5b. Verified DB Updates: Expected Price = ₹{updated_row.expected_price}/kg, Qty = {updated_row.quantity} kg")

        # 6. RAG Ingestion & Query Verification for Farmer
        rag_res = await client.get("/api/v1/rag/query", params={
            "q": "onion cultivation and harvesting guidelines",
            "collection": "crop_knowledge",
            "crop": "Onion",
            "limit": 2
        })
        assert rag_res.status_code == 200, f"RAG query failed: {rag_res.text}"
        rag_data = rag_res.json()
        assert len(rag_data["data"]) > 0, "No RAG documents returned for crop_knowledge Onion!"
        print(f"✅ 6. RAG Vector Retrieval: Retrieved {len(rag_data['data'])} real documents from crop_knowledge collection")
        for idx, doc in enumerate(rag_data["data"]):
            src = doc.get("metadata", {}).get("source", "ICAR")
            print(f"   [{idx+1}] Source: {src} | Preview: {doc.get('document', '')[:90]}...")

        # 7. Farmer Profile Persistence
        profile_res = await client.get("/api/v1/profiles/me", headers=headers)
        assert profile_res.status_code == 200
        print(f"✅ 7. Farmer Profile Verified: {profile_res.json().get('name', 'Farmer')}")

        # 8. Withdraw / Delete Listing
        del_res = await client.delete(f"/api/v1/listings/{listing_id}", headers=headers)
        assert del_res.status_code == 200, f"Delete listing failed: {del_res.text}"
        print(f"✅ 8. Withdrew/Deleted Listing {listing_id}")

        # 9. Verify Excluded from Future Buyer Matching
        matches_after_del = await match_requirement_to_listings(buyer_req)
        matched_after_ids = [m["listing_id"] for m in matches_after_del]
        assert listing_id not in matched_after_ids, f"Withdrawn listing {listing_id} still appears in buyer matching!"
        print(f"✅ 9. Verified Isolation: Withdrawn listing {listing_id} is cleanly excluded from Buyer Matching Engine")

    print("=" * 60)
    print("ALL 9 E2E FARMER AGENT AUDIT CHECKS PASSED WITH FULL PERSISTENCE & RAG VERIFICATION")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_e2e_farmer_audit())
