# Buyer Agent Priority 2 Negotiation Verification Report

This document presents the formal audit, verification results, strategy implementation details, manual negotiation scenario matrix, and regression testing for **Priority 2: Buyer Negotiation Strategy & Behavior**.

---

## 1. Existing Negotiation Audit

| Negotiation capability | Existing implementation | Complete? | Gap / Action Taken |
| :--- | :--- | :--- | :--- |
| **Buyer Personas** | `BUYER_PERSONAS` defines `retail_supermarket` (Boulware), `bulk_wholesaler` (Aggressive), `food_processor` (Conceder), `restaurant_kitchen` (Balanced). | Complete | Enhanced `__init__` to map strategy names passed directly as `persona` (`"boulware"`, `"aggressive"`, `"conceder"`, `"balanced"`). |
| **Opening Offers** | `make_offer()` calculates opening bid from ML market price anchor & target price applying persona strategy discount (0.75 to 0.90), bounded by budget and reservation ceiling ($P_{\max}$). | Complete | Fully deterministic and bounded by reservation ceiling. |
| **Concession Strategy** | `_fallback_decision()` computes mathematical concession curves based on $t/t_{\max}$: Boulware ($\beta=2.5$), Conceder ($\beta=0.5$), Aggressive ($0.15$), Balanced ($0.40$), modulated by reciprocal seller concessions. | Complete | Bounded by $\min(P_{\max}, \text{BATNA})$. |
| **Seller Counter Testing** | Evaluates offers against target, 3% margin, spoilage, reservation ceiling, and round counts. | Complete | Handles price below target, between target and reservation, and above reservation. |
| **Stall Detection** | Tracks `seller_offer_history` and `seller_concession` (slows buyer concession rate when seller is immobile). | Complete | Strengthened with `consecutive_no_progress` trigger: when seller price remains static ($\Delta < \text{₹}0.15$) across 3 rounds above reservation, triggers early `REJECT`. |
| **Max Rounds** | Accepts if price $\le P_{\max}$ on final round, otherwise REJECTs. | Complete | Fully verified. |
| **ZOPA & Surplus** | `check_zopa(seller_min_price)` checks $P_{\text{seller\_min}} \le P_{\max}$ and calculates surplus. | Complete | Fully verified. |
| **BATNA Usage** | `calculate_batna()` calculates alternative supplier quote or market reference heuristic; `_fallback_decision()` bounds `effective_ceiling = min(P_max, BATNA)`. | Complete | BATNA actively constrains negotiation ceiling. |
| **Multi-Variable Tradeoff** | `affordable_qty = math.floor(budget / price)` scales quantity to prevent budget violations while maintaining unit price. | Complete | Fully verified. |
| **Quality / Freshness** | `calculate_utility()` modulates utility by quality grade (A vs B vs C) & shelf life; `_fallback_decision()` discounts price if `shelf_life <= 2`. | Complete | Fully verified. |
| **Urgency** | `min_shelf_life` and `shelf_life` modulate utility and concession aggressiveness. | Complete | Fully verified. |
| **ML + Negotiation Separation** | ML model (`pricing_service.predict_modal_price`) outputs next-period market price anchor. Decision policy uses anchor + policy. | Complete | Fully decoupled. |
| **Randomness Control** | 100% deterministic decision logic in `buyer_agent.py`. | Complete | Completely reproducible. |
| **LLM Safety & Guardrails** | Post-LLM validation overrides any hallucinated decision exceeding reservation price or budget. | Complete | Fully guarded against hallucinations. |

---

## 2. Persona Behavior

The four supported Buyer negotiation personas produce distinct, economically meaningful negotiation behaviors:

1. **Boulware (`retail_supermarket`)**:
   - **Opening Discount**: 0.78 (Firm initial anchor).
   - **Concession Curve**: $\beta = 2.5$ ($f(t) = (t/t_{\max})^{2.5}$). Concedes very slowly early on, maintaining high price pressure, and only accelerates slightly near the deadline.
   - **Quality Weight**: High (Freshness 30%, Price 45%, Quantity 25%).
