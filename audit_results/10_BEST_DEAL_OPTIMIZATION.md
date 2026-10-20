# FarmGenAI / AgriNegotiator — 10. Best-Deal Optimization & Net Realization Economics

**Classification:** VERIFIED  

---

## 1. The Core Economic Principle: Highest Nominal Price != Best Deal

In rural Maharashtra agricultural logistics, road freight, APMC market cess, transit shrinkage, and buyer default risk create massive wedges between nominal offer price and farmer take-home pay.

### Counterfactual Candidate Evaluation Matrix (1,000 kg Lot, Floor = ₹20.00/kg):

| Candidate | Nominal Price | Distance | Freight Cost | Handling Cess | Transit Shrinkage | Payment Risk | Net Take-Home | Decision Outcome |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Buyer D (Local Direct)** | ₹27.00/kg | 5 km | ₹2,250.00 | ₹500.00 | ₹0.68 | ₹54.00 | **₹24,195.32** | **SELECTED (OPTIMAL)** |
| **Buyer B (Moderate Freight)**| ₹28.00/kg | 30 km | ₹3,500.00 | ₹500.00 | ₹4.20 | ₹140.00 | **₹23,855.80** | **REJECTED (-₹339.52)** |
| **Buyer A (High Nominal)** | ₹30.00/kg | 250 km | ₹14,500.00 | ₹500.00 | ₹37.50 | ₹300.00 | **₹14,662.50** | **REJECTED (-₹9,532.82)** |
| **Buyer C (Highest Nominal)** | ₹34.00/kg | 420 km | ₹23,000.00 | ₹500.00 | ₹71.40 | ₹2,720.00 | **₹7,708.60** | **REJECTED (-₹16,486.72)** |

### Key Takeaway:
Buyer C offered the highest nominal price (₹34.00/kg vs ₹27.00/kg, +25.9%), but due to long-haul freight (420 km) and higher default risk, selecting Buyer C would have destroyed **₹16,486.72** of farmer net revenue. The system correctly chose Buyer D.
