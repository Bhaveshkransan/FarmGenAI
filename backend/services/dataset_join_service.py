"""
Dataset Join & Relational Integration Service
Implements Phase 8 requirements:
- Multi-dataset inventory with data provenance, schemas, candidate keys.
- Configurable composite 2-4 column joins.
- LEFT JOIN and RIGHT JOIN support.
- Exact matching default, with optional normalization.
- Cardinality analysis (1:1, 1:N, N:1, M:N).
- Row multiplication detection.
- Matched and unmatched record auditing.
- Provenance tracking with dataset prefixes.
- Zero source dataset overwrite.
"""

import os
import glob
import json
import csv
import copy
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

DATASET_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset"))
JOIN_OUTPUT_DIR = os.path.join(DATASET_ROOT, "joined_outputs")

PROVENANCE_REGISTRY = {
    "buyer_feature_dataset.csv": ("Buyer Procurement Intelligence", "Buyer Requirements, Target Prices, APMC Features"),
    "clean_buyer_market_data.csv": ("APMC Market Directorate", "Commodity arrivals, modal prices, district trends"),
    "clean_buyer_market_data.json": ("APMC Market Directorate", "JSON representation of commodity arrivals and modal prices"),
    "CMO_MSP_Mandi.csv": ("Commission for Agricultural Costs & Prices (CACP)", "Minimum Support Price benchmarks and historical Mandi prices"),
    "maharashtra_market_mapping.csv": ("Maharashtra State Agricultural Marketing Board (MSAMB)", "APMC Mandi locations, geo-coordinates, district mapping"),
    "Market_Wise_Price_Arrival_06-08-2026_08-18-20_PM.csv": ("AGMARKNET Live Feed", "Daily Mandi arrivals and modal price snapshots"),
    "Monthly_data_cmo.csv": ("Maharashtra Directorate of Economics & Statistics", "Monthly historical price time series by commodity and center"),
    "buyer_current_mandi_prices.json": ("Mandi Integration Service", "Cleaned real-time benchmark mandi prices"),
    "cleaned_mandi_prices.json": ("Mandi Scraping & API Pipeline", "Standardized mandi prices across Maharashtra districts"),
    "cleaned_msp_prices.json": ("CACP MSP Reference Feed", "Official government MSP floor rates by crop"),
    "crop_knowledge.json": ("ICAR / State Agricultural Universities", "Crop agronomy, shelf life, perishability, moisture tolerances"),
    "crop_quality_references.json": ("APMC Grading Standards (AGMARK)", "Grade A/B/FAQ specifications, moisture cutoffs, foreign matter"),
    "government_rules.json": ("APMC Regulatory Framework", "Mandi cess rates (1.05%), market committee fees, weighing charges"),
    "historical_negotiations.json": ("FarmGenAI Historical Platform Logs", "Historical buyer-farmer negotiation trajectories and agreed discounts"),
    "maharashtra_historical_prices.json": ("MSAMB Historical Records", "Seasonal high/low/modal price bands across Maharashtra"),
    "seasonal_calendar.json": ("Department of Agriculture, Maharashtra", "Kharif/Rabi sowing, peak arrival, and lean supply months"),
    "transporters.json": ("Logistics Fleet Registry", "Registered freight carriers, truck categories, base per-km rates"),
    "trust_scores.json": ("FarmGenAI Escrow & Reputation Engine", "Buyer and Farmer historical reliability, dispute rates, payment speed"),
    "warehouses.json": ("Warehousing Development & Regulatory Authority (WDRA)", "Registered cold storages, capacity in MT, daily storage tariff"),
    "synthetic_buyer_requirements.json": ("Synthetic Data Generator", "Realistic buyer procurement intents across crops and regions"),
    "synthetic_farmers.json": ("Synthetic Data Generator", "Farmer stakeholder personas, farm sizes, crop holdings, coordinates"),
    "synthetic_negotiations.json": ("Synthetic Data Generator", "Multi-round simulated negotiation transcripts and outcomes"),
    "synthetic_processors.json": ("Synthetic Data Generator", "Milling and agro-processing plants, daily capacities, conversion rates"),
    "synthetic_produce_listings.json": ("Synthetic Data Generator", "Farmer spot listings with harvest dates, grades, asking prices"),
    "synthetic_transport_providers.json": ("Synthetic Data Generator", "Carrier fleet records, operational radii, vehicle specs"),
    "synthetic_vehicles.json": ("Synthetic Data Generator", "Vehicle registry with live GPS, capacity in kg, reefer capabilities"),
    "synthetic_warehouses.json": ("Synthetic Data Generator", "Warehouse facility locations, temperature ranges, open capacity")
}


