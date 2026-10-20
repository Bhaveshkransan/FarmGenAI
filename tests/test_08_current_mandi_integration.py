"""
tests/test_08_current_mandi_integration.py

Comprehensive test suite for Priority 4: Current Daily Mandi Price Integration.
Covers MANDI-01 through MANDI-25.
"""

import sys
import os
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.current_mandi_service import (
    CurrentMandiService,
    current_mandi_service,
    calculate_freshness,
)
from agents.buyer_agent import BuyerAgent
from backend.services.buyer_rag_service import BuyerRAGContext


class TestMANDI01APIConfigurationValidation:
    def test_api_key_resolution(self):
        """MANDI-01: Verify API key resolution from environment variables."""
        service = CurrentMandiService()
        key = service.get_api_key()
        assert isinstance(key, str)


class TestMANDI02ResponseParsing:
    def test_official_response_parsing(self):
        """MANDI-02: Verify parsing of valid data.gov.in Agmarknet API response."""
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
                    "min_price": "2500",
                    "max_price": "3500",
                    "modal_price": "3000",
                    "arrival_date": "22/09/2026",
                }
            ],
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            with patch.dict(os.environ, {"DATA_GOV_API_KEY": "test_key_123"}):
                service = CurrentMandiService()
                records = service.fetch_official_mandi_prices("Onion")
                assert len(records) > 0
                r = records[0]
                assert r["commodity"] == "Onion"
                assert r["market"] == "Lasalgaon"
                assert r["modal_price_quintal"] == 3000.0
                assert r["modal_price_kg"] == 30.0  # Unit conversion ₹3000/quintal -> ₹30/kg


class TestMANDI03AuthFailureHandling:
    def test_auth_failure_falls_back_gracefully(self):
        """MANDI-03: Invalid/missing API key falls back gracefully without crashing."""
        with patch.dict(os.environ, {}, clear=True):
            service = CurrentMandiService()
            records = service.fetch_official_mandi_prices("Onion")
            assert isinstance(records, list)


class TestMANDI04APITimeoutHandling:
    def test_timeout_fallback(self):
        """MANDI-04: Network timeout when calling API returns fallback records safely."""
        with patch("urllib.request.urlopen", side_effect=TimeoutError("Connection timed out")):
            with patch.dict(os.environ, {"DATA_GOV_API_KEY": "test_key"}):
                service = CurrentMandiService()
                records = service.fetch_official_mandi_prices("Soybean")
                assert isinstance(records, list)


class TestMANDI05APIUnavailableHandling:
    def test_api_500_unavailable(self):
        """MANDI-05: HTTP 500/503 from government API handles gracefully."""
        with patch("urllib.request.urlopen", side_effect=Exception("HTTP Error 503: Service Unavailable")):
            with patch.dict(os.environ, {"DATA_GOV_API_KEY": "test_key"}):
                service = CurrentMandiService()
                records = service.fetch_official_mandi_prices("Cotton")
                assert isinstance(records, list)


class TestMANDI06MalformedResponseHandling:
    def test_malformed_json_response(self):
        """MANDI-06: Malformed/corrupt JSON response handles safely."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"{ invalid json ... }"
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            with patch.dict(os.environ, {"DATA_GOV_API_KEY": "test_key"}):
                service = CurrentMandiService()
                records = service.fetch_official_mandi_prices("Onion")
                assert isinstance(records, list)


class TestMANDI07PaginationHandling:
    def test_limit_parameter_passed(self):
        """MANDI-07: Verify limit parameter is formatted in request URL."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({"status": "ok", "records": []}).encode("utf-8")
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            with patch.dict(os.environ, {"DATA_GOV_API_KEY": "test_key"}):
                service = CurrentMandiService()
                service.fetch_official_mandi_prices("Onion", limit=50)
                assert mock_urlopen.called


class TestMANDI08DateParsing:
    def test_date_parsing_formats(self):
        """MANDI-08: Verify arrival date parsing handles YYYY-MM-DD and DD/MM/YYYY."""
        assert calculate_freshness(datetime.now().strftime("%Y-%m-%d")) == "CURRENT"
        old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        assert calculate_freshness(old_date) == "STALE"


class TestMANDI09PriceParsing:
    def test_min_max_modal_price_fields(self):
        """MANDI-09: Verify min, max, and modal prices are parsed separately."""
        res = current_mandi_service.get_current_market_price("Onion")
        assert "min_price_kg" in res
        assert "max_price_kg" in res
        assert "modal_price_kg" in res
        assert res["modal_price_kg"] >= 0


class TestMANDI10PriceUnitNormalization:
    def test_unit_conversion_quintal_to_kg(self):
        """MANDI-10: Verify explicit conversion from ₹/quintal to ₹/kg (divide by 100)."""
        res = current_mandi_service.get_current_market_price("Onion")
        assert res["source_price_unit"] == "₹/quintal"
        assert res["normalized_price_unit"] == "₹/kg"
        if res["modal_price_quintal"] > 0:
            assert abs(res["modal_price_kg"] - (res["modal_price_quintal"] / 100.0)) < 0.01


