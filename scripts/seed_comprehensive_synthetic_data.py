"""
Robust, Repeatable, Idempotent PostgreSQL Database Seeder for FarmGenAI Buyer Agent.
Loads and upserts all synthetic datasets:
  - 119+ Farmers across 20 Maharashtra districts
  - 40 Warehouses (ambient + cold chain)
  - 24 Industrial Processors (milling, crushing, solvent, ginning, dehydration)
  - 40 Transport Vehicles across 6 vehicle classes
  - 249+ Produce Listings (all 7 crops, all grades A+/A/B/C, small/medium/bulk quantities)
  - 80+ Buyer Requirements (normal, tight budget, bulk, small-batch, perishable, edge cases)
  - 20 Negotiation Histories & Deals (accepted, counter, rejected, failed)

Idempotent: Upserts without duplicate errors. Preserves all authentic data!
"""

import sys
import json
import os
import asyncio
from datetime import datetime, timezone

sys.path.insert(0, ".")

from database.db import (
    AsyncSessionLocal,
    DBUser,
    DBFarmer,
    DBBuyer,
    DBProduce,
    DBWarehouse,
    DBProcessor,
    DBTransportProvider,
    DBTransporter,
)
from backend.core.security import hash_password
from sqlalchemy import select, text

SYNTHETIC_DIR = os.path.join("backend", "dataset", "synthetic")