class DatasetJoinService:
    def __init__(self, dataset_dir: str = DATASET_ROOT):
        self.dataset_dir = dataset_dir
        os.makedirs(JOIN_OUTPUT_DIR, exist_ok=True)

    def _locate_file(self, filename: str) -> Optional[str]:
        """Resolve full filepath safely within DATASET_ROOT (including subdirs)."""
        clean_name = os.path.basename(filename)
        # Search direct in dataset_dir and subdirectories
        matches = glob.glob(os.path.join(self.dataset_dir, "**", clean_name), recursive=True)
        return matches[0] if matches else None

    def _load_data(self, filepath: str) -> List[Dict[str, Any]]:
        """Load CSV or JSON file into uniform list of dictionaries."""
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".csv":
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                return list(reader)
        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                first_list = next((v for v in data.values() if isinstance(v, list)), None)
                if first_list:
                    return first_list
                return [data]
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def get_inventory(self) -> List[Dict[str, Any]]:
        """Scan all datasets and produce verified schema inventory."""
        files = (
            glob.glob(os.path.join(self.dataset_dir, "*.csv")) +
            glob.glob(os.path.join(self.dataset_dir, "*.json")) +
            glob.glob(os.path.join(self.dataset_dir, "synthetic", "*.json"))
        )

        inventory = []
        for f in sorted(files):
            name = os.path.basename(f)
            rel_path = os.path.relpath(f, self.dataset_dir).replace("\\", "/")
            ext = os.path.splitext(f)[1].lower()
            prov_src, prov_desc = PROVENANCE_REGISTRY.get(name, ("FarmGenAI Repository", "System reference data"))

            try:
                rows = self._load_data(f)
                row_count = len(rows)
                if row_count > 0 and isinstance(rows[0], dict):
                    cols_set = set()
                    for r in rows:
                        if isinstance(r, dict):
                            cols_set.update(r.keys())
                    cols = sorted(list(cols_set))

                    null_counts = {c: 0 for c in cols}
                    col_vals = {c: [] for c in cols}
                    for r in rows:
                        if not isinstance(r, dict):
                            continue
                        for c in cols:
                            val = r.get(c)
                            if val is None or val == "" or str(val).strip().lower() in ("null", "none", "nan"):
                                null_counts[c] += 1
                            else:
                                col_vals[c].append(str(val))

                    candidate_keys = [
                        c for c in cols
                        if null_counts[c] == 0 and len(col_vals[c]) == len(set(col_vals[c])) and row_count > 1
                    ]

                    inventory.append({
                        "name": name,
                        "path": rel_path,
                        "format": ext[1:].upper(),
                        "row_count": row_count,
                        "column_count": len(cols),
                        "columns": cols,
                        "null_counts": null_counts,
                        "candidate_keys": candidate_keys,
                        "provenance_source": prov_src,
                        "provenance_description": prov_desc,
                        "sample_record": rows[0] if rows else {}
                    })
            except Exception as e:
                inventory.append({
                    "name": name,
                    "path": rel_path,
                    "error": str(e)
                })

        return inventory

    def _extract_composite_key(
        self,
        row: Dict[str, Any],
        keys: List[str],
        normalize: bool = False
    ) -> Optional[Tuple]:
        """Extract and optionally normalize composite key values."""
        vals = []
        for k in keys:
            val = row.get(k)
            if val is None or val == "" or str(val).strip().lower() in ("null", "none", "nan"):
                return None  # Key has null component
            str_val = str(val)
            if normalize:
                str_val = str_val.strip().lower()
            vals.append(str_val)
        return tuple(vals)

    def execute_join(
        self,
        dataset_a_name: str,
        dataset_b_name: str,
        join_keys_a: List[str],
        join_keys_b: List[str],
        join_type: str = "left",
        normalize_text: bool = False,
        limit_preview: Optional[int] = None,
        save_output: bool = False
    ) -> Dict[str, Any]:
        """
        Execute validated composite join with strict audit reporting.
        Supports 2 to 4 composite keys.
        Supports 'left' or 'right' joins.
        """
        # 1. Validate composite key count (2 to 4 columns required)
        if not (2 <= len(join_keys_a) <= 4):
            raise ValueError(f"Composite join requires between 2 and 4 join keys, got {len(join_keys_a)} for dataset A")
        if len(join_keys_a) != len(join_keys_b):
            raise ValueError(f"Join key length mismatch: Dataset A has {len(join_keys_a)} keys, Dataset B has {len(join_keys_b)} keys")

        # 2. Locate and load datasets
        path_a = self._locate_file(dataset_a_name)
        if not path_a:
            raise FileNotFoundError(f"Dataset A '{dataset_a_name}' not found")
        path_b = self._locate_file(dataset_b_name)
        if not path_b:
            raise FileNotFoundError(f"Dataset B '{dataset_b_name}' not found")

        data_a = self._load_data(path_a)
        data_b = self._load_data(path_b)

        # 3. Validate columns exist
        sample_a = data_a[0] if data_a else {}
        sample_b = data_b[0] if data_b else {}
        for k in join_keys_a:
            if k not in sample_a:
                raise ValueError(f"Join key '{k}' does not exist in dataset A ({dataset_a_name})")
        for k in join_keys_b:
            if k not in sample_b:
                raise ValueError(f"Join key '{k}' does not exist in dataset B ({dataset_b_name})")

        join_type = join_type.lower()
        if join_type not in ("left", "right"):
            raise ValueError(f"Supported join types are 'left' and 'right', got '{join_type}'")

        # Handle RIGHT JOIN by swapping primary/secondary sides internally
        if join_type == "right":
            primary_data, sec_data = data_b, data_a
            primary_keys, sec_keys = join_keys_b, join_keys_a
            primary_name, sec_name = dataset_b_name, dataset_a_name
            primary_prefix, sec_prefix = "ds_b", "ds_a"
        else:
            primary_data, sec_data = data_a, data_b
            primary_keys, sec_keys = join_keys_a, join_keys_b
            primary_name, sec_name = dataset_a_name, dataset_b_name
            primary_prefix, sec_prefix = "ds_a", "ds_b"

        # 4. Build secondary index with collision/duplicate detection
        sec_index: Dict[Tuple, List[Dict[str, Any]]] = {}
        sec_null_keys = 0
        for row in sec_data:
            ck = self._extract_composite_key(row, sec_keys, normalize_text)
            if ck is None:
                sec_null_keys += 1
                continue
            sec_index.setdefault(ck, []).append(row)

        # 5. Perform relational join
        joined_records = []
        matched_primary_count = 0
        unmatched_primary_count = 0
        primary_null_keys = 0
        sec_matched_keys = set()
        max_matches_per_key = 0

        for row in primary_data:
            ck = self._extract_composite_key(row, primary_keys, normalize_text)
            if ck is None:
                primary_null_keys += 1
                unmatched_primary_count += 1
                # Include row with null secondary fields for LEFT join
                prefixed_primary = {f"{primary_prefix}_{k}": v for k, v in row.items()}
                prefixed_sec = {f"{sec_prefix}_{k}": None for k in (data_b[0].keys() if join_type == "left" else data_a[0].keys())}
                joined_records.append({**prefixed_primary, **prefixed_sec})
                continue

            matches = sec_index.get(ck)
            if matches:
                matched_primary_count += 1
                sec_matched_keys.add(ck)
                match_count = len(matches)
                if match_count > max_matches_per_key:
                    max_matches_per_key = match_count

                for m in matches:
                    prefixed_primary = {f"{primary_prefix}_{k}": v for k, v in row.items()}
                    prefixed_sec = {f"{sec_prefix}_{k}": v for k, v in m.items()}
                    joined_records.append({**prefixed_primary, **prefixed_sec})
            else:
                unmatched_primary_count += 1
                prefixed_primary = {f"{primary_prefix}_{k}": v for k, v in row.items()}
                prefixed_sec = {f"{sec_prefix}_{k}": None for k in (data_b[0].keys() if join_type == "left" else data_a[0].keys())}
                joined_records.append({**prefixed_primary, **prefixed_sec})

        # 6. Cardinality and row multiplication analysis
        primary_duplicates = len(primary_data) - len({
            self._extract_composite_key(r, primary_keys, normalize_text)
            for r in primary_data if self._extract_composite_key(r, primary_keys, normalize_text)
        })
        sec_duplicates = sum(len(v) - 1 for v in sec_index.values() if len(v) > 1)

        is_primary_unique = primary_duplicates == 0
        is_sec_unique = sec_duplicates == 0

        if is_primary_unique and is_sec_unique:
            cardinality = "1:1"
        elif is_primary_unique and not is_sec_unique:
            cardinality = "1:N"
        elif not is_primary_unique and is_sec_unique:
            cardinality = "N:1"
        else:
            cardinality = "M:N"

        row_multiplication_detected = len(joined_records) > len(primary_data)
        multiplication_factor = round(len(joined_records) / max(len(primary_data), 1), 3)

        # 7. Unmatched secondary records
        unmatched_sec_count = len(sec_data) - sum(len(sec_index[k]) for k in sec_matched_keys)

        # 8. Output preparation
        output_records = joined_records[:limit_preview] if limit_preview else joined_records
        saved_file = None

        if save_output:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            clean_out = f"join_{os.path.splitext(dataset_a_name)[0]}_{os.path.splitext(dataset_b_name)[0]}_{ts}.json"
            saved_file = os.path.join(JOIN_OUTPUT_DIR, clean_out)
            with open(saved_file, "w", encoding="utf-8") as out_f:
                json.dump({
                    "meta": {
                        "dataset_a": dataset_a_name,
                        "dataset_b": dataset_b_name,
                        "join_keys_a": join_keys_a,
                        "join_keys_b": join_keys_b,
                        "join_type": join_type,
                        "cardinality": cardinality,
                        "row_count": len(joined_records),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    "records": joined_records
                }, out_f, indent=2)

        return {
            "status": "SUCCESS",
            "join_configuration": {
                "dataset_a": dataset_a_name,
                "dataset_b": dataset_b_name,
                "join_keys_a": join_keys_a,
                "join_keys_b": join_keys_b,
                "join_type": join_type.upper(),
                "normalized": normalize_text
            },
            "cardinality": cardinality,
            "row_multiplication": {
                "detected": row_multiplication_detected,
                "factor": multiplication_factor,
                "warning": (
                    f"Row multiplication occurred: Output rows ({len(joined_records)}) > Primary rows ({len(primary_data)}) "
                    f"due to non-unique composite keys ({cardinality})."
                ) if row_multiplication_detected else None
            },
            "statistics": {
                "primary_total_rows": len(primary_data),
                "secondary_total_rows": len(sec_data),
                "joined_total_rows": len(joined_records),
                "matched_primary_rows": matched_primary_count,
                "unmatched_primary_rows": unmatched_primary_count,
                "unmatched_secondary_rows": unmatched_sec_count,
                "primary_null_keys": primary_null_keys,
                "secondary_null_keys": sec_null_keys
            },
            "provenance": {
                "dataset_a_source": PROVENANCE_REGISTRY.get(dataset_a_name, ("FarmGenAI", "Repository dataset"))[0],
                "dataset_b_source": PROVENANCE_REGISTRY.get(dataset_b_name, ("FarmGenAI", "Repository dataset"))[0],
                "primary_columns_prefix": f"{primary_prefix}_",
                "secondary_columns_prefix": f"{sec_prefix}_"
            },
            "preview_limit": limit_preview,
            "preview_records_count": len(output_records),
            "preview_records": output_records,
            "persisted_output_path": saved_file
        }