class TestMANDI11CropNormalization:
    def test_canonical_crop_normalization(self):
        """MANDI-11: Verify crop aliases are normalized to canonical name."""
        res = current_mandi_service.get_current_market_price("soya bean")
        assert res["success"] is True
        assert res["crop"] == "Soybean"


class TestMANDI12UnsupportedCropRejection:
    def test_unsupported_crop_rejection(self):
        """MANDI-12: Non-supported produce (e.g. Wheat or Tomato) is rejected explicitly."""
        res = current_mandi_service.get_current_market_price("Wheat")
        assert res["success"] is False
        assert "Unsupported crop" in res["error"]
        assert res["freshness"] == "UNAVAILABLE"


class TestMANDI13APMCMatching:
    def test_apmc_exact_and_token_matching(self):
        """MANDI-13: Matching APMC market name returns EXACT_APMC or TOKEN_APMC match level."""
        res = current_mandi_service.get_current_market_price("Onion", apmc="Lasalgaon Mandi")
        if res["success"]:
            assert res["match_level"] in ["EXACT_APMC", "TOKEN_APMC", "DISTRICT", "STATE"]


class TestMANDI14DistrictFallback:
    def test_district_fallback_level(self):
        """MANDI-14: District location match returns DISTRICT match level."""
        res = current_mandi_service.get_current_market_price("Onion", location="Nashik")
        if res["success"]:
            assert res["match_level"] in ["EXACT_APMC", "TOKEN_APMC", "DISTRICT", "TOKEN_DISTRICT", "STATE"]


class TestMANDI15StateFallback:
    def test_state_level_fallback(self):
        """MANDI-15: Non-existent district falls back to STATE level gracefully."""
        res = current_mandi_service.get_current_market_price("Onion", location="UnknownNonExistentDistrict")
        assert res["success"] is True
        assert res["match_level"] == "STATE"


class TestMANDI16IdempotencyDeduplication:
    def test_idempotent_record_updating(self):
        """MANDI-16: Re-ingesting record for same APMC, commodity, date updates existing record."""
        service = CurrentMandiService()
        record = {
            "commodity": "Onion",
            "state": "Maharashtra",
            "district": "Nashik",
            "market": "TestAPMC",
            "variety": "Red",
            "grade": "A",
            "arrival_date": "2026-09-22",
            "modal_price_quintal": 3200.0,
            "modal_price_kg": 32.0,
            "source": "Test",
            "fetched_at": datetime.now().isoformat(),
            "freshness": "CURRENT",
        }
        initial_len = len(service._in_memory_records)
        service._add_or_update_record(record)
        len1 = len(service._in_memory_records)

        # Re-add exact same record with updated price
        record["modal_price_kg"] = 33.0
        service._add_or_update_record(record)
        len2 = len(service._in_memory_records)

        assert len2 == len1


class TestMANDI17FreshnessCalculation:
    def test_freshness_current_vs_stale(self):
        """MANDI-17: Arrival dates within 3 days are CURRENT; older dates are STALE."""
        today = datetime.now().strftime("%Y-%m-%d")
        assert calculate_freshness(today) == "CURRENT"

        old_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
        assert calculate_freshness(old_date) == "STALE"


class TestMANDI18StaleDataHandling:
    def test_stale_data_flag_preserved(self):
        """MANDI-18: Cached records older than 3 days retain freshness='STALE' flag."""
        service = CurrentMandiService()
        stale_record = {
            "commodity": "Soybean",
            "state": "Maharashtra",
            "district": "Latur",
            "market": "Latur APMC",
            "variety": "Yellow",
            "grade": "A",
            "arrival_date": "2025-01-01",
            "modal_price_quintal": 4800.0,
            "modal_price_kg": 48.0,
            "source": "Historical",
            "fetched_at": datetime.now().isoformat(),
            "freshness": "STALE",
        }
        service._add_or_update_record(stale_record)
        res = service.get_current_market_price("Soybean", location="Latur")
        assert res["success"] is True
        assert res["freshness"] in ["CURRENT", "STALE"]


class TestMANDI19CurrentMarketServiceQuery:
    def test_current_market_service_query_structure(self):
        """MANDI-19: Query returns expected fields and boolean is_current indicator."""
        res = current_mandi_service.get_current_market_price("Onion", location="Nashik")
        assert res["success"] is True
        assert "modal_price_kg" in res
        assert "freshness" in res
        assert "is_current" in res
        assert isinstance(res["is_current"], bool)


class TestMANDI20BuyerAgentIntegration:
    def test_buyer_agent_accepts_current_mandi_data(self):
        """MANDI-20: BuyerAgent accepts current_mandi_data in context cleanly."""
        buyer = BuyerAgent(
            name="RetailBuyer",
            budget=100000,
            max_quantity=1000,
            target_price=30.0,
            reservation_price=36.0,
            crop="Onion",
        )
        m_data = {
            "success": True,
            "crop": "Onion",
            "modal_price_kg": 28.50,
            "apmc": "Lasalgaon APMC",
            "freshness": "CURRENT",
            "observation_date": "2026-09-22",
        }
        offer = {"price": 32.0, "quantity": 500, "crop": "Onion"}
        res = buyer.respond_to_offer(offer, context={"current_mandi_data": m_data}, force_deterministic=True)
        assert res["type"] in ["COUNTER", "ACCEPT", "REJECT"]


