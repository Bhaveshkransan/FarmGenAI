# FarmGenAI / AgriNegotiator: Farmer Agent Integration Audit

- **Repository**: `Bhaveshkransan/FarmGenAI`
- **Branch**: `feature/buyer-agent-verification`
- **Latest Commit**: `b9967b1`
- **Audit Date**: October 20, 2026
- **Status**: **VERIFIED PASS**

---

## 1. Executive Summary
The Farmer Agent (`FarmerAgent` / `DecentralizedNode`) serves as the autonomous representative for agricultural producers in the FarmGenAI decentralized network. It manages produce listings, evaluates incoming buyer bids, participates in parallel multi-turn negotiations, optimizes reserve pricing against live XGBoost price forecasts, and enforces strict non-negotiable minimum price floors.

Every component of the Farmer Agent was verified against live PostgreSQL data (`agrinegotiator` database), active WebSocket telemetry, and Playwright automated browser sessions.

---

## 2. Farmer Agent Architectural Blueprint

```
[Farmer UI (React/TS)]
        │
        ├── 1. POST /api/v1/farmer/produce ─────────► [ProduceListing DB Table]
        │                                                    │
        ├── 2. POST /api/v1/farmer/negotiations ─────► [FarmerAgent / DecentralizedNode]
        │                                                    │
        │                                     ┌──────────────┴──────────────┐
        │                                     ▼                             ▼
        │                              [XGBoost Forecast]          [RAG Knowledge Store]
        │                              (7 Maharashtra Crops)      (Storage & Fair Pricing)
        │                                     │                             │
        │                                     └──────────────┬──────────────┘
        │                                                    ▼
        └── 3. WebSocket /api/v1/ws/negotiate/{id} ◄─── [Parallel Negotiation Engine]
```

---

## 3. Input & Output Schemas

### Input Schema (`ProduceListingCreate` & `FarmerNegotiationRequest`)
```json
{
  "farmer_id": "usr_farmer_nashik_01",
  "crop_name": "Soybean",
  "quantity": 100.0,
  "unit": "quintal",
  "min_acceptable_price": 4200.0,
  "asking_price": 4600.0,
  "quality_grade": "Grade A",
  "harvest_date": "2026-10-15",
  "location": "Nashik, Maharashtra",
  "shelf_life_days": 180,
  "storage_condition": "ambient_dry"
}
```

### Output Schema (`FarmerAgentEvaluationResult`)
```json
{
  "negotiation_id": "neg_soybean_8821",
  "status": "ACCEPTED",
  "agreed_price": 4480.0,
  "agreed_quantity": 100.0,
  "reserve_price_enforced": 4200.0,
  "counter_offer": null,
  "spoilage_risk_discount": 0.0,
  "market_forecast_delta": 180.0,
  "rationale": "Offer Rs 4480/q exceeds enforced floor Rs 4200/q and aligns with 7-day XGBoost forecast of Rs 4450/q."
}
```

---

## 4. Deterministic Business Rules & Invariants
1. **Absolute Minimum Floor**: Under no circumstance will the Farmer Agent accept an offer below `min_acceptable_price`. In `test_master_stakeholder_integration.py` (`test_farmer_enforces_floor_price`), an offer of Rs 4100 on a Rs 4200 floor was rejected 100% of the time.
2. **Quality Premium / Discount Adjustment**:
   - `Grade A`: Premium of +4% to +8% above regional modal price.
   - `Grade B`: Baseline modal price.
   - `Grade C`: Discount of -5% to -10%.
3. **Perishability / Shelf-life Urgency**: For highly perishable crops (e.g. Onion with <15 days shelf life remaining), the agent progressively scales its counter-offer concession rate from 0.05 to 0.15 per round to prevent total post-harvest spoilage.
4. **Deterministic Validation Pre-LLM**:
   - Pre-computation determines feasible price boundaries. LLM prompt instructs persona and tone, but deterministic Python guardrails intercept and override any hallucinated price outside `[min_acceptable_price, asking_price * 1.15]`.

---

## 5. Database Entity Persistence
- **Table `produce_listings`**: 421 active listings across 7 crops in Maharashtra.
- **Table `negotiations`**: 108 records tracking multi-turn offers, counters, and status (`PENDING`, `IN_PROGRESS`, `AGREED`, `REJECTED`).
- **Table `deals`**: Contains binding contracts with foreign keys to farmer, buyer, transport booking, and escrow status.

---

## 6. Verification & Test Evidence
- **Integration Test Suite**: `tests/test_master_stakeholder_integration.py`
  - Farmer Floor Invariant: **PASS**
  - Farmer Concession Trajectory: **PASS**
  - Farmer Spoilage Acceleration: **PASS**
  - Produce Listing CRUD: **PASS**
- **Browser Playwright Walkthrough**:
  - URL: `http://localhost:8080/dashboard/farmer`
  - Rendered correctly with active produce inventory, price distribution charts, and incoming negotiation alerts.
  - Screenshot verified: `manual_ui_farmer_dashboard.png`.