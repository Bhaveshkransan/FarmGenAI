"""
backend/agents/stakeholders/farmer_agent.py

Farmer Stakeholder Agent implementation.
Extends BaseAgent. Replaces the legacy `agents/farmer_agent.py`.
Enforces strict business rules via FarmerBusinessRules.
"""

from typing import Dict, Any, Tuple
import json
from backend.agents.common.core import BaseAgent, AgentValidator
from backend.core.business_rules import FarmerBusinessRules, StorageRequirementEvaluator
from backend.agents.prompts import FARMER_PROMPT

class FarmerValidator(AgentValidator):
    def validate(self, output: Dict[str, Any], state: Any) -> Tuple[bool, str, Dict[str, Any]]:
        decision = output.get("decision", "COUNTER").upper()
        raw_price = output.get("price") if output.get("price") is not None else output.get("counter_price")
        price = float(raw_price if raw_price is not None else state.get("latest_buyer_offer", state.get("min_price", 0.0)))
        message = output.get("reason", "")
        
        # Hard Rule 1: Min Price Floor
        if decision == "ACCEPT":
            is_valid, reason, action = FarmerBusinessRules.validate_offer(
                offer_price=state.get("latest_buyer_offer", state.get("min_price", 0.0)),
                farmer_min_price=state["min_price"],
                crop=state["crop"]
            )
            if not is_valid:
                return False, reason, {
                    "decision": action,
                    "counter_price": state["min_price"],
                    "reason": f"LLM Override: {reason}"
                }
                
        # Hard Rule 2: Counter Price Math
        if decision == "COUNTER":
            if price < state["min_price"]:
                return False, "Counter price below minimum", {
                    "decision": "COUNTER",
                    "counter_price": state["min_price"],
                    "reason": "Adjusted to minimum price floor."
                }
                
        return True, "", output


class FarmerAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id="farmer_01", stakeholder_type="FARMER")
        self.validator = FarmerValidator()

    async def build_prompt(self, state: Any) -> str:
        from backend.core.constants import SUPPORTED_CROPS
        # Evaluate storage urgency instead of hardcoded `if shelf_life <= 5:`
        storage_urgency = StorageRequirementEvaluator.evaluate(state["spoilage_days"])
        trust_context = state.get("trust_context") or "No trust history available for this buyer."
        
        return FARMER_PROMPT.format(
            crop=state["crop"],
            quantity=state["quantity"],
            min_price=state["min_price"],
            target_price=state.get("target_price") or round(state["min_price"] * 1.2, 2),
            location=state["location"],
            shelf_life=state["spoilage_days"],
            storage_urgency=storage_urgency,
            market_price=state.get("market_price", 0.0),
            buyer_offer=state.get("latest_buyer_offer", 0.0),
            round=state.get("round", 0),
            history=state.get("history", []),
            rag_context=state.get("rag_context") or "No market context available.",
            trust_context=trust_context,
            supported_crops=", ".join(SUPPORTED_CROPS),
            market_intelligence=state.get("market_intelligence") or "Market intelligence not yet available.",
        )

    async def process_response(self, response_text: str, state: Any) -> Dict[str, Any]:
        from backend.agents.graph_orchestrator import _parse_json_response
        
        # 1. Parse Output
        parsed = await _parse_json_response(response_text)
        if not parsed:
            min_p = float(state.get("min_price", 0.0))
            target_p = float(state.get("target_price") or round(min_p * 1.2, 2))
            buyer_p = float(state.get("latest_buyer_offer") or 0.0)
            curr_r = int(state.get("round", 0))
            max_r = int(state.get("max_rounds", 5))

            if buyer_p >= target_p * 0.98 and buyer_p >= min_p:
                parsed = {"decision": "ACCEPT", "counter_price": buyer_p, "reason": "Price meets our target expectation."}
            elif buyer_p >= min_p and (curr_r >= max_r - 1 or abs(target_p - buyer_p) < 0.5):
                parsed = {"decision": "ACCEPT", "counter_price": buyer_p, "reason": "Accepting viable offer at or above minimum price floor."}
            elif buyer_p >= min_p:
                gap = target_p - buyer_p
                counter_p = round(max(min_p, buyer_p + gap * 0.5), 2)
                parsed = {"decision": "COUNTER", "counter_price": counter_p, "reason": "Countering partway towards buyer offer."}
            elif buyer_p > 0:
                parsed = {"decision": "COUNTER", "counter_price": min_p, "reason": "Buyer offer is below minimum floor. Standing firm."}
            else:
                parsed = {"decision": "COUNTER", "counter_price": target_p, "reason": "Initial target ask."}

        # 2. Validate against Business Rules
        is_valid, error_msg, corrected = self.validator.validate(parsed, state)
        if not is_valid:
            parsed = corrected

        decision = parsed.get("decision", "COUNTER")
        # M5 fix: LLM schema uses 'price'; normalize both 'price' and legacy 'counter_price'
        counter_price = (
            parsed.get("price")
            or parsed.get("counter_price")
            or state.get("latest_buyer_offer")
            or state.get("min_price", 0.0)
        )
        try:
            counter_price = float(counter_price)
        except (TypeError, ValueError):
            counter_price = float(state.get("min_price", 0.0))

        # C2 fix: store the full conversational LLM message, not just the short 'reason'
        full_message = parsed.get("message") or parsed.get("reason", "")
        reason = parsed.get("reason") or full_message
        
        current_round = state.get("round", 0)
        logs = [f"👨‍🌾 [Farmer] {decision} ₹{counter_price}/kg: {reason}"]
        history = list(state.get("history", []))
        
        record = {
            "round": current_round,
            "agent": "Farmer",
            "price": counter_price if decision == "COUNTER" else state.get("latest_buyer_offer", state.get("min_price", 0.0)),
            "decision": decision,
            "quantity": state["quantity"],
            "message": full_message,    # C2: full conversational LLM response
            "reason": reason            # short internal summary
        }
        history.append(record)

        if decision == "ACCEPT":
            return {
                "status": "DEAL",
                "history": history,
                "latest_farmer_ask": state.get("latest_buyer_offer", state.get("min_price", 0.0)),
                "logs": logs,
                "round": current_round
            }
        elif decision == "REJECT":
            return {
                "status": "REJECT",
                "history": history,
                "logs": logs,
                "round": current_round
            }
        else:
            return {
                "history": history,
                "latest_farmer_ask": counter_price,
                "logs": logs,
                "round": current_round
            }
