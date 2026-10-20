"""
backend/services/current_mandi_service.py
------------------------------------------------------------------------
Authoritative Current Daily Mandi Price Service for Buyer Agent (Priority 5A).

Primary Pipeline:
    Official Government Mandi API (data.gov.in Agmarknet)
            ↓
    Buyer Current Mandi Service
            ↓
    Buyer-Only Current Market Cache (backend/dataset/buyer_current_mandi_prices.json)
            ↓
    Buyer Market Context

Key Invariants:
1. Primary path is the live data.gov.in Agmarknet API (requires DATA_GOV_API_KEY).
2. Live API verification strictly requires real API requests (no silent fallbacks).
3. Dedicated isolated Buyer cache: backend/dataset/buyer_current_mandi_prices.json (atomic writes).
4. Zero dependency on shared PostgreSQL tables or cleaned_mandi_prices.json.
5. Unit normalization: ₹/quintal -> ₹/kg (divide by 100), preserving both units.
6. Freshness: CURRENT (<= 3 days), STALE (> 3 days), UNAVAILABLE (invalid/missing date).
7. Location hierarchy matching: EXACT_APMC -> TOKEN_APMC -> DISTRICT -> TOKEN_DISTRICT -> STATE.
8. Strict 7 Buyer canonical crops allowlist.
"""

import os
import json
import logging
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

from shared.crop_catalog import (
    BUYER_SUPPORTED_CROPS,
    normalize_crop_name,
    is_supported_buyer_crop,
)

logger = logging.getLogger("CurrentMandiService")

DATA_GOV_IN_BASE_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"


def calculate_freshness(arrival_date_str: Optional[str]) -> str:
    """
    Calculates freshness status based on arrival date:
    - 'CURRENT': Observation date is within 3 days of today.
    - 'STALE': Observation date is older than 3 days.
    - 'UNAVAILABLE': Date is missing, None, or invalid format (never classify unknown as CURRENT).
    """
    if not arrival_date_str or not isinstance(arrival_date_str, str):
        return "UNAVAILABLE"

    clean_date = arrival_date_str.strip()
    if clean_date.lower() in ["unknown", "n/a", "none", ""]:
        return "UNAVAILABLE"

    parsed_dt = None
    # Try parsing common Agmarknet date formats: DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            parsed_dt = datetime.strptime(clean_date[:10], fmt)
            break
        except (ValueError, TypeError):
            continue

    if parsed_dt is None:
        return "UNAVAILABLE"

    today = datetime.now().date()
    delta_days = (today - parsed_dt.date()).days

    if 0 <= delta_days <= 3:
        return "CURRENT"
    elif delta_days > 3:
        return "STALE"
    else:
        # Future-dated record glitch
        return "STALE"


AGMARKNET_QUERY_CROP_MAP: Dict[str, List[str]] = {
    "Soybean": ["Soyabean", "Soybean", "Soyabean(Yellow)"],
    "Onion": ["Onion", "Nasik Onion"],
    "Cotton": ["Cotton", "Cotton(Unginned)", "Cotton(Ginned)"],
    "Jowar": ["Jowar(Sorghum)", "Jowar"],
    "Bajra": ["Bajra(Pearl Millet/Cumbu)", "Bajra"],
    "Rice": ["Rice", "Paddy(Dhan)(Common)", "Paddy(Dhan)"],
    "Sugarcane": ["Sugarcane", "Gur(Jaggery)"],
}


