# Instructions for ChatGPT — FarmGenAI Multi-Agent Procurement System

## Overview
This zip bundle contains the complete, crucial source code of **FarmGenAI (AgriNegotiator)**, an end-to-end autonomous multi-agent agricultural procurement and negotiation system.

### Core Architecture
- **Backend**: FastAPI, SQLAlchemy 2.0 (async), LangGraph + deterministic multi-agent state machines, Pydantic v2.
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide icons.
- **Buyer Multi-Agent Orchestration Flow**:
  1. **Buyer Requirement**: Buyer defines crop requirement (crop, quantity, target price, delivery location, deadline).
  2. **Farmer Negotiation Prerequisite**: Buyer negotiates and agrees on base crop price with farmer (`agreed_price`, `quantity`).
  3. **Buyer Orchestrator**: Evaluates service requirements (Transport, Warehouse, Processing).
  4. **Specialized Agents**: 
     - `TransportAgent` (calculates freight, distance, perishability, refrigeration, cold-chain).
     - `WarehouseAgent` (calculates storage duration, spoilage mitigation, humidity control).
     - `ProcessorAgent` (calculates grading, milling, packaging, moisture normalization).
  5. **Agent Outcomes**: Each agent returns structured `AgentOutcome` with cost, delivery days, risks, and counter-proposals.
  6. **Buyer Aggregator**: Combines farmer base contract + service agent outcomes into an optimized procurement plan.
  7. **Durable Persistence**: Saves `final_plan` JSON and status to SQLite/PostgreSQL.
  8. **Contract Finalization**: Generates binding tripartite/multipartite contract.

---

## 1. What Is Included in This Archive (`farmgenai_crucial_source.zip`)

| Component | Included Files | Purpose |
|---|---|---|
| **Backend Source** | `backend/agents/`, `backend/routes/`, `backend/services/`, `backend/repositories/`, `backend/db/`, `backend/models/`, `backend/config.py`, `backend/main.py` | Complete backend API, agent state machines, business logic, DB repository |
| **Test Suites** | `tests/test_buyer_workflow_security_and_persistence.py`<br>`tests/test_buyer_multi_agent_acceptance.py`<br>`tests/test_buyer_state_machine_p1.py`<br>`tests/conftest.py`, etc. | 42+ comprehensive automated tests covering Flows A–G, RBAC authorization, and persistence |
| **Frontend Source** | `frontend/src/`, `frontend/public/`, `frontend/index.html`, `frontend/vite.config.ts`, `frontend/package.json` | Complete buyer & farmer UI, negotiation dashboards, workflow execution panels |
| **Local Datasets** | `dataset/*.csv` | Real Indian agricultural market datasets (mandi prices, logistics benchmarks) |
| **Configuration** | `.env.example`, `requirements.txt`, `pytest.ini` | Base configuration schemas, dependency definitions |
| **Verification Reports** | `MULTI_AGENT_RUNTIME_VERIFICATION_REPORT.md`, `BUYER_MULTI_AGENT_ORCHESTRATION_FINAL_REPORT.md` | Verification logs and architectural audits |

---

## 2. What Is Missing & Intentionally Excluded

To keep the upload lightweight (<28 MB vs the 512 MB limit) and maintain security, the following were excluded:

1. **Python Virtual Environment (`.venv/`)**:
   - Contains platform-specific compiled wheels and binaries.
2. **Node Modules (`frontend/node_modules/`)**:
   - Contains hundreds of MBs of local JavaScript packages.
3. **Live Secrets & API Keys (`.env`)**:
   - Real Gemini API keys, OpenAI keys, JWT secrets, or DB passwords are not stored in the zip.
4. **Live External Services (PostgreSQL / Redis / Ollama / MinIO)**:
   - External daemons are not running inside the archive.
5. **Git History (`.git/`)**:
   - Full commit history was stripped to save bandwidth.

---

## 3. How ChatGPT Can Fetch / Run Everything (Self-Contained & Offline)

The entire backend and multi-agent test suite is designed to run **100% OFFLINE without any live LLM or external database**.

### A. How to Install Python Dependencies
In your Python environment or Code Interpreter sandbox:
```bash
# Minimal set needed to run all backend agent tests:
pip install pytest pytest-asyncio aiosqlite sqlalchemy pydantic pydantic-settings fastapi httpx passlib python-jose[cryptography] langgraph

# OR install the complete requirements file:
pip install -r requirements.txt
```

### B. Environment Configuration (Zero External Keys Needed)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default testing flags inside the code:
- `ENABLE_LLM=false`: Agents automatically use deterministic, rule-based reasoning engines and structured mock agents. No Gemini or OpenAI API keys are required!
- `DATABASE_URL=sqlite+aiosqlite:///:memory:`: Tests automatically spin up an async SQLite in-memory database with full table creation and teardown.
- `JWT_SECRET_KEY=test-secret-key-32-chars-minimum-abcdef12345`: Built-in default for fast local token generation.

### C. Optional: How to Connect External Live LLM (If Live Generation is Wanted)
If you wish to test with actual Google Gemini or OpenAI LLMs:
1. Obtain an API key from Google AI Studio (`GEMINI_API_KEY`) or OpenAI (`OPENAI_API_KEY`).
2. In `.env`, set:
   ```env
   ENABLE_LLM=true
   LLM_PROVIDER=gemini       # or openai / ollama
   GEMINI_API_KEY=your_actual_key_here
   ```
3. If using local Ollama:
   ```env
   ENABLE_LLM=true
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=qwen2.5:7b
   ```

### D. How to Test Frontend (If Frontend Verification is Needed)
```bash
cd frontend
npm install
npm run build     # Verifies TypeScript types and Vite bundle
```

---

## 4. Test Execution Commands

Run these commands in the root directory to test the multi-agent orchestration:

### 1. Test Security Authorization & Plan Persistence (New Fixes):
Verifies that:
- Non-owners cannot mutate or read requirements/workflows (HTTP 403).
- Unauthenticated requests are rejected (HTTP 401).
- Workflow execution durably persists `final_plan` in the database repository.
```bash
python -m pytest tests/test_buyer_workflow_security_and_persistence.py -v
```

### 2. Test Multi-Agent Acceptance Suite (Flows A–G):
Verifies:
- **Flow A**: Full Procurement Chain (Farmer + Transport + Warehouse + Processor)
- **Flow B**: Transport + Warehouse
- **Flow C**: Transport Only
- **Flow D**: Warehouse Only
- **Flow E**: Processor Only
- **Flow F**: No Services (Farmer base only)
- **Flow G**: Validation (Rejection if farmer prerequisite is missing)
```bash
python -m pytest tests/test_buyer_multi_agent_acceptance.py -v
```

### 3. Test Phase 1 Buyer State Machine:
```bash
python -m pytest tests/test_buyer_state_machine_p1.py -v
```

### 4. Run All 42 Multi-Agent Verification Tests Together:
```bash
python -m pytest tests/test_buyer_workflow_security_and_persistence.py tests/test_buyer_multi_agent_acceptance.py tests/test_buyer_state_machine_p1.py -v
```
All 42 tests should execute and pass in ~3 to 5 seconds.
