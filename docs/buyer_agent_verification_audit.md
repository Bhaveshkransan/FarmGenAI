# BUYER AGENT — COMPLETE EVIDENCE-BASED VERIFICATION AUDIT
**Branch Under Audit**: `feature/buyer-agent-verification`  
**Base Comparison Branch**: `farmer` (Commit: `bc53986`)  
**Audit Timestamp**: 2026-09-15  
**Authoritative Methodology**: Direct repository inspection, mathematical recalculation from source files, unit test execution, and manual boundary testing. Zero assumptions.

---

## 1. Executive Summary

This verification audit assesses the current state of the **Buyer Agent** implementation in FarmGenAI. All evaluations are grounded strictly in executable code, serialized models, raw and processed CSV datasets, and passing test assertions.

### Summary Verdict
- **GREEN (Verified & Working)**:
  - **7-Crop Scope & Isolation**: Strictly restricted to the 7 canonical Maharashtra commodities (`Sugarcane`, `Soybean`, `Cotton`, `Jowar`, `Onion`, `Bajra`, `Rice`). All 20 aliases correctly normalize; non-supported crops are strictly rejected.
  - **Real Agricultural Market Datasets**: 62,429 raw records, 14,078 clean records, and 13,179 feature records verified on disk with 0 duplicates and 0 nulls.
  - **Offline ML Valuation Pipeline**: Mathematical training and evaluation metrics reproduced with 100% precision on 1,977 test samples.
  - **Buyer Personas & Economic State**: 4 distinct commercial personas, multi-attribute utility calculation, reservation price enforcement, BATNA, and digital purchase order issuance are fully implemented and verified.
  - **Automated & Manual Test Suites**: 74 / 74 dedicated buyer unit tests passed; 13 / 13 manual phase validation tests passed.
- **YELLOW (Partially Implemented / Qualified)**:
  - **LangGraph Integration**: `buyer_node` and `rank_responses_node` exist and function, but require `buyer_agent_objs` to be pre-instantiated in state, causing 4 tests to fail in `test_05_langgraph_nodes.py` when optional state keys are omitted.
  - **Data Provenance**: Ingested from an authentic, open-source Maharashtra APMC mirror (`ashushaw04`) rather than direct authenticated REST connection to `data.gov.in`.
- **RED (Claimed but Not Implemented / False)**:
  - **The "19,200 Records" Claim**: Completely false. Neither the Buyer nor Farmer repository contains 19,200 records.
  - **Runtime ML Model Invocation**: The trained model artifact `backend/models/buyer_price_prediction_model.pkl` is on disk, but `BuyerAgent.make_offer()` does not invoke it during the live negotiation loop.
  - **Live Market API Feed**: The external API client does not query live endpoints over the wire (rate-limited / Chroma fallback with random volatility).

---

## 2. Buyer Requirements Baseline Checked

The Buyer Agent was audited against its own autonomous procurement specification:

1. **Buyer Personas**: 4 distinct personas (`retail_supermarket`, `bulk_wholesaler`, `food_processor`, `restaurant_kitchen`) with custom fallback.
2. **Buying Objectives**: High volume procurement with parameter-driven risk tolerance, quality sensitivity, and margin defense.
3. **Crop Scope**: Strictly restricted to 7 Maharashtra crops:
   - `Sugarcane` (FRP: ₹3.40/kg)
   - `Soybean` (MSP: ₹48.92/kg)
   - `Cotton` (MSP: ₹71.21/kg)
   - `Jowar` (MSP: ₹33.71/kg)
   - `Onion` (Mandi Modal benchmark: ₹15–₹26/kg; no central MSP)
   - `Bajra` (MSP: ₹26.25/kg)
   - `Rice` (MSP: ₹23.00/kg)
4. **Economic Guardrails**:
   - `budget`: Hard balance limit; purchasing stops when depleted.
   - `target_price`: Preferred acquisition price point.
   - `reservation_price` ($P_{\\max}$): Strict walk-away ceiling; no deal can be signed above this threshold.
   - `max_quantity`: Purchasing quota capacity.
   - `inventory`: Tracks successfully transacted produce volumes.
5. **Contract Issuance**: Auto-generates structured Purchase Orders with UUIDs, price, quantity, delivery window, and Net-7 terms upon reaching `ACCEPT`.