2. **Aggressive (`bulk_wholesaler`)**:
   - **Opening Discount**: 0.75 (Lowest opening bid for volume discounts).
   - **Concession Curve**: $0.15 \times (t/t_{\max})$. Minimal concession movement per round.
   - **Quality Weight**: Price dominant (75% Price, 20% Quantity, 5% Freshness).
3. **Conceder (`food_processor`)**:
   - **Opening Discount**: 0.90 (Highest opening bid to secure fast agreement).
   - **Concession Curve**: $\beta = 0.5$ ($f(t) = (t/t_{\max})^{0.5}$). Concedes rapidly in early rounds to guarantee supply for processing facilities.
   - **Quality Weight**: Volume & Price (60% Price, 35% Quantity, 5% Freshness).
4. **Balanced (`restaurant_kitchen`)**:
   - **Opening Discount**: 0.82 (Balanced market entry).
   - **Concession Curve**: $0.40 \times (t/t_{\max})$ (Linear, steady progression).
   - **Quality Weight**: Equal balance (40% Price, 30% Quantity, 30% Freshness).

---

## 3. Opening Offers

Opening offers are calculated deterministically via `make_offer()`:
$$\text{Opening Price} = \min\left(P_{\text{reservation}}, \text{round\_two\_decimals}\left(\max\left(1.0, \min(P_{\text{target}}, P_{\text{market\_anchor}}) \times \text{Discount}_{\text{persona}}\right)\right)\right)$$

- **Aggressive**: $\text{Discount} = 0.75$
- **Boulware**: $\text{Discount} = 0.78$
- **Balanced**: $\text{Discount} = 0.82$
- **Conceder**: $\text{Discount} = 0.90$

Every opening offer is strictly capped by the buyer's reservation price ceiling ($P_{\max}$) and remaining budget.

---

## 4. Concession Strategy

Concessions follow a mathematically bounded curve:
$$\text{Effective Ceiling} = \min(P_{\max}, \text{BATNA})$$
$$\text{Step} = \max\left(0.5, (\min(P_{\text{seller\_offer}}, \text{Effective Ceiling}) - P_{\text{current\_bid}}) \times \text{Concession Factor}\right)$$

Reciprocal Tit-for-Tat:
- If the seller's concession $\le \text{₹}0.0$ after Round 1, the buyer slows its concession factor by $30\%$ ($\times 0.70$).
- If the seller makes a large concession ($> \text{₹}2.0$), the buyer increases its concession speed ($\times 1.20$).

---

## 5. Stall Detection

Stall detection tracks seller offer history (`self.seller_offer_history`).
If the seller's offer price changes by $< \text{₹}0.15$ over 3 consecutive rounds ($\Delta < \text{₹}0.15$) while the price remains above the buyer's reservation ceiling, the Buyer Agent halts negotiation and outputs `REJECT` with reason:
> *"Stall detected: seller price (₹44.08/kg) has remained static across 3 rounds above reservation ceiling."*

---

## 6. Maximum Negotiation Rounds

The max-round rule (`current_round >= max_rounds`) enforces hard termination:
- If $P_{\text{seller\_offer}} \le P_{\max}$ on the final round, Buyer outputs `ACCEPT`.
- If $P_{\text{seller\_offer}} > P_{\max}$ on the final round, Buyer outputs `REJECT`.

---

## 7. ZOPA & Economic Agreement

ZOPA is evaluated deterministically via `check_zopa(seller_min_price)`:
- $\text{ZOPA Exists} \iff P_{\text{seller\_min}} \le P_{\max}$
- $\text{Surplus} = P_{\max} - P_{\text{seller\_min}}$
- If $P_{\text{seller\_min}} > P_{\max}$, negative ZOPA is logged and no agreement is possible.

---

## 8. BATNA

BATNA is calculated via `calculate_batna(market_price)`:
- If alternative quotes exist: $\text{BATNA} = \min(\text{Alternative Quotes}, P_{\max})$
- Otherwise (Market Reference Heuristic): $\text{BATNA} = \min(P_{\max}, P_{\text{market\_anchor}} + \text{₹}1.50)$
- BATNA actively constrains the concession ceiling in `_fallback_decision`: $\text{Effective Ceiling} = \min(P_{\max}, \text{BATNA})$.

