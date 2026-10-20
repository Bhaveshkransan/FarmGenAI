# FarmGenAI / AgriNegotiator: Parallel Negotiation & Top-5 Candidate Audit

- **Repository**: `Bhaveshkransan/FarmGenAI`
- **Branch**: `feature/buyer-agent-verification`
- **Latest Commit**: `b9967b1`
- **Status**: **VERIFIED PASS**
- **Date**: October 20, 2026

---

## 1. Top-5 Candidate Selection & Ranking Architecture

The parallel negotiation engine discovers all eligible counterparties and reduces them to the top $\le 5$ ranked candidates using a deterministic multi-factor composite scoring function:

$$\text{Score} = w_p \cdot S_{\text{price}} + w_d \cdot S_{\text{dist}} + w_q \cdot S_{\text{quality}} + w_r \cdot S_{\text{rating}} + w_v \cdot S_{\text{verified}}$$

Where default weights are:
- Price Competitiveness ($w_p$): **0.35**
- Logistical Proximity ($w_d$): **0.25**
- Quality Grade Consistency ($w_q$): **0.20**
- Historical Fulfillment Rating ($w_r$): **0.10**
- Counterparty Verification ($w_v$): **0.10**

---

## 2. Hard Eligibility Filter Gate (Pre-Ranking)
Before any candidate is scored or ranked, strict non-negotiable filters are evaluated:
1. **Quantity Sufficiency**: `candidate.available_quantity >= request.min_lot_size`.
2. **Crop & Variety Exact Match**: `candidate.crop_name.lower() == request.crop_name.lower()`.
3. **Geographic Feasibility**: Transit distance $< 600\text{ km}$ (for perishables like Onion/Tomatoes) or $< 1200\text{ km}$ for grains.
4. **Price Sanity**: Asking price $\le 1.35 \times \text{regional modal price}$.

*Rule Verified*: If fewer than 5 candidates meet hard constraints, the system returns **only** the eligible candidates (e.g. 2 or 3). It **never** manufactures fake candidates to pad the UI list.

---

## 3. Parallel Branch Isolation & Concurrency
Each shortlisted candidate is allocated an isolated negotiation branch:

```
[Buyer Orchestrator]
       ├── Branch 1: Farmer Shinde (Nashik)   ── Round 1: Offer Rs 4300 ── Counter: Rs 4500 ── Round 2: Rs 4420 (ACCEPTED)
       ├── Branch 2: Farmer Patil (Jalgaon)   ── Round 1: Offer Rs 4300 ── Counter: Rs 4600 ── Round 2: Rs 4380 (REJECTED)
       ├── Branch 3: Farmer Deshmukh (Pune)   ── Round 1: Offer Rs 4350 ── Counter: Rs 4480 ── Round 2: Rs 4400 (ACCEPTED)
       ├── Branch 4: Farmer Jadhav (Solapur)  ── Round 1: Offer Rs 4280 ── Counter: Rs 4550 ── Round 2: Rs 4350 (STALLED)
       └── Branch 5: Farmer More (Ahmednagar) ── Round 1: Offer Rs 4300 ── Counter: Rs 4450 ── Round 2: Rs 4410 (ACCEPTED)
```

### Critical Bug Fix: Concurrent Budget Reservation
- **Defect**: Originally, `BudgetReservationTracker` subtracted uncommitted parallel bids from the remaining buyer budget. By Branch 3, the engine believed the budget was exhausted and aborted remaining parallel negotiations.
- **Resolution**: Updated `BudgetReservationTracker` to allow non-binding concurrent discovery bids across branches, reserving budget only upon affirmative deal closure (`COMMIT`).
- **Verified in**: `test_parallel_negotiation_budget_isolation` (5 concurrent branches run without false budget exhaustion).

---

## 4. Deal Selection & Global Winner Determination
When branches finish their negotiation rounds (max 3 rounds), `select_optimal_deal` compares all `ACCEPTED` deals on **Net Landed Cost**:

$$\text{Net Landed Cost} = \text{Agreed Produce Price} + \text{Freight Cost} + \text{Platform Fee} - \text{Quality Premium Offset}$$

The branch with the lowest Net Landed Cost is designated the global winner (`STATUS_WINNER`), while other branches receive a graceful `STATUS_CONCLUDED_COMPETITOR_SELECTED` notification.

---

## 5. Verification Edge Cases Matrix

| Scenario | Candidate Count | Expected Outcome | Actual Result |
| :--- | :--- | :--- | :--- |
| Zero eligible counterparties | 0 | `NO_ELIGIBLE_CANDIDATES` response | PASS |
| Single counterparty in district | 1 | Single branch launched, 1 card rendered | PASS |
| 3 eligible counterparties | 3 | Exactly 3 branches launched, no filler cards | PASS |
| 12 eligible counterparties | 12 | Top 5 selected based on composite score | PASS |
| All candidates reject budget ceiling | 5 | All branches terminate `REJECTED`, Deal: None | PASS |
| One branch fails / times out | 5 | Failing branch marked `TIMEOUT`; remaining 4 proceed | PASS |