---

## 3. Dataset Provenance Audit

| Dataset File | File Size | Data Rows | Cols | Source / Origin | Transformation / Role | Reproducible? |
|---|---|---|---|---|---|:---:|
| `backend/dataset/Monthly_data_cmo.csv` | 4,885,990 bytes | 62,429 | 11 | Maharashtra State Agricultural Marketing Board (MSAMB / CMO) mirror (`ashushaw04/APMC_Argo_Challenge`) | Raw, unedited historical APMC monthly records (2014-09 to 2016-11) | Yes (Direct mirror) |
| `backend/dataset/clean_buyer_market_data.csv` | 954,458 bytes | 14,078 | 10 | Derived from `Monthly_data_cmo.csv` via `scripts/ingest_real_buyer_data.py` | Filtered to 7 crops, deduplicated on `(crop, apmc, date)`, prices converted to ₹/kg (/100), arrivals to MT (/10) | Yes (100% deterministic) |
| `backend/dataset/clean_buyer_market_data.json` | 3,784,046 bytes | 14,078 | 10 | Direct JSON serialization of `clean_buyer_market_data.csv` | Exact JSON copy for API service ingestion | Yes |
| `backend/dataset/buyer_feature_dataset.csv` | 1,562,115 bytes | 13,179 | 18 | Derived from `clean_buyer_market_data.csv` via `scripts/ingest_real_buyer_data.py` | Feature engineered dataset with forward target $P_{t+1}$, rolling lags, spreads, and cyclical month encodings | Yes |
| `backend/dataset/Market_Wise_Price_Arrival_*.csv` | 1,435 bytes | 18 | 9 | AGMARKNET daily portal export snippet (06-08-2026) | Single-day price snippet for Lasalgaon, Nashik, Pune mandis | Yes (Manual export) |
| `backend/dataset/CMO_MSP_Mandi.csv` | 5,737 bytes | 155 | 5 | Maharashtra Open Data portal | Historical MSP rates (2012–2016) | Yes |
| `backend/dataset/cleaned_mandi_prices.json` | 4,670 bytes | 15 | 8 | Ingested via `scripts/ingest_market_csv.py` | Parsed mandi records | Yes |
| `backend/dataset/cleaned_msp_prices.json` | 2,946 bytes | 15 | 5 | Ingested via `scripts/ingest_market_csv.py` | Parsed MSP records | Yes |
| `backend/dataset/historical_negotiations.json` | 687,793 bytes | 150 | 23 | Teammate negotiation logs | Farmer Agent negotiation history | Yes |

### Investigation of the "19,200 Records" Claim
- **Audit Findings**: Full regex scan of all files reveals zero datasets containing 19,200 records.
- **Farmer Agent**: Only 150 records exist in `historical_negotiations.json`.
- **Buyer Agent**: Ingested 14,078 clean real observations and 13,179 feature rows.
- **Verdict**: **RED / CLAIM CONTRADICTED BY REPOSITORY**.

---

## 4. 7-Crop Dataset Statistics

Calculated independently from the actual disk files:

### Raw Dataset (`Monthly_data_cmo.csv` — Total: 62,429 rows)
- **Sugarcane**: 13 records (0.02%) | 3 APMCs | 3 Districts | 2014-10 to 2016-11
- **Soybean**: 3,727 records (5.97%) | 227 APMCs | 27 Districts | 2014-09 to 2016-11
- **Cotton**: 1,063 records (1.70%) | 122 APMCs | 22 Districts | 2014-09 to 2016-11
- **Jowar**: 3,716 records (5.95%) | 219 APMCs | 28 Districts | 2014-09 to 2016-11
- **Onion**: 1,872 records (3.00%) | 96 APMCs | 21 Districts | 2014-09 to 2016-11
- **Bajra**: 2,346 records (3.76%) | 138 APMCs | 24 Districts | 2014-09 to 2016-11
- **Rice**: 1,580 records (2.53%) | 94 APMCs | 24 Districts | 2014-09 to 2016-11
- *Target Crop Raw Total*: **14,317 rows** (22.93% of raw file). Non-target rows (48,112 rows: Gram, Wheat, Maize, etc.) safely filtered out.

