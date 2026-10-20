# Priority 5: Buyer Market Context Integration & Full Decision-Pipeline Verification

## 1. Executive Summary & Existing Architecture
In earlier priorities, three separate information capabilities were established for the Buyer Agent in `FarmGenAI`:
- **Priority 2 & Runtime ML**: Statistical machine learning model forecasting next-period wholesale modal prices ($P_{\text{modal}, t+1}$).
- **Priority 3 & Buyer RAG**: Purpose-built vector retrieval delivering qualitative domain knowledge (crop quality specs, APMC regulations, buyer preferences, negotiation memory).
- **Priority 4 & Current Mandi Integration**: Official Government of India `data.gov.in` Agmarknet integration capturing observed current daily mandi market prices.

Priority 5 unifies these three distinct information streams into a single, cohesive, strongly typed architecture: **`BuyerMarketContext`**. It guarantees strict source segregation, unit consistency ($\text{₹/kg}$), location hierarchy preservation, and freshness awareness, while ensuring that **deterministic economic guardrails** (`reservation_price`, `budget`, `max_quantity`, 7-crop isolation, `max_rounds`) remain the absolute, unyielding decision authority.

---

## 2. Integrated Market-Context Architecture

```
                                 BUYER AGENT
                                      │
                     ┌────────────────┼────────────────┐
                     │                │                │
                     ▼                ▼                ▼
                BUYER RAG       CURRENT MANDI       BUYER ML
                Knowledge            Data           Forecast
               (Qualitative)      (Observed)      (Prediction)
                     │                │                │
                     └────────────────┼────────────────┘
                                      ▼
                             BuyerMarketContext
                     (Unified Composite Container)
                                      │
                                      ▼
                           Deterministic Guardrails
                     (Reservation Ceiling, Budget, Qty)
                                      │
                         ┌────────────┼────────────┐
                         ▼            ▼            ▼
                      ACCEPT       COUNTER       REJECT
```

---

## 3. Current Market Data Domain (`CurrentMarketContext`)
- **Nature**: Empirical, observed daily market transactions from Agmarknet / APMC mandis.
- **Attributes**:
  - `modal_price`: Normalized modal price ($\text{₹/kg}$).
  - `min_price` / `max_price`: Normalized price spread ($\text{₹/kg}$).
  - `observation_date`: Date of market arrival.
  - `market` / `district` / `state`: Geographic APMC identifiers.
  - `freshness`: Freshness categorization (`CURRENT`, `STALE`, `UNAVAILABLE`).
  - `match_level`: Hierarchy match level (`EXACT_APMC`, `TOKEN_APMC`, `DISTRICT`, `TOKEN_DISTRICT`, `STATE`).

---

## 4. ML Forecast Domain (`MLForecastContext`)
- **Nature**: Statistical econometric prediction of next-period market price ($P_{\text{modal}, t+1}$).
- **Model**: Ridge Regression pipeline (`buyer_price_prediction_model.pkl`) using 12 numerical features + 7 canonical crop indicators.
- **Attributes**:
  - `predicted_modal_price`: Projected wholesale price ($\text{₹/kg}$).
  - `forecast_period`: Target timeframe (`next_period (t+1)`).
  - `feature_source`: Provenance of features retrieved from `buyer_feature_dataset.csv`.
  - `audit_status`: `ML_USED` vs `FALLBACK_USED`.

---

## 5. Buyer RAG Domain (`BuyerRAGContextSummary`)
- **Nature**: Unstructured and semi-structured contextual agricultural guidelines.
- **Attributes**:
  - `quality_context`: Visual/chemical inspection specs (e.g. moisture $<12\%$, oil content, broken grain limits).
  - `procurement_context`: Commercial terms (e.g. Net-7 inspection, delivery windows).
  - `government_rules_context`: Statutory regulations (MSP, FRP, APMC cess).
  - `negotiation_memory_context`: Prior negotiation reflections and strategic adjustments.

---

## 6. Composite `BuyerMarketContext` Schema
Defined in `backend/schemas/buyer_market_context.py`:
- Encapsulates `current_market`, `ml_forecast`, and `buyer_rag`.
- Evaluates composite states: `is_complete` (all 3 active), `is_partial` ($1$ or $2$ active), and `is_empty` (pure fallback).
- Implements `validate_units()` to guard against unnormalized $\text{₹/quintal}$ errors.
- Implements `to_prompt_text()` to generate segregated prompt blocks with distinct visual markers:
  - 📍 `Current Daily Mandi Price (Observed)`
  - 🔮 `Predicted Next-Period Modal Price (ML Forecast)`
  - 📚 `Relevant Buyer RAG Knowledge`

---

## 7. Strict Source Separation
| Domain | Concept | Semantic Role | Prohibited Uses |
| :--- | :--- | :--- | :--- |
| **Current Mandi** | Observed Market Price | Baseline current transaction level | Never called a "forecast" or "future prediction" |
| **Buyer ML** | Projected Modal Price | Future price anchor ($P_{\text{modal}, t+1}$) | Never called a "live price" or "current observation" |
| **Buyer RAG** | Domain Guidelines | Quality, regulatory, and strategy context | Never used as numerical price authority |

