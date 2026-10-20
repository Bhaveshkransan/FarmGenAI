"""
backend/core/business_rules.py

Hardcoded business rules and guardrails that no LLM agent is allowed to override.
Provides deterministic enforcement of constraints (inventory, budget, minimum price).
"""

from typing import Dict, Any, Tuple
from backend.core.constants import STATUTORY_BENCHMARKS, get_crop_info

class FarmerBusinessRules:
    @staticmethod
    def validate_offer(offer_price: float, farmer_min_price: float, crop: str) -> Tuple[bool, str, str]:
        """
        Validates if an offer received by the farmer is acceptable based on hard constraints.
        Returns: (is_valid, rejection_reason, action)
        """
        crop_info = get_crop_info(crop)
        display_name = crop_info["display_name"] if crop_info else crop

        # 1. Floor guard: Reject anything below farmer's hard min price
        if offer_price < farmer_min_price:
            return False, f"Offer ₹{offer_price} is below the strict minimum price of ₹{farmer_min_price}.", "REJECT"

        # 2. Statutory guard: Check against MSP / Reference Price
        stat_data = STATUTORY_BENCHMARKS.get(display_name)
        if stat_data:
            benchmark = stat_data["benchmark"]
            if stat_data.get("unit") == "per_quintal":
                benchmark /= 100.0
            # Floor = 35% of benchmark (anti-predatory guard)
            predatory_floor = benchmark * 0.35
            if offer_price < predatory_floor:
                return False, f"Offer ₹{offer_price} is dangerously below the market benchmark (₹{benchmark}). This appears predatory.", "REJECT"

        return True, "", "ACCEPT_OR_COUNTER"

    @staticmethod
    def validate_quantity(requested_quantity: float, available_inventory: float) -> Tuple[bool, str]:
        """Ensures the LLM does not sell more inventory than the farmer has."""
        if requested_quantity > available_inventory:
            return False, f"Requested quantity ({requested_quantity}) exceeds available inventory ({available_inventory})."
        return True, ""


class BuyerBusinessRules:
    @staticmethod
    def validate_bid(proposed_bid: float, target_price: float, max_budget_price: float, crop: str) -> Tuple[bool, float, str]:
        """
        Ensures the buyer agent does not bid above maximum budget or hallucinate prices.
        Returns: (is_valid, corrected_bid, reason)
        """
        crop_info = get_crop_info(crop)
        display_name = crop_info["display_name"] if crop_info else crop

        # 1. Budget ceiling: Cannot bid above absolute maximum budget per unit
        if proposed_bid > max_budget_price:
            return False, max_budget_price, f"Proposed bid (₹{proposed_bid}) capped at max budget (₹{max_budget_price})."

        # 2. Hallucination guard: Target price + 35% or Benchmark + 40%
        ceiling = target_price * 1.35
        stat_data = STATUTORY_BENCHMARKS.get(display_name)
        if stat_data:
            benchmark = stat_data["benchmark"]
            if stat_data.get("unit") == "per_quintal":
                benchmark /= 100.0
            benchmark_ceiling = benchmark * 1.40
            ceiling = max(ceiling, benchmark_ceiling)

        if proposed_bid > ceiling:
            return False, ceiling, f"Proposed bid (₹{proposed_bid}) exceeds hallucination ceiling (₹{ceiling})."

        return True, proposed_bid, ""


class StorageRequirementEvaluator:
    @staticmethod
    def evaluate(spoilage_days: int, target_transit_days: int = 2) -> str:
        """
        Evaluates if warehouse storage or cold chain is required.
        Replaces the hardcoded `if shelf_life <= 5:` logic.
        """
        if spoilage_days <= 3:
            return "URGENT_SALE_OR_COLD_STORAGE"
        elif spoilage_days <= 7:
            if target_transit_days >= 3:
                return "COLD_CHAIN_TRANSPORT"
            return "SELL_PROMPTLY"
        elif spoilage_days <= 14:
            return "AMBIENT_STORAGE_SHORT"
        else:
            return "LONG_TERM_STORAGE_VIABLE"