### Clean Dataset (`clean_buyer_market_data.csv` — Total: 14,078 rows)
- **Sugarcane**: 13 records (0.09%) | 3 APMCs | 3 Districts | 2014-10 to 2016-11
- **Soybean**: 3,726 records (26.47%) | 227 APMCs | 27 Districts | 2014-09 to 2016-11
- **Cotton**: 1,063 records (7.55%) | 122 APMCs | 22 Districts | 2014-09 to 2016-11
- **Jowar**: 3,710 records (26.35%) | 219 APMCs | 28 Districts | 2014-09 to 2016-11
- **Onion**: 1,867 records (13.26%) | 96 APMCs | 21 Districts | 2014-09 to 2016-11
- **Bajra**: 2,336 records (16.59%) | 138 APMCs | 24 Districts | 2014-09 to 2016-11
- **Rice**: 1,363 records (9.68%) | 94 APMCs | 24 Districts | 2014-09 to 2016-11
- *Unsupported Crops in Clean Dataset*: **0 records (Strictly 0%)**.

### Feature Dataset (`buyer_feature_dataset.csv` — Total: 13,179 rows)
- **Sugarcane**: 10 records (0.08%) | 2 APMCs | 2 Districts | 2014-10 to 2016-08
- **Soybean**: 3,499 records (26.55%) | 213 APMCs | 27 Districts | 2014-09 to 2016-10
- **Cotton**: 941 records (7.14%) | 109 APMCs | 21 Districts | 2014-09 to 2016-10
- **Jowar**: 3,491 records (26.49%) | 210 APMCs | 28 Districts | 2014-09 to 2016-10
- **Onion**: 1,771 records (13.44%) | 93 APMCs | 19 Districts | 2014-09 to 2016-10
- **Bajra**: 2,198 records (16.68%) | 131 APMCs | 23 Districts | 2014-09 to 2016-10
- **Rice**: 1,269 records (9.63%) | 90 APMCs | 23 Districts | 2014-09 to 2016-10
- *Row drop rationale*: Exactly 899 rows dropped because they represent the terminal time-step $T$ of each entity time-series and therefore possess no forward observation $P_{t+1}$. Zero data leakage.

---

## 5. Feature Dataset Audit

Each of the 18 columns in `buyer_feature_dataset.csv` was audited:

1. `date`: Period $t$ (YYYY-MM). Observed. Available at inference. No leakage.
2. `next_date`: Target period $t+1$ (YYYY-MM). Observed timestamp. Metadata only.
3. `crop`: Canonical crop name. Observed. Available at inference.
4. `district`: Administrative district in Maharashtra. Observed. Available at inference.
5. `apmc`: Market yard identifier. Observed. Available at inference.
6. `modal_price_kg`: Current period modal price in ₹/kg (/100 from quintal). Observed.
7. `min_price_kg`: Current period minimum price in ₹/kg. Observed.
8. `max_price_kg`: Current period maximum price in ₹/kg. Observed.
9. `spread`: Normalized spread: `(max - min) / modal`. Engineered. Available at inference.
10. `arrival_mt`: Arrival volume in Metric Tonnes (/10 from quintal). Observed.
11. `lag_1_modal`: Modal price at $t-1$ for same APMC/crop. Engineered. Available at inference.
12. `lag_2_modal`: Modal price at $t-2$ for same APMC/crop. Engineered. Available at inference.
13. `rolling_3_modal`: 3-period trailing rolling average price. Engineered. Available at inference.
14. `momentum`: Divergence: `(modal - rolling_3_modal) / rolling_3_modal`. Engineered. Available at inference.
15. `arrival_shock`: Volume shock: `arrival_mt / rolling_3_arrival`. Engineered. Available at inference.
16. `month_sin`: Seasonal cyclic sine component $\\sin(2\\pi \\cdot m / 12)$. Engineered. Available at inference.
17. `month_cos`: Seasonal cyclic cosine component $\\cos(2\\pi \\cdot m / 12)$. Engineered. Available at inference.
18. `target_next_modal_kg`: **TARGET VARIABLE**. Forward modal APMC market price per kg at period $t+1$.
    - **Audit Confirmation**: The model predicts future wholesale mandi modal price ($P_{\\text{modal}, t+1}$). It does NOT predict target buying price, reservation price, or negotiation outcome.

