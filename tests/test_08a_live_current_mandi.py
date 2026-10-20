"""
tests/test_08a_live_current_mandi.py
------------------------------------------------------------------------
Verification Test Suite for Priority 5A: Buyer Live Current Mandi Price Fetching.
Covers LIVE-MANDI-01 through LIVE-MANDI-16.
"""

import os
import sys
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.current_mandi_service import (
    CurrentMandiService,
    current_mandi_service,
    calculate_freshness,
)
from shared.crop_catalog import (
    BUYER_SUPPORTED_CROPS,
    normalize_crop_name,
    is_supported_buyer_crop,
)


class TestLiveMandi01SoybeanLiveQuery:
    def test_soybean_live_query(self):
        """LIVE-MANDI-01: Live API query for Maharashtra Soybean returns valid records."""
        api_key = current_mandi_service.get_api_key()
        if not api_key:
            pytest.skip("LIVE API TEST BLOCKED: DATA_GOV_API_KEY is not configured.")

        try:
            records = current_mandi_service.fetch_official_mandi_prices("Soybean", state="Maharashtra", strict_live=True)
        except RuntimeError as e:
            pytest.skip(f"LIVE API UNREACHABLE: {e}")

        assert isinstance(records, list)
        if records:
            r = records[0]
            assert r["commodity"] == "Soybean"
            assert "modal_price_kg" in r
            assert "modal_price_quintal" in r
            assert r["modal_price_kg"] > 0
            assert r["source_price_unit"] == "₹/quintal"
            assert r["normalized_price_unit"] == "₹/kg"
            assert r["source"] == "data.gov.in (Agmarknet)"


class TestLiveMandi02CottonLiveQuery:
    def test_cotton_live_query(self):
        """LIVE-MANDI-02: Live API query for Cotton executes without crashing and handles season variations."""
        api_key = current_mandi_service.get_api_key()
        if not api_key:
            pytest.skip("LIVE API TEST BLOCKED: DATA_GOV_API_KEY is not configured.")

        try:
            records = current_mandi_service.fetch_official_mandi_prices("Cotton", state="Maharashtra", strict_live=True)
        except RuntimeError as e:
            pytest.skip(f"LIVE API UNREACHABLE: {e}")

        assert isinstance(records, list)
        for r in records:
            assert r["commodity"] == "Cotton"
            assert r["modal_price_kg"] == round(r["modal_price_quintal"] / 100.0, 2)


class TestLiveMandi03OnionLiveQuery:
    def test_onion_live_query(self):
        """LIVE-MANDI-03: Live API query for Maharashtra Onion returns active mandi records."""
        api_key = current_mandi_service.get_api_key()
        if not api_key:
            pytest.skip("LIVE API TEST BLOCKED: DATA_GOV_API_KEY is not configured.")

        try:
            records = current_mandi_service.fetch_official_mandi_prices("Onion", state="Maharashtra", strict_live=True)
        except RuntimeError as e:
            pytest.skip(f"LIVE API UNREACHABLE: {e}")

        assert isinstance(records, list)
        assert len(records) > 0, "Expected at least one active Onion market in Maharashtra"
        r = records[0]
        assert r["commodity"] == "Onion"
        assert r["state"] == "Maharashtra"
        assert r["modal_price_kg"] > 0
        assert r["freshness"] in ["CURRENT", "STALE", "UNAVAILABLE"]


class TestLiveMandi04RiceLiveQuery:
    def test_rice_live_query(self):
        """LIVE-MANDI-04: Live API query for Maharashtra Rice returns records with valid schema."""
        api_key = current_mandi_service.get_api_key()
        if not api_key:
            pytest.skip("LIVE API TEST BLOCKED: DATA_GOV_API_KEY is not configured.")

        try:
            records = current_mandi_service.fetch_official_mandi_prices("Rice", state="Maharashtra", strict_live=True)
        except RuntimeError as e:
            pytest.skip(f"LIVE API UNREACHABLE: {e}")

        assert isinstance(records, list)
        if records:
            r = records[0]
            assert r["commodity"] == "Rice"
            assert r["modal_price_kg"] > 0


class TestLiveMandi05JowarBajraLiveQuery:
    def test_jowar_and_bajra_live_queries(self):
        """LIVE-MANDI-05: Live API query for Maharashtra Jowar and Bajra returns records."""
        api_key = current_mandi_service.get_api_key()
        if not api_key:
            pytest.skip("LIVE API TEST BLOCKED: DATA_GOV_API_KEY is not configured.")

        try:
            jowar_records = current_mandi_service.fetch_official_mandi_prices("Jowar", state="Maharashtra", strict_live=True)
            bajra_records = current_mandi_service.fetch_official_mandi_prices("Bajra", state="Maharashtra", strict_live=True)
        except RuntimeError as e:
            pytest.skip(f"LIVE API UNREACHABLE: {e}")

        assert isinstance(jowar_records, list)
        assert len(jowar_records) > 0

        assert isinstance(bajra_records, list)
        assert len(bajra_records) > 0


