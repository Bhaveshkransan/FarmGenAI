# agents/buyer_agent.py
"""
agents/buyer_agent.py
------------------------------------------------------------------------
Autonomous Buyer Agent for AgriNegotiator.

Architecture:
  1. Multi-Attribute Utility Function (Price, Quantity, Freshness)
  2. Mathematical Concession Generator (Boulware, Linear, Conceder, Aggressive)
  3. Deterministic Safety Guardrails (Budget Protection, Reservation Ceiling P_max)
  4. Hybrid Cognitive Reasoning (LLM Proposal + Deterministic Policy Filter)
  5. Adversarial Input Validation (NaN, Inf, negatives, type errors)
"""

import math
import random
import re
import json
import uuid
from datetime import datetime, timezone
from agents.base_agent import BaseAgent
from intelligence.llm_client import LLMClient
from shared.crop_catalog import (
    BUYER_SUPPORTED_CROPS,
    normalize_crop_name,
    is_supported_buyer_crop,
    validate_buyer_crop,
    get_crop_benchmark_info,
)

try:
    from backend.services.buyer_pricing_service import get_buyer_pricing_service
except Exception:
    try:
        from services.buyer_pricing_service import get_buyer_pricing_service
    except Exception:
        get_buyer_pricing_service = None

try:
    llm_client = LLMClient()
except Exception:
    llm_client = None

BUYER_PERSONAS = {
    "retail_supermarket": {
        "strategy": "boulware",
        "weights": {"price": 0.45, "quantity": 0.25, "freshness": 0.30},
        "min_shelf_life": 4,
        "concession_rate": 0.20,
        "description": "Retail Supermarket Chain prioritizing fresh A-grade produce.",
    },
    "bulk_wholesaler": {
        "strategy": "aggressive",
        "weights": {"price": 0.75, "quantity": 0.20, "freshness": 0.05},
        "min_shelf_life": 2,
        "concession_rate": 0.10,
        "description": "Wholesale Mandi Merchant demanding high volume discounts.",
    },
    "food_processor": {
        "strategy": "conceder",
        "weights": {"price": 0.60, "quantity": 0.35, "freshness": 0.05},
        "min_shelf_life": 1,
        "concession_rate": 0.35,
        "description": "Food Processing Plant accepting ripe produce for immediate processing.",
    },
    "restaurant_kitchen": {
        "strategy": "balanced",
        "weights": {"price": 0.40, "quantity": 0.30, "freshness": 0.30},
        "min_shelf_life": 3,
        "concession_rate": 0.25,
        "description": "Commercial Kitchen requiring regular fresh batch delivery.",
    },
}


