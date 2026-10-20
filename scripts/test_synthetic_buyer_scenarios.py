"""
Comprehensive Test Suite for FarmGenAI Buyer Agent Synthetic Scenarios.
Tests matching, recommendation, validation, and diversity across all 7 canonical crops.
"""

import sys
import json
import asyncio
import httpx

API_BASE = "http://localhost:8000"

async def run_tests():
    print("=================================================================")
    print("RUNNING FARMGENAI BUYER AGENT SYNTHETIC SCENARIO TEST SUITE")
    print("=================================================================")
    
    test_results = []
    
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0) as client:
        # 0. Healthcheck
        h_resp = await client.get("/health")
        assert h_resp.status_code == 200, f"Healthcheck failed: {h_resp.text}"
        print("✔ System Healthcheck OK:", h_resp.json())

        # 0.1 Login to get JWT Token
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "buyer@agrinegotiator.com", "password": "password123"}
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✔ Buyer Authentication OK: JWT session established.")

        # -------------------------------------------------------------
        # TEST 1-7: All 7 Canonical Crops Normal Match Scenarios
        # -------------------------------------------------------------
        crops_test_data = [
            {"crop": "Soybean", "quantity": 3000.0, "target_price": 52.0, "max_price": 56.0, "location": "Pune", "expected_farmer": "Tukaram Shinde"},
            {"crop": "Cotton", "quantity": 4000.0, "target_price": 72.0, "max_price": 76.0, "location": "Amravati", "expected_farmer": "Arjunrao Kale"},
            {"crop": "Onion", "quantity": 5000.0, "target_price": 23.0, "max_price": 26.0, "location": "Nashik", "expected_farmer": "Sita Deshmukh"},
            {"crop": "Sugarcane", "quantity": 35000.0, "target_price": 3.85, "max_price": 4.10, "location": "Kolhapur", "expected_farmer": "Meera Jagtap"},
            {"crop": "Jowar", "quantity": 3000.0, "target_price": 60.0, "max_price": 65.0, "location": "Solapur", "expected_farmer": "Sunita Shinde"},
            {"crop": "Bajra", "quantity": 3500.0, "target_price": 30.0, "max_price": 33.0, "location": "Ahmednagar", "expected_farmer": "Dnyaneshwar More"},
            {"crop": "Rice", "quantity": 4000.0, "target_price": 36.0, "max_price": 40.0, "location": "Pune", "expected_farmer": "Govind Joshi"},
        ]

        distinct_farmers_found = set()

        for idx, tdata in enumerate(crops_test_data, 1):
            req_payload = {
                "crop": tdata["crop"],
                "quantity": tdata["quantity"],
                "target_price": tdata["target_price"],
                "max_price": tdata["max_price"],
                "location": tdata["location"]
            }
            resp = await client.post("/api/v1/matching/requirement-to-listings", json=req_payload, headers=headers)
            assert resp.status_code == 200, f"Matching failed for {tdata['crop']}: {resp.text}"
            data = resp.json()
            matches = data.get("data", [])
            assert len(matches) > 0, f"Expected matching listings for {tdata['crop']}, got 0!"
            top_match = matches[0]
            top_farmer = top_match.get("farmer_name")
            distinct_farmers_found.add(top_farmer)
            score = top_match.get("compatibility_score", 0)
            
            print(f"✔ [Crop {idx}/7: {tdata['crop']:<10}] Found {len(matches)} candidates | Top: '{top_farmer}' | Score: {score}/100 | Ask: ₹{top_match.get('min_price')}/kg")
            test_results.append({
                "test": f"Canonical Crop Match: {tdata['crop']}",
                "status": "PASS",
                "top_farmer": top_farmer,
                "score": score,
                "candidates_count": len(matches)
            })

        # -------------------------------------------------------------
        # TEST 8: Dynamic Input Variation (Location Sensitivity)
        # -------------------------------------------------------------
        print("\n--- Testing Dynamic Input Variation: Location Shift ---")
        pune_rice_resp = await client.post("/api/v1/matching/requirement-to-listings", json={
            "crop": "Rice", "quantity": 3000.0, "target_price": 36.0, "max_price": 40.0, "location": "Pune"
        }, headers=headers)
        pune_top = pune_rice_resp.json()["data"][0]

        gondia_rice_resp = await client.post("/api/v1/matching/requirement-to-listings", json={
            "crop": "Rice", "quantity": 3000.0, "target_price": 36.0, "max_price": 40.0, "location": "Gondia"
        }, headers=headers)
        gondia_top = gondia_rice_resp.json()["data"][0]

        print(f"  When buyer location = 'Pune':   Top Match = '{pune_top['farmer_name']}' (Distance: {pune_top['distance_km']} km | Score: {pune_top['compatibility_score']})")
        print(f"  When buyer location = 'Gondia': Top Match = '{gondia_top['farmer_name']}' (Distance: {gondia_top['distance_km']} km | Score: {gondia_top['compatibility_score']})")
        assert pune_top["farmer_name"] != gondia_top["farmer_name"], "Matching failed to shift top candidate based on buyer location proximity!"
        print("✔ Dynamic Proximity Shift Verified: Top candidate changed deterministically with buyer location.")
        test_results.append({"test": "Dynamic Proximity Sensitivity", "status": "PASS"})

        # -------------------------------------------------------------
        # TEST 9: Edge Case — Budget Exceeded / Sub-Market Bid
        # -------------------------------------------------------------
        print("\n--- Testing Edge Case: Budget Far Below Market Floor ---")
        normal_cotton_resp = await client.post("/api/v1/matching/requirement-to-listings", json={
            "crop": "Cotton", "quantity": 2000.0, "target_price": 72.0, "max_price": 76.0, "location": "Amravati"
        }, headers=headers)
        normal_score = normal_cotton_resp.json()["data"][0]["compatibility_score"]

        low_bid_resp = await client.post("/api/v1/matching/requirement-to-listings", json={
            "crop": "Cotton", "quantity": 2000.0, "target_price": 18.0, "max_price": 22.0, "location": "Amravati"
        }, headers=headers)
        low_bid_data = low_bid_resp.json()
        low_score = low_bid_data["data"][0]["compatibility_score"] if low_bid_data.get("data") else 0
        print(f"  Normal Cotton Bid (₹72) Match Score: {normal_score}/100")
        print(f"  Low Cotton Bid (₹18) Match Score:    {low_score}/100")
        assert low_score < normal_score, "Score did not penalize sub-market bid!"
        print("✔ Budget Disconnect Handled: Unrealistic sub-market bids penalized in 8-factor NRV model.")
        test_results.append({"test": "Sub-Market Budget Disconnect", "status": "PASS"})

        # -------------------------------------------------------------
        # TEST 10: Edge Case — Insufficient Market Stock
        # -------------------------------------------------------------
        print("\n--- Testing Edge Case: Excessive Quantity (Insufficient Stock) ---")
        normal_jowar_resp = await client.post("/api/v1/matching/requirement-to-listings", json={
            "crop": "Jowar", "quantity": 3000.0, "target_price": 60.0, "max_price": 65.0, "location": "Solapur"
        }, headers=headers)
        norm_jowar_score = normal_jowar_resp.json()["data"][0]["compatibility_score"]

        huge_qty_resp = await client.post("/api/v1/matching/requirement-to-listings", json={
            "crop": "Jowar", "quantity": 95000.0, "target_price": 60.0, "max_price": 65.0, "location": "Solapur"
        }, headers=headers)
        huge_score = huge_qty_resp.json()["data"][0]["compatibility_score"] if huge_qty_resp.json().get("data") else 0
        print(f"  Standard Jowar Demand (3,000 kg) Match Score:  {norm_jowar_score}/100")
        print(f"  Excessive Jowar Demand (95,000 kg) Match Score: {huge_score}/100")
        assert huge_score < norm_jowar_score, "Excessive quantity did not lower compatibility score!"
        print("✔ Insufficient Stock Handled: Stock deficit accurately penalized.")
        test_results.append({"test": "Insufficient Stock Degradation", "status": "PASS"})

        # -------------------------------------------------------------
        # TEST 11: Edge Case — Expired Listings Filtered
        # -------------------------------------------------------------
        print("\n--- Testing Edge Case: Expired Listings Filtering ---")
        soy_matches = (await client.post("/api/v1/matching/requirement-to-listings", json={
            "crop": "Soybean", "quantity": 1000.0, "target_price": 45.0, "max_price": 50.0, "location": "Latur"
        }, headers=headers)).json()["data"]
        matched_ids = [m.get("id") or m.get("listing_id") for m in soy_matches]
        assert "synth_prod_soybean_05_expired" not in matched_ids, "Expired listing was incorrectly included in active matching pool!"
        print("✔ Expired Listing Filtering OK: 'synth_prod_soybean_05_expired' correctly excluded.")
        test_results.append({"test": "Expired Listing Discarding", "status": "PASS"})

        # -------------------------------------------------------------
        # TEST 12: Invalid Input Validation (Non-Maharashtra Location)
        # -------------------------------------------------------------
        print("\n--- Testing Input Validation: Outside Operational Area ---")
        invalid_loc_resp = await client.post("/api/v1/requirements", json={
            "crop": "Soybean", "quantity": 1000.0, "target_price": 50.0, "max_price": 55.0, "location": "London, UK"
        }, headers=headers)
        assert invalid_loc_resp.status_code == 422, f"Expected 422 for non-Maharashtra location, got: {invalid_loc_resp.status_code}"
        print("✔ Invalid Operational Location Rejected (HTTP 422):", invalid_loc_resp.json()["detail"][0]["msg"])
        test_results.append({"test": "Out-of-Area Validation", "status": "PASS"})

        # -------------------------------------------------------------
        # TEST 13: Invalid Input Validation (Negative Quantity)
        # -------------------------------------------------------------
        print("\n--- Testing Input Validation: Non-Positive Quantity ---")
        neg_qty_resp = await client.post("/api/v1/requirements", json={
            "crop": "Soybean", "quantity": -500.0, "target_price": 50.0, "max_price": 55.0, "location": "Pune"
        }, headers=headers)
        assert neg_qty_resp.status_code == 422, f"Expected 422 for negative quantity, got: {neg_qty_resp.status_code}"
        print("✔ Negative Quantity Rejected (HTTP 422):", neg_qty_resp.json()["detail"][0]["msg"])
        test_results.append({"test": "Negative Quantity Validation", "status": "PASS"})

        # -------------------------------------------------------------
        # TEST 14: Diversity Audit (Supplier Monotony Check)
        # -------------------------------------------------------------
        print("\n--- Testing Supplier Diversity (No Hardcoded Suresh Deshmukh Monotony) ---")
        print(f"  Distinct farmers returned across crop tests: {len(distinct_farmers_found)}")
        for f in distinct_farmers_found:
            print(f"    - {f}")
        assert len(distinct_farmers_found) >= 5, f"Expected at least 5 distinct farmers, got {len(distinct_farmers_found)}"
        print("✔ Supplier Diversity Confirmed: Unique realistic farmers across diverse Maharashtra districts.")
        test_results.append({"test": "Supplier Diversity Guarantee", "status": "PASS", "unique_farmers": len(distinct_farmers_found)})

    print("\n=================================================================")
    print("ALL 14 COMPREHENSIVE BUYER SCENARIO TESTS PASSED SUCCESSFULLY!")
    print("=================================================================")
    return test_results

if __name__ == "__main__":
    results = asyncio.run(run_tests())
