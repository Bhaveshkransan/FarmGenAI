import asyncio
from backend.services.matching_service import match_requirement_to_listings

async def main():
    req = {"crop": "Soybean", "quantity": 1000, "location": "Pune", "user_id": "usr_buyer_demo"}
    matches = await match_requirement_to_listings(req)
    print(f"Discovered listings for Soybean: {len(matches)}")
    for m in matches:
        print(f" - ID: {m['listing_id']}, Crop: {m['crop']}, Qty: {m['quantity']}, Score: {m['compatibility_score']}, Farmer: {m['farmer_name']}")

if __name__ == "__main__":
    asyncio.run(main())