class BuyerAgent(BaseAgent):
    """
    Autonomous Procurement Agent acting on behalf of retail, wholesale,
    or commercial agricultural produce buyers.
    """

    def __init__(
        self,
        name: str,
        budget: float,
        max_quantity: float,
        target_price: float,
        location: str | None = None,
        reservation_price: float | None = None,
        strategy: str = "balanced",
        min_shelf_life: int = 2,
        preferred_crops: list[str] | None = None,
        persona: str | None = None,
        crop: str | None = None,
    ):
        # Configure persona-derived attributes if passed
        self.persona = persona if persona in BUYER_PERSONAS else "custom"
        if self.persona in BUYER_PERSONAS:
            p_config = BUYER_PERSONAS[self.persona]
            self.weights = p_config["weights"]
            if strategy == "balanced" and "strategy" in p_config:
                strategy = p_config["strategy"]
            if min_shelf_life == 2 and "min_shelf_life" in p_config:
                min_shelf_life = p_config["min_shelf_life"]
        else:
            self.weights = {"price": 0.60, "quantity": 0.25, "freshness": 0.15}

        super().__init__(name, "buyer", strategy=strategy)

        # Handle backward-compatibility where 5th arg might be reservation_price if float
        if isinstance(location, (int, float)) and reservation_price is None:
            reservation_price = float(location)
            location = None

        self.budget = float(budget)
        self.initial_budget = float(budget)
        self.max_quantity = float(max_quantity)
        self.target_price = float(target_price)

        # Reservation price (P_max / walk-away ceiling)
        if reservation_price is not None:
            self.reservation_price = float(reservation_price)
        else:
            # Default reservation price allows up to 20% premium above target
            self.reservation_price = round(self.target_price * 1.20, 2)

        # Ensure target price does not exceed reservation price
        if self.target_price > self.reservation_price:
            self.reservation_price = self.target_price

        self.location = str(location) if location is not None else None
        self.min_shelf_life = min_shelf_life

        # Strict 7-crop normalization
        if crop is not None:
            self.crop = validate_buyer_crop(crop)
        else:
            self.crop = None

        if preferred_crops:
            norm_crops = []
            for c in preferred_crops:
                norm = normalize_crop_name(c)
                if norm:
                    norm_crops.append(norm)
            self.preferred_crops = norm_crops
        else:
            self.preferred_crops = [self.crop] if self.crop else []

        self.inventory = 0.0

        # Opening bid initialization
        self.current_bid = round(max(1.0, self.target_price * 0.80), 2)
        self.round_count = 0
        self.seller_offer_history: list[float] = []
        self.generated_contracts: list[dict] = []
        self.pricing_service = get_buyer_pricing_service() if get_buyer_pricing_service else None
        self.last_ml_prediction: dict | None = None

    # -------------------------------------------------------------------------
    # Utility Function: Multi-Attribute Preference Scoring
    # -------------------------------------------------------------------------
    def calculate_utility(
        self,
        price: float,
        quantity: float,
        shelf_life: int | None = None,
        quality_grade: str | None = None,
    ) -> float:
        """
        Calculates multi-attribute utility score in range [0.0, 1.0].
        Utility = w_price * PriceUtility + w_qty * QuantityUtility + w_fresh * FreshnessUtility
        Optionally modulated by quality grade (Grade A vs B vs C) based on buyer persona.
        """
        if price > self.reservation_price or price <= 0:
            return 0.0

        # Price utility: 1.0 if at or below target, scales to 0.0 at reservation price
        if price <= self.target_price:
            u_price = 1.0
        else:
            denom = max(0.01, self.reservation_price - self.target_price)
            u_price = max(0.0, (self.reservation_price - price) / denom)

        # Quantity utility: ratio of quantity fulfilling requirement up to max_quantity
        capped_qty = min(quantity, self.max_quantity)
        u_qty = min(1.0, capped_qty / max(1.0, self.max_quantity))

        # Freshness utility: penalize if near expiration
        if shelf_life is not None:
            if shelf_life <= 0:
                return 0.0
            u_fresh = min(1.0, shelf_life / max(1.0, self.min_shelf_life * 2))
        else:
            u_fresh = 1.0

        w_p = self.weights.get("price", 0.60)
        w_q = self.weights.get("quantity", 0.25)
        w_f = self.weights.get("freshness", 0.15)
        base_utility = w_p * u_price + w_q * u_qty + w_f * u_fresh

        # Quality grade modulation if provided
        if quality_grade is not None:
            q_str = str(quality_grade).strip().upper()
            if "A" in q_str or "FAQ" in q_str or "1" in q_str:
                u_qual = 1.0
            elif "B" in q_str or "2" in q_str:
                # Retail supermarkets & kitchens penalize Grade B; processors accept it
                u_qual = 0.60 if self.persona in ["retail_supermarket", "restaurant_kitchen"] else 0.90
            elif "C" in q_str or "3" in q_str:
                # Food processors accept Grade C for pulp/crush; retail rejects it
                u_qual = 0.75 if self.persona == "food_processor" else 0.25
            else:
                u_qual = 0.70
            base_utility = base_utility * (0.60 + 0.40 * u_qual)

        return round(min(1.0, max(0.0, base_utility)), 4)

    # -------------------------------------------------------------------------
    # BATNA, ZOPA & Contract Generation
    # -------------------------------------------------------------------------
    def calculate_batna(
        self,
        market_price: float | None = None,
        transport_buffer: float = 1.50,
        alternative_offers: list[dict] | None = None,
    ) -> float:
        """
        Calculates BATNA (Best Alternative to a Negotiated Agreement).
        - If alternative supplier quotes exist, true BATNA is the minimum alternative price.
        - Otherwise, returns a clearly designated MARKET_REFERENCE_HEURISTIC:
          min(reservation_price, market_price + transport_buffer)
        """
        if alternative_offers:
            valid_alt = [
                float(o["price"]) for o in alternative_offers
                if isinstance(o, dict) and o.get("price") and float(o["price"]) > 0
            ]
            if valid_alt:
                return round(min(min(valid_alt), self.reservation_price), 2)

        if market_price is not None and market_price > 0:
            return round(min(self.reservation_price, market_price + transport_buffer), 2)
        return self.reservation_price

    def get_batna_source_type(self, alternative_offers: list[dict] | None = None) -> str:
        """Distinguishes true alternative quotes from market-reference heuristics."""
        if alternative_offers and any(o.get("price") for o in alternative_offers):
            return "TRUE_ALTERNATIVE_SUPPLIER"
        return "MARKET_REFERENCE_HEURISTIC"

    def check_zopa(self, seller_min_price: float | None) -> tuple[bool, str]:
        """
        Checks Zone of Possible Agreement (ZOPA):
        Seller Minimum Price <= Buyer Reservation Ceiling (P_max)
        """
        if seller_min_price is None or seller_min_price <= 0:
            return True, "ZOPA status unknown (seller minimum price confidential)."
        if seller_min_price <= self.reservation_price:
            surplus = round(self.reservation_price - seller_min_price, 2)
            return True, f"ZOPA exists with positive surplus band of ₹{surplus}/kg."
        return False, f"Negative ZOPA: seller minimum (₹{seller_min_price}/kg) > buyer reservation ceiling (₹{self.reservation_price}/kg)."

    def generate_purchase_order(
        self, price: float, quantity: float, seller_name: str = "Farmer", context: dict | None = None
    ) -> dict:
        """
        Generates formal structured digital purchase order upon reaching DEAL.
        """
        contract_id = f"PO-{uuid.uuid4().hex[:8].upper()}"
        crop_name = context.get("crop") if context else getattr(self, "crop", None)
        normalized_crop = normalize_crop_name(crop_name) if crop_name else (self.crop or "Produce")
        contract = {
            "po_number": contract_id,
            "buyer_name": self.name,
            "buyer_persona": self.persona,
            "seller_name": seller_name,
            "crop": normalized_crop,
            "agreed_price": round(price, 2),
            "agreed_quantity": round(quantity, 2),
            "total_value": round(price * quantity, 2),
            "currency": "INR",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "delivery_window_days": int(context.get("delivery_days", 3)) if context else 3,
            "terms": "Net 7 on delivery inspection. Quality grade verification required.",
            "status": "ISSUED",
        }
        self.generated_contracts.append(contract)
        return contract

    # -------------------------------------------------------------------------
    # Adversarial & Input Validation
    # -------------------------------------------------------------------------
    def _validate_offer_inputs(self, offer: dict, context: dict | None = None) -> tuple[str, str]:
        """
        Guards against malformed, malicious, or unfulfillable offers.
        Enforces strict 7-crop allowlist restriction for BuyerAgent.
        """
        if not isinstance(offer, dict):
            return "REJECT", "Invalid offer format (must be a dictionary)."

        # Strict 7-crop validation
        crop_input = (
            offer.get("crop")
            or (context.get("crop") if context else None)
            or getattr(self, "crop", None)
        )
        if crop_input is not None:
            if not is_supported_buyer_crop(crop_input):
                return "REJECT", (
                    f"Unsupported crop '{crop_input}'. BuyerAgent strictly negotiates only "
                    f"the 7 Maharashtra crops: Sugarcane, Soybean, Cotton, Jowar, Onion, Bajra, Rice."
                )

        price = offer.get("price")
        if (
            price is None
            or not isinstance(price, (int, float))
            or math.isnan(price)
            or math.isinf(price)
            or price <= 0
        ):
            return "REJECT", "Invalid price: must be a positive finite number."

        qty = offer.get("quantity")
        if (
            qty is None
            or not isinstance(qty, (int, float))
            or math.isnan(qty)
            or math.isinf(qty)
            or qty <= 0
        ):
            return "REJECT", "Invalid quantity: must be a positive finite number."

        # Spoilage check from offer or context
        shelf_life = offer.get("shelf_life")
        if shelf_life is None and context:
            shelf_life = context.get("shelf_life", context.get("spoilage_days"))

        if shelf_life is not None and isinstance(shelf_life, (int, float)) and shelf_life <= 0:
            return "REJECT", "Crop has already spoiled and cannot be purchased."

        # Budget exhaustion check
        if self.budget <= 0 or price > self.budget:
            return "REJECT", "Buyer budget is insufficient to purchase even 1 unit."

        return "OK", ""

    # -------------------------------------------------------------------------
    # Interface Methods (get_market_valuation, evaluate_offer, make_offer)
    # -------------------------------------------------------------------------
    def get_market_valuation(
        self,
        crop: str | None = None,
        location: str | None = None,
        context: dict | None = None,
    ) -> float:
        """
        Calculates next-period wholesale modal market valuation using the pre-trained ML model.
        Returns the predicted next modal price (P_modal, t+1) to serve as the market anchor.
        Falls back to context market_price or target_price if ML prediction is unavailable.
        Strictly preserves all economic constraints.
        """
        target_crop = crop or getattr(self, "crop", None)
        if target_crop:
            norm_crop = normalize_crop_name(target_crop)
        else:
            norm_crop = None

        # Lazy service resolution if not yet loaded
        if self.pricing_service is None and get_buyer_pricing_service:
            try:
                self.pricing_service = get_buyer_pricing_service()
            except Exception:
                self.pricing_service = None

        if norm_crop and is_supported_buyer_crop(norm_crop) and self.pricing_service:
            features = None
            feature_meta = None
            if context and isinstance(context.get("market_features"), dict):
                features = context["market_features"]
                feature_meta = context.get("feature_source", {
                    "dataset": "caller_context",
                    "type": "context_market_features",
                    "is_real_data": True,
                })
            elif context and "modal_price_kg" in context:
                features = {
                    col: context[col] for col in self.pricing_service.feature_cols
                    if col in context
                }
                feature_meta = context.get("feature_source", {
                    "dataset": "caller_context",
                    "type": "flat_context_features",
                    "is_real_data": True,
                })

            loc = location or self.location

            # Dynamically resolve features from real APMC historical dataset if missing or incomplete
            if not features or any(col not in features for col in self.pricing_service.feature_cols):
                try:
                    features, feature_meta = self.pricing_service.get_market_features(norm_crop, loc)
                except Exception as e:
                    self.log_action(f"Failed to auto-resolve market features: {e}")
                    features = None

            if features:
                try:
                    pred_res = self.pricing_service.predict_modal_price(
                        norm_crop, features, location=loc, feature_source=feature_meta
                    )
                    self.last_ml_prediction = pred_res
                    predicted_modal = pred_res["predicted_modal_price"]
                    match_info = feature_meta.get("match_level", "APMC record") if feature_meta else "APMC record"
                    self.log_action(
                        f"ML Valuation: Predicted next-period modal price for {norm_crop} is ₹{predicted_modal}/kg (Source: {match_info})"
                    )
                    return float(predicted_modal)
                except Exception as e:
                    self.last_ml_prediction = None
                    self.log_action(f"ML Valuation controlled fallback: {e}")

        # Deterministic fallback when crop is unsupported or prediction is unavailable
        fallback_price = float(context["market_price"]) if (context and context.get("market_price") is not None) else self.target_price
        self.last_ml_prediction = {
            "audit_status": "FALLBACK_USED",
            "is_ml_prediction": False,
            "crop": norm_crop,
            "fallback_price": fallback_price,
            "reason": (
                f"Unsupported crop '{target_crop}'" if (target_crop and not is_supported_buyer_crop(norm_crop or target_crop))
                else "Pricing service unavailable or feature resolution failed"
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return fallback_price

    def evaluate_offer(self, offer: dict, context: dict | None = None) -> str:
        """
        Deterministic evaluation returning 'ACCEPT', 'REJECT', or 'COUNTER'.
        """
        result = self.respond_to_offer(offer, context, force_deterministic=True)
        return result["type"]

    def make_offer(self, context: dict | None = None) -> dict:
        """
        Generates an initial or opening bid informed by the ML market valuation anchor.
        """
        target_crop = (context.get("crop") if context else None) or self.crop
        market_price = self.get_market_valuation(target_crop, self.location, context)

        # Opening bid strategy discount
        if self.strategy == "aggressive":
            discount = 0.75
        elif self.strategy == "conceder":
            discount = 0.90
        elif self.strategy == "boulware":
            discount = 0.78
        else:  # balanced
            discount = 0.82

        base = min(self.target_price, market_price)
        opening_price = round(max(1.0, base * discount), 2)
        opening_price = min(opening_price, self.reservation_price)
        self.current_bid = opening_price

        # Quantity calculation within max capacity and budget
        affordable_qty = math.floor(self.budget / opening_price) if opening_price > 0 else 0
        if affordable_qty <= 0:
            return {
                "type": "REJECT",
                "price": 0.0,
                "quantity": 0.0,
                "message": self.log_action("REJECT: Insufficient budget to make an opening procurement bid."),
                "error": "INSUFFICIENT_BUDGET"
            }
        target_qty = self.max_quantity
        if context and "quantity" in context:
            target_qty = min(self.max_quantity, float(context["quantity"]))

        offer_qty = min(target_qty, affordable_qty)
        if offer_qty <= 0:
            return {
                "type": "REJECT",
                "price": 0.0,
                "quantity": 0.0,
                "message": self.log_action("REJECT: Calculated procurement quantity is zero."),
                "error": "INSUFFICIENT_BUDGET"
            }

        message = self.log_action(
            f"Initial procurement bid: ₹{opening_price}/kg for {offer_qty}kg"
        )

        return {
            "price": opening_price,
            "quantity": offer_qty,
            "message": message,
        }

    # -------------------------------------------------------------------------
    # Cognitive Reasoning with Resilient Multi-Pattern Extraction
    # -------------------------------------------------------------------------
    def think(self, prompt: str, schema: dict = None) -> dict:
        """
        Cognitive reasoning engine for Buyer Agent.
        Supports standard JSON, markdown-fenced JSON, and XML structured tags
        (<decision>, <counter_price>, <reason>) inspired by AgenticPay benchmarks.
        Cleans currency formatting from small models (e.g. Qwen 2.5) and ensures
        confidential reservation pricing is never leaked.
        """
        if not llm_client or not getattr(llm_client, "enabled", False):
            return None

        guided_prompt = prompt + (
            "\n\nCRITICAL INSTRUCTIONS:"
            "\nRespond with either valid JSON or XML tags:"
            "\n<decision>ACCEPT, REJECT, or COUNTER</decision>"
            "\n<counter_price>numeric price (e.g. 21.50)</counter_price>"
            "\n<reason>brief professional market rationale</reason>"
            "\nDO NOT reveal your confidential maximum reservation ceiling to the seller."
        )

        try:
            raw = llm_client.generate(guided_prompt, max_tokens=250)
            if not raw:
                return None

            cleaned = re.sub(r"```(?:json)?", "", raw).strip()

            # 1. Try JSON extraction
            json_match = re.search(r"\{.*?\}", cleaned, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    if isinstance(data, dict):
                        sanitized = self._sanitize_llm_dict(data)
                        if sanitized:
                            return sanitized
                except Exception:
                    pass

            # 2. Try XML-style tag extraction
            dec_match = re.search(r"<decision>\s*([A-Za-z_]+)\s*</decision>", raw, re.IGNORECASE)
            price_match = re.search(r"<counter_price>\s*([^\s<]+)\s*</counter_price>", raw, re.IGNORECASE)
            reason_match = re.search(r"<reason>\s*(.*?)\s*</reason>", raw, re.IGNORECASE | re.DOTALL)

            if dec_match:
                parsed_data = {
                    "decision": dec_match.group(1).upper().strip(),
                    "counter_price": price_match.group(1) if price_match else None,
                    "reason": reason_match.group(1).strip() if reason_match else "Strategic market bid.",
                }
                sanitized = self._sanitize_llm_dict(parsed_data)
                if sanitized:
                    return sanitized

            # 3. Fallback key-value pattern extraction
            dec_line = re.search(r"(?:decision|action)\s*[:=]\s*([A-Za-z]+)", raw, re.IGNORECASE)
            if dec_line:
                d_val = dec_line.group(1).upper()
                p_line = re.search(r"(?:counter_price|price|bid)\s*[:=]\s*([\d.]+)", raw, re.IGNORECASE)
                r_line = re.search(r"(?:reason|message)\s*[:=]\s*(.+)", raw, re.IGNORECASE)
                parsed_data = {
                    "decision": d_val,
                    "counter_price": float(p_line.group(1)) if p_line else None,
                    "reason": r_line.group(1).strip() if r_line else "Market-based counter.",
                }
                sanitized = self._sanitize_llm_dict(parsed_data)
                if sanitized:
                    return sanitized

        except Exception:
            pass

        return None

    def _sanitize_llm_dict(self, data: dict) -> dict:
        """Sanitizes parsed LLM output: standardizes decisions, strips currency symbols."""
        decision = str(data.get("decision", "")).upper().strip()
        if "ACCEPT" in decision:
            decision = "ACCEPT"
        elif "REJECT" in decision:
            decision = "REJECT"
        elif "COUNTER" in decision:
            decision = "COUNTER"
        else:
            return None

        counter_p = data.get("counter_price")
        if counter_p is not None:
            if isinstance(counter_p, (int, float)):
                counter_p = float(counter_p)
            else:
                clean_num = re.sub(r"[^\d.]", "", str(counter_p))
                try:
                    counter_p = float(clean_num) if clean_num else None
                except ValueError:
                    counter_p = None

        reason = str(data.get("reason", "Strategic pricing compromise."))
        if hasattr(self, "reservation_price") and str(self.reservation_price) in reason:
            reason = reason.replace(str(self.reservation_price), "[confidential threshold]")

        return {
            "decision": decision,
            "counter_price": counter_p,
            "reason": reason,
        }

    # -------------------------------------------------------------------------
    # Primary Response Engine (Hybrid: Cognitive LLM + Deterministic Guardrails)
    # -------------------------------------------------------------------------
    def respond_to_offer(
        self,
        offer: dict,
        context: dict | None = None,
        force_deterministic: bool = False,
    ) -> dict:
        self.round_count += 1

        # 1. Strict Input Validation
        val_status, val_reason = self._validate_offer_inputs(offer, context)
        if val_status == "REJECT":
            return {
                "type": "REJECT",
                "price": offer.get("price", 0) if isinstance(offer, dict) else 0,
                "quantity": offer.get("quantity", 0) if isinstance(offer, dict) else 0,
                "message": self.log_action(f"REJECTED: {val_reason}"),
            }

        price = float(offer["price"])
        req_qty = float(offer["quantity"])
        target_crop = offer.get("crop") or (context.get("crop") if context else None) or self.crop
        market_price = self.get_market_valuation(target_crop, self.location, context)
        current_round = int(context.get("round", self.round_count)) if context else self.round_count
        max_rounds = int(context.get("max_rounds", 5)) if context else 5

        # Track seller concession velocity
        self.seller_offer_history.append(price)
        seller_concession = 0.0
        if len(self.seller_offer_history) >= 2:
            seller_concession = round(self.seller_offer_history[-2] - self.seller_offer_history[-1], 2)

        # BATNA threshold
        batna = self.calculate_batna(market_price)

        shelf_life = offer.get("shelf_life")
        if shelf_life is None and context:
            shelf_life = context.get("shelf_life", context.get("spoilage_days"))

        # 2. Hybrid Reasoning (LLM Proposal)
        llm_decision = None
        if llm_client and getattr(llm_client, "enabled", False) and not force_deterministic:
            prompt = f"""
            You are a buyer agent ({self.persona}) negotiating the purchase of agricultural produce.
            - Your target price: ₹{self.target_price}/kg
            - Your maximum reservation price (hard ceiling): ₹{self.reservation_price}/kg
            - Your BATNA outside option: ₹{batna}/kg
            - Your current budget: ₹{self.budget}
            - Maximum quantity needed: {self.max_quantity}kg
            - Seller offered price: ₹{price}/kg for {req_qty}kg
            - Regional market benchmark: ₹{market_price}/kg
            - Produce shelf life: {shelf_life if shelf_life is not None else 'Normal'} days
            - Negotiation round: {current_round} of {max_rounds}

            Decide whether to ACCEPT, REJECT, or COUNTER.
            If COUNTER, provide a realistic counter_price <= ₹{min(self.reservation_price, batna)}.
            """
            schema = {"decision": "ACCEPT/REJECT/COUNTER", "counter_price": 0.0, "reason": "string"}
            try:
                llm_decision = self.think(prompt, schema)
                if not isinstance(llm_decision, dict) or llm_decision.get("decision") not in [
                    "ACCEPT",
                    "REJECT",
                    "COUNTER",
                ]:
                    llm_decision = None
            except Exception:
                llm_decision = None

        # 3. Deterministic Fallback & Hallucination Enforcement
        if not llm_decision:
            fallback = self._fallback_decision(
                offer, market_price, current_round, max_rounds, shelf_life, batna, seller_concession
            )
            decision = fallback["decision"]
            counter_price = fallback["counter_price"]
            reason = fallback["reason"]
        else:
            decision = llm_decision.get("decision", "COUNTER")
            counter_price = llm_decision.get("counter_price", self.current_bid)
            reason = llm_decision.get("reason", "Strategic counter.")

            # Hallucination Override: Never accept a price above reservation price
            if decision == "ACCEPT" and price > self.reservation_price:
                decision = "COUNTER"
                counter_price = min(self.reservation_price, self.current_bid + 1.0)
                reason = "LLM Override: Offer exceeds maximum allowable reservation price."

            # Hallucination Override: Invalid counter price validation
            if decision == "COUNTER":
                if (
                    not isinstance(counter_price, (int, float))
                    or math.isnan(counter_price)
                    or counter_price <= 0
                    or counter_price > self.reservation_price
                    or counter_price >= price
                ):
                    fb = self._fallback_decision(
                        offer, market_price, current_round, max_rounds, shelf_life, batna, seller_concession
                    )
                    decision = fb["decision"]
                    counter_price = fb["counter_price"]
                    reason = fb["reason"]

        # 4. Final Execution & State Update
        if decision == "ACCEPT":
            # Determine maximum purchasable quantity bounded by max_quantity and remaining budget
            affordable_qty = math.floor(self.budget / price)
            purchasable_qty = min(req_qty, self.max_quantity, affordable_qty)

            if purchasable_qty <= 0:
                return {
                    "type": "REJECT",
                    "price": price,
                    "quantity": req_qty,
                    "message": self.log_action("REJECTED: Insufficient budget to fulfill transaction."),
                }

            total_cost = round(purchasable_qty * price, 2)
            self.inventory += purchasable_qty
            self.budget = max(0.0, round(self.budget - total_cost, 2))

            # Auto-generate formal Purchase Order
            seller_name = context.get("seller_name", "Farmer") if context else "Farmer"
            contract = self.generate_purchase_order(price, purchasable_qty, seller_name, context)

            return {
                "type": "ACCEPT",
                "price": price,
                "quantity": purchasable_qty,
                "contract": contract,
                "message": self.log_action(
                    f"ACCEPTED ₹{price}/kg for {purchasable_qty}kg ({contract['po_number']}, Total: ₹{total_cost}): {reason}"
                ),
            }

        elif decision == "REJECT":
            return {
                "type": "REJECT",
                "price": price,
                "quantity": req_qty,
                "message": self.log_action(f"REJECTED offer ₹{price}/kg: {reason}"),
            }

        elif decision == "COUNTER":
            # Guarantee counter does not exceed reservation price and does not exceed offer
            counter_price = min(float(counter_price), self.reservation_price, price - 0.1)
            counter_price = max(1.0, round(counter_price, 2))
            self.current_bid = counter_price

            # Check quantity affordability at counter price
            affordable_qty = math.floor(self.budget / counter_price) if counter_price > 0 else 0
            if affordable_qty <= 0:
                return {
                    "type": "REJECT",
                    "price": price,
                    "quantity": req_qty,
                    "message": self.log_action("REJECTED: Insufficient budget to purchase even 1 unit at counter price."),
                }
            counter_qty = min(req_qty, self.max_quantity, affordable_qty)
            if counter_qty <= 0:
                return {
                    "type": "REJECT",
                    "price": price,
                    "quantity": req_qty,
                    "message": self.log_action("REJECTED: Affordable quantity is zero at counter price."),
                }

            return {
                "type": "COUNTER",
                "price": counter_price,
                "quantity": counter_qty,
                "message": self.log_action(f"COUNTER ₹{counter_price}/kg for {counter_qty}kg: {reason}"),
            }

        return {
            "type": "REJECT",
            "price": price,
            "quantity": req_qty,
            "message": "Failsafe rejection.",
        }

    # -------------------------------------------------------------------------
    # Deterministic Concession Logic
    # -------------------------------------------------------------------------
    def _fallback_decision(
        self,
        offer: dict,
        market_price: float,
        current_round: int = 1,
        max_rounds: int = 5,
        shelf_life: int | None = None,
        batna: float | None = None,
        seller_concession: float = 0.0,
    ) -> dict:
        price = float(offer["price"])
        if batna is None:
            batna = self.calculate_batna(market_price)

        # 1. Direct Target Satisfaction
        # Accept if price is at or below target price
        if price <= self.target_price:
            return {
                "decision": "ACCEPT",
                "counter_price": None,
                "reason": "Offered price meets or beats our procurement target.",
            }

        # Accept if within tight 3% margin of target price
        if price <= round(self.target_price * 1.03, 2):
            return {
                "decision": "ACCEPT",
                "counter_price": None,
                "reason": "Offered price is within acceptable 3% operational tolerance.",
            }

        # 2. Hard Ceiling Walk-Away
        # Reject if offer is astronomically beyond any possible negotiation ground (> 2.5x reservation price)
        if price > self.reservation_price * 2.5:
            return {
                "decision": "REJECT",
                "counter_price": None,
                "reason": "Offered price far exceeds sustainable market pricing and reservation ceiling.",
            }

        # 3. Spoilage Advantage
        # If shelf-life is critical (<= 2 days), farmer is under decay pressure. Hold firm or discount.
        if shelf_life is not None and shelf_life <= 2:
            discounted_target = max(1.0, round(self.target_price * 0.90, 2))
            if price <= discounted_target:
                return {
                    "decision": "ACCEPT",
                    "counter_price": None,
                    "reason": "Accepting discounted produce nearing end of shelf life.",
                }
            # Counter with lower price due to spoilage risk
            counter = min(discounted_target, price - 0.5)
            return {
                "decision": "COUNTER",
                "counter_price": max(1.0, round(counter, 2)),
                "reason": "Produce has low remaining shelf life; price must reflect spoilage risk.",
            }

        # 4. Final Round Resolution
        if current_round >= max_rounds:
            if price <= self.reservation_price:
                return {
                    "decision": "ACCEPT",
                    "counter_price": None,
                    "reason": "Final negotiation round reached; price is within reservation ceiling.",
                }
            return {
                "decision": "REJECT",
                "counter_price": None,
                "reason": "Final round reached without reaching acceptable terms below reservation price.",
            }

        # 5. Strategic Concession Step (Boulware vs Linear vs Conceder)
        round_ratio = min(1.0, current_round / max(1, max_rounds))

        if self.strategy == "boulware":
            # Boulware: concedes slowly at first, accelerates slightly near deadline
            beta = 2.5
            concession_factor = math.pow(round_ratio, beta)
        elif self.strategy == "conceder":
            # Conceder: concedes quickly early on
            beta = 0.5
            concession_factor = math.pow(round_ratio, beta)
        elif self.strategy == "aggressive":
            # Aggressive: minimal movement
            concession_factor = round_ratio * 0.15
        else:  # balanced / linear
            concession_factor = round_ratio * 0.40

        # Reciprocal concession modulation (Tit-for-Tat):
        # If seller is stubborn (zero or negative concession after round 1), slow down concession
        if seller_concession <= 0.0 and current_round > 1:
            concession_factor *= 0.70
        elif seller_concession > 2.0:
            concession_factor = min(1.0, concession_factor * 1.20)

        # Compute next counter bounded by both reservation ceiling and BATNA
        effective_ceiling = min(self.reservation_price, batna)
        spread = min(price, effective_ceiling) - self.current_bid
        step = max(0.5, spread * concession_factor)
        new_counter = round(min(effective_ceiling, self.current_bid + step), 2)

        # Ensure counter is strictly below seller's offer
        if new_counter >= price:
            new_counter = round(price - 0.5, 2)

        # Ensure counter never goes below initial bid
        new_counter = max(self.current_bid, new_counter, 1.0)

        # If counter exceeds reservation price, cap at reservation price or reject
        if new_counter > self.reservation_price:
            if price <= self.reservation_price:
                return {
                    "decision": "ACCEPT",
                    "counter_price": None,
                    "reason": "Accepting at reservation ceiling boundary.",
                }
            return {
                "decision": "REJECT",
                "counter_price": None,
                "reason": "Cannot negotiate beyond reservation ceiling.",
            }

        return {
            "decision": "COUNTER",
            "counter_price": new_counter,
            "reason": f"Proposing compromise bid (Round {current_round}/{max_rounds}) to reach agreement.",
        }