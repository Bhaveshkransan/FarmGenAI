# agents/farmer_agent.py
import random
import math
from agents.base_agent import BaseAgent
from intelligence.llm_client import LLMClient

try:
    llm_client = LLMClient()
except Exception:
    llm_client = None

class FarmerAgent(BaseAgent):

    def __init__(
        self,
        name,
        crop,
        quantity,
        min_price,
        shelf_life,
        location=None,
        min_sale_quantity=100,
        initial_price=None,
        has_storage_option=True,
        has_processor_option=True
    ):

        super().__init__(name, "farmer")

        self.crop = crop
        self.quantity = quantity
        self.location = location

        self.min_price = min_price
        
        if initial_price is not None:
            self.current_price = initial_price
        else:
            self.current_price = min_price + random.randint(2, 4)

        self.shelf_life = shelf_life
        self.min_sale_quantity = min_sale_quantity

        # fallback options
        self.has_storage_option = has_storage_option
        self.has_processor_option = has_processor_option

    def evaluate_offer(self, offer, context=None):
        target = getattr(self, "current_price", self.min_price)
        if offer.get("price", 0) >= target * 0.98:
            return "ACCEPT"
        return "COUNTER"

    def make_offer(self, context=None):
        message = self.log_action(
            f"Selling {self.quantity}kg {self.crop} at ₹{self.current_price}/kg"
        )
        return {
            "price": self.current_price,
            "quantity": self.quantity,
            "message": message
        }

    def _validate_offer_inputs(self, offer):
        """Level 7 Adversarial & Level 2 Quantity Protection"""
        if not isinstance(offer, dict):
            return "REJECT", "Invalid offer format."
            
        price = offer.get("price")
        if price is None or not isinstance(price, (int, float)) or math.isnan(price) or math.isinf(price) or price <= 0:
            return "REJECT", "Invalid price."
            
        qty = offer.get("quantity")
        if qty is None or not isinstance(qty, (int, float)) or math.isnan(qty) or math.isinf(qty) or qty <= 0:
            return "REJECT", "Invalid quantity."
            
        if qty > self.quantity:
            return "COUNTER_QTY", f"I only have {self.quantity}kg available."
            
        if qty < self.min_sale_quantity:
            return "REJECT", f"Minimum sale quantity is {self.min_sale_quantity}kg."
            
        if self.shelf_life <= 0:
            return "REJECT", "Crop has already spoiled and cannot be sold for standard consumption."
            
        return "OK", ""

    def respond_to_offer(self, offer, context=None, force_deterministic=False):
        # 1. Strict Validation (Level 2 & 4: Quantity & Input Protection)
        val_status, val_reason = self._validate_offer_inputs(offer)
        if val_status == "REJECT":
            return {
                "type": "REJECT",
                "price": offer.get("price", 0),
                "quantity": offer.get("quantity", 0),
                "message": self.log_action(f"REJECTED: {val_reason}")
            }
        if val_status == "COUNTER_QTY":
            return {
                "type": "COUNTER",
                "price": self.current_price,
                "quantity": self.quantity,
                "message": self.log_action(f"COUNTER: {val_reason}")
            }

        price = offer["price"]
        req_qty = offer["quantity"]
        market_price = context.get("market_price", self.current_price) if context else self.current_price

        # 2. Hybrid Reasoning (LLM Proposal)
        llm_decision = None
        if llm_client and not force_deterministic:
            prompt = f"""
            You are a farmer negotiating the sale of {req_qty}kg of {self.crop}.
            - Your minimum acceptable price: ₹{self.min_price}
            - Your target/expected price: ₹{self.current_price}
            - Buyer offered price: ₹{price}
            - Market price: ₹{market_price}
            - Shelf life remaining: {self.shelf_life} days
            - Has Storage Option: {self.has_storage_option}
            - Has Processor Option: {self.has_processor_option}
            
            Determine whether to ACCEPT, REJECT, or COUNTER. Provide a counter_price if COUNTER.
            """
            schema = {"decision": "ACCEPT/REJECT/COUNTER", "counter_price": 0, "reason": "string"}
            llm_decision = self.think(prompt, schema)
            
            if not isinstance(llm_decision, dict) or llm_decision.get("decision") not in ["ACCEPT", "REJECT", "COUNTER"]:
                llm_decision = None

        # 3. Deterministic Fallback & Hallucination Enforcement
        if not llm_decision:
            fallback = self._fallback_decision(offer, market_price)
            decision = fallback["decision"]
            counter_price = fallback["counter_price"]
            reason = fallback["reason"]
        else:
            decision = llm_decision.get("decision", "COUNTER")
            counter_price = llm_decision.get("counter_price", self.current_price)
            reason = llm_decision.get("reason", "")
            
            # Hallucination Protection (Level 13: Hard Business Rules)
            # If LLM rejects prematurely in early rounds, counter at floor instead of giving up
            max_r = (context or {}).get("max_rounds", 5)
            curr_r = (context or {}).get("round", 1)
            if decision == "REJECT" and curr_r < max_r and self.shelf_life > 1:
                decision = "COUNTER"
                counter_price = max(self.min_price, self.current_price)
                reason = f"Floor defense: countered at ₹{counter_price}/kg instead of walking away in round {curr_r}."

            if decision == "ACCEPT":
                # Strictly enforce min_price constraint
                if price < self.min_price:
                    decision = "COUNTER"
                    counter_price = self.min_price
                    reason = f"LLM Override: Cannot accept ₹{price} below strict minimum price of ₹{self.min_price}."
                    
            if decision == "COUNTER":
                # Ensure counter price is mathematically valid
                if not isinstance(counter_price, (int, float)) or counter_price <= price or counter_price <= 0:
                    fb = self._fallback_decision(offer, market_price)
                    decision = fb["decision"]
                    counter_price = fb["counter_price"] if fb["counter_price"] else self.min_price
                    reason = "LLM Override: Invalid counter price."
                # Don't counter below min price
                elif counter_price < self.min_price:
                    counter_price = self.min_price
                    reason += " (Adjusted to min price floor)"

        # 4. Final State Update
        if decision == "ACCEPT":
            self.quantity -= req_qty
            return {
                "type": "ACCEPT",
                "price": price,
                "quantity": req_qty,
                "message": self.log_action(f"ACCEPTED ₹{price}/kg: {reason}")
            }
        elif decision == "REJECT":
            return {
                "type": "REJECT",
                "price": price,
                "quantity": req_qty,
                "message": self.log_action(f"REJECTED offer ₹{price}/kg: {reason}")
            }
        elif decision == "COUNTER":
            self.current_price = max(counter_price, self.min_price)
            return {
                "type": "COUNTER",
                "price": self.current_price,
                "quantity": req_qty,
                "message": self.log_action(f"COUNTER ₹{self.current_price}/kg: {reason}")
            }
            
        return {"type": "REJECT", "price": price, "quantity": req_qty, "message": "Failsafe"}

    def _fallback_decision(self, offer, market_price):
        price = offer["price"]
        
        # Level 5 & 16: Urgency & Spoilage Intelligence
        if self.shelf_life <= 1:
            processor_value = self.min_price * 0.7
            if self.has_processor_option and price < processor_value:
                return {"decision": "REJECT", "counter_price": None, "reason": "Offer below processor salvage value. Will send to processor."}
            if price >= self.min_price * 0.8:
                return {"decision": "ACCEPT", "counter_price": None, "reason": "Critical spoilage risk. Accepting offer meeting 80% of minimum price."}
            return {"decision": "REJECT", "counter_price": None, "reason": "Offer is below minimum price, even for distressed sale."}

        # Level 1: Normal Target Resolution
        if price >= self.current_price * 0.98:
            return {"decision": "ACCEPT", "counter_price": None, "reason": "Price meets our target expectation."}
            
        if price >= self.min_price:
            # Level 13: Rational Counter
            gap = self.current_price - price
            counter_price = round(price + (gap * 0.4), 2)  # Fight for higher margin
            counter_price = max(self.min_price, counter_price)
            return {"decision": "COUNTER", "counter_price": counter_price, "reason": "I can meet you part way."}

        # Level 6 & 18: Storage Fallback
        if self.has_storage_option and self.shelf_life >= 10:
             return {"decision": "REJECT", "counter_price": None, "reason": "Offer below minimum. I will store the crop and wait for better market."}
             
        # Level 20: Processor Fallback without critical spoilage
        if self.has_processor_option and price < self.min_price * 0.8:
            return {"decision": "REJECT", "counter_price": None, "reason": "Offer is far below minimum. I will consider processing."}

        # Last resort: Counter at minimum price to protect floor
        return {"decision": "COUNTER", "counter_price": self.min_price, "reason": "Offer is below minimum. Standing firm at my floor price."}