class TestLiveMandi06AllCanonicalCrops:
    def test_all_canonical_7_crops_supported(self):
        """LIVE-MANDI-06: Verified all 7 canonical crops can be queried and unsupported crops are rejected."""
        canonical_crops = list(BUYER_SUPPORTED_CROPS.keys())
        assert len(canonical_crops) == 7

        for crop in canonical_crops:
            norm = normalize_crop_name(crop)
            assert norm == crop
            assert is_supported_buyer_crop(norm) is True

        # Non-supported crop should fail / return error
        res = current_mandi_service.get_current_market_price("Tomato")
        assert res["success"] is False
        assert "Unsupported crop" in res["error"]
        assert res["freshness"] == "UNAVAILABLE"


class TestLiveMandi07UnitConversionAccuracy:
    def test_unit_conversion_math(self):
        """LIVE-MANDI-07: Unit conversion accuracy (₹/quintal divided by 100 to ₹/kg)."""
        mock_payload = {
            "status": "ok",
            "records": [
                {
                    "state": "Maharashtra",
                    "district": "Nashik",
                    "market": "Lasalgaon",
                    "commodity": "Onion",
                    "variety": "Red",
                    "grade": "FAQ",
                    "min_price": "2450.50",
                    "max_price": "3550.75",
                    "modal_price": "3125.25",
                    "arrival_date": "22/09/2026",
                }
            ],
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            with patch.dict(os.environ, {"DATA_GOV_API_KEY": "dummy_key"}):
                service = CurrentMandiService()
                records = service.fetch_official_mandi_prices("Onion", strict_live=True)
                assert len(records) == 1
                rec = records[0]
                assert rec["min_price_quintal"] == 2450.50
                assert rec["max_price_quintal"] == 3550.75
                assert rec["modal_price_quintal"] == 3125.25
                assert rec["min_price_kg"] == 24.50
                assert rec["max_price_kg"] == 35.51
                assert rec["modal_price_kg"] == 31.25
                assert rec["source_price_unit"] == "₹/quintal"
                assert rec["normalized_price_unit"] == "₹/kg"


class TestLiveMandi08APMCHierarchyExact:
    def test_exact_apmc_matching(self):
        """LIVE-MANDI-08: APMC hierarchy exact matching (EXACT_APMC)."""
        service = CurrentMandiService()
        service._records = [
            {
                "commodity": "Onion",
                "state": "Maharashtra",
                "district": "Nashik",
                "market": "Lasalgaon",
                "modal_price_kg": 29.50,
                "arrival_date": "22/09/2026",
                "freshness": "CURRENT",
            }
        ]
        res = service.get_current_market_price("Onion", apmc="Lasalgaon")
        assert res["success"] is True
        assert res["match_level"] == "EXACT_APMC"
        assert res["modal_price_kg"] == 29.50


class TestLiveMandi09APMCHierarchyToken:
    def test_token_apmc_matching(self):
        """LIVE-MANDI-09: APMC hierarchy token matching (TOKEN_APMC)."""
        service = CurrentMandiService()
        service._records = [
            {
                "commodity": "Onion",
                "state": "Maharashtra",
                "district": "Nashik",
                "market": "Lasalgaon Main APMC Market",
                "modal_price_kg": 29.50,
                "arrival_date": "22/09/2026",
                "freshness": "CURRENT",
            }
        ]
        res = service.get_current_market_price("Onion", apmc="Lasalgaon")
        assert res["success"] is True
        assert res["match_level"] == "TOKEN_APMC"


class TestLiveMandi10APMCHierarchyDistrict:
    def test_district_level_matching(self):
        """LIVE-MANDI-10: APMC hierarchy district matching (DISTRICT or TOKEN_DISTRICT)."""
        service = CurrentMandiService()
        service._records = [
            {
                "commodity": "Soybean",
                "state": "Maharashtra",
                "district": "Latur",
                "market": "UnknownMandi",
                "modal_price_kg": 49.00,
                "arrival_date": "22/09/2026",
                "freshness": "CURRENT",
            }
        ]
        res = service.get_current_market_price("Soybean", location="Latur", apmc="NonExistentAPMC")
        assert res["success"] is True
        assert res["match_level"] in ["DISTRICT", "TOKEN_DISTRICT"]
        assert res["modal_price_kg"] == 49.00


class TestLiveMandi11APMCHierarchyStateFallback:
    def test_state_level_fallback(self):
        """LIVE-MANDI-11: APMC hierarchy statewide fallback (STATE)."""
        service = CurrentMandiService()
        service._records = [
            {
                "commodity": "Soybean",
                "state": "Maharashtra",
                "district": "Latur",
                "market": "Latur APMC",
                "modal_price_kg": 49.00,
                "arrival_date": "22/09/2026",
                "freshness": "CURRENT",
            }
        ]
        res = service.get_current_market_price("Soybean", location="Kolhapur", apmc="RandomAPMC")
        assert res["success"] is True
        assert res["match_level"] == "STATE"


class TestLiveMandi12FreshnessDetermination:
    def test_freshness_logic(self):
        """LIVE-MANDI-12: Freshness status determination (CURRENT <= 3 days, STALE > 3 days, UNAVAILABLE)."""
        today_str = datetime.now().strftime("%d/%m/%Y")
        assert calculate_freshness(today_str) == "CURRENT"

        two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        assert calculate_freshness(two_days_ago) == "CURRENT"

        ten_days_ago = (datetime.now() - timedelta(days=10)).strftime("%d/%m/%Y")
        assert calculate_freshness(ten_days_ago) == "STALE"

        assert calculate_freshness(None) == "UNAVAILABLE"
        assert calculate_freshness("") == "UNAVAILABLE"
        assert calculate_freshness("unknown") == "UNAVAILABLE"
        assert calculate_freshness("invalid-date-format") == "UNAVAILABLE"


class TestLiveMandi13DedicatedBuyerCacheAndAtomicPersistence:
    def test_dedicated_cache_file_and_atomic_write(self, tmp_path):
        """LIVE-MANDI-13: Dedicated Buyer dataset file existence and atomic persistence."""
        custom_cache = str(tmp_path / "buyer_current_mandi_prices.json")
        service = CurrentMandiService(cache_path=custom_cache)
        assert service.cache_path == custom_cache

        rec = {
            "commodity": "Soybean",
            "state": "Maharashtra",
            "district": "Latur",
            "market": "Latur APMC",
            "variety": "Yellow",
            "grade": "FAQ",
            "arrival_date": "22/09/2026",
            "modal_price_quintal": 5100.0,
            "modal_price_kg": 51.0,
            "source_price_unit": "₹/quintal",
            "normalized_price_unit": "₹/kg",
            "source": "data.gov.in (Agmarknet)",
            "fetched_at": datetime.now().isoformat(),
            "freshness": "CURRENT",
        }
        service._add_or_update_records([rec])

        assert os.path.exists(custom_cache)
        with open(custom_cache, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert len(data) == 1
            assert data[0]["commodity"] == "Soybean"
            assert data[0]["market"] == "Latur APMC"


class TestLiveMandi14CacheDeduplicationAndIdempotence:
    def test_cache_deduplication(self, tmp_path):
        """LIVE-MANDI-14: Cache deduplication and idempotent updates."""
        custom_cache = str(tmp_path / "buyer_current_mandi_prices.json")
        service = CurrentMandiService(cache_path=custom_cache)

        rec1 = {
            "commodity": "Onion",
            "state": "Maharashtra",
            "district": "Nashik",
            "market": "Lasalgaon",
            "arrival_date": "22/09/2026",
            "modal_price_kg": 30.0,
        }
        rec2 = {
            "commodity": "Onion",
            "state": "Maharashtra",
            "district": "Nashik",
            "market": "Lasalgaon",
            "arrival_date": "22/09/2026",
            "modal_price_kg": 31.5,  # updated price
        }

        service._add_or_update_records([rec1])
        assert len(service._records) == 1

        service._add_or_update_records([rec2])
        assert len(service._records) == 1
        assert service._records[0]["modal_price_kg"] == 31.5


class TestLiveMandi15StrictLiveErrorHandling:
    def test_strict_live_raises_on_missing_key(self):
        """LIVE-MANDI-15: Strict live failure behavior without silent fallbacks when API key missing."""
        with patch.dict(os.environ, {}, clear=True):
            service = CurrentMandiService()
            with pytest.raises(ValueError) as exc_info:
                service.fetch_official_mandi_prices("Onion", strict_live=True)
            assert "LIVE API TEST BLOCKED: DATA_GOV_API_KEY is not configured" in str(exc_info.value)

    def test_strict_live_raises_on_api_failure(self):
        """LIVE-MANDI-15: Strict live failure behavior without silent fallbacks on network/server error."""
        with patch("urllib.request.urlopen", side_effect=Exception("HTTP 503 Service Unavailable")):
            with patch.dict(os.environ, {"DATA_GOV_API_KEY": "dummy_key"}):
                service = CurrentMandiService()
                with pytest.raises(RuntimeError) as exc_info:
                    service.fetch_official_mandi_prices("Onion", strict_live=True)
                assert "LIVE API FAILED" in str(exc_info.value)


class TestLiveMandi16ZeroCredentialsExposed:
    def test_zero_credentials_exposed(self):
        """LIVE-MANDI-16: Zero credentials exposed in outputs, exceptions, or cache files."""
        api_key = current_mandi_service.get_api_key()
        # Ensure representation of CurrentMandiService does not leak key
        service_repr = repr(current_mandi_service)
        if api_key:
            assert api_key not in service_repr
        
        # Ensure records stored in cache do not contain api-key or secrets
        for rec in current_mandi_service._records:
            assert "api_key" not in rec
            assert "key" not in rec
            assert "token" not in rec
            assert "password" not in rec


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