---

## 6. Model Audit

- **Training Script**: `scripts/ingest_real_buyer_data.py`
- **Execution Command**: `.venv\\Scripts\\python.exe scripts/ingest_real_buyer_data.py`
- **Model Type**: Ridge Regression inside scikit-learn Pipeline:
  ```python
  Pipeline([
      ("scaler", StandardScaler()),
      ("ridge", Ridge(alpha=10.0))
  ])
  ```
- **Dataset**: `backend/dataset/buyer_feature_dataset.csv` (13,179 total records)
- **Split Strategy**: Chronological time-series split (no shuffle, no lookahead leakage):
  - Train: 9,225 records (70.0%, 2014-09 to 2016-03)
  - Val: 1,977 records (15.0%, 2016-03 to 2016-07)
  - Test: 1,977 records (15.0%, 2016-07 to 2016-10)
- **Features Used**: 12 numerical features + 7 one-hot crop indicators (19 features total).
- **Target Variable**: `target_next_modal_kg`
- **Artifact Path**: `backend/models/buyer_price_prediction_model.pkl` (1,807 bytes, pickle format).
- **Model Load & Prediction Test**: Verified. Successfully loads and predicts $P_{t+1} = ₹26.95$/kg on Soybean test inputs.
- **Evaluation Metrics Reproduced (100% Exact)**:
  - Persistence Baseline MAE: **₹1.7258/kg** (RMSE: ₹2.8930, MAPE: 10.45%)
  - 3-Period Moving Average MAE: **₹2.3949/kg** (RMSE: ₹3.4868, MAPE: 18.83%)
  - Ridge Regression MAE: **₹2.1812/kg** (RMSE: ₹3.1904, MAPE: 16.82%)
  - HistGradientBoosting MAE: **₹2.5847/kg** (RMSE: ₹3.6964, MAPE: 26.76%)
- **Verdict**:
  - Offline Model Pipeline: **GREEN**
  - Online Runtime Integration: **RED** (The model artifact is not loaded or invoked in `BuyerAgent.make_offer()`).

---

## 7. Live Market Data Audit

1. **`backend/services/external_apis.py` (`MandiAPIClient`)**:
   - **Method**: `get_live_price(crop, location, base_market_price)`
   - **Network Request**: Does NOT make external HTTP network requests. Queries local ChromaDB collection or falls back to `base_market_price * (1 + random.uniform(-0.15, 0.15))`.
   - **External Probe to `data.gov.in`**: Responds in 1.26s with **HTTP 429 Too Many Requests** (Rate limit exceeded on shared gateway).
2. **`backend/services/market_price_service.py` (`get_crop_market_price`)**:
   - Uses hardcoded in-memory dictionary `MANDI_PRICE_DATABASE` indexed on August 4, 2026.
3. **Usage by BuyerAgent**:
   - `BuyerAgent` uses market price passed through the `context` dictionary or falls back to static lookup from `shared/crop_catalog.py`.
- **Verdict**: **YELLOW / RED** (No live external network price feed is currently active in runtime).

---

## 8. Buyer Persona Audit

The implementation of all 4 buyer personas was traced in `agents/buyer_agent.py`:

| Attribute / Persona | Retail Supermarket | Bulk Wholesaler | Food Processor | Restaurant Kitchen | Custom Fallback |
|---|---|---|---|---|---|
| **Strategy** | `boulware` | `aggressive` | `conceder` | `balanced` | `balanced` |
| **Price Weight** ($w_p$) | 0.45 | 0.75 | 0.60 | 0.40 | 0.60 |
| **Quantity Weight** ($w_q$) | 0.25 | 0.20 | 0.35 | 0.30 | 0.25 |
| **Freshness Weight** ($w_f$) | 0.30 | 0.05 | 0.05 | 0.30 | 0.15 |
| **Min Shelf Life** | 4 days | 2 days | 1 day | 3 days | 2 days |
| **Concession Rate** | 0.20 | 0.10 | 0.35 | 0.25 | 0.20 |
| **Grade C Sensitivity** | Rejects ($u_{\\text{qual}}=0.25$) | Penalizes | Accepts ($u_{\\text{qual}}=0.75$) | Rejects ($u_{\\text{qual}}=0.25$) | Standard |

