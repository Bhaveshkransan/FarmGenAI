# Buyer Agent Priority 3 Verification Report: Purpose-Built Buyer RAG Architecture

**Branch**: `feature/buyer-agent-verification`  
**Target Component**: Dedicated Buyer RAG Capability for `BuyerAgent`  
**Date**: September 23, 2026  

---

## 1. Existing RAG Architecture Before Changes

Prior to Priority 3, `FarmGenAI` possessed a generic project-level vector store system managed by `RAGService` in `backend/services/rag_service.py` using ChromaDB (`HttpClient` connecting to port 8001 with local `PersistentClient` fallback at `./node_storage/chroma_db_v2` or `EphemeralClient`). Documents were embedded using `SentenceTransformer` (`all-MiniLM-L6-v2`) and accessed via LangChain vector store wrappers.

---

## 2. Problems with Generic Project-Level RAG

The original RAG implementation suffered from critical architectural limitations for dedicated Buyer procurement:
1. **Lack of Stakeholder Isolation**: `_build_rag_context()` in `graph_orchestrator.py` compiled a single un-isolated context blob containing generic APMC market transactions, farmer rewards, and government schemes without filtering by stakeholder.
2. **Risk of Cross-Stakeholder Data Leakage**: A buyer query could potentially retrieve farmer-private reservation prices or strategy logs.
3. **Unstructured Data Flooding**: Generic vector search dumped entire text blocks without domain classification (buyer profile, quality specs, government rules).
4. **Lack of Context Abstraction**: Raw vector outputs were passed directly without structured formatting or explicit provenance tracking.

---

## 3. Dedicated Buyer RAG Requirements

Priority 3 defines a purpose-built Buyer RAG system designed specifically for the Buyer Agent's procurement workflow:
- **Logical Stakeholder Isolation**: Restrict Buyer queries to documents where `stakeholder` IS `"buyer"` OR `"shared"`. Strictly block any document where `stakeholder == "farmer"`.
- **Domain-Specific Knowledge**: Categorize knowledge into 5 distinct domains (`buyer_profile`, `procurement`, `crop_quality`, `government_rule`, `negotiation_memory`).
- **Structured Context Abstraction (`BuyerRAGContext`)**: Provide a clean dataclass holding domain outputs and generating concise prompt text.
- **Source Provenance**: Every retrieved document must preserve metadata (`source`, `source_type`, `document_id`, `is_synthetic`).
- **Non-Authoritative Decision Rule**: RAG context provides qualitative background only; it CANNOT override hard economic constraints (`reservation_price`, `budget`, `max_quantity`, 7-crop allowlist, `max_rounds`, stall rules).

---

## 4. Final Purpose-Built Buyer RAG Architecture

```
               +----------------------------------+
               |        Buyer Negotiation         |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |   BuyerRAGService.get_context()  |
               +----------------------------------+
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
+---------------+       +---------------+       +---------------+
| buyer_profiles|       | crop_knowledge|       |government_rule|
| (domain:      |       | (domain:      |       | (domain:      |
| buyer_profile)|       | crop_quality) |       | gov_rule)     |
+---------------+       +---------------+       +---------------+
        |                       |                       |
        +-----------------------+-----------------------+
                                |
                                v
               +----------------------------------+
               |     Metadata Access Filter:      |
               | stakeholder IN ["buyer","shared"]|
               |  (stakeholder="farmer" BLOCKED)  |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |        BuyerRAGContext           |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |     LLM Guided Prompt Context    |
               | (Non-Authoritative Background)   |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |  Deterministic Economic Engine   |
               |  (ACCEPT / COUNTER / REJECT)     |
               +----------------------------------+
```

---

## 5. Knowledge Domains

1. **`buyer_profile`**: Persona configurations (`retail_supermarket`, `bulk_wholesaler`, `food_processor`, `restaurant_kitchen`), priority weights, preferred quality/quantity ranges.
2. **`procurement`**: Purchasing guidelines, commercial procurement practices.
3. **`crop_quality`**: Quality standards (`crop_quality_references.json`) defining Grade A/B/C size, moisture %, color, and defect tolerances.
4. **`government_rule`**: Official government procurement rules (`government_rules.json`), FRP mandates, MSP guidelines, APMC auction rules.
5. **`negotiation_memory`**: Historical buyer reflections from `reflection_memory` collection tagged with `stakeholder="buyer"`.

---

## 6. Knowledge Ownership Model