---

## 8. Unit Consistency & Normalization
- All internal calculations in `BuyerAgent` execute in **normalized $\text{₹/kg}$**.
- Government source data in $\text{₹/quintal}$ is explicitly divided by $100$ at ingestion.
- `validate_units()` validates that all prices are within biologically and economically plausible per-kg bounds:
  - Sugarcane: ₹1.0 – ₹15.0/kg
  - Soybean: ₹20.0 – ₹150.0/kg
  - Cotton: ₹30.0 – ₹200.0/kg
  - Jowar: ₹10.0 – ₹100.0/kg
  - Onion: ₹3.0 – ₹120.0/kg
  - Bajra: ₹10.0 – ₹100.0/kg
  - Rice: ₹10.0 – ₹120.0/kg

---

## 9. Freshness Handling
- **`CURRENT`**: Arrival date is within $\le 3$ calendar days of today.
- **`STALE`**: Arrival date is older than $3$ days. Rendered with explicit `[STALE]` warning in prompt context.
- **`UNAVAILABLE`**: No mandi observation available for crop/location.

---

## 10. Location Hierarchy Matching
1. `EXACT_APMC`: Exact match on APMC mandi name (e.g. "Lasalgaon Mandi").
2. `TOKEN_APMC`: Substring/token match on market name.
3. `DISTRICT`: Primary APMC within the matching district (e.g. "Nashik").
4. `TOKEN_DISTRICT`: Fuzzy match on district name.
5. `STATE`: Statewide benchmark APMC for Maharashtra.

---

## 11. Provenance & Auditability
Every decision context preserves full provenance:
- **Current Mandi**: Stored with `source`, `market`, `arrival_date`, and `freshness`.
- **ML Forecast**: Stored with `model`, `feature_source` (APMC dataset row and match level), and `features_used`.
- **Buyer RAG**: Stored with `sources`, `knowledge_domains`, and collection IDs.

---

## 12. Decision Authority & Economic Invariance
The deterministic Buyer economic engine remains the **absolute authority**:
- **Reservation Ceiling ($P_{\text{max}}$)**: Offers exceeding reservation price CANNOT be accepted under any circumstance, regardless of high observed mandi prices, high ML forecasts, or glowing RAG quality descriptions.
- **Budget Protection**: Total commitment cannot exceed remaining buyer budget.
- **Quantity Protection**: Purchases cannot exceed `max_quantity`.
- **7-Crop Allowlist**: Non-whitelisted crops are rejected immediately on input validation.
- **Max Rounds**: Reaching round 5 of 5 forces final settlement within reservation or hard rejection.

---

## 13. Persona Integration
Concession curves under market context:
- **Boulware**: Slow early concessions ($\beta=2.5$), firm stance.
- **Aggressive**: Minimal concessions ($0.15 \times \text{round\_ratio}$).
- **Conceder**: Rapid concessions ($\beta=0.5$), quick to settle.
- **Balanced**: Linear, structured compromise ($0.40 \times \text{round\_ratio}$).

---

## 14. Failure & Fallback Behavior
- If **Current Mandi** is down $\rightarrow$ proceeds with ML Forecast + RAG.
- If **ML** is down $\rightarrow$ proceeds with Current Mandi + RAG.
- If **RAG** is down $\rightarrow$ proceeds with Current Mandi + ML.
- If **All Context** is down $\rightarrow$ operates on pure deterministic game theory without crash.

---

## 15. Test Matrix Results (MC-01 through MC-30)

| Test ID | Scenario | Result |
| :--- | :--- | :--- |
| **MC-01** | Current market only |  **PASSED** |
| **MC-02** | ML forecast only |  **PASSED** |
| **MC-03** | RAG only |  **PASSED** |
| **MC-04** | Current market + ML |  **PASSED** |
| **MC-05** | Current market + RAG |  **PASSED** |
| **MC-06** | ML + RAG |  **PASSED** |
| **MC-07** | Current market + ML + RAG (Full composite context) |  **PASSED** |
| **MC-08** | All market context unavailable |  **PASSED** |
| **MC-09** | Current market stale flagged |  **PASSED** |
| **MC-10** | Location exact APMC match level |  **PASSED** |
| **MC-11** | Location district fallback match level |  **PASSED** |
| **MC-12** | Location state fallback match level |  **PASSED** |
| **MC-13** | Price unit consistency validator |  **PASSED** |
| **MC-14** | ML forecast is not treated as current price |  **PASSED** |
| **MC-15** | Current price is not treated as forecast |  **PASSED** |
| **MC-16** | RAG cannot override reservation ceiling |  **PASSED** |
| **MC-17** | Market price cannot override reservation ceiling |  **PASSED** |
| **MC-18** | ML cannot override reservation ceiling |  **PASSED** |
| **MC-19** | Budget remains authoritative |  **PASSED** |
| **MC-20** | Quantity remains authoritative |  **PASSED** |
| **MC-21** | Crop isolation remains authoritative |  **PASSED** |
| **MC-22** | Maximum rounds remain authoritative |  **PASSED** |
| **MC-23** | Boulware behavior with market context |  **PASSED** |
| **MC-24** | Aggressive behavior with market context |  **PASSED** |
| **MC-25** | Conceder behavior with market context |  **PASSED** |
| **MC-26** | Balanced behavior with market context |  **PASSED** |
| **MC-27** | Deterministic behavior (no random drift) |  **PASSED** |
| **MC-28** | Malformed market context handling |  **PASSED** |
| **MC-29** | Missing market data handling |  **PASSED** |
| **MC-30** | Full end-to-end Buyer negotiation |  **PASSED** |