class CurrentMandiService:
    """
    Authoritative Current Daily Mandi Price Service for Buyer Agent.
    Queries official Government data.gov.in API, normalizes units (₹/quintal -> ₹/kg),
    stores observations in dedicated Buyer cache, and applies hierarchical location matching.
    """

    def __init__(self, cache_path: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if cache_path is None:
            cache_path = os.path.join(base_dir, "backend", "dataset", "buyer_current_mandi_prices.json")
        self.cache_path = cache_path
        self._records: List[Dict[str, Any]] = []
        self._load_cache()

    @property
    def _in_memory_records(self) -> List[Dict[str, Any]]:
        """Backward-compatibility alias for _records."""
        return self._records

    @_in_memory_records.setter
    def _in_memory_records(self, value: List[Dict[str, Any]]) -> None:
        self._records = value

    def _load_cache(self) -> None:
        """Loads buyer-only current mandi observations from disk cache."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._records = data
                        logger.info(f"Loaded {len(self._records)} buyer mandi records from {self.cache_path}")
            except Exception as e:
                logger.warning(f"Could not load buyer mandi cache: {e}")
                self._records = []
        else:
            self._records = []

    def _save_cache_atomic(self) -> None:
        """Atomically writes cached records to buyer_current_mandi_prices.json."""
        cache_dir = os.path.dirname(self.cache_path)
        os.makedirs(cache_dir, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile("w", dir=cache_dir, delete=False, encoding="utf-8") as tf:
                json.dump(self._records, tf, indent=2, ensure_ascii=False)
                temp_name = tf.name
            os.replace(temp_name, self.cache_path)
            logger.debug(f"Atomically saved {len(self._records)} records to {self.cache_path}")
        except Exception as e:
            logger.error(f"Failed to atomically write buyer mandi cache: {e}")
            if 'temp_name' in locals() and os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except Exception:
                    pass

    def _add_or_update_record(self, record: Dict[str, Any]) -> None:
        """Backward-compatibility wrapper for single record ingestion."""
        self._add_or_update_records([record])

    def _add_or_update_records(self, new_records: List[Dict[str, Any]]) -> None:
        """Idempotently adds or updates records in cache and persists atomically."""
        record_map = {}
        # Index existing
        for r in self._records:
            key = (
                r.get("commodity", ""),
                r.get("state", ""),
                r.get("district", ""),
                r.get("market", ""),
                r.get("arrival_date", ""),
            )
            record_map[key] = r

        # Update / insert new
        for r in new_records:
            key = (
                r.get("commodity", ""),
                r.get("state", ""),
                r.get("district", ""),
                r.get("market", ""),
                r.get("arrival_date", ""),
            )
            record_map[key] = r

        self._records = list(record_map.values())
        self._save_cache_atomic()

    def get_api_key(self) -> str:
        """Resolves DATA_GOV_API_KEY from environment variables without logging/printing."""
        return os.getenv("DATA_GOV_API_KEY") or os.getenv("DATA_GOV_IN_API_KEY") or ""

    def fetch_official_mandi_prices(
        self,
        crop: str,
        state: str = "Maharashtra",
        limit: int = 100,
        strict_live: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetches live daily mandi prices from official Government of India data.gov.in API.
        
        Args:
            crop: Commodity name (must normalize to one of the 7 supported Buyer crops).
            state: Target state filter (default: 'Maharashtra').
            limit: Maximum records to return.
            strict_live: If True, raises exceptions on API failure or missing keys (NO fallback).
        """
        norm_crop = normalize_crop_name(crop)
        if not norm_crop or not is_supported_buyer_crop(norm_crop):
            err_msg = f"Fetch rejected for unsupported crop: '{crop}'"
            logger.warning(err_msg)
            if strict_live:
                raise ValueError(err_msg)
            return []

        api_key = self.get_api_key()
        if not api_key:
            err_msg = "LIVE API TEST BLOCKED: DATA_GOV_API_KEY is not configured."
            if strict_live:
                raise ValueError(err_msg)
            logger.info(err_msg + " Returning cached observations.")
            return [r for r in self._records if r.get("commodity") == norm_crop]

        # Candidate query terms for the crop in Agmarknet API
        query_terms = AGMARKNET_QUERY_CROP_MAP.get(norm_crop, [norm_crop])
        fetched_records = []

        try:
            for term in query_terms:
                params = {
                    "api-key": api_key,
                    "format": "json",
                    "limit": str(limit),
                    "filters[commodity]": term,
                }
                if state:
                    params["filters[state]"] = state

                url = f"{DATA_GOV_IN_BASE_URL}?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(url, headers={"User-Agent": "FarmGenAI/1.0"})

                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                if not data or data.get("status") != "ok":
                    err_details = data.get("message") if data else "Empty response"
                    if strict_live:
                        raise RuntimeError(f"LIVE API FAILED: data.gov.in returned non-ok status: {err_details}")
                    logger.warning(f"data.gov.in API returned non-ok response: {data}")
                    continue

                raw_records = data.get("records", [])
                for rec in raw_records:
                    try:
                        min_q = float(rec.get("min_price", 0))
                        max_q = float(rec.get("max_price", 0))
                        modal_q = float(rec.get("modal_price", 0))

                        if modal_q <= 0:
                            continue

                        # Explicit unit normalization: source is ₹/quintal -> normalized is ₹/kg (divide by 100)
                        min_kg = round(min_q / 100.0, 2)
                        max_kg = round(max_q / 100.0, 2)
                        modal_kg = round(modal_q / 100.0, 2)

                        arr_date = rec.get("arrival_date", "")
                        freshness = calculate_freshness(arr_date)

                        item = {
                            "commodity": norm_crop,
                            "state": rec.get("state", state),
                            "district": rec.get("district", "Maharashtra"),
                            "market": rec.get("market", "APMC Market"),
                            "variety": rec.get("variety", "General"),
                            "grade": rec.get("grade", "FAQ"),
                            "arrival_date": arr_date,
                            "min_price": min_kg,
                            "max_price": max_kg,
                            "modal_price": modal_kg,
                            "min_price_kg": min_kg,
                            "max_price_kg": max_kg,
                            "modal_price_kg": modal_kg,
                            "min_price_quintal": min_q,
                            "max_price_quintal": max_q,
                            "modal_price_quintal": modal_q,
                            "source_price": modal_q,
                            "source_price_unit": "₹/quintal",
                            "normalized_price_unit": "₹/kg",
                            "source": "data.gov.in (Agmarknet)",
                            "fetched_at": datetime.now(timezone.utc).isoformat(),
                            "freshness": freshness,
                        }
                        fetched_records.append(item)
                    except (ValueError, TypeError):
                        continue

                # If records found for this term, break
                if fetched_records:
                    break

            if fetched_records:
                self._add_or_update_records(fetched_records)
                logger.info(f"Successfully fetched {len(fetched_records)} live records for {norm_crop} from data.gov.in")
            elif strict_live:
                logger.info(f"Official API reachable: 0 records currently listed for {norm_crop} in {state}")

            return fetched_records or [r for r in self._records if r.get("commodity") == norm_crop]

        except Exception as e:
            if strict_live:
                raise RuntimeError(f"LIVE API FAILED: {e}")
            logger.warning(f"Error calling data.gov.in live API: {e}. Returning cached records.")
            return [r for r in self._records if r.get("commodity") == norm_crop]

    def get_current_market_price(
        self,
        crop: str,
        location: Optional[str] = None,
        apmc: Optional[str] = None,
        observation_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves current daily market price benchmark for a given crop.
        Enforces strict 7-crop allowlist and applies location matching hierarchy:
        1. EXACT_APMC
        2. TOKEN_APMC
        3. DISTRICT
        4. TOKEN_DISTRICT
        5. STATE
        """
        norm_crop = normalize_crop_name(crop)
        if not norm_crop or not is_supported_buyer_crop(norm_crop):
            return {
                "success": False,
                "error": f"Unsupported crop '{crop}'. CurrentMandiService strictly supports 7 crops: {', '.join(BUYER_SUPPORTED_CROPS.keys())}",
                "freshness": "UNAVAILABLE",
                "is_current": False,
            }

        matching_records = [r for r in self._records if r.get("commodity") == norm_crop]

        if not matching_records:
            # Attempt live fetch
            matching_records = self.fetch_official_mandi_prices(norm_crop, strict_live=False)

        if not matching_records:
            return {
                "success": False,
                "crop": norm_crop,
                "error": f"No market price observations available for '{norm_crop}'.",
                "freshness": "UNAVAILABLE",
                "is_current": False,
            }

        # Hierarchy Matching Logic
        target_loc = (location or "").strip().lower()
        target_apmc = (apmc or "").strip().lower()

        matched_record = None
        match_level = "STATE"

        if target_apmc:
            # 1. Exact APMC match
            for r in matching_records:
                if r.get("market", "").strip().lower() == target_apmc:
                    matched_record = r
                    match_level = "EXACT_APMC"
                    break

            # 2. Token-normalized APMC match
            if not matched_record:
                for r in matching_records:
                    m_name = r.get("market", "").strip().lower()
                    if target_apmc in m_name or m_name in target_apmc:
                        matched_record = r
                        match_level = "TOKEN_APMC"
                        break

        if not matched_record and target_loc:
            # 3. Exact District match
            for r in matching_records:
                if r.get("district", "").strip().lower() == target_loc:
                    matched_record = r
                    match_level = "DISTRICT"
                    break

            # 4. Token-normalized District match
            if not matched_record:
                for r in matching_records:
                    d_name = r.get("district", "").strip().lower()
                    if target_loc in d_name or d_name in target_loc:
                        matched_record = r
                        match_level = "TOKEN_DISTRICT"
                        break

        # 5. Statewide / Latest Fallback
        if not matched_record:
            matched_record = matching_records[0]
            match_level = "STATE"

        freshness_status = matched_record.get("freshness", "UNAVAILABLE")
        is_current = (freshness_status == "CURRENT")

        return {
            "success": True,
            "crop": norm_crop,
            "state": matched_record.get("state", "Maharashtra"),
            "district": matched_record.get("district", "Maharashtra"),
            "apmc": matched_record.get("market", "APMC Market"),
            "variety": matched_record.get("variety", "General"),
            "grade": matched_record.get("grade", "FAQ"),
            "min_price": matched_record.get("min_price", matched_record.get("min_price_kg", 0.0)),
            "max_price": matched_record.get("max_price", matched_record.get("max_price_kg", 0.0)),
            "modal_price": matched_record.get("modal_price", matched_record.get("modal_price_kg", 0.0)),
            "min_price_kg": matched_record.get("min_price_kg", 0.0),
            "max_price_kg": matched_record.get("max_price_kg", 0.0),
            "modal_price_kg": matched_record.get("modal_price_kg", 0.0),
            "min_price_quintal": matched_record.get("min_price_quintal", 0.0),
            "max_price_quintal": matched_record.get("max_price_quintal", 0.0),
            "modal_price_quintal": matched_record.get("modal_price_quintal", 0.0),
            "source_price_unit": matched_record.get("source_price_unit", "₹/quintal"),
            "normalized_price_unit": matched_record.get("normalized_price_unit", "₹/kg"),
            "observation_date": matched_record.get("arrival_date", ""),
            "fetched_at": matched_record.get("fetched_at", datetime.now(timezone.utc).isoformat()),
            "source": matched_record.get("source", "data.gov.in (Agmarknet)"),
            "freshness": freshness_status,
            "match_level": match_level,
            "is_current": is_current,
        }


# Singleton instance
current_mandi_service = CurrentMandiService()
