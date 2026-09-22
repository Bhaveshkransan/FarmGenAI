# Buyer Agent Priority 4 Verification Report: Current Daily Mandi Price Integration

**Branch**: `feature/buyer-agent-verification`  
**Target Component**: Current Daily Mandi Market Price Service for `BuyerAgent`  
**Date**: September 23, 2026  

---

## 1. Official Data Source

Primary Source: Official Government of India Open Data Portal (`data.gov.in`) / Directorate of Marketing & Inspection (Agmarknet).  
Dataset Name: *"Current Daily Price of Various Commodities from Various Markets (Mandi)"*  
Resource Endpoint: `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`

---

## 2. API Verification

The official API contract was audited prior to implementation:
- **Protocol**: HTTPS GET
- **Format**: JSON (`format=json`)
- **Query Filter Parameters**: `filters[commodity]`, `filters[state]`, `filters[district]`, `filters[market]`, `limit`, `offset`.
- **Response Fields**: `state`, `district`, `market`, `commodity`, `variety`, `grade`, `arrival_date`, `min_price`, `max_price`, `modal_price`.

---

## 3. Authentication

- **Mechanism**: API Key via query parameter `api-key`.
- **Configuration**: Environment variables `DATA_GOV_API_KEY` or `DATA_GOV_IN_API_KEY`.
- **Security Rule**: API keys are loaded strictly from system environment variables; never hardcoded, never committed, and never exposed to client-side frontend.
- **Current Key Status**: `DATA_GOV_API_KEY` is currently not set in local `.env`. Live fetching falls back to cached/mocked Agmarknet datasets while unit tests verify payload parsing via mock HTTP responses.
- **Required Statement**: *"API integration is implemented/configured but live verification requires DATA_GOV_API_KEY."*

---

## 4. API Request Structure

```http
GET https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key=YOUR_KEY&format=json&limit=100&filters[commodity]=Onion&filters[state]=Maharashtra HTTP/1.1
Host: api.data.gov.in
User-Agent: FarmGenAI/1.0
```

---

## 5. Response Structure

```json
{
  "status": "ok",
  "records": [
    {
      "state": "Maharashtra",
      "district": "Nashik",
      "market": "Lasalgaon",
      "commodity": "Onion",
      "variety": "Red",
      "grade": "FAQ",
      "arrival_date": "22/09/2026",
      "min_price": "2500",
      "max_price": "3500",
      "modal_price": "3000"
    }
  ]
}
```

---

## 6. Supported Crops

BuyerAgent is strictly restricted to the canonical 7 Maharashtra crops defined in `shared/crop_catalog.py`:
1. **Sugarcane** (FRP Benchmark)
2. **Soybean** (MSP Benchmark)
3. **Cotton** (MSP Benchmark)
4. **Jowar** (MSP Benchmark)
5. **Onion** (Mandi Modal Price Benchmark — No central MSP)
6. **Bajra** (MSP Benchmark)
7. **Rice** (MSP Benchmark)

All non-supported crops (e.g., `Wheat`, `Tomato`, `Potato`) are rejected explicitly with `freshness="UNAVAILABLE"`.

---

## 7. Price Semantics

- **Modal Price (`modal_price`)**: Primary observed market price benchmark.
- **Minimum Price (`min_price`)**: Floor transaction price.
- **Maximum Price (`max_price`)**: Ceiling transaction price.
- **Sugarcane**: Uses FRP (Fair & Remunerative Price) rather than MSP.
- **Onion**: Uses APMC mandi modal price (no central MSP benchmark exists).
- **Soybean / Cotton / Jowar / Bajra / Rice**: observed mandi modal price is used as the primary market observation, while MSP serves as a reference.

---

## 8. Unit Normalization

The official Government API returns price figures in **₹/quintal** ($1 \text{ quintal} = 100 \text{ kg}$).  
`CurrentMandiService` performs explicit unit conversion:

$$\text{Price (\text{₹}/kg)} = \frac{\text{Price (\text{₹}/quintal)}}{100}$$

Both source fields (`modal_price_quintal`, `source_price_unit="₹/quintal"`) and normalized fields (`modal_price_kg`, `normalized_price_unit="₹/kg"`) are preserved in the data structure.

---

