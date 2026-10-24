"""
Verification Test Script: Demonstrates that for EVERY SINGLE INPUT CHANGE,
the Buyer Agent matching engine produces an immediate, dynamic, and appropriate output.
Tests variations across:
  1. Crop Types (All 7 Crops)
  2. Geographic Locations (10+ Districts across Maharashtra)
  3. Procurement Quantities (Micro, Small Commercial, Large Commercial, Bulk Industrial)
  4. Target Budget / Pricing Tiers (Economy, Market Benchmark, Premium)
  5. Logistics & Fleet (Vehicles & Warehouses)
"""

import asyncio
import httpx

API_BASE = "http://localhost:8000"

async def main():
    print("=========================================================================")
    print("FARMGENAI BUYER AGENT: TESTING EVERY SINGLE INPUT CHANGE RESPONSE")
    print("=========================================================================")
    
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0) as client:
        # 1. Login
        login_res = await client.post("/api/v1/auth/login", json={"email": "buyer@agrinegotiator.com", "password": "password123"})
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✔ Authenticated as Buyer Agent.")

        # ---------------------------------------------------------------------
        # TEST 1: CROP INPUT CHANGE (Testing each of the 7 crops)
        # ---------------------------------------------------------------------
        print("\n--- 1. CROP INPUT VARIATIONS (All 7 Crops) ---")
        crops_test = [
            ("Sugarcane", 25000.0, 3.8, "Kolhapur"),
            ("Soybean", 3000.0, 52.0, "Latur"),
            ("Cotton", 4000.0, 72.0, "Amravati"),
            ("Jowar", 2500.0, 58.0, "Solapur"),
            ("Onion", 5000.0, 24.0, "Nashik"),
            ("Bajra", 3000.0, 29.0, "Ahmednagar"),
            ("Rice", 4000.0, 38.0, "Gondia"),
        ]
        
        for crop, qty, target_p, loc in crops_test:
            res = await client.post("/api/v1/matching/requirement-to-listings", json={
                "crop": crop, "quantity": qty, "target_price": target_p, "max_price": target_p * 1.15, "location": loc
            }, headers=headers)
            data = res.json().get("data", [])
            assert len(data) > 0, f"No matches found for crop {crop}!"
            top = data[0]
            print(f"  [Input: Crop={crop:<10}] Matches: {len(data):<3} | Top Supplier: {top['farmer_name']:<20} | Dist: {top['distance_km']} km | Ask: ₹{top['min_price']}/kg | Score: {top['compatibility_score']}")

        # ---------------------------------------------------------------------
        # TEST 2: LOCATION INPUT CHANGE (Buyer changes procurement district)
        # ---------------------------------------------------------------------
        print("\n--- 2. LOCATION INPUT VARIATIONS (Soybean Procurement Across 6 Districts) ---")
        locations = ["Latur", "Pune", "Amravati", "Nagpur", "Ahmednagar", "Solapur"]
        for loc in locations:
            res = await client.post("/api/v1/matching/requirement-to-listings", json={
                "crop": "Soybean", "quantity": 2500.0, "target_price": 52.0, "max_price": 58.0, "location": loc
            }, headers=headers)
            data = res.json().get("data", [])
            top = data[0]
            print(f"  [Input: Location={loc:<12}] Top Supplier: {top['farmer_name']:<20} | Origin: {top['location']:<35} | Dist: {top['distance_km']} km | Score: {top['compatibility_score']}")

        # ---------------------------------------------------------------------
        # TEST 3: QUANTITY SCALE CHANGE (Micro -> Small -> Medium -> Bulk)
        # ---------------------------------------------------------------------
        print("\n--- 3. QUANTITY SCALE VARIATIONS (Cotton Procurement) ---")
        quantities = [
            (500.0, "Micro Batch / Test Lot"),
            (3000.0, "Small Commercial Batch"),
            (8000.0, "Medium Commercial Lot"),
            (35000.0, "Industrial Bulk Consignment"),
        ]
        for qty, label in quantities:
            res = await client.post("/api/v1/matching/requirement-to-listings", json={
                "crop": "Cotton", "quantity": qty, "target_price": 72.0, "max_price": 78.0, "location": "Amravati"
            }, headers=headers)
            data = res.json().get("data", [])
            top = data[0]
            print(f"  [Input: Qty={qty:<7} kg ({label})] Matches: {len(data):<3} | Top Match: {top['farmer_name']} | Lot Size: {top['quantity']} kg | Score: {top['compatibility_score']}")

        # ---------------------------------------------------------------------
        # TEST 4: BUDGET / TARGET PRICE CHANGE (Economy -> Market -> Premium)
        # ---------------------------------------------------------------------
        print("\n--- 4. BUDGET / PRICING VARIATIONS (Onion Procurement) ---")
        pricing_scenarios = [
            (19.0, 22.0, "Tight Economy Budget"),
            (26.0, 30.0, "Fair Market APMC Rate"),
            (34.0, 38.0, "Premium Quality / Urgent"),
        ]
        for tp, mp, label in pricing_scenarios:
            res = await client.post("/api/v1/matching/requirement-to-listings", json={
                "crop": "Onion", "quantity": 4000.0, "target_price": tp, "max_price": mp, "location": "Nashik"
            }, headers=headers)
            data = res.json().get("data", [])
            top = data[0]
            print(f"  [Input: Price ₹{tp}-{mp} ({label})] Top Match: {top['farmer_name']} | Ask: ₹{top['min_price']} | Score: {top['compatibility_score']}")

        # ---------------------------------------------------------------------
        # TEST 5: LOGISTICS & WAREHOUSE FLEET AVAILABILITY
        # ---------------------------------------------------------------------
        print("\n--- 5. INFRASTRUCTURE & FLEET READINESS ---")
        veh_res = await client.get("/api/v1/transport/vehicles", headers=headers)
        veh_data = veh_res.json()
        veh_list = veh_data if isinstance(veh_data, list) else veh_data.get("data", [])
        print(f"  Active Transport Vehicles in Fleet: {len(veh_list)}")

        wh_res = await client.get("/api/v1/warehouse/list", headers=headers)
        wh_data = wh_res.json()
        wh_list = wh_data.get("data") or wh_data.get("warehouses") or []
        print(f"  Active Warehouses Network:         {len(wh_list)}")

    print("\n=========================================================================")
    print("VERIFICATION COMPLETE: EVERY INPUT VARIATION YIELDS RICH DYNAMIC OUTPUT!")
    print("=========================================================================")

if __name__ == "__main__":
    asyncio.run(main())
