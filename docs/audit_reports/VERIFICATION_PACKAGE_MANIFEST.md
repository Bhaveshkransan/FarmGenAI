# FarmGenAI — Verification Package Manifest

This package is prepared for independent, production-grade runtime verification of the **FarmGenAI (AgriNegotiator)** Multi-Agent Procurement and Autonomous Negotiation System.

---

## 1. Archive & Distribution Specifications
- **Package Name**: `farmgenai_complete_runtime_verification.zip`
- **Target Size**: Under 512 MB (OpenAI ChatGPT upload limit).
- **Placement**: Available directly in `Downloads` (`c:\Users\bhave\Downloads\farmgenai_complete_runtime_verification.zip`) and in `c:\Users\bhave\Downloads\FarmGenAI_ChatGPT_Upload\`.
- **Target Environments**: Linux x86_64 (ChatGPT Code Interpreter sandbox, Ubuntu), macOS, Windows.

---

## 2. Major Included Directories & Contents

| Directory | Contents | Verification Role |
|---|---|---|
| `backend/agents/` | `transport_agent/` (graph.py, nodes.py, state.py, prompts.py), `warehouse_agent/`, `processor_agent/`, `buyer_orchestrator.py`, `farmer_negotiation.py`, `decision_engine.py` | Complete real multi-agent runtimes, LangGraph state graphs, heuristic/ML ranking, AgentOutcome generation. |
| `backend/routes/` | `buyer_requirement_routes.py`, `farmer_routes.py`, `contracts.py`, `auth.py`, `produce_routes.py`, `warehouse_routes.py`, etc. | All REST API endpoints, RBAC authentication checks, workflow stepping, agent selection. |
| `backend/services/` | `buyer_workflow_service.py`, `negotiation_service.py`, `routing_service.py`, `transporter_marketplace_service.py`, `security.py`, etc. | Core orchestration workflows, distance calculations, market matching, security tokens. |
| `backend/repositories/` | `database_repo.py` | Asynchronous SQLAlchemy database operations, workflow persistence, final_plan serialization. |
| `backend/db/` | `models/schema.py`, `models/transport_agent_models.py`, `session.py`, `migrations/` | Database models, dual PostgreSQL/SQLite connection manager with fallback and auto-migrations. |
| `backend/schemas/` | `orchestration_contracts.py` (AgentOutcome, DownstreamAgentContext), `buyer_workflow_schemas.py`, etc. | Canonical Pydantic v2 schemas defining agent contracts and plan envelopes. |
| `backend/dataset/` | `transporters.json`, `warehouses.json`, `buyer_current_mandi_prices.json`, `crop_knowledge.json`, etc. | Real Indian agricultural benchmarks, Maharashtra APMC mandi rates, logistics catalogs. |
| `dataset/` | Mandi prices, crop calendars, MSP data | Agricultural datasets for price forecasting and market matching. |
| `tests/` | 50+ test files including `test_buyer_workflow_security_and_persistence.py`, `test_buyer_multi_agent_acceptance.py`, `test_buyer_state_machine_p1.py`, etc. | Full acceptance, integration, unit, security, and persistence test suites. |
| `frontend/src/` | React 18, Vite, Tailwind CSS components, pages, hooks, contexts | Complete buyer & farmer web interface, multi-agent execution dashboards, contract viewers. |
| `wheels/` | Pre-downloaded `.whl` files | Offline dependencies for zero-internet environments (ChatGPT Code Interpreter sandbox). |
| `scripts/` | `run_full_local_e2e.py`, `run_full_local_e2e.sh`, `download_all_wheels.py` | Automated 35-step runtime verification runner. |

---

## 3. Database Architecture & Persistence
- **Primary Engine**: Asynchronous SQLAlchemy 2.0.
- **Fallback / Test Engine**: Local asynchronous SQLite via `aiosqlite`.
- **Database Fallback Behavior**: In `backend/db/session.py`, if PostgreSQL is not reachable or `TESTING=1`, the engine falls back to `sqlite+aiosqlite:///agrinegotiator.db`.
- **Cold Restart Verification**: Because `agrinegotiator.db` is stored on disk, stopping the process, clearing memory, and restarting verifies that `final_plan`, `agent_outcomes`, and `workflow_status` reliably survive cold restarts.

---

## 4. Multi-Agent System Execution & Graph Structure
- **Buyer Orchestrator**: Manages state, enforces the Authoritative Farmer Deal prerequisite, and orchestrates downstream auxiliary agents.
- **Transport Agent**:
  - Implementation: `backend/agents/transport_agent/graph.py`
  - **Verified Node Count: Exactly 12 nodes** in the LangGraph StateGraph:
    1. `receive_transport_request`
    2. `validate_request`
    3. `check_vehicle_availability`
    4. `filter_vehicles`
    5. `recommend_vehicles`
    6. `calculate_route`
    7. `calculate_cost`
    8. `calculate_profit`
    9. `calculate_floor_price`
    10. `negotiate`
    11. `final_validation`
    12. `generate_transport_plan`
    *(Note: Historical docstrings mention "11-node", but the compiled graph contains 12 active nodes).*
- **Warehouse Agent**: `backend/agents/warehouse_agent/workflow.py` with multi-tier capacity checking and cold/dry compatibility.
- **Processor Agent**: `backend/agents/processor_agent/workflow.py` with batch constraint checking and yield normalization.

---

## 5. Offline Test Configuration
- Configuration file: `.env.test`
- Key settings:
  ```env
  ENABLE_LLM=false
  LLM_PROVIDER=offline_mock
  TESTING=1
  DATABASE_URL=sqlite+aiosqlite:///agrinegotiator.db
  JWT_SECRET_KEY=test-secret-key-32-chars-minimum-abcdef12345
  ```
- **Zero External API Requirement**: When `ENABLE_LLM=false`, all agents execute with deterministic rule-based engines, zero token costs, and zero network latency.

---

## 6. Intentionally Excluded Items (To Respect 512 MB Limit & Security)
- Python virtual environment (`.venv/`): Excluded.
- Node modules (`frontend/node_modules/`): Excluded.
- Git repository history (`.git/`): Excluded (saves ~36 MB).
- Live API keys / credentials: Real OpenAI, Gemini, Groq, MinIO secrets are omitted.

---

## 7. Automated 35-Step Verification Runner
- Python script: `python scripts/run_full_local_e2e.py`
- Bash script: `./scripts/run_full_local_e2e.sh`
- Automates all 35 verification steps end-to-end, testing:
  - Buyer requirement creation
  - Authoritative Farmer Deal gate
  - Transport, Warehouse, and Processor execution
  - AgentOutcome generation
  - Aggregation & final_plan generation
  - Cryptographic SHA-256 contract signing
  - Process stop & cold restart
  - Database recovery & persistence verification
  - Cross-buyer RBAC authorization (HTTP 403)
  - Unauthenticated access rejection (HTTP 401/403)
  - Pytest regression suite
  - Frontend build check
