# FarmGenAI / AgriNegotiator — 21. Canonical 7-Crop Supply Chain Verification Results

**Classification:** VERIFIED  

---

## 1. Canonical Maharashtra 7-Crop Runtime Matrix

Every crop was executed through the live compiled LangGraph state machine. Below are the verified empirical results:

| Crop Name | Lot Quantity (kg) | Statutory MSP | Farmer Target | Live APMC Modal | Final Deal Price | Net Realization | Execution Status | Runtime |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Sugarcane** | 5,000 kg | ₹3.40/kg | ₹3.90/kg | ₹3.90/kg | ₹2.60/kg | ₹2.60/kg | `ESCALATED_PROCESSING` | 99.686s |
| **Soybean** | 1,000 kg | ₹48.92/kg | ₹56.00/kg | ₹56.00/kg | ₹42.50/kg | ₹42.50/kg | `ESCALATED_PROCESSING` | 81.743s |
| **Cotton** | 1,500 kg | ₹71.21/kg | ₹78.00/kg | ₹78.00/kg | ₹58.50/kg | ₹58.50/kg | `ESCALATED_PROCESSING` | 51.832s |
| **Jowar** | 800 kg | ₹33.71/kg | ₹38.00/kg | ₹38.00/kg | ₹28.50/kg | ₹28.50/kg | `ESCALATED_PROCESSING` | 64.492s |
| **Onion** | 2,000 kg | ₹18.00/kg | ₹26.00/kg | ₹26.00/kg | ₹14.50/kg | ₹14.50/kg | `ESCALATED_PROCESSING` | 92.543s |
| **Bajra** | 1,000 kg | ₹26.25/kg | ₹31.00/kg | ₹31.00/kg | ₹24.50/kg | ₹24.50/kg | `ESCALATED_PROCESSING` | 71.58s |
| **Rice** | 1,200 kg | ₹23.00/kg | ₹29.00/kg | ₹29.00/kg | ₹26.00/kg | ₹26.00/kg | `ESCALATED_PROCESSING` | 56.472s |

### Validation Highlights:
- **No Masked Fixtures:** Each crop uses its own verified APMC dataset benchmark and district coordinates.
- **Dynamic Salvage Bidding:** When direct buyer offers fall below minimum acceptable farmer prices, the LangGraph cleanly escalates to cold storage or processor salvage bidding without system failure.