## 9. PostgreSQL Schema

```python
class DBCurrentMandiPrice(Base):
    __tablename__ = "current_mandi_prices"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    state: Mapped[str] = mapped_column(nullable=False, index=True)
    district: Mapped[str] = mapped_column(nullable=False, index=True)
    market: Mapped[str] = mapped_column(nullable=False, index=True)
    commodity: Mapped[str] = mapped_column(nullable=False, index=True)
    variety: Mapped[str] = mapped_column(nullable=True)
    grade: Mapped[str] = mapped_column(nullable=True)
    arrival_date: Mapped[str] = mapped_column(nullable=False, index=True)
    min_price_quintal: Mapped[float] = mapped_column(nullable=True)
    max_price_quintal: Mapped[float] = mapped_column(nullable=True)
    modal_price_quintal: Mapped[float] = mapped_column(nullable=True)
    min_price_kg: Mapped[float] = mapped_column(nullable=True)
    max_price_kg: Mapped[float] = mapped_column(nullable=True)
    modal_price_kg: Mapped[float] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(nullable=False)
    fetched_at: Mapped[str] = mapped_column(nullable=False)
    freshness: Mapped[str] = mapped_column(nullable=False, default="CURRENT")
```

---

## 10. Ingestion Architecture & Deduplication

```
  Government API (data.gov.in)
              │
              ▼
   CurrentMandiService.fetch()
              │
              ▼
    Price Unit Normalization (₹/quintal → ₹/kg)
              │
              ▼
    Deduplication Check: (commodity, market, arrival_date)
              │
              ▼
   PostgreSQL / In-Memory Table (current_mandi_prices)
```

The ingestion is fully idempotent: fetching identical observations for the same APMC mandi, crop, and arrival date updates the existing record rather than creating duplicate entries.

---

## 11. Freshness Policy

- **`CURRENT`**: Arrival date is within 3 days of the query date.
- **`STALE`**: Arrival date is older than 3 days. Cached database records are marked with `freshness="STALE"`.
- **`UNAVAILABLE`**: No data exists for the crop/location. (No dummy values or ₹0/kg figures are generated).

---

## 12. Location Matching Hierarchy

1. `EXACT_APMC`: Exact match on market name (e.g. `"Lasalgaon Mandi"`).
2. `TOKEN_APMC`: Substring/token match on market name.
3. `DISTRICT`: Exact match on district name (e.g. `"Nashik"`).
4. `TOKEN_DISTRICT`: Substring match on district name.
5. `STATE`: Statewide latest fallback for the crop.

---

## 13. Fallback Behavior

If the external government API is unreachable, times out, or fails:
1. `CurrentMandiService` catches network/HTTP errors safely.
2. Returns the latest stored database observation for the crop/location.
3. Explicitly sets `freshness="STALE"` and `is_current=False`.
4. Negotiation continues without crashing.

---

## 14. Buyer Agent Integration

`BuyerAgent` accepts `context["current_mandi_data"]` and incorporates it into the LLM guided prompt:
```text
- Predicted Next-Period Modal Price (ML Forecast): ₹32.50/kg
- Current Daily Mandi Price (Observed): ₹30.00/kg at Lasalgaon APMC (Date: 2026-09-22, Freshness: CURRENT)
```

**Non-Authoritative Rule**: Current mandi data is informational context. It CANNOT override `reservation_price` ceiling ($P_{\text{max}}$), remaining `budget`, `max_quantity`, 7-crop allowlist, or `max_rounds`.

---

## 15. Architectural Separation

```
                         BUYER AGENT
                              │
          ┌───────────────────┼──────────────────┐
          │                   │                  │
          ▼                   ▼                  ▼
      BUYER RAG          CURRENT MANDI        BUYER ML
      KNOWLEDGE             DATA             FORECAST
          │                   │                  │
          ▼                   ▼                  ▼
     Text/context       Current modal       Next-period
                         market price        forecast
          │                   │                  │
          └───────────────────┼──────────────────┘
                              ▼
                   Deterministic Buyer Engine
                              │
                              ▼
                       ACCEPT / COUNTER /
                           REJECT
```

---

## 16. Security

- API keys loaded from environment variables (`DATA_GOV_API_KEY`).
- Credentials are never hardcoded, logged, or returned in API responses to the frontend.