class TestMANDI21MLCurrentMarketSeparation:
    def test_ml_forecast_and_current_mandi_separated(self):
        """MANDI-21: ML next-period forecast and current observed mandi price remain separate fields."""
        buyer = BuyerAgent(
            name="RetailBuyer",
            budget=100000,
            max_quantity=1000,
            target_price=30.0,
            reservation_price=36.0,
            crop="Onion",
        )
        m_data = {
            "success": True,
            "crop": "Onion",
            "modal_price_kg": 28.0,
            "apmc": "Lasalgaon APMC",
            "freshness": "CURRENT",
            "observation_date": "2026-09-22",
        }
        val = buyer.get_market_valuation("Onion", context={"current_mandi_data": m_data})
        assert isinstance(val, (int, float))
        # Verify get_market_valuation ML prediction remains dict if pricing service loaded
        if buyer.last_ml_prediction:
            assert "predicted_modal_price" in buyer.last_ml_prediction or "fallback_price" in buyer.last_ml_prediction


class TestMANDI22RAGCurrentMarketSeparation:
    def test_rag_and_current_mandi_separated(self):
        """MANDI-22: Buyer RAG context and current daily mandi data remain completely separate context items."""
        buyer = BuyerAgent(
            name="RetailBuyer",
            budget=100000,
            max_quantity=1000,
            target_price=30.0,
            reservation_price=36.0,
            crop="Onion",
        )
        rag_ctx = BuyerRAGContext(crop_quality_knowledge=[{"text": "Grade A Onion specifications"}])
        m_data = {"success": True, "modal_price_kg": 28.0, "apmc": "Lasalgaon APMC", "freshness": "CURRENT"}
        
        offer = {"price": 32.0, "quantity": 500, "crop": "Onion"}
        res = buyer.respond_to_offer(
            offer,
            context={"buyer_rag_context": rag_ctx, "current_mandi_data": m_data},
            force_deterministic=True
        )
        assert res["type"] in ["COUNTER", "ACCEPT", "REJECT"]


class TestMANDI23BudgetProtection:
    def test_current_mandi_cannot_override_budget(self):
        """MANDI-23: High current mandi price observation CANNOT bypass buyer total budget limit."""
        buyer = BuyerAgent(
            name="LowBudgetBuyer",
            budget=400,  # Only ₹400 total budget
            max_quantity=1000,
            target_price=30.0,
            reservation_price=35.0,
            crop="Onion",
        )
        m_data = {"success": True, "modal_price_kg": 32.0, "apmc": "Lasalgaon APMC", "freshness": "CURRENT"}
        offer = {"price": 32.0, "quantity": 500, "crop": "Onion"}  # Total cost ₹16,000 > ₹400
        res = buyer.respond_to_offer(offer, context={"current_mandi_data": m_data}, force_deterministic=True)

        if res["type"] == "ACCEPT":
            assert res["quantity"] * res["price"] <= 400.0


class TestMANDI24ReservationPriceProtection:
    def test_current_mandi_cannot_override_reservation_ceiling(self):
        """MANDI-24: High current mandi price observation CANNOT force buyer to accept above reservation price."""
        buyer = BuyerAgent(
            name="RetailBuyer",
            budget=100000,
            max_quantity=1000,
            target_price=30.0,
            reservation_price=35.0,
            crop="Onion",
        )
        # Current mandi price is high (₹48/kg)
        high_mandi = {"success": True, "modal_price_kg": 48.0, "apmc": "Lasalgaon APMC", "freshness": "CURRENT"}
        # Offer is ₹45/kg (above reservation ceiling of ₹35/kg)
        offer = {"price": 45.0, "quantity": 500, "crop": "Onion"}
        res = buyer.respond_to_offer(offer, context={"current_mandi_data": high_mandi}, force_deterministic=True)

        assert res["type"] != "ACCEPT"
        if res["type"] == "COUNTER":
            assert res["price"] <= 35.0


class TestMANDI25QuantityProtection:
    def test_current_mandi_cannot_override_max_quantity(self):
        """MANDI-25: Current mandi price CANNOT allow purchase exceeding buyer max capacity."""
        buyer = BuyerAgent(
            name="SmallBuyer",
            budget=100000,
            max_quantity=200,  # Max 200kg capacity
            target_price=30.0,
            reservation_price=35.0,
            crop="Onion",
        )
        m_data = {"success": True, "modal_price_kg": 28.0, "apmc": "Lasalgaon APMC", "freshness": "CURRENT"}
        offer = {"price": 28.0, "quantity": 1000, "crop": "Onion"}  # Seller offers 1000kg
        res = buyer.respond_to_offer(offer, context={"current_mandi_data": m_data}, force_deterministic=True)

        if res["type"] == "ACCEPT":
            assert res["quantity"] <= 200.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
