import os
import json
import asyncio
from datetime import datetime, timezone
from backend.db.session import AsyncSessionLocal
from sqlalchemy import text
from backend.repositories.database_repo import Database

UNIQUE_NEGOTIATIONS = [
    {
        "negotiation_id": "neg_soybean_latur_01",
        "crop": "Soybean",
        "quantity": 2500.0,
        "farmer_name": "Balasaheb Patil (Latur)",
        "buyer_name": "AgroCorp Pune Enterprise",
        "status": "DEAL",
        "final_price": 52.5,
        "market_price": 54.0,
        "min_price": 49.0,
        "location": "Latur APMC, Maharashtra",
        "district": "Latur",
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "summary": "Agreed 2,500kg Soybean at Rs.52.50/kg with Balasaheb Patil (Latur).",
        "transport_plan": {
            "vehicle_name": "Mahindra Bolero Maxi Truck",
            "vehicle_type": "LCV",
            "cost": 7680,
            "agreed_freight": 7680,
            "distance": 320,
            "distance_km": 320,
            "origin": "Latur APMC, Maharashtra",
            "destination": "Pune Hadapsar Logistics Hub"
        }
    },
    {
        "negotiation_id": "neg_cotton_akola_02",
        "crop": "Cotton",
        "quantity": 5000.0,
        "farmer_name": "Gajanan Deshmukh (Akola)",
        "buyer_name": "Vidarbha Textile Spinners",
        "status": "DEAL",
        "final_price": 71.8,
        "market_price": 73.5,
        "min_price": 68.0,
        "location": "Akola APMC, Maharashtra",
        "district": "Akola",
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "summary": "Agreed 5,000kg Cotton (Kapas) at Rs.71.80/kg with Gajanan Deshmukh.",
        "transport_plan": {
            "vehicle_name": "Eicher Pro 2059",
            "vehicle_type": "Medium Truck",
            "cost": 9000,
            "agreed_freight": 9000,
            "distance": 250,
            "distance_km": 250,
            "origin": "Akola APMC, Maharashtra",
            "destination": "Nagpur Textile Cluster"
        }
    },
    {
        "negotiation_id": "neg_onion_lasalgaon_03",
        "crop": "Onion",
        "quantity": 4000.0,
        "farmer_name": "Sambhaji Shinde (Lasalgaon)",
        "buyer_name": "Metro Fresh Produce Mumbai",
        "status": "DEAL",
        "final_price": 25.8,
        "market_price": 27.0,
        "min_price": 23.0,
        "location": "Lasalgaon APMC, Nashik",
        "district": "Nashik",
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "summary": "Agreed 4,000kg Onion at Rs.25.80/kg with Sambhaji Shinde (Lasalgaon).",
        "transport_plan": {
            "vehicle_name": "Kisan ColdChain Reefer 4MT",
            "vehicle_type": "Refrigerated Truck",
            "cost": 6880,
            "agreed_freight": 6880,
            "distance": 215,
            "distance_km": 215,
            "origin": "Lasalgaon APMC, Nashik",
            "destination": "Vashi APMC Navi Mumbai"
        }
    },
    {
        "negotiation_id": "neg_jowar_solapur_04",
        "crop": "Jowar",
        "quantity": 3500.0,
        "farmer_name": "Basavaraj Birajdar (Solapur)",
        "buyer_name": "Sahyadri Flour Mills",
        "status": "DEAL",
        "final_price": 34.2,
        "market_price": 35.5,
        "min_price": 32.0,
        "location": "Solapur APMC, Maharashtra",
        "district": "Solapur",
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "summary": "Agreed 3,500kg Jowar (Maldandi) at Rs.34.20/kg with Basavaraj Birajdar.",
        "transport_plan": {
            "vehicle_name": "Mahindra Bolero Maxi Truck",
            "vehicle_type": "LCV",
            "cost": 5880,
            "agreed_freight": 5880,
            "distance": 245,
            "distance_km": 245,
            "origin": "Solapur APMC, Maharashtra",
            "destination": "Pune Agro Industrial Complex"
        }
    },
    {
        "negotiation_id": "neg_bajra_ahmednagar_05",
        "crop": "Bajra",
        "quantity": 2000.0,
        "farmer_name": "Gorakhnath Jagtap (Ahmednagar)",
        "buyer_name": "Marathwada Feed & Grain Corp",
        "status": "ACCEPTED",
        "final_price": 26.5,
        "market_price": 28.0,
        "min_price": 25.0,
        "location": "Ahmednagar APMC, Maharashtra",
        "district": "Ahmednagar",
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "summary": "Accepted 2,000kg Bajra at Rs.26.50/kg with Gorakhnath Jagtap.",
        "transport_plan": {
            "vehicle_name": "Tata Ace Gold",
            "vehicle_type": "Mini Truck",
            "cost": 1840,
            "agreed_freight": 1840,
            "distance": 115,
            "distance_km": 115,
            "origin": "Ahmednagar APMC, Maharashtra",
            "destination": "Chhatrapati Sambhajinagar"
        }
    },
    {
        "negotiation_id": "neg_rice_gondia_06",
        "crop": "Rice",
        "quantity": 4500.0,
        "farmer_name": "Dhananjay Bisen (Gondia)",
        "buyer_name": "Nagpur Kolam Rice Merchants",
        "status": "DEAL",
        "final_price": 23.8,
        "market_price": 25.0,
        "min_price": 22.0,
        "location": "Gondia APMC, Maharashtra",
        "district": "Gondia",
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "summary": "Agreed 4,500kg Rice (Kolam) at Rs.23.80/kg with Dhananjay Bisen.",
        "transport_plan": {
            "vehicle_name": "Eicher Pro 2059",
            "vehicle_type": "Medium Truck",
            "cost": 5760,
            "agreed_freight": 5760,
            "distance": 160,
            "distance_km": 160,
            "origin": "Gondia APMC, Maharashtra",
            "destination": "Nagpur Central Food Hub"
        }
    },
    {
        "negotiation_id": "neg_sugarcane_kolhapur_07",
        "crop": "Sugarcane",
        "quantity": 25000.0,
        "farmer_name": "Tanaji Yadav (Kolhapur)",
        "buyer_name": "Baramati Agro Industries",
        "status": "DEAL",
        "final_price": 3.65,
        "market_price": 3.8,
        "min_price": 3.4,
        "location": "Kolhapur Agro Cluster",
        "district": "Kolhapur",
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "summary": "Agreed 25,000kg Sugarcane at Rs.3.65/kg with Tanaji Yadav.",
        "transport_plan": {
            "vehicle_name": "BharatBenz 2823C Multi-Axle",
            "vehicle_type": "Heavy Commercial Vehicle",
            "cost": 10140,
            "agreed_freight": 10140,
            "distance": 195,
            "distance_km": 195,
            "origin": "Kolhapur Sugar Belt",
            "destination": "Baramati Agro Processing"
        }
    },
    {
        "negotiation_id": "neg_wheat_dhule_08",
        "crop": "Wheat",
        "quantity": 2800.0,
        "farmer_name": "Pandharinath Patil (Dhule)",
        "buyer_name": "Khandesh Flour Mills",
        "status": "IN_PROGRESS",
        "final_price": 31.5,
        "market_price": 33.0,
        "min_price": 29.5,
        "location": "Dhule APMC, Maharashtra",
        "district": "Dhule",
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "summary": "Negotiating 2,800kg Wheat (Sharbati) at Rs.31.50/kg with Pandharinath Patil.",
        "transport_plan": {
            "vehicle_name": "Mahindra Bolero Maxi Truck",
            "vehicle_type": "LCV",
            "cost": 8160,
            "agreed_freight": 8160,
            "distance": 340,
            "distance_km": 340,
            "origin": "Dhule APMC, Maharashtra",
            "destination": "Pune Processing Plant"
        }
    },
    {
        "negotiation_id": "neg_tur_nanded_09",
        "crop": "Tur",
        "quantity": 1200.0,
        "farmer_name": "Maruti Kadam (Nanded)",
        "buyer_name": "Latur Dal Processors Union",
        "status": "ACCEPTED",
        "final_price": 78.0,
        "market_price": 82.0,
        "min_price": 74.0,
        "location": "Nanded APMC, Maharashtra",
        "district": "Nanded",
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "summary": "Accepted 1,200kg Tur Dal at Rs.78.00/kg with Maruti Kadam.",
        "transport_plan": {
            "vehicle_name": "Tata Ace Gold",
            "vehicle_type": "Mini Truck",
            "cost": 2080,
            "agreed_freight": 2080,
            "distance": 130,
            "distance_km": 130,
            "origin": "Nanded APMC, Maharashtra",
            "destination": "Latur Dal Mill Cluster"
        }
    },
    {
        "negotiation_id": "neg_tomato_jalgaon_10",
        "crop": "Tomato",
        "quantity": 2200.0,
        "farmer_name": "Anil Sonawane (Jalgaon)",
        "buyer_name": "Deccan Cold Chain Retail",
        "status": "DEAL",
        "final_price": 28.4,
        "market_price": 30.0,
        "min_price": 25.0,
        "location": "Jalgaon APMC, Maharashtra",
        "district": "Jalgaon",
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "summary": "Agreed 2,200kg Fresh Tomato at Rs.28.40/kg with Anil Sonawane (Jalgaon).",
        "transport_plan": {
            "vehicle_name": "Kisan ColdChain Reefer 4MT",
            "vehicle_type": "Refrigerated Truck",
            "cost": 11680,
            "agreed_freight": 11680,
            "distance": 365,
            "distance_km": 365,
            "origin": "Jalgaon APMC, Maharashtra",
            "destination": "Pune Hadapsar Cold Hub"
        }
    }
]

