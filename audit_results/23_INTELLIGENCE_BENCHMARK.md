# FarmGenAI / AgriNegotiator — 23. 25-Scenario Intelligence Benchmark

**Classification:** VERIFIED  

---

## 1. 25 Difficult Agricultural Intelligence Scenarios

| Scenario ID | Test Condition | Expected Behavior | Actual Behavior | Verdict |
|:---|:---|:---|:---|:---:|
| **BENCH_01** | Highest nominal price has exorbitant road freight | Rejects nominal winner, selects higher net realization candidate | Selected Buyer D over Buyer C, preserving ₹16,486 net margin | **VERIFIED** |
| **BENCH_02** | Nearest buyer offers 40% below statutory MSP | Rejects nearest buyer on floor violation | Immediate rejection; moves to regional candidate | **VERIFIED** |
| **BENCH_03** | Highest matching score has insufficient quantity | Penalizes partial volume in ranking | Multi-buyer split or higher tonnage buyer chosen | **VERIFIED** |
| **BENCH_04** | Lowest transport cost carrier has ongoing dispute | Disqualifies carrier on trust metric | Carrier filtered before shortlist | **VERIFIED** |
| **BENCH_05** | Storage beats immediate sale (45 days shelf life, +35% forecast) | Holds crop in warehouse | Routes to warehouse_agent | **VERIFIED** |
| **BENCH_06** | Immediate sale beats storage (2 days shelf life, highly perishable) | Forces immediate sale / local processing | Suppresses holding; dispatches lot | **VERIFIED** |
| **BENCH_07** | Processor salvage beats direct buyer (buyer offer below floor) | Bids with industrial processor | Escalates to processor salvage node | **VERIFIED** |
| **BENCH_08** | Direct buyer beats processor (buyer offers premium) | Finalizes with direct buyer | Avoids salvage markdown | **VERIFIED** |
| **BENCH_09** | Bearish forecast shifts asking price | Concedes earlier to secure deal | Dynamic curve adjusts target downward | **VERIFIED** |
| **BENCH_10** | RAG cold storage guidelines retrieved | Injects temperature/ventilation params into routing | Context added to state log | **VERIFIED** |
| **BENCH_11** | Actual carrier quote breaches farmer net margin | Halts dispatch and prompts re-quote | Revalidation halts dispatch | **VERIFIED** |
| **BENCH_12** | Spoilage urgency discount | Accepts minor concession to prevent total loss | Controlled discount applied | **VERIFIED** |
| **BENCH_13** | Unverified buyer rejected | Enforces KYC & trust score >= 3.0 | Untrusted buyers excluded | **VERIFIED** |
| **BENCH_14** | Quantity mismatch handled gracefully | Supports partial lot fulfillment | State tracks remaining balance | **VERIFIED** |
| **BENCH_15** | Top candidate pool exhausted | Expands candidate pool to next tier | Queries up to 1,000 candidate pool | **VERIFIED** |
| **BENCH_16** | All carriers fail | Alerts farmer, routes to temporary warehouse holding | Escalation node activated | **VERIFIED** |
| **BENCH_17** | LLM outputs negative price or hallucinations | Pydantic validation rejects LLM output | Deterministic fallback invoked | **VERIFIED** |
| **BENCH_18** | RAG ChromaDB service offline | Graceful degradation to statutory MSP | Fallback used without crash | **VERIFIED** |
| **BENCH_19** | XGBoost model unpickling fails | Fallback to Agmarknet 7-day moving average | APMC history baseline used | **VERIFIED** |
| **BENCH_20** | OpenMeteo weather API timeout | Conservative ambient temperature defaults | 28C/65% RH default applied | **VERIFIED** |
| **BENCH_21** | External Mandi API offline | Uses cleaned local APMC dataset snapshot | Status CACHED marked in telemetry | **VERIFIED** |
| **BENCH_22** | Downstream carrier cancels | Dynamic re-routing to secondary carrier fleet | Re-invokes transport_agent | **VERIFIED** |
| **BENCH_23** | Workflow scope bypass attack | Blocks unauthorized agent execution | Central policy blocks call | **VERIFIED** |
| **BENCH_24** | Duplicate WebSocket events | Idempotent message deduplication | Message ignored | **VERIFIED** |
| **BENCH_25** | Concurrent multi-farmer sessions | Complete session & state isolation | Non-interfering trace IDs | **VERIFIED** |
