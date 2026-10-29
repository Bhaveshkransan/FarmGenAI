# FarmGenAI / AgriNegotiator: Defects & Fixes Engineering Log

- **Repository**: `Bhaveshkransan/FarmGenAI`
- **Branch**: `feature/buyer-agent-verification`
- **Latest Commit**: `b9967b1`
- **Audit Date**: October 20, 2026
- **Status**: **ALL DEFECTS RESOLVED & VERIFIED**

---

## Defect Summary by Priority
- **P0 (Critical / Financial & Concurrency)**: 1 Defect (Resolved)
- **P1 (Workflow / Routing & Handoff)**: 1 Defect (Resolved)
- **P2 (Data Schemas & Environment Config)**: 2 Defects (Resolved)
- **P3 (UI Polish & Telemetry Latency)**: 1 Defect (Resolved)

---

## Detailed Defect Records

### Defect P0-01: Premature Budget Exhaustion in Parallel Candidate Discovery
- **Component**: `backend/services/budget_tracker.py`
- **Root Cause**: The `BudgetReservationTracker` subtracted uncommitted bids in concurrent branches from the buyer's remaining budget. Consequently, candidate 3 and 4 were rejected due to "insufficient funds" even though candidate 1 and 2 had not yet agreed to any deal.
- **Fix**: Decoupled price exploration from budget commitment. Bids are verified against total budget during negotiation rounds, but funds are only locked upon mutual agreement (`STATUS_AGREED` / `COMMIT`).
- **Proof**: `tests/test_master_stakeholder_integration.py` - 5 parallel branches now run concurrently to completion without budget starvation.

### Defect P1-01: WebSocket Missing Parameterized Endpoint `/ws/negotiate/{id}`
- **Component**: `backend/websocket/manager.py`
- **Root Cause**: `NegotiationRoom.tsx` connected to `${baseWsUrl}/negotiate/${activeId}`, but FastAPI only had `@router.websocket("/ws")` and `@router.websocket("/ws/negotiation")`. The missing path parameter caused HTTP 403 / 404 connection rejections in the browser.
- **Fix**: Added `@router.websocket("/ws/negotiate/{negotiation_id}")` and `@router.websocket("/api/v1/ws/negotiate/{negotiation_id}")` decorators.
- **Proof**: Verified live WebSocket handshake inside backend container (HTTP 101 Switching Protocols accepted).

### Defect P2-01: XGBoost Market Predictor Output Key Mismatch
- **Component**: `backend/models/xgboost_market_predictor.py`
- **Root Cause**: Caller services expected `predicted_price`, but XGBoost returned `forecast_price`.
- **Fix**: Standardized return dictionary to include both `forecast_price` and backwards-compatible alias `predicted_price`.
- **Proof**: Verified in `test_7_crops_xgboost.py` across all 7 crops.

### Defect P2-02: PostgreSQL Connection String Credentials
- **Component**: Database settings / migration scripts
- **Root Cause**: Some scripts assumed user `postgres` or DB `farmgenai`, while the live Docker container was provisioned with `admin:admin_password@postgres:5432/agrinegotiator`.
- **Fix**: Unified configuration to respect environment variables with fallback to `admin:admin_password@postgres:5432/agrinegotiator`.
- **Proof**: 30 tables and 421 listings queried successfully without authentication errors.