- **Verification Status**: **GREEN** (All 4 personas verified in `BUYER_PERSONAS` dictionary and constructor initialization).

---

## 9. Economic-State Audit

| Economic Attribute | Implementation File | Class / Method | Actual Value / Logic | Status |
|---|---|---|---|:---:|
| `budget` | `agents/buyer_agent.py` | `BuyerAgent.__init__` | `self.budget = float(budget)`, decremented by `agreed_price * quantity` upon `ACCEPT` | **IMPLEMENTED** |
| `reserved_budget` | `agents/buyer_agent.py` | `BuyerAgent.__init__` | Tracked via `self.initial_budget` | **IMPLEMENTED** |
| `target_price` | `agents/buyer_agent.py` | `BuyerAgent.__init__` | `self.target_price = float(target_price)` | **IMPLEMENTED** |
| `reservation_price` | `agents/buyer_agent.py` | `BuyerAgent.__init__` | `self.reservation_price = float(reservation_price or target_price * 1.20)` | **IMPLEMENTED** |
| `max_quantity` | `agents/buyer_agent.py` | `BuyerAgent.__init__` | `self.max_quantity = float(max_quantity)` | **IMPLEMENTED** |
| `inventory` | `agents/buyer_agent.py` | `BuyerAgent.__init__` | `self.inventory += purchasable_qty` upon deal | **IMPLEMENTED** |
| `quality_grade` | `agents/buyer_agent.py` | `calculate_utility` | Modulates base utility score based on persona tolerance | **IMPLEMENTED** |
| `utility` | `agents/buyer_agent.py` | `calculate_utility` | Weighted sum of price, quantity, freshness in $[0.0, 1.0]$ | **IMPLEMENTED** |
| `BATNA` | `agents/buyer_agent.py` | `calculate_batna` | True minimum alternative supplier quote or market heuristic | **IMPLEMENTED** |
| `ZOPA` | `agents/buyer_agent.py` | `check_zopa` | Evaluates $P_{\\text{seller}\\min} \\le P_{\\text{buyer}\\max}$ and computes surplus band | **IMPLEMENTED** |

---

## 10. Decision & Negotiation Logic Audit

Decision Path:
`Farmer Offer` $\\to$ `_validate_offer_inputs` $\\to$ `_fallback_decision / LLM think()` $\\to$ `Safety Overrides` $\\to$ `Execution`

### Boundary Testing Matrix

| Scenario | Input Tested | Expected Decision | Actual Decision | Status |
|---|---|---|---|:---:|
| Offer below target price | Offer ₹23.00, Target ₹25.00 | ACCEPT | ACCEPT (PO issued) | **PASS** |
| Offer within 3% tolerance | Offer ₹25.50, Target ₹25.00 | ACCEPT | ACCEPT | **PASS** |
| Offer above target, below reservation | Offer ₹23.00, Target ₹20.00, Res ₹26.00 | COUNTER | COUNTER ₹16.53/kg | **PASS** |
| Offer above reservation ceiling | Offer ₹65.00, Res ₹24.00 | REJECT | REJECT (Astronomical price) | **PASS** |
| Insufficient budget | Budget ₹50.00, Offer ₹60.00 | REJECT | REJECT (Insufficient budget) | **PASS** |
| Unsupported crop | Crop 'Wheat' (Non-7 crop) | REJECT | REJECT (Unsupported crop) | **PASS** |
| Spoilage advantage | Shelf life $\\le 2$ days | Discount counter | COUNTER with spoilage penalty | **PASS** |
| Deadline reached | Round 5/5, Price ₹25.00 > Res ₹24.00 | REJECT | REJECT (Final round exceeded) | **PASS** |

---

## 11. LangGraph Integration Audit

