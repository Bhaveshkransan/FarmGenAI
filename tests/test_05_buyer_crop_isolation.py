"""
tests/test_05_buyer_crop_isolation.py
------------------------------------------------------------------------
Verification Suite for Phase 1: 7-Crop Allowlist Isolation & Alias Normalization.

Tests:
  - Canonical 7-crop recognition & normalization
  - Multi-alias resolution (e.g. ganna, kapas, kanda, soya, sorghum, paddy)
  - Strict rejection of unallowlisted crops (Tomato, Wheat, Potato, Maize, Cabbage, etc.)
  - BuyerAgent crop-bound initialization & adversarial crop offer rejection
  - Purchase order crop normalization
  - Official GoI pricing mechanism verification (FRP for Sugarcane, No MSP for Onion)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.crop_catalog import (
    BUYER_SUPPORTED_CROPS,
    normalize_crop_name,
    is_supported_buyer_crop,
    validate_buyer_crop,
    get_crop_benchmark_info,
)
from agents.buyer_agent import BuyerAgent

# Force deterministic testing
import agents.buyer_agent as _ba_mod
_ba_mod.llm_client = None


class TestBuyerCropIsolation(unittest.TestCase):

    # =========================================================================
    # 1. CANONICAL CROPS & ALIAS NORMALIZATION
    # =========================================================================

    def test_all_seven_canonical_crops_supported(self):
        expected_crops = ["Sugarcane", "Soybean", "Cotton", "Jowar", "Onion", "Bajra", "Rice"]
        self.assertEqual(len(BUYER_SUPPORTED_CROPS), 7)
        for crop in expected_crops:
            self.assertTrue(is_supported_buyer_crop(crop), f"Expected {crop} to be supported")
            self.assertEqual(normalize_crop_name(crop), crop)
            self.assertEqual(validate_buyer_crop(crop), crop)

    def test_sugarcane_aliases(self):
        for alias in ["sugarcane", "cane", "ganna", "sugar cane", "sugarcane (ganna)", "OOS"]:
            self.assertEqual(normalize_crop_name(alias), "Sugarcane", f"Failed for {alias}")
            self.assertEqual(validate_buyer_crop(alias), "Sugarcane")

    def test_soybean_aliases(self):
        for alias in ["soybean", "soya", "soyabean", "yellow soybean", "soya bean", "SOY"]:
            self.assertEqual(normalize_crop_name(alias), "Soybean", f"Failed for {alias}")
            self.assertEqual(validate_buyer_crop(alias), "Soybean")

    def test_cotton_aliases(self):
        for alias in ["cotton", "kapas", "raw cotton", "medium staple cotton", "kapaas", "rui"]:
            self.assertEqual(normalize_crop_name(alias), "Cotton", f"Failed for {alias}")
            self.assertEqual(validate_buyer_crop(alias), "Cotton")

    def test_jowar_aliases(self):
        for alias in ["jowar", "sorghum", "maldandi jowar", "jowari", "Jowar (Sorghum)"]:
            self.assertEqual(normalize_crop_name(alias), "Jowar", f"Failed for {alias}")
            self.assertEqual(validate_buyer_crop(alias), "Jowar")

    def test_onion_aliases(self):
        for alias in ["onion", "onions", "kanda", "pyaz", "red onion", "Kanda (Onion)", "pyaaz"]:
            self.assertEqual(normalize_crop_name(alias), "Onion", f"Failed for {alias}")
            self.assertEqual(validate_buyer_crop(alias), "Onion")

    def test_bajra_aliases(self):
        for alias in ["bajra", "pearl millet", "cumbu", "sajje", "bajri", "Bajra (Pearl Millet)"]:
            self.assertEqual(normalize_crop_name(alias), "Bajra", f"Failed for {alias}")
            self.assertEqual(validate_buyer_crop(alias), "Bajra")

    def test_rice_aliases(self):
        for alias in ["rice", "paddy", "dhan", "chawal", "basmati", "common paddy", "Paddy (Common)"]:
            self.assertEqual(normalize_crop_name(alias), "Rice", f"Failed for {alias}")
            self.assertEqual(validate_buyer_crop(alias), "Rice")

    # =========================================================================
    # 2. STRICT REJECTION OF UNSUPPORTED CROPS
    # =========================================================================

    def test_unsupported_crops_rejected(self):
        unsupported = [
            "Tomato", "Wheat", "Potato", "Maize", "Cabbage",
            "Pomegranate", "Turmeric", "Apple", "Mango", "Ginger", "Garlic"
        ]
        for crop in unsupported:
            self.assertFalse(is_supported_buyer_crop(crop), f"{crop} should NOT be supported")
            self.assertIsNone(normalize_crop_name(crop), f"{crop} should normalize to None")
            with self.assertRaises(ValueError):
                validate_buyer_crop(crop)

    # =========================================================================
    # 3. BUYER AGENT INITIALIZATION & CROP CONSTRAINTS
    # =========================================================================

    def test_buyer_agent_init_with_canonical_crop(self):
        buyer = BuyerAgent(
            name="SugarBuyer",
            budget=50000.0,
            max_quantity=10000.0,
            target_price=3.50,
            crop="sugarcane"
        )
        self.assertEqual(buyer.crop, "Sugarcane")
        self.assertEqual(buyer.preferred_crops, ["Sugarcane"])

    def test_buyer_agent_init_with_unsupported_crop_raises_error(self):
        with self.assertRaises(ValueError) as ctx:
            BuyerAgent(
                name="TomatoBuyer",
                budget=50000.0,
                max_quantity=1000.0,
                target_price=20.0,
                crop="Tomato"
            )
        self.assertIn("Unsupported crop 'Tomato'", str(ctx.exception))

    def test_buyer_agent_preferred_crops_normalization(self):
        buyer = BuyerAgent(
            name="MultiBuyer",
            budget=100000.0,
            max_quantity=5000.0,
            target_price=40.0,
            preferred_crops=["ganna", "kapas", "kanda", "Tomato", "Wheat"]
        )
        # Tomato and Wheat must be filtered out, aliases normalized
        self.assertEqual(buyer.preferred_crops, ["Sugarcane", "Cotton", "Onion"])

    # =========================================================================
    # 4. RUNTIME OFFER VALIDATION AGAINST 7 CROPS
    # =========================================================================

    def test_offer_with_unsupported_crop_rejected(self):
        buyer = BuyerAgent(
            name="GeneralBuyer",
            budget=50000.0,
            max_quantity=1000.0,
            target_price=25.0
        )
        for bad_crop in ["Tomato", "Wheat", "Potato", "Cabbage"]:
            resp = buyer.respond_to_offer(
                offer={"price": 20.0, "quantity": 100, "crop": bad_crop},
                context={"market_price": 22.0},
                force_deterministic=True
            )
            self.assertEqual(resp["type"], "REJECT")
            self.assertIn("Unsupported crop", resp["message"])

    def test_offer_with_supported_crop_alias_proceeds(self):
        buyer = BuyerAgent(
            name="SoyBuyer",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=45.0,
            crop="Soybean"
        )
        resp = buyer.respond_to_offer(
            offer={"price": 44.0, "quantity": 500, "crop": "soya"},
            context={"market_price": 46.0, "seller_name": "Farmer Ramesh"},
            force_deterministic=True
        )
        self.assertEqual(resp["type"], "ACCEPT")
        self.assertIn("contract", resp)
        self.assertEqual(resp["contract"]["crop"], "Soybean")

    # =========================================================================
    # 5. GOI PRICING BENCHMARK INTEGRITY
    # =========================================================================

    def test_sugarcane_pricing_is_frp_not_msp(self):
        info = get_crop_benchmark_info("Sugarcane")
        self.assertIsNotNone(info)
        self.assertEqual(info["pricing_mechanism"], "FRP")
        self.assertIsNone(info["msp_price_per_kg"])
        self.assertEqual(info["frp_price_per_kg"], 3.40)

    def test_onion_has_no_central_msp(self):
        info = get_crop_benchmark_info("Onion")
        self.assertIsNotNone(info)
        self.assertEqual(info["pricing_mechanism"], "MANDI_MODAL")
        self.assertIsNone(info["msp_price_per_kg"])
        self.assertIsNone(info["msp_price_per_quintal"])

    def test_msp_crops_have_valid_msp(self):
        for crop in ["Soybean", "Cotton", "Jowar", "Bajra", "Rice"]:
            info = get_crop_benchmark_info(crop)
            self.assertIsNotNone(info)
            self.assertEqual(info["pricing_mechanism"], "MSP")
            self.assertGreater(info["msp_price_per_kg"], 0.0)


if __name__ == "__main__":
    unittest.main()
