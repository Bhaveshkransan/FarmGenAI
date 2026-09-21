"""Direct factual calculation of dataset statistics for verification audit."""
import os
import sys
import csv
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.crop_catalog import BUYER_SUPPORTED_CROPS

raw_path = os.path.abspath("backend/dataset/Monthly_data_cmo.csv")
clean_path = os.path.abspath("backend/dataset/clean_buyer_market_data.csv")
feature_path = os.path.abspath("backend/dataset/buyer_feature_dataset.csv")

def verify_raw(path):
    print("==================================================")
    print("VERIFY RAW DATASET:", path)
    print("==================================================")
    size = os.path.getsize(path)
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    row_count = len(rows)
    col_count = len(fieldnames)
    print(f"File Size: {size} bytes ({size / (1024*1024):.2f} MB)")
    print(f"Row Count: {row_count}")
    print(f"Col Count: {col_count}")
    print(f"Columns: {fieldnames}")

    dates = [r["date"].strip() for r in rows if r.get("date")]
    first_date = min(dates) if dates else "None"
    last_date = max(dates) if dates else "None"
    print(f"First Date: {first_date}")
    print(f"Last Date:  {last_date}")

    # Maharashtra count
    mh_count = sum(1 for r in rows if r.get("state_name", "").strip().lower() == "maharashtra")
    print(f"Maharashtra Records: {mh_count} (out of {row_count}, {mh_count/row_count:.1%})")

    # Crop counts
    crop_counts = Counter(r.get("Commodity", "").strip() for r in rows)
    print("\nTop 15 Commodity Raw Counts:")
    for c, cnt in crop_counts.most_common(15):
        print(f"  {c}: {cnt}")

    # 7-crop specific matching
    canonical_alias_map = {
        "BAJRI": "Bajra", "Bajri": "Bajra",
        "COTTON": "Cotton", "Cotton": "Cotton",
        "ONION": "Onion", "Onion": "Onion",
        "PADDY-UNHUSKED": "Rice", "Paddy-Unhusked": "Rice",
        "RICE(PADDY-HUS)": "Rice", "Rice(Paddy-Hus)": "Rice",
        "SORGUM(JAWAR)": "Jowar", "Sorgum(Jawar)": "Jowar",
        "SOYBEAN": "Soybean", "Soybean": "Soybean",
        "Sugarcane": "Sugarcane"
    }
    seven_crop_totals = defaultdict(int)
    for r in rows:
        c = r.get("Commodity", "").strip()
        if c in canonical_alias_map:
            seven_crop_totals[canonical_alias_map[c]] += 1
    print("\nTarget 7-Crop Raw Observation Counts:")
    for c, cnt in sorted(seven_crop_totals.items()):
        print(f"  {c}: {cnt}")
    print(f"  TOTAL 7-CROP RAW ROWS: {sum(seven_crop_totals.values())}")

    # Duplicates on (Commodity, APMC, date)
    seen = set()
    dup_count = 0
    null_count = 0
    for r in rows:
        key = (r.get("Commodity", "").strip(), r.get("APMC", "").strip(), r.get("date", "").strip())
        if key in seen:
            dup_count += 1
        else:
            seen.add(key)
        for v in r.values():
            if v is None or v.strip() == "" or v.strip() == "-":
                null_count += 1
    print(f"Duplicate (Commodity, APMC, Date) keys: {dup_count}")
    print(f"Null/Empty/Dash cells in dataset: {null_count}")

    print("\nSample Row 1:", rows[0])
    print("Sample Row 2:", rows[1])
    return row_count, col_count, size


def verify_clean(path):
    print("\n==================================================")
    print("VERIFY CLEAN DATASET:", path)
    print("==================================================")
    size = os.path.getsize(path)
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    row_count = len(rows)
    col_count = len(fieldnames)
    print(f"File Size: {size} bytes ({size / 1024:.2f} KB)")
    print(f"Row Count: {row_count}")
    print(f"Col Count: {col_count}")
    print(f"Columns: {fieldnames}")

    dates = [r["date"].strip() for r in rows if r.get("date")]
    first_date = min(dates) if dates else "None"
    last_date = max(dates) if dates else "None"
    print(f"First Date: {first_date}")
    print(f"Last Date:  {last_date}")

    # Crop breakdown
    crop_counts = Counter(r.get("crop", "").strip() for r in rows)
    print("\n7-Crop Clean Records Breakdown:")
    for c, cnt in sorted(crop_counts.items()):
        print(f"  {c}: {cnt}")
    print(f"  TOTAL CLEAN ROWS: {sum(crop_counts.values())}")

    # Duplicates on (crop, apmc, date)
    seen = set()
    dup_count = 0
    null_count = 0
    for r in rows:
        key = (r.get("crop", "").strip(), r.get("apmc", "").strip(), r.get("date", "").strip())
        if key in seen:
            dup_count += 1
        else:
            seen.add(key)
        for v in r.values():
            if v is None or v.strip() == "":
                null_count += 1
    print(f"Duplicate (Crop, APMC, Date) keys: {dup_count} (Must be 0)")
    print(f"Null/Empty cells in clean dataset: {null_count} (Must be 0)")

    print("\nSample Clean Row 1:", rows[0])
    print("Sample Clean Row 2:", rows[1])
    return row_count, col_count, size


def verify_feature(path):
    print("\n==================================================")
    print("VERIFY FEATURE DATASET:", path)
    print("==================================================")
    size = os.path.getsize(path)
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    row_count = len(rows)
    col_count = len(fieldnames)
    print(f"File Size: {size} bytes ({size / (1024*1024):.2f} MB)")
    print(f"Row Count: {row_count}")
    print(f"Col Count: {col_count}")
    print(f"Columns: {fieldnames}")

    dates = [r["date"].strip() for r in rows if r.get("date")]
    first_date = min(dates) if dates else "None"
    last_date = max(dates) if dates else "None"
    print(f"First Date: {first_date}")
    print(f"Last Date:  {last_date}")

    # Target check
    target_vals = [float(r["target_next_modal_kg"]) for r in rows]
    print(f"Target Column: 'target_next_modal_kg'")
    print(f"  Min Target Price: Rs. {min(target_vals):.4f}/kg")
    print(f"  Max Target Price: Rs. {max(target_vals):.4f}/kg")
    print(f"  Mean Target Price: Rs. {sum(target_vals)/len(target_vals):.4f}/kg")

    # Crop breakdown
    crop_counts = Counter(r.get("crop", "").strip() for r in rows)
    print("\n7-Crop Feature Rows Breakdown:")
    for c, cnt in sorted(crop_counts.items()):
        print(f"  {c}: {cnt}")
    print(f"  TOTAL FEATURE ROWS: {sum(crop_counts.values())}")

    # Null count
    null_count = 0
    for r in rows:
        for v in r.values():
            if v is None or v.strip() == "":
                null_count += 1
    print(f"Null/Empty cells in feature dataset: {null_count} (Must be 0)")

    print("\nSample Feature Row 1:", rows[0])
    return row_count, col_count, size


if __name__ == "__main__":
    from collections import defaultdict
    verify_raw(raw_path)
    verify_clean(clean_path)
    verify_feature(feature_path)