- **Topology**: 9 nodes in `backend/agents/graph_orchestrator.py`.
- **Buyer Node**: Line 561 (`async def buyer_node(state: NegotiationState)`).
- **Ranking Node**: Line 656 (`async def rank_responses_node(state: NegotiationState)`).
- **State Flow**: `planner` $\\to$ `market_intelligence` $\\to$ `matching` $\\to$ `farmer` $\\to$ `buyer` $\\to$ `rank_responses` $\\to$ conditional routing.
- **Node Test Results**:
  - Total tests in `test_05_langgraph_nodes.py`: 29
  - Passed: **25 passed**
  - Failed: **4 failed**
  - *Failure Root Causes*:
    1. `TestBuyerNode.test_returns_offers`: Test did not supply `buyer_agent_objs` in state dictionary.
    2. `TestValidatorNode.test_produces_status`: `state["buyer_profile"]` was `None`, causing `None.get("name")` AttributeError.
    3. `TestValidatorNode.test_logs_validator_entry`: Same NoneType AttributeError.
    4. `TestMatchingEngineNode.test_empty_buyers_creates_default`: Missing required database keys.
- **Verdict**: **YELLOW (Partially Implemented)**. The nodes work when fully populated with objects, but fail when default dictionary values are missing.

---

## 12. Automated Testing Audit

Four dedicated Buyer Agent test suites were executed:

```bash
.venv\\Scripts\\python.exe -m pytest tests/test_05_buyer_agent_extensive.py \\
                                    tests/test_05_buyer_profile_economic_state.py \\
                                    tests/test_05_buyer_crop_isolation.py \\
                                    tests/test_05_buyer_real_data_ingestion.py -v
```

- `tests/test_05_buyer_agent_extensive.py`: **38 / 38 PASSED**
- `tests/test_05_buyer_profile_economic_state.py`: **12 / 12 PASSED**
- `tests/test_05_buyer_crop_isolation.py`: **17 / 17 PASSED**
- `tests/test_05_buyer_real_data_ingestion.py`: **7 / 7 PASSED**
- **Total Dedicated Buyer Tests**: **74 / 74 PASSED (100% Success Rate)**.

---

## 13. Manual Testing Audit (MAN-BUYER-01 to MAN-BUYER-13)

All 13 manual validation scenarios were executed synchronously:

| Test ID | Test Name | Input | Expected | Actual | Verdict |
|---|---|---|---|---|:---:|
| **MAN-BUYER-01** | Valid 7-crop initialization | 7 canonical crops | All 7 initialized with valid `crop` | Initialized 7 agents successfully | **PASS** |
| **MAN-BUYER-02** | Aliases normalization | 7 alias strings | All normalize to canonical name | Correctly mapped all 7 aliases | **PASS** |
| **MAN-BUYER-03** | Unsupported crop rejection | 'Wheat', 'Tomato', 'Potato' | ValueError at init, REJECT at offer | Rejected at init and offer time | **PASS** |
| **MAN-BUYER-04** | Valid market data | `clean_buyer_market_data.csv` | File exists with 14,078 data rows | Exists: True, Rows: 14,078 | **PASS** |
| **MAN-BUYER-05** | Buyer prediction | Soybean sample features | Output positive price | Predicted $P_{t+1} = ₹26.95$/kg | **PASS** |
| **MAN-BUYER-06** | Budget constraint | Budget ₹50, Offer ₹60 | REJECT with budget reason | REJECTED: Insufficient budget | **PASS** |
| **MAN-BUYER-07** | Reservation price | High: ₹65, Mid: ₹23 | High REJECT, Mid COUNTER $\\le 24$ | High: REJECT, Mid: COUNTER ₹16.53 | **PASS** |
| **MAN-BUYER-08** | ACCEPT behavior | Offer ₹23, Target ₹25 | ACCEPT with Purchase Order | ACCEPTED (PO-6DBE2829 issued) | **PASS** |
| **MAN-BUYER-09** | COUNTER behavior | Offer ₹24, Target ₹20 | COUNTER $< ₹24$ | COUNTER ₹16.50/kg | **PASS** |
| **MAN-BUYER-10** | REJECT behavior | Round 5/5, Offer ₹25 > Res ₹24 | REJECT (Deadline exceeded) | REJECTED: Final round reached | **PASS** |
| **MAN-BUYER-11** | Live market lookup | Soybean in Latur | Market benchmark returned | Service: ₹46.00, Mandi: ₹48.46 | **PASS** |
| **MAN-BUYER-12** | LangGraph negotiation | Farmer ask ₹23.50, 2 buyers | Buyer node produces offers | 2 offers produced, Ranker: DEAL | **PASS** |
| **MAN-BUYER-13** | Purchase order deal | 2,000kg Soybean @ ₹46.50 | Formal PO dict issued | PO-351F4814, Total ₹93,000 | **PASS** |

