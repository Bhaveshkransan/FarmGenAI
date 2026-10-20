# FarmGenAI / AgriNegotiator — 04. Farmer Agent Intelligence Audit

**Classification:** VERIFIED  

---

## 1. Farmer Decision Engine Principles

The Farmer Agent does NOT merely relay prices. It acts as an autonomous economic advocate for the grower.
Its objective function is:

$$\max \mathbb{E}[\text{Net Payout}] = \text{Offer Price} - \text{Estimated Freight} - \text{APMC Cess} - \text{Shrinkage}$$

### Decision Rules:
1. **Absolute Floor Guardrail:** If $\text{Counter} < \text{Farmer Floor}$, immediate rejection. No LLM prompt can bypass this.
2. **Target Concession Curve:** Concedes towards target based on remaining shelf life:
   $$P_{\text{ask}}(t) = P_{\text{target}} - (P_{\text{target}} - P_{\text{floor}}) \times \left(1 - \frac{\text{Days Left}}{\text{Total Shelf Life}}\right)^{1.8}$$
3. **Storage Option Value:** If market forecast is bullish and storage cost is less than anticipated price rise:
   $$\Delta P_{\text{forecast}} - C_{\text{storage}} \times t > 0 \implies \text{HOLD / STORE}$$
