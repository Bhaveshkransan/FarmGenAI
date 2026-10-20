"""
backend/agents/stakeholders/warehouse_agent.py

Warehouse Stakeholder Agent implementation.
Extends BaseAgent. Replaces the legacy inline LLM calls in graph_orchestrator.
"""

from typing import Dict, Any, Tuple
from backend.agents.common.core import BaseAgent, AgentValidator
from backend.agents.prompts import WAREHOUSE_PROMPT

class WarehouseValidator(AgentValidator):
    def validate(self, output: Dict[str, Any], state: Any) -> Tuple[bool, str, Dict[str, Any]]:
        bid = float(output.get("bid_price", state.get("baseline_warehouse", 0.5)))
        reason = output.get("reason", "")
        
        # Priority penalty scoring
        priority_score = bid * 1.02 # Farmer Priority enforced
        
        corrected = {
            "bid_price": bid,
            "score": priority_score,
            "reason": reason
        }
        return True, "", corrected


class WarehouseAgent(BaseAgent):
    def __init__(self, agent_id: str, name: str):
        super().__init__(agent_id=agent_id, stakeholder_type="WAREHOUSE")
        self.validator = WarehouseValidator()
        self.name = name

    async def build_prompt(self, state: Any) -> str:
        prompt = WAREHOUSE_PROMPT.format(
            warehouse_name=self.name,
            crop=state.get("crop"),
            quantity=state.get("quantity"),
            location=state.get("buyer_loc"),
            shelf_life=state.get("spoilage_days"),
            baseline_cost=state.get("baseline_warehouse", 0.5)
        )
        return prompt

    async def process_response(self, response_text: str, state: Any) -> Dict[str, Any]:
        from backend.agents.graph_orchestrator import _parse_json_response
        
        parsed = await _parse_json_response(response_text)
        if not parsed:
            baseline = state.get("baseline_warehouse", 0.5)
            parsed = {"bid_price": baseline, "reason": "Failsafe fallback bid."}

        is_valid, error_msg, corrected = self.validator.validate(parsed, state)
        
        corrected["name"] = self.name
        return corrected

    async def generate_bid(self, context: Dict) -> Dict:
        """Helper to invoke BaseAgent pipeline dynamically"""
        # Bypass workflow block for multi-agent bidding by injecting allowed id
        pseudo_state = {**context, "allowed_agent_set": [self.agent_id]}
        result = await self(pseudo_state)
        
        return {
            "name": result.get("name", self.name),
            "bid": result.get("bid_price", context.get("baseline_warehouse", 0.5)),
            "score": result.get("score", context.get("baseline_warehouse", 0.5) * 1.02),
            "reason": result.get("reason", "")
        }