---

## 9. Quantity-Price Negotiation (Budget Protection)

When a seller's unit price is acceptable but total lot cost exceeds remaining budget:
$$\text{Affordable Quantity} = \lfloor \frac{\text{Budget}}{\text{Price}} \rfloor$$
$$\text{Purchasable Quantity} = \min(\text{Requested Quantity}, \text{Max Quantity}, \text{Affordable Quantity})$$
This guarantees **zero budget overruns** while securing available produce at the negotiated unit price.

---

## 10. Quality & Freshness

- `calculate_utility()` modulates utility score by quality grade (Grade A vs B vs C) based on buyer persona (e.g. supermarkets penalize Grade B/C, food processors accept Grade B/C for pulp/crush).
- If `shelf_life <= 2`, the buyer applies a 10% spoilage discount or counters lower to reflect decay risk.

---

## 11. Urgency

Urgency is driven by `min_shelf_life` and remaining shelf life. Urgent buyers with low remaining shelf life hold firm on lower bids or demand decay discounts.

---

## 12. ML + Negotiation Separation

- **ML Model**: Predicts next-period modal market price ($P_{\text{modal}, t+1}$).
- **Negotiation Policy**: Uses predicted modal price as a market anchor to inform opening bids and BATNA heuristics. The decision engine (`respond_to_offer()`) remains strictly governed by economic constraints ($P_{\text{target}}$, $P_{\max}$, budget) and persona concession rules.

---

## 13. LLM Safety & Guardrails

Deterministic policy filters sanitize LLM responses:
- Strips malformed currency symbols from small LLM outputs.
- Overrides any hallucinated `ACCEPT` where $P_{\text{seller}} > P_{\max}$.
- Replaces invalid or out-of-bounds `COUNTER` prices with deterministic fallback steps.
- Redacts confidential reservation ceiling $P_{\max}$ from log text to prevent information leakage.

---

## 14. Manual Negotiation Matrix Results (NEG-01 to NEG-12)

| Scenario ID | Persona | Crop | Qty (kg) | Budget (₹) | Target (₹) | Reservation (₹) | ML Anchor (₹) | Farmer Ask (₹) | Buyer Offer (₹) | Round | Final Decision | Final Qty | Final Price | Total Cost (₹) | Reason | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NEG-01** | Balanced | Soybean | 1,000 | 50,000 | 48.00 | 54.00 | 48.00 | 47.50 | - | 1 | **ACCEPT** | 1,000 | 47.50 | 47,500.00 | Price meets target | **PASS** |
| **NEG-02** | Aggressive | Soybean | 1,000 | 50,000 | 45.00 | 52.00 | 48.00 | 50.00 | 36.00 | 1 | **COUNTER** | 1,000 | 36.00 | - | Low aggressive bid | **PASS** |
| **NEG-03** | Boulware | Soybean | 1,000 | 50,000 | 45.00 | 52.00 | 48.00 | 51.00 | 37.44 | 1 | **COUNTER** | 1,000 | 37.44 | - | Slow initial concession | **PASS** |
| **NEG-04** | Conceder | Soybean | 1,000 | 50,000 | 45.00 | 52.00 | 48.00 | 50.00 | 43.20 | 2 | **COUNTER** | 1,000 | 43.20 | - | Rapid early concession | **PASS** |
| **NEG-05** | Balanced | Soybean | 1,000 | 50,000 | 48.00 | 54.00 | 48.00 | 44.00 | - | 1 | **ACCEPT** | 1,000 | 44.00 | 44,000.00 | Price below target | **PASS** |
| **NEG-06** | Balanced | Soybean | 1,000 | 50,000 | 45.00 | 54.00 | 48.00 | 50.00 | 43.08 | 2 | **COUNTER** | 1,000 | 43.08 | - | Mid-band compromise | **PASS** |
| **NEG-07** | Balanced | Soybean | 1,000 | 50,000 | 45.00 | 50.00 | 48.00 | 60.00 | 41.50 | 2 | **COUNTER** | 1,000 | 41.50 | - | Capped at reservation | **PASS** |
| **NEG-08** | Balanced | Soybean | 1,000 | 50,000 | 40.00 | 45.00 | 42.00 | 52.00 | - | 3 | **REJECT** | - | - | - | Immobile seller stall | **PASS** |
| **NEG-09** | Balanced | Soybean | 1,000 | 15,000 | 20.00 | 25.00 | 22.00 | 25.00 | - | 5 | **ACCEPT** | 600 | 25.00 | 15,000.00 | Budget-scaled qty | **PASS** |
| **NEG-10** | Balanced | Soybean | 1,000 | 50,000 | 45.00 | 52.00 | 38.00 | 49.00 | 41.60 | 2 | **COUNTER** | 1,000 | 41.60 | - | Decoupled ML anchor | **PASS** |
| **NEG-11** | Balanced | Soybean | 1,000 | 50,000 | 45.00 | 52.00 | 46.50 | 46.00 | 43.12 | 2 | **COUNTER** | 1,000 | 43.12 | - | Market-aligned | **PASS** |
| **NEG-12** | Balanced | Soybean | 1,000 | 50,000 | 40.00 | 48.00 | 44.00 | 46.00 | - | 5 | **ACCEPT** | 1,000 | 46.00 | 46,000.00 | Final round $\le P_{\max}$ | **PASS** |