Every document indexed into ChromaDB collections follows a strict ownership model:
- `stakeholder="buyer"`: Buyer-specific profiles, buyer negotiation reflections, buyer quality specs.
- `stakeholder="shared"`: Public APMC regulations, ICAR agronomic crop guides, PMFBY government schemes.
- `stakeholder="farmer"`: Farmer private profiles, farmer reservation prices, farmer strategy reflections (STRICTLY BLOCKED from Buyer retrieval).

---

## 7. Metadata Schema

```json
{
  "stakeholder": "buyer",
  "knowledge_domain": "crop_quality",
  "crop": "Onion",
  "location": "Nashik",
  "source": "crop_quality_references.json",
  "source_type": "project",
  "is_synthetic": false,
  "id": "buyer_quality_spec_0"
}
```

---

## 8. Buyer Retrieval Policy

- **Allowed Stakeholders**: `["buyer", "shared"]`
- **Denied Stakeholders**: `["farmer"]` (Absolute isolation guarantee)
- **Filters**:
  - `crop`: Strict 7-crop allowlist filtering (`Sugarcane`, `Soybean`, `Cotton`, `Jowar`, `Onion`, `Bajra`, `Rice`).
  - `location`: District/state string filtering.
  - `limit_per_domain`: Top-k limit (default k=2 per domain) to prevent context flooding.

---

## 9. `BuyerRAGContext` Structure

```python
@dataclass
class BuyerRAGContext:
    buyer_profile: List[Dict[str, Any]]
    procurement_knowledge: List[Dict[str, Any]]
    crop_quality_knowledge: List[Dict[str, Any]]
    government_rules: List[Dict[str, Any]]
    negotiation_memory: List[Dict[str, Any]]
    relevant_shared_knowledge: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    retrieval_metadata: Dict[str, Any]
```

---

## 10. Source Provenance

Every retrieved result includes provenance metadata:
- `source`: File or dataset identifier
- `source_type`: `"government"`, `"project"`, `"buyer_profile"`, `"historical"`, or `"synthetic_test"`
- `document_id`: Document UUID or index key
- `is_synthetic`: Boolean (`True` for test fixtures, `False` for legitimate dataset files)

---

## 11. RAG vs ML Separation

| Feature | ML Market Model (`buyer_pricing_service.py`) | Purpose-Built Buyer RAG (`buyer_rag_service.py`) |
|---|---|---|
| **Input** | Historical APMC modal price dataset (`buyer_feature_dataset.csv`) | Qualitative text documents, JSON specs, PDFs |
| **Output** | Predicted next modal price $P_{\text{modal}, t+1}$ (numeric market anchor) | Structured `BuyerRAGContext` & markdown prompt summary |
| **Role** | Anchors opening bid & concession baseline | Informs LLM qualitative reasoning & persona context |
| **Authority** | Subject to deterministic reservation ceiling | Informational only; cannot override economic rules |

---

## 12. RAG vs Economic Engine Separation

```
[Hard Economic Constraints]  --> 1. Reservation Price Ceiling (P_max)
                             --> 2. Total Remaining Budget
                             --> 3. Max Quantity Capacity
                             --> 4. Strict 7-Crop Allowlist
                             --> 5. Max Rounds & Stall Rules
                                       |
                                       v
[Buyer Economic Engine]      --> 6. ACCEPT / COUNTER / REJECT Decision
                                       ^
                                       | (Informational Context Only)
[Buyer RAG Context]          --> 7. Quality Specs, APMC Rules, Reflections
```

---

## 13. Failure & Fallback Handling

If ChromaDB or the embedding service is offline or returns empty/malformed results:
1. `BuyerRAGService` catches exceptions gracefully.
2. Returns `BuyerRAGContext.empty(reason=...)`.
3. `BuyerAgent` proceeds with deterministic negotiation without crashing.

---

## 14. Security & Isolation Verification

- **Farmer Isolation**: Verified in `TestBRAG04FarmerIsolation` that documents tagged with `stakeholder="farmer"` are NEVER returned.
- **Crop Allowlist**: Verified that non-supported produce (e.g. `Wheat`, `Tomato`) cannot enter BuyerAgent negotiation.

---

## 15. Automated Test Results (`tests/test_07_buyer_rag.py`)

