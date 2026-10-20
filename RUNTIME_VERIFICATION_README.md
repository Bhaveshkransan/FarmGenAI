# FarmGenAI — Independent Runtime Verification Guide

This guide provides instructions for independently verifying the **FarmGenAI (AgriNegotiator)** Multi-Agent Procurement and Autonomous Negotiation Platform.

---

## 1. Unpacking the Package
Extract the archive into your working directory:
```bash
unzip farmgenai_complete_runtime_verification.zip -d farmgenai
cd farmgenai
```

---

## 2. Installing Dependencies (100% Offline via Pre-Packaged Wheels)
The `wheels/` directory contains all Python wheels required for offline installation in both Linux x86_64 (e.g. ChatGPT Code Interpreter / Ubuntu sandbox) and Windows environments:

```bash
# Option A: Install directly from the included wheels folder (No internet required!)
pip install wheels/*.whl

# Option B: Use pip find-links offline
pip install --no-index --find-links=wheels -r requirements.txt
```

---

## 3. Environment Configuration
Copy the provided deterministic test configuration:
```bash
cp .env.test .env
```
Default testing flags:
- `ENABLE_LLM=false`: Directs all agents (Buyer, Transport, Warehouse, Processor, Farmer) to execute via deterministic rule-based engines with zero token costs and zero external LLM API dependencies.
- `DATABASE_URL=sqlite+aiosqlite:///agrinegotiator.db`: Connects to local persistent asynchronous SQLite.
- `TESTING=1`: Enables test bypasses for external network calls (e.g. OSRM, live weather).

---

## 4. Run the Automated 35-Step E2E Verification
Execute the automated end-to-end runner:
```bash
# Python runner (Linux, macOS, Windows):
python scripts/run_full_local_e2e.py

# OR Bash runner (Linux / macOS):
bash scripts/run_full_local_e2e.sh
```

### What this runner verifies automatically:
1. **Environment Setup**: Validates `ENABLE_LLM=false` and SQLite configurations.
2. **Database Schema**: Executes `init_db()` to create/migrate all SQLAlchemy async tables.
3. **Seed Data**: Loads 110 transporters, warehouse catalog, crop references, and mandi rates.
4. **FastAPI & ASGI Client**: Spins up in-process API client.
5. **Authentication**: Generates valid JWT tokens for buyers and adversarial attackers.
6. **Buyer Requirement**: Stores requirement in database (`quantity=1000kg`, `crop=Soybean`).
7. **Authoritative Farmer Deal**: Records valid farmer deal (`agreed_price=₹47.5/kg`).
8. **Farmer Deal Gate**: Verifies downstream services are locked until deal exists.
9. **Agent Selection**: Updates selected downstream agents (`TRANSPORT`, `WAREHOUSE`, `PROCESSOR`).
10. **Transport Agent**: Executes real LangGraph workflow (freight calculation, route distance, cost).
11. **Transport Outcome**: Verifies structured `AgentOutcome` envelope (status, cost, execution_id).
12. **Warehouse Agent**: Executes real capacity and cold/dry compatibility ranking.
13. **Warehouse Outcome**: Verifies structured `AgentOutcome` envelope.
14. **Processor Agent**: Executes real crop milling/grading/yield logic.
15. **Processor Outcome**: Verifies structured `AgentOutcome` envelope.
16. **Aggregation**: Aggregates all outcomes into final supply chain state.
17. **Final Procurement Plan**: Generates `final_plan` with cost breakdown and cryptographic SHA-256 signature hash.
18. **Durable Persistence**: Commits `final_plan` and multi-agent state to SQLite.
19. **Process Termination**: Wipes application memory and disposes DB engine.
20. **Cold Restart**: Spawns fresh engine and recovers state from disk.
21. **Restart Recovery**: Proves `final_plan`, `agent_outcomes`, and `completed_agents` survived restart.
22. **RBAC Security**: Proves non-owners receive `HTTP 403 Forbidden` and unauthenticated receive `HTTP 401/403`.
23. **Transition Validation**: Proves invalid steps and downstream execution without a deal are rejected with `HTTP 400 Bad Request`.
24. **Failure Propagation**: Verifies non-zero errors and `status="FAILED"` propagation.
25. **Pytest Suite**: Runs 9/9 regression tests in subprocess.
26. **Frontend Verification**: Confirms package.json and React 18 UI components.

---

## 5. Running Pytest Test Suites
To run specific test suites:
```bash
# 1. Security Authorization & Plan Persistence Suite (9 tests):
python -m pytest tests/test_buyer_workflow_security_and_persistence.py -v

# 2. Buyer Acceptance Suite (Flows A through G):
python -m pytest tests/test_buyer_multi_agent_acceptance.py -v

# 3. Phase 1 Buyer State Machine Suite (15 tests):
python -m pytest tests/test_buyer_state_machine_p1.py -v

# 4. Run all buyer workflow tests together:
python -m pytest tests/test_buyer_workflow_security_and_persistence.py tests/test_buyer_multi_agent_acceptance.py tests/test_buyer_state_machine_p1.py -v
```

---

## 6. Frontend Compilation & UI Verification
If Node.js (v18+) is available:
```bash
cd frontend
npm install
npm run build
```
This runs TypeScript checking (`tsc`) and Vite bundling to produce the production distribution in `frontend/dist`.

---

## 7. Known Architectural Discrepancies & Implementations
1. **Transport Agent Graph Node Count**:
   - The compiled LangGraph StateGraph in `backend/agents/transport_agent/graph.py` contains **exactly 12 nodes**:
     `receive_transport_request`, `validate_request`, `check_vehicle_availability`, `filter_vehicles`, `recommend_vehicles`, `calculate_route`, `calculate_cost`, `calculate_profit`, `calculate_floor_price`, `negotiate`, `final_validation`, `generate_transport_plan`.
   - Historical documentation references an "11-node graph", but the live production implementation adds `receive_transport_request` as the 12th entry-point node.
2. **Database Engine Fallback**:
   - In `backend/db/session.py`, if PostgreSQL is not reachable or `TESTING=1`, `DATABASE_URL` automatically falls back to `sqlite+aiosqlite:///agrinegotiator.db`.
   - This ensures full persistence to disk even without a running PostgreSQL server.
3. **Deterministic Testing Guarantee**:
   - All tests run offline with `ENABLE_LLM=false`. No Gemini or OpenAI API keys are required.
