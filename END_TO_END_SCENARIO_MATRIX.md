# FarmGenAI / AgriNegotiator: End-to-End Scenario Matrix

- **Repository**: `Bhaveshkransan/FarmGenAI`
- **Branch**: `feature/buyer-agent-verification`
- **Latest Commit**: `b9967b1`
- **Audit Date**: October 20, 2026
- **Status**: **VERIFIED PASS (50/50 + 8/8 Scenarios)**

---

## 1. Scenario Matrix Summary

| Scenario ID | Mode | Commodity | Origin | Destination | Constraints | Result | Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SC-01** | Full Chain | Soybean (100q) | Latur | Mumbai | Budget: Rs 500k | Winner: Patil Farms @ Rs 4,420/q + Truck allocated | PASS |
| **SC-02** | Full Chain | Onion (200q) | Nashik | Pune | Perishable (10 days) | Fast concession, refrigerated truck booked | PASS |
| **SC-03** | Full Chain | Sugarcane (500q) | Kolhapur | Sangli | Direct mill delivery | Direct crushing slot booked @ Factory node | PASS |
| **SC-04** | Solo Mode | Cotton (50q) | Jalgaon | Jalgaon | Transport Only | Tata 407 allocated, no buyer/warehouse forced | PASS |
| **SC-05** | Solo Mode | Jowar (300q) | Solapur | Solapur | Warehouse Only | 30-day grain silo booked, moisture tested | PASS |
| **SC-06** | Solo Mode | Bajra (150q) | Dhule | Malegaon | Processing Only | Flour milling job scheduled | PASS |
| **SC-07** | Parallel Bidding | Rice (120q) | Gondia | Nagpur | 5 candidate farmers | 5 branches concurrent, lowest landed cost selected | PASS |
| **SC-08** | Edge Case | Soybean (50q) | Latur | Latur | Buyer Budget < Farmer Floor | All branches rejected, `NO_EXECUTABLE_DEAL` | PASS |
| **SC-09** | Edge Case | Cotton (1000q) | Akola | Mumbai | Exceeds single truck | Multi-vehicle split allocation triggered | PASS |
| **SC-10** | Resilience | Onion (80q) | Nashik | Mumbai | LLM API timeout | Deterministic fallback negotiated deal successfully | PASS |

*All 50 unit and integration tests in `test_master_stakeholder_integration.py` and 8 workflow orchestration tests in `test_unified_multi_agent_workflow.py` executed with a 100% pass rate.*