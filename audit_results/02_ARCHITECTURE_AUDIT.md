# FarmGenAI / AgriNegotiator — 02. Architecture & Compiled LangGraph Audit

**Classification:** VERIFIED  

---

## 1. System Topology & Microservices Map

```
+---------------------------------------------------------------------------------------------------+
|                                      CLIENT LAYER (SPA)                                           |
|  React 18 + Vite 5 + TailwindCSS + Lucide Icons + React Query                                    |
|  - FarmerDashboard: Crop Listing, Live Mandi Map, Crop Diagnostics, Copilot AI                   |
|  - NegotiationRoom: Multi-Buyer Cards, Live Concession Chart, LangGraph Node Visualizer           |
+---------------------------------------------------------------------------------------------------+
                                              |  HTTP REST & WebSocket (ws://)
+---------------------------------------------v-----------------------------------------------------+
|                                   FASTAPI API GATEWAY (:8000)                                     |
|  - Auth & RBAC: JWT Bearer Tokens, Role Guard (FARMER, BUYER, TRANSPORTER, AGENT)                 |
|  - Routers: /auth, /farmer, /negotiations, /market, /transport, /warehouse, /health               |
|  - WebSocket Manager: Client Connection Registry, Topic Subscriptions, Broadcast Engine          |
+---------------------------------------------------------------------------------------------------+
                                              |
+---------------------------------------------v-----------------------------------------------------+
|                              LANGGRAPH ORCHESTRATION ENGINE                                       |
|  Compiled State Machine (13 Interconnected Agent Nodes):                                          |
|  1. planner_agent          2. knowledge_manager     3. market_intelligence                         |
|  4. matching_agent         5. farmer_agent          6. buyer_agent                                 |
|  7. rank_responses_agent   8. validator_agent       9. dynamic_routing_agent                       |
|  10. transport_agent       11. warehouse_agent      12. processor_agent    13. reflection_agent   |
+---------------------------------------------------------------------------------------------------+
        |                         |                         |                         |
+-------v---------+       +-------v---------+       +-------v---------+       +-------v---------+
|  POSTGRESQL 16  |       |     REDIS 7     |       |   CHROMADB 0.5  |       | OLLAMA / GEMINI |
|  Authoritative  |       | Task Queue &    |       | 4 Collections:  |       | Multi-Agent LLM |
|  Relational DB  |       | PubSub Cache    |       | agri_knowledge  |       | Fallback Engine |
+-----------------+       +-----------------+       +-----------------+       +-----------------+
```

---

## 2. Compiled LangGraph State Execution Proof

The graph is compiled via `workflow.compile()` in `backend/agents/graph_orchestrator.py` and executed via `ainvoke(initial_state)`.

### Actual Runtime Execution Metrics (from `full_langgraph_runtime_trace.json`):
- **Trace ID:** `trace_master_1791174778`
- **Execution Duration:** `111.388s`
- **Total Logged Events:** `54`
- **Entry Point:** `planner_agent`
- **Exit Point:** `reflection_agent`
- **Final Status:** `ESCALATED_PROCESSING`
- **Selected Buyer:** `Mumbai Exports`