async def seed_unique_negotiations():
    print("Seeding 10 Unique Maharashtra Negotiations into PostgreSQL...")
    async with AsyncSessionLocal() as session:
        # First clean out the old duplicate soybean 180km records
        await session.execute(text("DELETE FROM negotiations WHERE negotiation_id LIKE 'neg_%' OR negotiation_id LIKE 'synth_neg_%'"))
        
        for item in UNIQUE_NEGOTIATIONS:
            tp_json = json.dumps(item["transport_plan"])
            created_time = datetime.now(timezone.utc).isoformat()
            
            await session.execute(text("""
                INSERT INTO negotiations (
                    negotiation_id, crop, quantity, farmer_name, buyer_name, user_id,
                    status, current_round, final_price, market_price, min_price,
                    summary, transport_plan, location, district, workflow_mode, created_at
                ) VALUES (
                    :nid, :crop, :qty, :fname, :bname, 'usr_buyer_demo',
                    :status, 3, :fprice, :mprice, :minp,
                    :summary, :tplan, :loc, :dist, :wf, :created
                ) ON CONFLICT (negotiation_id) DO UPDATE SET
                    crop = EXCLUDED.crop,
                    quantity = EXCLUDED.quantity,
                    farmer_name = EXCLUDED.farmer_name,
                    buyer_name = EXCLUDED.buyer_name,
                    status = EXCLUDED.status,
                    final_price = EXCLUDED.final_price,
                    market_price = EXCLUDED.market_price,
                    min_price = EXCLUDED.min_price,
                    summary = EXCLUDED.summary,
                    transport_plan = EXCLUDED.transport_plan,
                    location = EXCLUDED.location,
                    district = EXCLUDED.district,
                    workflow_mode = EXCLUDED.workflow_mode,
                    created_at = EXCLUDED.created_at;
            """), {
                "nid": item["negotiation_id"],
                "crop": item["crop"],
                "qty": item["quantity"],
                "fname": item["farmer_name"],
                "bname": item["buyer_name"],
                "status": item["status"],
                "fprice": item["final_price"],
                "mprice": item["market_price"],
                "minp": item["min_price"],
                "summary": item["summary"],
                "tplan": tp_json,
                "loc": item["location"],
                "dist": item["district"],
                "wf": item["workflow_mode"],
                "created": created_time
            })
            # Also update Database.negotiations in memory
            item_copy = dict(item)
            item_copy["id"] = item["negotiation_id"]
            Database.negotiations[item["negotiation_id"]] = item_copy

        await session.commit()
    print("✔ Successfully seeded 10 completely UNIQUE negotiations across all 7+ crops and unique distances (115km to 365km)!")

if __name__ == '__main__':
    asyncio.run(seed_unique_negotiations())
