"""
backend/agents/stakeholders/buyer_agent.py

Buyer Stakeholder Agent implementation.
Extends BaseAgent. Replaces the legacy `agents/buyer_agent.py`.
Enforces strict business rules via BuyerBusinessRules.
"""

from typing import Dict, Any, Tuple
from backend.agents.common.core import BaseAgent, AgentValidator

class BuyerValidator(AgentValidator):
    def validate(self, output: Dict[str, Any], state: Any) -> Tuple[bool, str, Dict[str, Any]]:
        decision = output.get("type", "COUNTER").upper()
        price = float(output.get("price", state.get("latest_farmer_ask", 0.0)))
        message = output.get("message", "")
        
        # Hard Rule: Target/Reservation Price Ceiling
        target = state.get("buyer_target_price", 0.0)
        ceiling = target * 1.25 # E.g., max walk-away limit

        if decision == "ACCEPT":
            if state.get("latest_farmer_ask", 0.0) > ceiling:
                return False, "Ask price exceeds maximum budget ceiling.", {
                    "type": "REJECT",
                    "price": state.get("latest_farmer_ask"),
                    "message": f"LLM Override: Ask price {state.get('latest_farmer_ask')} exceeds budget ceiling."
                }
                
        if decision == "COUNTER":
            if price > ceiling:
                return False, "Counter price exceeds maximum budget ceiling.", {
                    "type": "COUNTER",
                    "price": target,
                    "message": "Adjusted to target limit."
                }
                
        return True, "", output


class BuyerAgent(BaseAgent):
    def __init__(self, agent_id: str, name: str, target_price: float, budget: float, max_quantity: float, strategy: str, location: str = None, crop: str = None):
        super().__init__(agent_id=agent_id, stakeholder_type="BUYER")
        self.validator = BuyerValidator()
        self.name = name
        self.target_price = target_price
        self.budget = budget
        self.max_quantity = max_quantity
        self.strategy = strategy
        self.location = location
        self.crop = crop

    async def build_prompt(self, state: Any) -> str:
        # Construct the buyer prompt using state variables
        farmer_ask = state.get("latest_farmer_ask", 0.0)
        
        prompt = f"""
You are {self.name}, an autonomous Buyer Agent.
Your strategy: {self.strategy}
Target Price: ₹{self.target_price}/kg
Budget: ₹{self.budget}
Quantity Requested: {state.get('quantity')} kg

The farmer is asking for ₹{farmer_ask}/kg.
Market Price is ₹{state.get('market_price', 0.0)}/kg.

If the farmer's ask is near your target, ACCEPT.
If the farmer's ask is too high, COUNTER with a lower price.
If it is completely unreasonable, REJECT.

Respond strictly in JSON format:
{{
    "type": "ACCEPT" | "COUNTER" | "REJECT",
    "price": <your_price_float>,
    "message": "<your reasoning>"
}}
"""
        return prompt

    async def process_response(self, response_text: str, state: Any) -> Dict[str, Any]:
        from backend.agents.graph_orchestrator import _parse_json_response
        
        # 1. Parse Output
        parsed = await _parse_json_response(response_text)
        if not parsed:
            parsed = {"type": "COUNTER", "price": self.target_price, "message": "Failsafe fallback"}

        # 2. Validate against Business Rules
        pseudo_state = {**state, "buyer_target_price": self.target_price}
        is_valid, error_msg, corrected = self.validator.validate(parsed, pseudo_state)
        if not is_valid:
            parsed = corrected

        return parsed

    # To be compatible with graph_orchestrator loops
    async def respond_to_offer(self, offer_payload: Dict, context: Dict) -> Dict:
        pseudo_state = {
            "latest_farmer_ask": offer_payload.get("price"),
            "quantity": offer_payload.get("quantity"),
            "market_price": context.get("market_price", 0.0),
            "allowed_agent_set": [self.agent_id], 
        }
        
        result = await self(pseudo_state)
        return result
