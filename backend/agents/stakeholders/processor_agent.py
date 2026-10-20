"""
backend/agents/stakeholders/processor_agent.py

Processor Stakeholder Agent implementation.
Extends BaseAgent. Replaces the legacy inline logic for processors.
"""

from typing import Dict, Any, Tuple
from backend.agents.common.core import BaseAgent, AgentValidator
from backend.agents.prompts import PROCESSOR_PROMPT

class ProcessorValidator(AgentValidator):
    def validate(self, output: Dict[str, Any], state: Any) -> Tuple[bool, str, Dict[str, Any]]:
        decision = output.get("decision", "REJECT").upper()
        bid = float(output.get("salvage_bid", state.get("min_price", 0.0) * 0.5))
        reason = output.get("reason", "")
        
        corrected = {
            "decision": decision,
            "salvage_bid": bid,
            "reason": reason
        }
        return True, "", corrected


class ProcessorAgent(BaseAgent):
    def __init__(self, agent_id: str, name: str):
        super().__init__(agent_id=agent_id, stakeholder_type="PROCESSOR")
        self.validator = ProcessorValidator()
        self.name = name

    async def build_prompt(self, state: Any) -> str:
        prompt = PROCESSOR_PROMPT.format(
            processor_name=self.name,
            crop=state.get("crop", "Produce"),
            quantity=state.get("quantity", 0),
            location=state.get("location", "Maharashtra"),
            market_price=state.get("market_price", state.get("min_price", 20.0))
        )
        return prompt

    async def process_response(self, response_text: str, state: Any) -> Dict[str, Any]:
        from backend.agents.graph_orchestrator import _parse_json_response
        
        parsed = await _parse_json_response(response_text)
        if not parsed:
            parsed = {"decision": "ACCEPT", "salvage_bid": state.get("min_price", 10.0) * 0.5, "reason": "Failsafe salvage bid."}

        is_valid, error_msg, corrected = self.validator.validate(parsed, state)
        
        corrected["name"] = self.name
        return corrected

    async def generate_salvage_bid(self, context: Dict) -> Dict:
        """Helper to invoke BaseAgent pipeline dynamically"""
        # Bypass workflow block for multi-agent bidding by injecting allowed id
        pseudo_state = {**context, "allowed_agent_set": [self.agent_id]}
        result = await self(pseudo_state)
        
        return {
            "name": result.get("name", self.name),
            "decision": result.get("decision", "ACCEPT"),
            "bid": result.get("salvage_bid", context.get("min_price", 10.0) * 0.5),
            "reason": result.get("reason", "")
        }
