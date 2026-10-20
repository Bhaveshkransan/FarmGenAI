"""
backend/agents/common/core.py

Defines the Common Agent Core for the FarmGenAI multi-stakeholder architecture.
All stakeholder agents (Farmer, Buyer, Transport, Warehouse, Processor) extend BaseAgent.
"""

from abc import ABC, abstractmethod
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Tuple
import operator
from langchain_core.messages import BaseMessage


# ─────────────────────────────────────────────
# 1. Common Agent State
# ─────────────────────────────────────────────
class CommonAgentState(TypedDict):
    """
    The baseline state dictionary inherited by all stakeholder-specific states.
    Guarantees trace_id, workflow mode, and messaging primitives are always present.
    """
    # Identity & Trace (P0 standard)
    trace_id: str
    workflow_id: str
    stakeholder: str  # "FARMER", "BUYER", "TRANSPORT", etc.
    workflow_mode: str
    allowed_agent_set: List[str]
    workflow_stage: str
    
    # Context
    rag_context: str
    market_intelligence: str
    
    # Conversational & Event Memory
    history: Annotated[List[BaseMessage], operator.add]
    logs: Annotated[List[str], operator.add]

    # Outcome
    status: str
    reflection: Optional[str]


# ─────────────────────────────────────────────
# 2. Base Agent ABC
# ─────────────────────────────────────────────
class BaseAgent(ABC):
    """
    Abstract Base Class for all stakeholder agents.
    Enforces a standard node signature: async def node(self, state: State) -> dict
    """
    def __init__(self, agent_id: str, stakeholder_type: str):
        self.agent_id = agent_id
        self.stakeholder_type = stakeholder_type

    @abstractmethod
    async def build_prompt(self, state: Any) -> str:
        """Construct the prompt using state and rag_context."""
        pass

    @abstractmethod
    async def process_response(self, response_text: str, state: Any) -> Dict[str, Any]:
        """Parse the LLM response, validate business rules, and prepare state updates."""
        pass

    async def __call__(self, state: Any) -> Dict[str, Any]:
        """The LangGraph node execution entry point."""
        from llm.llm_client import client as llm_client
        import asyncio
        
        logs = list(state.get("logs", []))
        
        # Scope Guardrail: Do not execute if agent is not explicitly permitted
        allowed_agents = state.get("allowed_agent_set", [])
        if allowed_agents and self.agent_id not in allowed_agents:
            logs.append(f"🚫 [{self.stakeholder_type}] Agent '{self.agent_id}' execution skipped (Not permitted by active workflow scope).")
            return {"logs": logs}
            
        logs.append(f"🤖 [{self.stakeholder_type}] Agent activated.")
        
        prompt = await self.build_prompt(state)
        response = await asyncio.to_thread(llm_client.generate, prompt, max_tokens=300)
        
        updates = await self.process_response(response, state)
        
        # Merge logs safely
        if "logs" in updates:
            logs.extend(updates["logs"])
            updates["logs"] = logs
            
        return updates


# ─────────────────────────────────────────────
# 3. Agent Context Assembler
# ─────────────────────────────────────────────
class AgentContext:
    """
    Helper to assemble market, trust, and RAG context specific to the stakeholder.
    """
    @staticmethod
    async def get_stakeholder_context(crop: str, district: str, stakeholder: str) -> str:
        from backend.services.rag_service import rag_service
        
        context_parts = []
        # Base agri knowledge for the crop
        agri_res = rag_service.query_collection("agri_knowledge", f"{crop} best practices", n_results=1)
        if agri_res and agri_res.get("documents") and agri_res["documents"][0]:
            context_parts.append(f"[Agri Knowledge] {agri_res['documents'][0][0]}")
            
        # Strategy memory based on stakeholder
        strat_res = rag_service.query_collection("negotiation_memory", f"successful {stakeholder.lower()} strategies for {crop}", n_results=1)
        if strat_res and strat_res.get("documents") and strat_res["documents"][0]:
            context_parts.append(f"[Past Strategies] {strat_res['documents'][0][0]}")
            
        return "\n\n".join(context_parts) if context_parts else "No specific RAG context available."


# ─────────────────────────────────────────────
# 4. Agent Validator Base
# ─────────────────────────────────────────────
class AgentValidator(ABC):
    """
    Abstract Base Class for stakeholder-specific output validators.
    Wraps the LLM output parser and business rule engines.
    """
    @abstractmethod
    def validate(self, output: Dict[str, Any], state: Any) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Return (is_valid, error_message, corrected_output).
        Must apply business rules (e.g. min_price, budget ceilings).
        """
        pass