---

## 16. Real E2E Verification Scenarios

| Scenario | Objective | Status | Verification Summary |
| :--- | :--- | :--- | :--- |
| **Scenario 1** | Full Context Pipeline |  **Verified** | All 3 domains assembled and passed into Buyer decision engine. |
| **Scenario 2** | Current Mandi Unavailable |  **Verified** | Buyer successfully negotiated using ML and RAG. |
| **Scenario 3** | ML Unavailable |  **Verified** | Buyer successfully negotiated using Mandi and RAG. |
| **Scenario 4** | RAG Unavailable |  **Verified** | Buyer successfully negotiated using Mandi and ML. |
| **Scenario 5** | All External Context Unavailable |  **Verified** | Failsafe pure mathematical game theory negotiated cleanly. |
| **Scenario 6** | Reservation Protection |  **Verified** | High market quotes ($>\text{reservation}$) did not breach $P_{\text{max}}$. |
| **Scenario 7** | Budget Protection |  **Verified** | Purchase order value bounded strictly by buyer budget. |
| **Scenario 8** | Quantity Protection |  **Verified** | Fulfillment capped strictly at `max_quantity`. |
| **Scenario 9** | Stale Data Identification |  **Verified** | Stale observations labeled `[STALE]`, never presented as current. |
| **Scenario 10** | Exact APMC Matching |  **Verified** | APMC level metadata accurately surfaced. |

---

## 17. Full Regression Results
Executed comprehensive regression suite across 11 test modules:
```
tests/test_05_buyer_agent_extensive.py ...................................... [ 17%]
tests/test_05_buyer_crop_isolation.py .................                       [ 24%]
tests/test_05_buyer_negotiation_strategy.py .......................           [ 35%]
tests/test_05_buyer_profile_economic_state.py ............                    [ 40%]
tests/test_05_buyer_real_data_ingestion.py .......                            [ 43%]
tests/test_05_buyer_runtime_ml_integration.py ...............                 [ 50%]
tests/test_07_buyer_rag.py ......................                             [ 60%]
tests/test_08_current_mandi_integration.py .........................          [ 71%]
tests/test_09_buyer_market_context.py ..............................          [ 85%]
tests/test_topic1_buyer_matching_flow.py .................                    [ 93%]
tests/test_05_farmer_agent_extensive.py ...............                      [100%]

====================== 221 passed, 0 failures in 27.83s ======================
```

---

## 18. Files Changed / Added
1. `backend/schemas/buyer_market_context.py` *(New)*: Structured models for `CurrentMarketContext`, `MLForecastContext`, `BuyerRAGContextSummary`, and composite `BuyerMarketContext`.
2. `backend/services/buyer_market_context_service.py` *(New)*: Orchestration service for assembling composite market context.
3. `agents/buyer_agent.py` *(Modified)*: Prompt generation updated to format `BuyerMarketContext` with strict visual and semantic segregation.
4. `backend/agents/graph_orchestrator.py` *(Modified)*: `buyer_node` updated to assemble `BuyerMarketContext` via `buyer_market_context_service`.
5. `tests/test_09_buyer_market_context.py` *(New)*: Comprehensive test suite covering MC-01 through MC-30.
6. `docs/buyer_priority5_market_context_verification.md` *(New)*: Complete verification documentation.

---

## 19. Files Intentionally Untouched
- `agents/farmer_agent.py` (**0 lines modified** — strict stakeholder isolation preserved).
- Farmer datasets and models.
- Core database schema and migration infrastructure.

---

## 20. Known Limitations & Operational Notes
1. **Network Mandi Latency**: When querying `data.gov.in` live over the network, requests average 500ms–1.5s; the service caches observations in PostgreSQL and in-memory fallback stores to maintain sub-second response times.
2. **Deterministic Precedence**: Strategic LLM generation proposals are subject to deterministic mathematical validation filters. If the LLM proposes an offer violating reservation ceiling or budget, the filter automatically overrides the proposal with the deterministic fallback calculation.