def load_json(filename: str):
    path = os.path.join(SYNTHETIC_DIR, filename)
    if not os.path.exists(path):
        print(f"Warning: File not found: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

async def seed_all():
    print("=================================================================")
    print("SEEDING LARGE-SCALE SYNTHETIC BUYER DATASET INTO POSTGRESQL")
    print("=================================================================")
    
    async with AsyncSessionLocal() as session:
        # -------------------------------------------------------------
        # 1. Seed Farmers & Farmer Users
        # -------------------------------------------------------------
        farmers_json = load_json("synthetic_farmers.json")
        farmer_count = 0
        for f in farmers_json:
            fid = f.get("id") or f.get("user_id")
            fname = f.get("name", "Farmer")
            fphone = f.get("phone", "+91-9800000000")
            fvillage = f.get("village", "Mandi")
            ftaluka = f.get("taluka", fvillage)
            fdist = f.get("district", "Pune")
            flat = f.get("lat") or f.get("latitude", 18.5)
            flon = f.get("lon") or f.get("longitude", 73.8)
            facres = f.get("acres") or f.get("land_acres", 10.0)
            ftype = f.get("type") or f.get("farming_practice", "Conventional APMC")
            fcrop = f.get("crop") or (f.get("crops_grown", ["Soybean"])[0] if f.get("crops_grown") else "Soybean")
            
            # User record for authentication
            u_res = await session.execute(select(DBUser).where(DBUser.user_id == fid))
            user = u_res.scalars().first()
            if not user:
                user = DBUser(
                    user_id=fid,
                    name=fname,
                    email=f.get("email", f"{fid}@farmgenai.synthetic"),
                    password=hash_password("password123"),
                    location=f.get("location", f"{fvillage}, {fdist}, Maharashtra"),
                    language="Marathi",
                    role="farmer",
                    verification_status="VERIFIED",
                    trust_score=round(f.get("rating", 4.8), 2),
                    preferences=json.dumps({"is_synthetic": True, "farm_acres": facres, "primary_crop": fcrop})
                )
                session.add(user)
            
            # Farmer record
            farm_res = await session.execute(select(DBFarmer).where(DBFarmer.id == fid))
            farmer = farm_res.scalars().first()
            if farmer:
                farmer.name = fname
                farmer.contact_number = fphone
                farmer.village = fvillage
                farmer.taluka = ftaluka
                farmer.district = fdist
                farmer.latitude = flat
                farmer.longitude = flon
                farmer.farm_size_acres = facres
                farmer.farming_type = ftype
            else:
                farmer = DBFarmer(
                    id=fid,
                    name=fname,
                    contact_number=fphone,
                    location=f.get("location", f"{fvillage}, {fdist}, Maharashtra"),
                    village=fvillage,
                    taluka=ftaluka,
                    district=fdist,
                    state="Maharashtra",
                    latitude=flat,
                    longitude=flon,
                    language="Marathi",
                    farm_size_acres=facres,
                    farming_type=ftype,
                    preferences={"is_synthetic": True, "crop": fcrop},
                    created_at=datetime.now(timezone.utc).isoformat()
                )
                session.add(farmer)
            farmer_count += 1
        print(f"✔ Upserted {farmer_count} Synthetic Farmers & Farmer Users.")

        # -------------------------------------------------------------
        # 2. Seed Warehouses
        # -------------------------------------------------------------
        warehouses_json = load_json("synthetic_warehouses.json")
        wh_count = 0
        for w in warehouses_json:
            wid = w.get("warehouse_id") or w.get("id")
            wname = w.get("name", "Warehouse")
            wdist = w.get("district", "Pune")
            wloc = w.get("location", f"{wdist}, Maharashtra")
            is_cold = w.get("cold_storage", w.get("refrigerated", False))
            wh_type = "Cold Storage" if is_cold else "Dry Grain Silo"
            cap_mt = w.get("capacity_mt") or (w.get("capacity_kg", 25000000.0) / 1000.0)
            avail_mt = w.get("available_mt") or (w.get("available_capacity_kg", 10000000.0) / 1000.0)
            rate_day = w.get("rate") or (w.get("base_cost_per_kg_per_day", 0.08) * 1000.0)
            
            w_res = await session.execute(select(DBWarehouse).where(DBWarehouse.warehouse_id == wid))
            wh = w_res.scalars().first()
            if wh:
                wh.name = wname
                wh.location = wloc
                wh.district = wdist
                wh.type = wh_type
                wh.capacity_mt = cap_mt
                wh.available_capacity_mt = avail_mt
                wh.price_per_mt_per_day = round(rate_day / 30.0, 2)
            else:
                wh = DBWarehouse(
                    warehouse_id=wid,
                    name=wname,
                    location=wloc,
                    district=wdist,
                    type=wh_type,
                    capacity_mt=cap_mt,
                    available_capacity_mt=avail_mt,
                    price_per_mt_per_day=round(rate_day / 30.0, 2),
                    rating=w.get("rating", 4.8),
                    contact_number=w.get("contact_number", "+91-9822100301")
                )
                session.add(wh)
            wh_count += 1
        print(f"✔ Upserted {wh_count} Synthetic Warehouses.")

        # -------------------------------------------------------------
        # 3. Seed Processors
        # -------------------------------------------------------------
        processors_json = load_json("synthetic_processors.json")
        proc_count = 0
        for p in processors_json:
            pid = p.get("processor_id") or p.get("id")
            pname = p.get("name") or p.get("company_name", "Processor")
            pdist = p.get("district", "Pune")
            crops_raw = p.get("crop_types") or p.get("crop_accepted") or p.get("crop", ["Soybean"])
            if isinstance(crops_raw, list):
                crops_str = ", ".join(crops_raw)
            else:
                crops_str = str(crops_raw)
            cap_mt = p.get("capacity_mt") or (p.get("capacity_kg_per_day", 50000.0) / 1000.0)
            price_kg = p.get("cost_per_kg") or (p.get("fee", 20.0) / 10.0)
            
            p_res = await session.execute(select(DBProcessor).where(DBProcessor.processor_id == pid))
            proc = p_res.scalars().first()
            if proc:
                proc.company_name = pname
                proc.crop_accepted = crops_str
                proc.capacity_mt = cap_mt
                proc.purchase_price_per_kg = price_kg
                proc.district = pdist
            else:
                proc = DBProcessor(
                    processor_id=pid,
                    company_name=pname,
                    crop_accepted=crops_str,
                    capacity_mt=cap_mt,
                    purchase_price_per_kg=price_kg,
                    district=pdist
                )
                session.add(proc)
            proc_count += 1
        print(f"✔ Upserted {proc_count} Synthetic Processors.")

        # -------------------------------------------------------------
        # 4. Seed Transport Vehicles & Transporters Table
        # -------------------------------------------------------------
        vehicles_json = load_json("synthetic_vehicles.json")
        veh_count = 0
        for v in vehicles_json:
            vid = v.get("vehicle_id") or v.get("id")
            tid = v.get("transporter_id") or v.get("tp", "synth_trans_default")
            vname = v.get("vehicle_name") or v.get("name", "Truck")
            vtype = v.get("vehicle_type") or v.get("type", "Medium Truck")
            cap = float(v.get("capacity_kg") or v.get("cap", 5000.0))
            fuel = v.get("fuel_type") or v.get("fuel", "Diesel")
            kmpl = float(v.get("fuel_efficiency_kmpl") or v.get("kmpl", 10.0))
            loc = v.get("current_location") or v.get("loc", "Pune, Maharashtra")
            lat = float(v.get("current_latitude") or v.get("lat", 18.5))
            lon = float(v.get("current_longitude") or v.get("lon", 73.8))
            reefer = bool(v.get("refrigerated") or v.get("reefer", False))
            tmin = float(v.get("temperature_min_c") or (-18.0 if reefer else 15.0))
            tmax = float(v.get("temperature_max_c") or (8.0 if reefer else 40.0))
            rating = float(v.get("rating", 4.8))
            rate_km = float(v.get("rate", 22.0))

            # 1. Upsert into vehicles table via raw SQL
            await session.execute(text("""
                INSERT INTO vehicles (
                    vehicle_id, transporter_id, vehicle_type, vehicle_name, capacity_kg,
                    fuel_type, fuel_efficiency_kmpl, current_location, current_latitude, current_longitude,
                    refrigerated, temperature_min_c, temperature_max_c, status, rating, contact_number
                ) VALUES (
                    :vid, :tid, :vtype, :vname, :cap,
                    :fuel, :kmpl, :loc, :lat, :lon,
                    :refrig, :tmin, :tmax, 'AVAILABLE', :rating, '+91-9822100401'
                ) ON CONFLICT (vehicle_id) DO UPDATE SET
                    current_location = EXCLUDED.current_location,
                    capacity_kg = EXCLUDED.capacity_kg,
                    status = EXCLUDED.status,
                    rating = EXCLUDED.rating;
            """), {
                "vid": vid, "tid": tid, "vtype": vtype, "vname": vname, "cap": cap,
                "fuel": fuel, "kmpl": kmpl, "loc": loc, "lat": lat, "lon": lon,
                "refrig": reefer, "tmin": tmin, "tmax": tmax,
                "rating": rating
            })
            
            # 2. Also mirror into transporters table
            t_res = await session.execute(select(DBTransporter).where(DBTransporter.transporter_id == vid))
            transporter = t_res.scalars().first()
            if transporter:
                transporter.provider_name = vname
                transporter.rate_per_km = rate_km
                transporter.current_location = loc
            else:
                transporter = DBTransporter(
                    transporter_id=vid,
                    provider_name=vname,
                    vehicle_type=vtype,
                    capacity_mt=round(cap / 1000.0, 1),
                    rate_per_km=rate_km,
                    base_fare=rate_km * 5.0,
                    rating=rating,
                    contact_number="+91-9822100401",
                    current_location=loc
                )
                session.add(transporter)
            veh_count += 1
        print(f"✔ Upserted {veh_count} Synthetic Vehicles across 6 vehicle classes.")

        # -------------------------------------------------------------
        # 5. Seed Produce Listings (All 7 Crops & Multi-Tier Grid)
        # -------------------------------------------------------------
        listings_json = load_json("synthetic_produce_listings.json")
        list_count = 0
        for l in listings_json:
            lid = l.get("id")
            l_res = await session.execute(select(DBProduce).where(DBProduce.id == lid))
            listing = l_res.scalars().first()
            
            qinfo = l.get("quality_info") or {"grade": l.get("grade", "A")}
            lat = float(l.get("latitude") or l.get("lat", 18.5))
            lon = float(l.get("longitude") or l.get("lon", 73.8))
            desc = l.get("description") or l.get("desc", f"Quality {l.get('crop')}")
            min_sale = float(l.get("min_sale_quantity") or l.get("min_sale_qty", 100.0))
            
            if listing:
                listing.quantity = float(l.get("quantity", 1000.0))
                listing.expected_price = float(l.get("expected_price", 50.0))
                listing.min_price = float(l.get("min_price", 45.0))
                listing.status = l.get("status", "ACTIVE")
                listing.quality_info = qinfo
                listing.location = l.get("location", "APMC Mandi")
            else:
                listing = DBProduce(
                    id=lid,
                    user_id=l.get("user_id"),
                    farmer_name=l.get("farmer_name"),
                    crop=l.get("crop"),
                    crop_category=l.get("crop_category", "Field Crops"),
                    variety=l.get("variety", "Standard"),
                    grade=l.get("grade", "A"),
                    quantity=float(l.get("quantity", 1000.0)),
                    unit="kg",
                    min_sale_quantity=min_sale,
                    expected_price=float(l.get("expected_price", 50.0)),
                    min_price=float(l.get("min_price", 45.0)),
                    price_unit="per_kg",
                    quality_info=qinfo,
                    harvest_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    shelf_life=int(l.get("shelf_life", 180)),
                    location=l.get("location", "APMC Mandi"),
                    latitude=lat,
                    longitude=lon,
                    description=desc,
                    status=l.get("status", "ACTIVE"),
                    created_at=datetime.now(timezone.utc).isoformat()
                )
                session.add(listing)
            list_count += 1
        print(f"✔ Upserted {list_count} Synthetic Produce Listings across all 7 crops & 20 districts.")

        # -------------------------------------------------------------
        # 6. Seed Buyer Requirements (All 7 Crops & Permutations)
        # -------------------------------------------------------------
        reqs_json = load_json("synthetic_buyer_requirements.json")
        req_count = 0
        for r in reqs_json:
            rid = r.get("id") or r.get("requirement_id")
            r_res = await session.execute(select(DBBuyer).where(DBBuyer.id == rid))
            req = r_res.scalars().first()
            if req:
                req.quantity = float(r.get("quantity", 1000.0))
                req.min_price = float(r.get("target_price", 50.0))
                req.max_price = float(r.get("max_price", 55.0))
                req.location = r.get("location", "Pune APMC")
                req.urgency = r.get("urgency", "MEDIUM")
            else:
                req = DBBuyer(
                    id=rid,
                    user_id=r.get("user_id", "usr_buyer_demo"),
                    buyer_name=r.get("buyer_name", "Agro Commodities Buyer"),
                    crop=r.get("crop"),
                    min_price=float(r.get("target_price", 50.0)),
                    max_price=float(r.get("max_price", 55.0)),
                    quantity=float(r.get("quantity", 1000.0)),
                    location=r.get("location", "Pune APMC"),
                    urgency=r.get("urgency", "MEDIUM"),
                    neg_mode="AGGRESSIVE" if r.get("urgency") == "HIGH" else "BALANCED",
                    strategy=r.get("strategy", "Balanced Mandi Procurement"),
                    status="ACTIVE"
                )
                session.add(req)
            req_count += 1
        print(f"✔ Upserted {req_count} Synthetic Buyer Requirements across all crops and districts.")

        # -------------------------------------------------------------
        # 7. Seed Negotiation Histories & Outcomes (via raw SQL)
        # -------------------------------------------------------------
        negs_json = load_json("synthetic_negotiations.json")
        neg_count = 0
        for n in negs_json:
            nid = n.get("negotiation_id") or n.get("id")
            crop = n.get("crop", "Soybean")
            qty = float(n.get("quantity", 1000.0))
            fid = n.get("farmer_id", "synth_farm_pune_001")
            fname = n.get("farmer_name", "Farmer")
            bid = n.get("buyer_id", "usr_buyer_demo")
            status = n.get("status", "ACCEPTED")
            rnd = int(n.get("round_number", n.get("current_round", 3)))
            fprice = float(n.get("current_price", n.get("final_price", 50.0)))
            mprice = float(n.get("farmer_price", n.get("market_price", 52.0)))
            minp = float(n.get("buyer_price", n.get("min_price", 48.0)))
            summary = n.get("summary", f"Procurement deal for {qty} kg {crop} ({status})")
            tplan = n.get("transport_plan", f"Direct logistics dispatch in {crop} corridor")
            logs = json.dumps(n.get("history", n.get("logs", [])))

            await session.execute(text("""
                INSERT INTO negotiations (
                    negotiation_id, crop, quantity, farmer_id, farmer_name, buyer_id, user_id,
                    status, current_round, final_price, market_price, min_price, summary, transport_plan, logs
                ) VALUES (
                    :nid, :crop, :qty, :fid, :fname, :bid, 'usr_buyer_demo',
                    :status, :rnd, :fprice, :mprice, :minp, :summary, :tplan, :logs
                ) ON CONFLICT (negotiation_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    final_price = EXCLUDED.final_price,
                    summary = EXCLUDED.summary;
            """), {
                "nid": nid, "crop": crop, "qty": qty, "fid": fid, "fname": fname, "bid": bid,
                "status": status, "rnd": rnd, "fprice": fprice, "mprice": mprice, "minp": minp,
                "summary": summary, "tplan": tplan, "logs": logs
            })
            neg_count += 1
        print(f"✔ Upserted {neg_count} Synthetic Negotiation Logs & Deals.")

        await session.commit()

    print("=================================================================")
    print("SUCCESS: ALL LARGE-SCALE SYNTHETIC DATASETS SEEDED IN POSTGRESQL!")
    print("=================================================================")

if __name__ == "__main__":
    asyncio.run(seed_all())
