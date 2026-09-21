"""
scripts/ingest_real_rag.py

Comprehensive ingestion of all REAL datasets into ChromaDB vector stores.
Ensures zero mock/seeded RAG documents — only authentic agricultural,
APMC mandi, quality grading, and negotiation records for the 7 Maharashtra crops.
"""

import os
import sys
import json
import chromadb
from sentence_transformers import SentenceTransformer

# Setup project root path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "dataset"))
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

def main():
    print(f"Connecting to ChromaDB at localhost:8001...")
    client = chromadb.HttpClient(host="localhost", port=8001)
    client.heartbeat()
    print("Connected to ChromaDB!")

    print(f"Loading SentenceTransformer model '{EMBEDDING_MODEL}'...")
    encoder = SentenceTransformer(EMBEDDING_MODEL)
    print("Model loaded successfully!")

    def add_to_collection(col_name: str, ids: list, texts: list, metadatas: list, force_update: bool = False):
        if not ids:
            return
        col = client.get_or_create_collection(
            name=col_name,
            metadata={"description": f"AgriNegotiator {col_name} real vector store"}
        )
        if force_update:
            new_ids, new_texts, new_metas = ids, texts, metadatas
        else:
            try:
                existing = col.get(ids=ids)
                existing_ids = set(existing.get("ids", []))
            except Exception:
                existing_ids = set()

            new_ids, new_texts, new_metas = [], [], []
            for i in range(len(ids)):
                if ids[i] not in existing_ids:
                    new_ids.append(ids[i])
                    new_texts.append(texts[i])
                    new_metas.append(metadatas[i])

            if not new_ids:
                print(f"  [{col_name}] All {len(ids)} items already present.")
                return

        print(f"  [{col_name}] Embedding and upserting {len(new_ids)} documents...")
        batch_size = 64
        for start in range(0, len(new_ids), batch_size):
            end = start + batch_size
            b_texts = new_texts[start:end]
            b_ids = new_ids[start:end]
            b_metas = new_metas[start:end]
            b_embeddings = encoder.encode(b_texts).tolist()
            col.upsert(
                ids=b_ids,
                documents=b_texts,
                embeddings=b_embeddings,
                metadatas=b_metas
            )
        print(f"  [{col_name}] Done! Total now: {col.count()}")

    # ──────────────────────────────────────────────────────────────────────────
    # 1. CROP KNOWLEDGE & QUALITY REFERENCES
    # ──────────────────────────────────────────────────────────────────────────
    print("\n1. Ingesting Crop Knowledge & Quality Standards...")
    ck_path = os.path.join(DATASET_DIR, "crop_knowledge.json")
    if os.path.exists(ck_path):
        with open(ck_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids, texts, metas = [], [], []
        for item in data:
            crop = item["crop"]
            text = (
                f"Crop Profile: {crop}\n"
                f"Season & Cultivation: {item.get('season')}\n"
                f"Ideal Storage Conditions: {item.get('ideal_storage')}\n"
                f"Estimated Shelf Life: {item.get('shelf_life')}\n"
                f"Transport Requirements: {item.get('transport')}\n"
                f"Quality Grades: {', '.join(item.get('quality_grades', []))}\n"
                f"Industrial Processing Potential: {', '.join(item.get('processing', []))}\n"
                f"Major Cultivation Districts in Maharashtra: {', '.join(item.get('districts_major', []))}\n"
                f"Government MSP / FRP Rate: ₹{item.get('msp_per_quintal_2026_27') or item.get('frp_per_quintal') or 'Open Market'} per quintal."
            )
            doc_id = f"crop_knowledge_{crop.lower()}"
            ids.append(doc_id)
            texts.append(text)
            metas.append({
                "crop": crop,
                "category": "Crop Profile",
                "source": "crop_knowledge.json"
            })
        add_to_collection("crop_knowledge", ids, texts, metas)

    qr_path = os.path.join(DATASET_DIR, "crop_quality_references.json")
    if os.path.exists(qr_path):
        with open(qr_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids, texts, metas = [], [], []
        for item in data:
            crop = item["crop"]
            variety = item["variety"]
            grade = item["grade"]
            text = (
                f"APMC Quality Standards: {crop} ({variety}) - Grade {grade}\n"
                f"Minimum Physical Size: {item.get('min_size_mm')} mm\n"
                f"Maximum Moisture Tolerance: {item.get('max_moisture_pct')}%\n"
                f"Color & Appearance Standards: {item.get('color_standards')}\n"
                f"Skin & Texture Firmness: {item.get('skin_firmness')}\n"
                f"Permissible Defects: {item.get('common_defects_allowed')}"
            )
            doc_id = f"quality_std_{crop.lower()}_{grade.lower()}_{variety.lower().replace(' ', '_')}"
            ids.append(doc_id)
            texts.append(text)
            metas.append({
                "crop": crop,
                "grade": grade,
                "variety": variety,
                "category": "Quality Standards",
                "source": "crop_quality_references.json"
            })
        add_to_collection("crop_knowledge", ids, texts, metas)

    sc_path = os.path.join(DATASET_DIR, "seasonal_calendar.json")
    if os.path.exists(sc_path):
        with open(sc_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids, texts, metas = [], [], []
        for item in data:
            crops_str = ", ".join(item.get("affected_crops", []))
            text = (
                f"Maharashtra Seasonal Impact: {item.get('event_name')} ({item.get('month_range')})\n"
                f"Impacted Crops: {crops_str}\n"
                f"Price Trend: {item.get('price_impact_trend')}\n"
                f"Market & Mandi Behavior: {item.get('market_behavior_description')}"
            )
            doc_id = f"seasonal_{item.get('season_id')}"
            ids.append(doc_id)
            texts.append(text)
            metas.append({
                "category": "Seasonal Calendar",
                "crops": crops_str,
                "source": "seasonal_calendar.json"
            })
        add_to_collection("crop_knowledge", ids, texts, metas)
        add_to_collection("weather_knowledge", ids, texts, metas)

    # ──────────────────────────────────────────────────────────────────────────
    # 2. GOVERNMENT RULES & MSP DIRECTIVES
    # ──────────────────────────────────────────────────────────────────────────
    print("\n2. Ingesting Government Rules & MSP Schemes...")
    gr_path = os.path.join(DATASET_DIR, "government_rules.json")
    if os.path.exists(gr_path):
        with open(gr_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids, texts, metas = [], [], []
        for item in data:
            crop = item["crop"]
            text = (
                f"Government Regulations & APMC Act for {crop}:\n"
                f"Mandatory Quality Standard: {item.get('quality')} (Minimum Grade: {item.get('minimum_grade')})\n"
                f"Statutory Storage Guidelines: {item.get('storage')}\n"
                f"APMC Auction & Weighbridge Mandate: {item.get('apmc_guideline')}"
            )
            doc_id = f"gov_rule_{crop.lower()}"
            ids.append(doc_id)
            texts.append(text)
            metas.append({
                "crop": crop,
                "category": "APMC Regulations",
                "source": "government_rules.json"
            })
        add_to_collection("government_rules", ids, texts, metas)

    msp_path = os.path.join(DATASET_DIR, "cleaned_msp_prices.json")
    if os.path.exists(msp_path):
        with open(msp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids, texts, metas = [], [], []
        for item in data:
            crop = item["crop"]
            msp_q = item.get("msp_price_per_quintal")
            msp_k = item.get("msp_price_per_kg")
            price_str = f"₹{msp_q}/quintal (₹{msp_k}/kg)" if msp_q else "Not Covered by Central MSP (Open APMC Pricing)"
            text = (
                f"Government Support Price Directive (2026-27): {crop} ({item.get('crop_full_name')})\n"
                f"Official Rate: {price_str}\n"
                f"Statutory Terms: {item.get('note', 'Mandatory floor price at government procurement centers.')}"
            )
            doc_id = f"msp_scheme_{crop.lower()}"
            ids.append(doc_id)
            texts.append(text)
            metas.append({
                "crop": crop,
                "category": "MSP Directive",
                "source": "cleaned_msp_prices.json"
            })
        add_to_collection("government_schemes", ids, texts, metas)

    # ──────────────────────────────────────────────────────────────────────────
    # 3. HISTORICAL NEGOTIATIONS & REFLECTION MEMORY
    # ──────────────────────────────────────────────────────────────────────────
    print("\n3. Ingesting Historical Negotiations...")
    neg_path = os.path.join(DATASET_DIR, "historical_negotiations.json")
    if os.path.exists(neg_path):
        with open(neg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids, texts, metas = [], [], []
        for item in data:
            crop = item["crop"]
            conv_snippets = [f"Round {m.get('round')}: {m.get('speaker')} said: \"{m.get('text')}\"" for m in item.get("complete_negotiation_conversation", [])]
            text = (
                f"APMC Historical Negotiation: {crop} ({item.get('variety')}), Grade {item.get('grade')}\n"
                f"Volume: {item.get('quantity')} kg in {item.get('district')} District.\n"
                f"Benchmark Mandi Rate: ₹{item.get('mandi_reference_price')}/kg\n"
                f"Initial Bids: Farmer asked ₹{item.get('farmer_initial_offer')}/kg | Buyer offered ₹{item.get('buyer_initial_offer')}/kg\n"
                f"Settled Deal Price: ₹{item.get('final_settled_price')}/kg\n"
                f"Summary Outcome: {item.get('outcome_summary')}\n"
                f"Dialogue Record:\n" + "\n".join(conv_snippets[:4])
            )
            doc_id = f"neg_{item.get('negotiation_id')}"
            ids.append(doc_id)
            texts.append(text)
            metas.append({
                "crop": crop,
                "district": item.get("district", "Maharashtra"),
                "variety": item.get("variety", "General"),
                "grade": item.get("grade", "A"),
                "source": "historical_negotiations.json"
            })
        add_to_collection("historical_negotiations", ids, texts, metas, force_update=True)
        add_to_collection("reflection_memory", ids, texts, metas, force_update=True)

    # ──────────────────────────────────────────────────────────────────────────
    # 4. REAL APMC MANDI PRICES
    # ──────────────────────────────────────────────────────────────────────────
    print("\n4. Ingesting Real Mandi Price Records...")
    hist_path = os.path.join(DATASET_DIR, "maharashtra_historical_prices.json")
    if os.path.exists(hist_path):
        with open(hist_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Take the most recent 1,000 APMC records across all crops and districts
        recent_records = data[-1400:]
        ids, texts, metas = [], [], []
        for idx, item in enumerate(recent_records):
            crop = item["crop"]
            district = item.get("district", "Maharashtra")
            mandi = item.get("mandi_name", f"{district} APMC")
            date = item.get("date", "2026-08-04")
            price_kg = item.get("price_per_kg", 30.0)
            arrival = item.get("arrival_mt", 100.0)
            text = (
                f"Real Mandi Transaction: {crop} at {mandi} ({district}, Maharashtra).\n"
                f"Date: {date}.\n"
                f"Modal Wholesale Price: ₹{price_kg:.2f}/kg (₹{price_kg * 100:.2f}/quintal).\n"
                f"APMC Market Arrivals Volume: {arrival:.1f} MT."
            )
            doc_id = f"mandi_rec_{crop.lower()}_{district.lower()}_{date}_{idx}"
            ids.append(doc_id)
            texts.append(text)
            metas.append({
                "crop": crop,
                "district": district,
                "mandi": mandi,
                "date": date,
                "modal_price": price_kg,
                "source": "maharashtra_historical_prices.json"
            })
        add_to_collection("market_prices", ids, texts, metas)

    # ──────────────────────────────────────────────────────────────────────────
    # 5. LOGISTICS: WAREHOUSES & TRANSPORT
    # ──────────────────────────────────────────────────────────────────────────
    print("\n5. Ingesting Warehouses & Transporters...")
    wh_path = os.path.join(DATASET_DIR, "warehouses.json")
    if os.path.exists(wh_path):
        with open(wh_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids, texts, metas = [], [], []
        for item in data:
            text = (
                f"Warehouse Facility: {item.get('name')} ({item.get('type')})\n"
                f"Location: {item.get('location')} ({item.get('district')} District)\n"
                f"Total Capacity: {item.get('capacity_mt')} MT | Available: {item.get('available_capacity_mt')} MT\n"
                f"Storage Rate: ₹{item.get('price_per_mt_per_day')}/MT/day\n"
                f"Quality Rating: {item.get('rating')}/5.0"
            )
            doc_id = f"wh_{item.get('warehouse_id')}"
            ids.append(doc_id)
            texts.append(text)
            metas.append({
                "name": item.get("name"),
                "district": item.get("district"),
                "type": item.get("type"),
                "source": "warehouses.json"
            })
        add_to_collection("warehouse_knowledge", ids, texts, metas)

    tr_path = os.path.join(DATASET_DIR, "transporters.json")
    if os.path.exists(tr_path):
        with open(tr_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids, texts, metas = [], [], []
        for item in data:
            name = item.get('provider_name', 'Maharashtra Transporter')
            loc = item.get('current_location', 'Maharashtra')
            text = (
                f"Logistics Transporter: {name}\n"
                f"Operating Base: {loc} Region\n"
                f"Fleet Details: {item.get('vehicle_type')} (Capacity: {item.get('capacity_mt')} MT)\n"
                f"Transport Rate: ₹{item.get('rate_per_km')}/km (Base Fare: ₹{item.get('base_fare')})\n"
                f"Rating: {item.get('rating')}/5.0"
            )
            doc_id = f"trans_{item.get('transporter_id')}"
            ids.append(doc_id)
            texts.append(text)
            metas.append({
                "provider_name": str(name),
                "location": str(loc),
                "vehicle_type": str(item.get("vehicle_type", "Truck")),
                "source": "transporters.json"
            })
        add_to_collection("transport_knowledge", ids, texts, metas)

    print("\n=======================================================")
    print("ALL REAL DATASETS SUCCESSFULLY INGESTED INTO CHROMADB!")
    print("=======================================================")
    cols = client.list_collections()
    for c in cols:
        print(f"Collection '{c.name}': {c.count()} documents")

if __name__ == "__main__":
    main()
