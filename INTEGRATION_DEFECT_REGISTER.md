# Integration Defect Register & Traceability Matrix

**Project:** FarmGenAI Multi-Agent Supply Chain System  
**Baseline Git Commit:** `5b7040a`  
**Current Resolution State:** 100% Resolved (0 Critical, 0 Major Open Defects)  

---

## 1. Summary Defect Metrics

| Severity Level | Identified | Resolved | Outstanding Blockers |
| :--- | :---: | :---: | :---: |
| **Critical (Sev-1)** | 3 | 3 | **0** |
| **Major (Sev-2)** | 3 | 3 | **0** |
| **Minor (Sev-3)** | 2 | 2 | **0** |
| **Total** | **8** | **8** | **0** |

---

## 2. Exhaustive Defect Register

### DEF-01: Unawaited Async Coroutines in Warehouse API Routes
- **Severity:** Sev-1 (Critical)
- **Component:** [backend/routes/warehouse_routes.py](file:///c:/PROJECT/FarmGenAI/backend/routes/warehouse_routes.py)
- **Description:** Calls to `assign_storage(payload)`, `assign_transport(payload)`, and `list_fleet()` lacked the `await` keyword.
- **Impact:** Requests returned unawaited coroutine objects, emitting `RuntimeWarning: coroutine was never awaited`, causing warehouse reservations to fail silently.
- **Root Cause:** Asynchronous functions were invoked synchronously without `await`.
- **Resolution:** Added `await` to lines 31, 40, and 48 of `backend/routes/warehouse_routes.py`.
- **Verification:** Unit tests and HTTP GET/POST queries to `/api/v1/warehouse/*` return 200 OK with resolved JSON objects.

### DEF-02: Isolated Mock Workflows in Downstream Buyer Graph Nodes
- **Severity:** Sev-1 (Critical)
- **Component:** [backend/agents/buyer_graph.py](file:///c:/PROJECT/FarmGenAI/backend/agents/buyer_graph.py)
- **Description:** `warehouse_agent_node` and `processor_agent_node` previously generated static mock dictionaries instead of executing actual domain service logic.
- **Impact:** Real godown capacities and processor yield parameters were never verified during graph execution.
- **Root Cause:** Placeholder stubs were left in place during initial LangGraph topology construction.
- **Resolution:** Integrated `run_warehouse_workflow()` (cold-chain checks, MSWC godown queries, bay reservation) and `run_processor_workflow()` (moisture ceilings, extraction ratios, batch scheduling) into the compiled graph.
- **Verification:** Verified in `tests/test_multi_agent_real_execution.py` (18/18 passed).

### DEF-03: Missing Authoritative Economic Validation in Workflow Completion
- **Severity:** Sev-1 (Critical)
- **Component:** [backend/agents/buyer_graph.py](file:///c:/PROJECT/FarmGenAI/backend/agents/buyer_graph.py)
- **Description:** The workflow completed deals without deterministically verifying that the farmer's net realization ($P_{\text{gross}} - \text{APMC Cess}$) met or exceeded their minimum price floor.
- **Impact:** Theoretical possibility of settling deals that violated statutory MSP protections.
- **Root Cause:** Lack of an explicit Economic Settlement Feasibility Audit node prior to digital contract sealing.
- **Resolution:** Implemented deterministic audit in `workflow_completion_node` calculating gross values, APMC 1.0% cess, logistics expenses, and comparing against floor prices. Cryptographically sealed with SHA-256 digital signature hash.
- **Verification:** Verified in `tests/test_loop2_supply_chain_integration.py` (`test_01_full_five_stage_supply_chain_integration`).

### DEF-04: Static Routing Ignoring Scope and Own Logistics Assets
- **Severity:** Sev-2 (Major)
- **Component:** [backend/services/negotiation_service.py](file:///c:/PROJECT/FarmGenAI/backend/services/negotiation_service.py)
- **Description:** `run_parallel_procurement` executed downstream agents regardless of whether the user selected `SINGLE_AGENT` mode or owned their own transport/storage.
- **Impact:** Single-agent workflows leaked execution into logistics agents, and farmers with their own trucks were charged for unnecessary third-party transport.
- **Root Cause:** Input parameters `workflow_mode`, `permitted_agents`, `has_transport`, and `has_storage` were ignored in the orchestration launcher.
- **Resolution:** Added dynamic policy checks that set `need_transport = False` if `has_transport=True` or `mode == "SINGLE_AGENT"`, and similarly for storage and processing.
- **Verification:** `tests/test_workflow_modes_matrix.py` (10/10 branches verified).

### DEF-05: Frontend Simulated Timers Bypassing Backend Orchestrator
- **Severity:** Sev-2 (Major)
- **Component:** [frontend/src/pages/negotiation/NegotiationRoom.tsx](file:///c:/PROJECT/FarmGenAI/frontend/src/pages/negotiation/NegotiationRoom.tsx)
- **Description:** `runParallelAutonomousNegotiation` used hardcoded `await sleep(...)` mock timers with hardcoded prices instead of invoking the backend's compiled LangGraph graph.
- **Impact:** Frontend showed fabricated simulation rather than actual multi-agent execution results.
- **Root Cause:** Prototype demo code was left in the UI handler.
- **Resolution:** Replaced mock progression with direct `api.post('/negotiations/' + targetNegId + '/parallel-procure', payload)` call, dynamically mapping real candidate bids and confirmed logistics assignments to the UI.
- **Verification:** Live browser verification at `http://localhost:8080/negotiations/neg_49bdbfad` verified actual event updates.

### DEF-06: Loss of Terminal Logs on Page Refresh
- **Severity:** Sev-2 (Major)
- **Component:** [frontend/src/pages/negotiation/NegotiationRoom.tsx](file:///c:/PROJECT/FarmGenAI/frontend/src/pages/negotiation/NegotiationRoom.tsx)
- **Description:** Refreshing the negotiation room reinitialized `liveTerminalLogs` to `[]`, erasing the audit trail.
- **Impact:** Users reloading the page lost visibility into previously completed agent execution stages.
- **Root Cause:** State was held only in React memory without hydrating from `negState.logs` returned by the server.
- **Resolution:** Added `useEffect` state recovery that parses `negState.logs` upon page load or reconnect and restores terminal messages and completed stepper nodes.
- **Verification:** Tested page refresh in browser; verified full terminal log restoration.

### DEF-07: Unpersisted Downstream Plan Fields in Negotiation Status
- **Severity:** Sev-3 (Minor)
- **Component:** [backend/services/negotiation_service.py](file:///c:/PROJECT/FarmGenAI/backend/services/negotiation_service.py)
- **Description:** `get_negotiation_status` returned `transport_plan` but omitted `warehouse_plan`, `processor_plan`, and `end_to_end_deal`.
- **Impact:** Frontend REST queries could not render warehouse and processor agreements after reload.
- **Root Cause:** Field mappings in `get_negotiation_status()` had not been updated after downstream agent integration.
- **Resolution:** Added `warehouse_plan`, `processor_plan`, `end_to_end_deal`, `logs`, and `contract_hash` to the returned dictionary.
- **Verification:** Verified REST endpoint returns all downstream objects.

### DEF-08: Frontend Build Transform Error on Stray Catch Block
- **Severity:** Sev-3 (Minor)
- **Component:** [frontend/src/pages/negotiation/NegotiationRoom.tsx](file:///c:/PROJECT/FarmGenAI/frontend/src/pages/negotiation/NegotiationRoom.tsx)
- **Description:** A duplicate catch block remained after consolidating the async execution handler.
- **Impact:** `npm run build` failed with `Expected ";" but found "catch"`.
- **Root Cause:** Redundant catch block syntax from contiguous code replacement.
- **Resolution:** Consolidated into a single clean `try-catch-finally` block.
- **Verification:** `npm run build` passed cleanly in 9.58s.