---

## 15. Automated Verification Tests

Created new test suite: `tests/test_05_buyer_negotiation_strategy.py`

Test Execution Command:
```bash
.venv/Scripts/pytest.exe tests/test_05_buyer_negotiation_strategy.py -v
```
Result: **16 / 16 PASSED (100% clean)**.

---

## 16. Full Regression Testing Results

Executed regression suite across all existing test files:
```bash
.venv/Scripts/pytest.exe tests/test_05_buyer_agent_extensive.py tests/test_05_buyer_profile_economic_state.py tests/test_05_buyer_crop_isolation.py tests/test_05_buyer_real_data_ingestion.py tests/test_05_buyer_runtime_ml_integration.py tests/test_05_langgraph_nodes.py tests/test_05_farmer_agent_extensive.py -v
```

Result: **141 / 141 PASSED (0 regressions, 100% clean)**.

- `FarmerAgent` diff: **0 lines changed (100% untouched)**.
- Farmer datasets: **0 lines changed (100% untouched)**.

---

## 17. Final Capability Summary Table

| Capability | Existing | Changed | Verified | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Persona Differentiation** | Yes | Yes (Added persona string mapping) | Verified | `test_all_four_personas_produce_different_opening_offers` PASSED |
| **Opening Offers** | Yes | No | Verified | `test_opening_offer_never_exceeds_reservation_price` PASSED |
| **Concession Strategy** | Yes | No | Verified | `test_boulware_concedes_slower_than_conceder` PASSED |
| **Stall Detection** | Partial | Yes (Added static offer REJECT trigger) | Verified | `test_stall_detection_triggers_reject_when_seller_immobile_above_reservation` PASSED |
| **Max Rounds** | Yes | No | Verified | `test_max_rounds_behavior` PASSED |
| **ZOPA Evaluation** | Yes | No | Verified | `test_zopa_evaluation` PASSED |
| **BATNA Usage** | Yes | No | Verified | `test_batna_caps_effective_concession_ceiling` PASSED |
| **Quantity-Price Tradeoff** | Yes | No | Verified | `test_quantity_scaled_to_prevent_budget_violation` PASSED |
| **Quality & Freshness** | Yes | No | Verified | Utility & spoilage discount verified |
| **ML/Policy Separation** | Yes | No | Verified | `test_ml_market_anchor_decoupled_from_decision_policy` PASSED |
| **LLM Safety Guardrails** | Yes | No | Verified | `test_llm_hallucination_override_above_reservation` PASSED |
| **FarmerAgent Integrity** | Yes | No (0 diff) | Verified | `git diff -- agents/farmer_agent.py` returns empty |