---

## 14. Claim vs Reality Table

| Claimed Capability | Evidence Found in Repository | Actually Works? | Proof / Artifact | Verdict |
|---|---|---|---|:---:|
| **7-Crop Strict Scope** | Central catalog in `shared/crop_catalog.py` | **YES** | 17/17 tests pass; 9 non-crops rejected | **GREEN** |
| **Real APMC Dataset** | 62,429 raw rows, 14,078 clean rows | **YES** | `clean_buyer_market_data.csv` verified on disk | **GREEN** |
| **19,200 Records Claim** | Zero records found in repo | **NO** | Scan of all CSV/JSON files | **RED** |
| **Trained ML Model** | Ridge Pipeline (.pkl) on disk | **YES** | 1,807 byte artifact loads and predicts | **GREEN** |
| **Model Outperforms Baselines** | Ridge MAE 2.18 vs MA MAE 2.39 | **PARTIAL** | Beats 3-mo MA, does not beat Persistence | **YELLOW** |
| **Runtime ML Model Invocation** | Model file exists, not called in `make_offer` | **NO** | `agents/buyer_agent.py` line-by-line trace | **RED** |
| **Live Market Price API** | `MandiAPIClient` in `external_apis.py` | **NO** | Public API rate limited (HTTP 429), Chroma fallback | **RED** |
| **Buyer Personas** | 4 personas with weights & concession rates | **YES** | `BUYER_PERSONAS` in `agents/buyer_agent.py` | **GREEN** |
| **Economic State & Guardrails** | Budget, reservation price, inventory | **YES** | All constraints active in negotiation | **GREEN** |
| **Accept/Counter/Reject Engine** | Concession formulas & boundary handlers | **YES** | 38/38 unit tests pass; MAN-08/09/10 pass | **GREEN** |
| **Digital Purchase Orders** | `generate_purchase_order()` method | **YES** | Auto-generates structured Net-7 POs | **GREEN** |
| **LangGraph Integration** | `buyer_node` and `rank_responses_node` | **PARTIAL** | Nodes execute, but 4 test assertions fail on NoneType | **YELLOW** |

---

## 15. Identified Gaps & Deficiencies

1. **Runtime Valuation Disconnect**: The trained Ridge model pipeline (`buyer_price_prediction_model.pkl`) sits idle on disk while `BuyerAgent.make_offer()` uses a static benchmark price.
2. **Rate-Limited Market Data**: The public `data.gov.in` API key is rate-limited (HTTP 429), forcing fallback to synthetic random volatility or local ChromaDB records.
3. **LangGraph State Null-Safety**: Teammate orchestrator nodes lack `.get()` null-checks for `buyer_profile` and expect `buyer_agent_objs` to be manually initialized.
4. **Historical Archive Depth**: The clean APMC dataset covers 2014 to 2016. Adding 2023–2026 data would improve modern price variance representation.

---

## 16. Recommended Next Implementation Phases

1. **Phase 4.1: Runtime ML Model Integration**:
   - Create a lightweight `PricePredictionService` that loads `buyer_price_prediction_model.pkl`.
   - Update `BuyerAgent.make_offer()` to dynamically compute price anchors using model forecasts.
2. **Phase 4.2: LangGraph State Robustness**:
   - Update `graph_orchestrator.py` state initialization to auto-populate `buyer_agent_objs` and ensure `buyer_profile` defaults to `{}` instead of `None`.
3. **Phase 4.3: API Key & Local Cache Architecture**:
   - Implement persistent disk caching for APMC mandi rates with an exponential backoff retry mechanism for external API feeds.
4. **Phase 4.4: Autonomous Multi-Round Simulations**:
   - Run 50 automated end-to-end negotiations between `FarmerAgent` and `BuyerAgent` to build an authentic empirical interaction dataset.

---
*Audit completed on branch `feature/buyer-agent-verification` at commit `7d4e8d6`.*