---

## 17. Automated Test Results (`tests/test_08_current_mandi_integration.py`)

| Test ID | Description | Result |
|---|---|---|
| **MANDI-01** | API config validation & API key resolution | **PASSED** |
| **MANDI-02** | Official response payload parsing | **PASSED** |
| **MANDI-03** | Auth failure graceful fallback | **PASSED** |
| **MANDI-04** | API network timeout fallback | **PASSED** |
| **MANDI-05** | API HTTP 500/503 service unavailable fallback | **PASSED** |
| **MANDI-06** | Malformed response JSON handling | **PASSED** |
| **MANDI-07** | Pagination limit parameter formatting | **PASSED** |
| **MANDI-08** | Arrival date format parsing | **PASSED** |
| **MANDI-09** | Min, max, modal price extraction | **PASSED** |
| **MANDI-10** | Price unit conversion (₹/quintal → ₹/kg) | **PASSED** |
| **MANDI-11** | Crop alias normalization to canonical 7 crops | **PASSED** |
| **MANDI-12** | Non-supported produce rejection | **PASSED** |
| **MANDI-13** | APMC matching (EXACT_APMC / TOKEN_APMC) | **PASSED** |
| **MANDI-14** | District fallback matching | **PASSED** |
| **MANDI-15** | State fallback matching | **PASSED** |
| **MANDI-16** | Idempotency / duplicate record updating | **PASSED** |
| **MANDI-17** | Freshness calculation (CURRENT vs STALE) | **PASSED** |
| **MANDI-18** | Stale data flag preservation | **PASSED** |
| **MANDI-19** | Current market service query method structure | **PASSED** |
| **MANDI-20** | Buyer Agent context integration | **PASSED** |
| **MANDI-21** | ML forecast vs Current market separation | **PASSED** |
| **MANDI-22** | Buyer RAG vs Current market separation | **PASSED** |
| **MANDI-23** | Budget protection under current mandi data | **PASSED** |
| **MANDI-24** | Reservation ceiling protection under current mandi data | **PASSED** |
| **MANDI-25** | Max quantity protection under current mandi data | **PASSED** |

**Suite Result**: **25 / 25 PASSED (100% clean)**.

---

## 18. Full Regression Results

Running core test suites (`test_05_buyer_negotiation_strategy.py`, `test_06_rag_quality.py`, `test_07_buyer_rag.py`, `test_08_current_mandi_integration.py`, `test_topic1_buyer_matching_flow.py`):
- **87 PASSED, 2 SKIPPED (unseeded env test), 0 FAILURES (100% clean)**.

---

## 19. Files Changed

- `backend/db/models/schema.py` (**MODIFY**): Added `DBCurrentMandiPrice` model table.
- `backend/services/current_mandi_service.py` (**NEW**): Core service for fetching, normalizing, storing, and querying current daily mandi prices.
- `agents/buyer_agent.py` (**MODIFY**): Formatted `current_mandi_data` into prompt as observed mandi price.
- `backend/agents/graph_orchestrator.py` (**MODIFY**): Injected `current_mandi_data` in `buyer_node`.
- `tests/test_08_current_mandi_integration.py` (**NEW**): Test suite covering MANDI-01 to MANDI-25.
- `docs/buyer_priority4_current_mandi_integration.md` (**NEW**): Verification report.

---

## 20. Files Intentionally NOT Changed

- `agents/farmer_agent.py` (**0 lines modified, 100% untouched**).
- Farmer datasets & models (100% untouched).
- `backend/services/buyer_pricing_service.py` (ML model untouched).
- `backend/services/buyer_rag_service.py` (RAG service untouched).

---

## 21. Real API Verification Results

- **Configuration**: Implemented and tested with mocked HTTP payloads matching official `data.gov.in` Agmarknet JSON schema.
- **Statement**: *"API integration is implemented/configured but live verification requires DATA_GOV_API_KEY."*

---

## 22. Known Limitations & Future Improvements

- Live API calls require `DATA_GOV_API_KEY` set in the environment.
- Secondary fallback to third-party endpoints (e.g. `Farmer.in` or `mandi-api`) can be evaluated as a secondary fallback layer in future tasks if desired.