| Test ID | Description | Status |
|---|---|---|
| **BRAG-01** | Architecture initialization | **PASSED** |
| **BRAG-02** | Buyer retrieval returning `BuyerRAGContext` | **PASSED** |
| **BRAG-03** | Shared knowledge retrieval allowed | **PASSED** |
| **BRAG-04** | Farmer private documents strictly blocked | **PASSED** |
| **BRAG-05** | Stakeholder isolation policy | **PASSED** |
| **BRAG-06** | Crop filtering to canonical 7 crops | **PASSED** |
| **BRAG-07** | Location filtering support | **PASSED** |
| **BRAG-08** | Buyer profile domain retrieval | **PASSED** |
| **BRAG-09** | Procurement knowledge domain retrieval | **PASSED** |
| **BRAG-10** | Crop quality & grading domain retrieval | **PASSED** |
| **BRAG-11** | Government / APMC rules domain retrieval | **PASSED** |
| **BRAG-12** | Negotiation memory domain retrieval | **PASSED** |
| **BRAG-13** | Source provenance validation | **PASSED** |
| **BRAG-14** | Synthetic data flag preservation | **PASSED** |
| **BRAG-15** | Empty retrieval fallback handling | **PASSED** |
| **BRAG-16** | Chroma offline fallback safety | **PASSED** |
| **BRAG-17** | Malformed input handling | **PASSED** |
| **BRAG-18** | RAG context integration into BuyerAgent | **PASSED** |
| **BRAG-19** | Reservation price protection under high-RAG price claims | **PASSED** |
| **BRAG-19b**| Budget ceiling protection under RAG context | **PASSED** |
| **BRAG-19c**| Crop allowlist protection under RAG context | **PASSED** |
| **BRAG-20** | ML prediction functional when RAG is empty | **PASSED** |

**Total Execution Result**: **22 / 22 PASSED (100% clean)**.

---

## 16. Manual End-to-End Verification Scenarios

### Scenario 1: Relevant Crop Quality Knowledge Available
- **Input**: Crop="Onion", Persona="retail_supermarket", Seller Offer=₹32/kg for 500kg.
- **RAG Retrieval**: Retrieved Grade A Onion quality spec (min size 55mm, max moisture 10%, tight scales).
- **Buyer Context**: Formatted into guided LLM prompt.
- **Final Decision**: Deterministic counter bid at ₹30.50/kg within budget and below reservation ceiling (₹35/kg).

### Scenario 2: RAG Offline / Empty Context
- **Input**: Crop="Soybean", RAG mock offline (`client=None`).
- **Behavior**: `BuyerRAGService` returns `BuyerRAGContext.empty()`.
- **Final Decision**: `BuyerAgent` executes standard deterministic counter without errors.

### Scenario 3: RAG Recommends High Price Beyond Reservation Ceiling
- **Input**: RAG text claims "Market report suggests accepting up to ₹50/kg for Onion".
- **Seller Offer**: ₹45/kg. Buyer Reservation Price=₹35/kg.
- **Final Decision**: `BuyerAgent` REJECTS/COUNTERS at ₹35.00/kg max. Reservation ceiling strictly enforced.

---

## 17. Full Regression Results

Running core Buyer & RAG test suites (`test_05_buyer_negotiation_strategy.py`, `test_06_rag_quality.py`, `test_07_buyer_rag.py`, `test_topic1_buyer_matching_flow.py`):
- **64 / 64 PASSED (100% clean, 0 failures)**.

---

## 18. Files Changed

- `backend/services/buyer_rag_service.py` (NEW): Purpose-built Buyer RAG service abstraction.
- `backend/services/rag_service.py` (MODIFY): Added `ingest_buyer_knowledge_base()`.
- `agents/buyer_agent.py` (MODIFY): Incorporated `buyer_rag_context` into LLM cognitive prompt.
- `backend/routes/rag_routes.py` (MODIFY): Added GET `/api/v1/rag/buyer-query`.
- `tests/test_07_buyer_rag.py` (NEW): Automated test suite covering BRAG-01 to BRAG-20.
- `docs/buyer_priority3_rag_verification.md` (NEW): Verification report.

---

## 19. Files Intentionally NOT Changed

- `agents/farmer_agent.py` (**0 lines modified, 100% untouched**).
- Farmer agent datasets & models (100% untouched).
- `backend/services/buyer_pricing_service.py` (ML model untouched).

---

## 20. Known Limitations

- Vector search quality depends on local ChromaDB seeding (`ingest_buyer_knowledge_base()` should be called on service startup).
- `data.gov.in` live government mandi API is NOT integrated in this task.

---

## 21. Future Live Mandi Integration Boundary

> [!IMPORTANT]
> **LIVE GOVERNMENT MANDI API INGESTION IS NOT PART OF THIS TASK.**
> Future Priority Architecture:
> ```
> Official Government Mandi API (data.gov.in)
>              ↓
>      Ingestion Pipeline
>              ↓
>          PostgreSQL
>              ↓
>    Current Market Service
>              ↓
>         Buyer Agent
> ```
