# Integration Defect Register & Traceability Matrix

**Project:** FarmGenAI Multi-Agent Supply Chain System  
**Baseline Git Commit:** `5b7040a`  
**Current Resolution State:** 100% Resolved (0 Critical, 0 Major Open Defects)  

---

## 1. Summary Defect Metrics

| Severity Level | Identified | Resolved | Outstanding Blockers |
| :--- | :---: | :---: | :---: |
| **Critical (Sev-1)** | 3 | 3 | **0** |
| **Major (Sev-2)** | 5 | 5 | **0** |
| **Minor (Sev-3)** | 4 | 4 | **0** |
| **Total** | **12** | **12** | **0** |

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

### DEF-09: Missing PostgreSQL Columns for Downstream Plans in `negotiations` Table
- **Severity:** Sev-2 (Major)
- **Component:** [backend/db/models/schema.py](file:///c:/PROJECT/FarmGenAI/backend/db/models/schema.py), [backend/repositories/database_repo.py](file:///c:/PROJECT/FarmGenAI/backend/repositories/database_repo.py)
- **Description:** Table `negotiations` and model `DBNegotiation` lacked columns for `warehouse_plan`, `processor_plan`, `end_to_end_deal`, and `contract_hash`, persisting them strictly in an in-memory dictionary.
- **Impact:** Backend process restarts or database-level cold reloads resulted in lost downstream supply-chain agreements.
- **Root Cause:** Database schema had not been updated after downstream warehouse/processor node integration.
- **Resolution:** Executed PostgreSQL `ALTER TABLE negotiations ADD COLUMN` for `warehouse_plan` (JSON), `processor_plan` (JSON), `end_to_end_deal` (JSON), and `contract_hash` (VARCHAR); declared columns on `DBNegotiation` model; mapped fields in `create_negotiation_async`, `update_negotiation_async`, `get_negotiation_async`, and `list_negotiations_async`.
- **Verification:** Verified by clearing in-memory dictionary cache and reading back records directly from PostgreSQL database; all assertions passed.

### DEF-10: In-Memory `active_negotiations` Cache Desynchronization
- **Severity:** Sev-3 (Minor)
- **Component:** [backend/services/negotiation_service.py](file:///c:/PROJECT/FarmGenAI/backend/services/negotiation_service.py)
- **Description:** `run_parallel_procurement` updated the database layer but did not update the `self.active_negotiations` in-memory dictionary, causing `get_negotiation_status` to serve initial negotiation data when hit.
- **Impact:** REST polling clients occasionally received pre-parallel-procure negotiation dictionaries.
- **Root Cause:** Dictionary mutation omitted in `run_parallel_procurement` completion block.
- **Resolution:** Synchronized `self.active_negotiations` with updated payload in `run_parallel_procurement` and added a fallback merge from the database row in `get_negotiation_status` if cached fields are missing.
- **Verification:** Verified in end-to-end parallel procurement query tests.

### DEF-11: Static Mock Text in Negotiation Room Supply-Chain Modals
- **Severity:** Sev-3 (Minor)
- **Component:** [frontend/src/pages/negotiation/NegotiationRoom.tsx](file:///c:/PROJECT/FarmGenAI/frontend/src/pages/negotiation/NegotiationRoom.tsx), [frontend/src/components/negotiation/TransactionValidationModal.tsx](file:///c:/PROJECT/FarmGenAI/frontend/src/components/negotiation/TransactionValidationModal.tsx)
- **Description:** Direct user invocation of Warehouse and Processor agent buttons (`invokeAgentAction`) generated hardcoded responses ("Pune District Cooperative Dry Godown", "Marathwada Solvent Extractions") without invoking backend REST routes `/api/v1/warehouse/book` and `/api/v1/processor/order`. Furthermore, `TransactionValidationModal` omitted warehouse and processor digital signatures.
- **Impact:** Interactive operator triggers for storage and processing did not communicate with live agent services or persist their reservations into component state and contract previews.
- **Root Cause:** Placeholder dispatch logic in `invokeAgentAction` and static parameter cards in the modal UI.
- **Resolution:** Connected `invokeAgentAction` to `POST /api/v1/warehouse/book` and `POST /api/v1/processor/order` (via `GET /api/v1/processor/matching`), populated `liveWarehousePlan` and `liveProcessorPlan` states, bound dynamic facility and pricing data to modal metric cards, and integrated warehouse and processor signatures into `TransactionValidationModal` and downloadable term sheets.
- **Verification:** Frontend production build passed cleanly (`npm run build`), and contract preview displays dynamic verified signatures.

### DEF-12: Disconnected Redis Stream Producer in Background Negotiations
- **Severity:** Sev-2 (Major)
- **Component:** [backend/core/redis.py](file:///c:/PROJECT/FarmGenAI/backend/core/redis.py), [backend/services/negotiation_service.py](file:///c:/PROJECT/FarmGenAI/backend/services/negotiation_service.py), [backend/routes/negotiation_routes.py](file:///c:/PROJECT/FarmGenAI/backend/routes/negotiation_routes.py), [backend/workers/agent_worker.py](file:///c:/PROJECT/FarmGenAI/backend/workers/agent_worker.py)
- **Description:** `agent_worker.py` and `docker-compose.yml` (`farmgenai-worker`) were designed to consume tasks from Redis Stream `agri:negotiation:jobs`, but no producer in FastAPI called `redis.xadd()`. Background negotiations were executed solely in-process via `asyncio.create_task`, leaving the worker daemon isolated without incoming tasks.
- **Impact:** Distributed worker scaling was inactive in production deployments, and worker daemon remained idle despite active marketplace volume.
- **Root Cause:** Missing `xadd()` publisher call in the negotiation creation lifecycle and lack of consumer group health detection.
- **Resolution:**
  1. Extended `RedisManager` with `enqueue_negotiation_job()`, `has_active_stream_workers()`, and `get_stream_stats()`.
  2. Integrated `enqueue_negotiation_job()` into `start_negotiation()` in `NegotiationService`, returning `stream_job_id` and routing to distributed `agent_worker.py` when active workers are detected or requested, with automatic graceful in-process fallback when offline.
  3. Updated `agent_worker.py`'s `_serialize_result()` to persist downstream `warehouse_plan`, `processor_plan`, and `end_to_end_deal` fields upon job completion.
  4. Added `GET /api/v1/negotiations/stream/status` and `POST /api/v1/negotiations/{negotiation_id}/dispatch-worker` diagnostic endpoints.
- **Verification:** Verified live `xadd` generating stream job IDs in Redis; verified `agent_worker.py` dequeuing `neg_aad5caee` from consumer group `worker_group` and acknowledging with `xack`; all 85 unit and integration tests passed.


