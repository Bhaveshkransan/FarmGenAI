# Agent Communication Contract & Authoritative State Specification

**Specification Version:** `2.0.0-PROD`  
**Governing Architecture:** LangGraph Stateful Multi-Agent System  
**Framework Law:** Maharashtra Agricultural Produce Marketing (Development and Regulation) Act & Model APMC Electronic Trading Rules  

---

## 1. Authoritative Orchestration State Contract

The central authoritative state is defined as `BuyerOrchestrationGraphState` (and mirrored in the PostgreSQL `negotiations` table). It maintains full provenance and cross-contract auditability across all five domain agents.

```python
class BuyerOrchestrationGraphState(TypedDict, total=False):
    # 1. Identification & Traceability
    workflow_id: str                      # Unique supply chain workflow execution identifier
    trace_id: str                         # W3C Distributed tracing correlation ID
    negotiation_id: str                   # Primary session key linked to DB
    requirement_id: Optional[str]         # Associated buyer requirement UUID
    listing_id: Optional[str]             # Farmer produce listing UUID

    # 2. Stakeholders & Agricultural Produce
    farmer_id: str                        # Persisted farmer entity UUID
    farmer_name: str                      # Verified producer name / FPO
    buyer_id: str                         # Persisted buyer entity UUID
    buyer_name: str                       # Procurement enterprise name
    crop: str                             # Canonical 7-Crop: Sugarcane, Soybean, Cotton, Jowar, Onion, Bajra, Rice
    quantity: float                       # Numerical volume in standard kilograms (kg)
    units: str                            # Authoritative standard unit: "kg" (or "MT" for bulk freight)
    farmer_floor_price: float             # Inviolable minimum farmer net reserve price (₹/kg)
    target_price: float                   # Buyer target procurement price (₹/kg)
    reservation_price: float              # Buyer hard ceiling ceiling price P_max (₹/kg)
    budget: float                         # Total landed procurement financial budget (₹)
    location: str                         # Pickup APMC Mandi / Village Hub in Maharashtra

    # 3. Policy & Dynamic Routing Scoping
    workflow_mode: str                    # "FULL_SUPPLY_CHAIN" | "SINGLE_AGENT"
    permitted_agents: List[str]           # Enforced allowable agents: ["BUYER", "TRANSPORT", "WAREHOUSE", "PROCESSOR"]
    completed_agents: List[str]           # Completed lifecycle stages: ["PLANNING", "FARMER", "BUYER", "TRANSPORT", ...]
    current_active_node: str              # Currently executing LangGraph node
    status: str                           # High-level state: "ACTIVE", "DEAL", "NO_EXECUTABLE_DEAL", "FAILED"

    # 4. Domain Service Triggers
    need_transport: bool                  # Evaluated: False if farmer delivers or mode excludes transport
    need_storage: bool                    # Evaluated: False if holding not required or own godown exists
    holding_days: int                     # Planned warehouse storage duration (days)
    allow_processing: bool                # Evaluated: True if raw commodity requires industrial milling

    # 5. Domain Agent State Records
    candidates: List[Dict[str, Any]]      # Discovered candidate sellers from APMC mandi network
    negotiations: List[Dict[str, Any]]    # Concurrently executed multi-round negotiation transcripts
    winner: Optional[Dict[str, Any]]      # Selected winning produce counterparty
    transport_assignment: Optional[Dict]  # Persisted transport dispatch plan & carrier contract
    warehouse_assignment: Optional[Dict]  # Persisted MSWC godown reservation & e-NWR receipt
    processor_assignment: Optional[Dict]  # Persisted industrial processing agreement & SLA
    end_to_end_deal: Optional[Dict]       # Complete consolidated contract with SHA-256 digital signature

    # 6. Authoritative Settlement & Economic Validation
    actual_net_realization: float         # Verified: Farmer Gross - APMC Cess >= Farmer Floor Price
    apmc_cess_amount: float               # Mandatory statutory 1.0% APMC market fee (₹)
    total_landed_cost: float              # Base Produce + Freight + Storage + Processing + Cess
    budget_compliant: bool                # Verified: Total Landed Cost <= Buyer Budget
    contract_hash: str                    # Cryptographic SHA-256 tamper-evident digital seal

    # 7. Telemetry & Logs
    logs: List[str]                       # Sequential, immutable audit trail of agent executions
    emitted_events: List[str]             # List of broadcasted event tags
```

---

## 2. Explicit Lifecycle State Separation

To eliminate confusion between preliminary estimates and legally binding commitments, the system enforces 8 discrete lifecycle states:

```
[ESTIMATED] ──> [REQUESTED_QUOTE] ──> [RECEIVED_QUOTE] ──> [NEGOTIATED_OFFER]
                                                                  │
                                                                  ▼
[CONFIRMED_BOOKING / RESERVATION] <── [ACCEPTED_AGREEMENT]
            │
            ▼
       [COMPLETED]  (or [CANCELLED / FAILED])
```

| Lifecycle State | Defining Criteria | Authoritative Evidence |
| :--- | :--- | :--- |
| **`ESTIMATED`** | Algorithmically predicted cost based on historical benchmarks or distance formulas. Not binding on any carrier or godown. | Telematics baseline rate ($\approx ₹40/\text{km}$); MSWC indicative tariff ($₹42/\text{MT}/\text{week}$). |
| **`REQUESTED_QUOTE`** | Formal dispatch of procurement inquiry to candidate counterparties or logistics providers. | Outbound multi-agent procurement dispatch logged with request timestamp. |
| **`RECEIVED_QUOTE`** | Concrete counter-offer submitted by candidate seller, carrier, or warehouse with locked price and valid period. | Inbound bid recorded with candidate ID, price, and expiration window. |
| **`NEGOTIATED_OFFER`** | Concession reached through automated multi-round Nash equilibrium or game-theoretic bargaining. | Round-by-round offer stored with concession delta ($\Delta P$) and strategy tag. |
| **`ACCEPTED_AGREEMENT`** | Mutual consensus reached meeting both Farmer Floor ($P \ge \text{Floor}$) and Buyer Ceiling ($P \le P_{\max}$). | Winner marked with `is_best: true`, contract terms drafted. |
| **`CONFIRMED_BOOKING`** | Real fleet operator assigned with vehicle license plate, driver verification, and guaranteed transit SLA. | Telematics vehicle ID (e.g. `MH-12-RN-8821`), driver name, and route toll manifest. |
| **`CONFIRMED_RESERVATION`** | Certified godown slot allocated with bay number, climate parameters, and electronic Negotiable Warehouse Receipt. | e-NWR receipt number (e.g. `MSWC-2026-9921`), bay ID, moisture monitoring active. |
| **`CONFIRMED_AGREEMENT`** | Industrial agro-processor contracted with guaranteed milling yield conversion and batch SLA. | Batch ID (e.g. `MILL-2026-B4`), processing tariff, yield percentages. |
| **`COMPLETED`** | Cross-contract audit validated, farmer net payout verified, and SHA-256 digital signature recorded. | Immutable SHA-256 hash stored in PostgreSQL and delivered to frontend. |
| **`CANCELLED / FAILED`** | Any stage failed sanity checks, exceeded reservation ceilings, or violated economic protections. | Rejection reason recorded, inventory released, downstream agents blocked. |

---

## 3. Versioned Inter-Agent Message Envelope (v2.0)

All inter-agent messages communicated through the LangGraph orchestrator or WebSocket bus adhere to the following schema:

```json
{
  "$schema": "https://farmgenai.org/schemas/agent-message-v2.json",
  "version": "2.0.0",
  "message_id": "msg-8f2e4b1a-9c7d",
  "trace_id": "trace-5b7040a-prod",
  "workflow_id": "wf-neg_49bdbfad",
  "timestamp": "2026-10-20T17:20:11.412Z",
  "sender": {
    "agent_id": "transport_agent",
    "role": "TRANSPORT",
    "node": "calculate_freight_node"
  },
  "recipient": {
    "agent_id": "buyer_orchestrator",
    "role": "BUYER"
  },
  "message_type": "CONFIRMED_TRANSPORT_QUOTE",
  "correlation_id": "req-tr-0042",
  "payload": {
    "lifecycle_state": "CONFIRMED_BOOKING",
    "vehicle_type": "Tata Ace Gold",
    "vehicle_number": "MH-12-RN-8821",
    "driver_name": "Ashok Shinde",
    "origin": "Latur APMC Yard",
    "destination": "Pune Agro Industrial Hub",
    "distance_km": 213.0,
    "base_freight": 6543.43,
    "toll_charges": 426.0,
    "fuel_surcharge": 2130.0,
    "total_tariff": 9099.43,
    "transit_hours": 5.5,
    "refrigerated": false
  },
  "signature": "0x4b7e8d2a1c9f3e5b..."
}
```

---

## 4. Centrally Enforced Business Rules

Deterministic business logic is strictly isolated from LLM output. LLM reasoning may propose explanations or human negotiation language, but all calculations and guardrails are enforced deterministically:

1. **Farmer Floor Protection:**  
   $$\text{Farmer Net Realization} = \text{Gross Deal Value} - \text{APMC Cess} \ge \text{Farmer Price Floor}$$  
   If an offer or settlement would yield a net price below the farmer's designated minimum reserve price, the workflow immediately rejects the offer or fails validation.

2. **Inventory Non-Overselling:**  
   $$\text{Procurement Quantity} \le \text{Listing Available Inventory}$$  
   Upon successful deal closure, `Database.deduct_produce_inventory_async(listing_id, qty)` atomically decrements remaining crop stock.

3. **Perishable Cold-Chain Compliance:**  
   Perishable commodities (e.g. Onion, Tomato, fresh fruit) mandate climate-controlled transit (reefer vehicles with temperature $-5^\circ\text{C}$ to $10^\circ\text{C}$) and MSWC cold-storage godowns. Dry cargo allocation for perishables is rejected.

4. **Moisture & Quality Ceilings:**  
   Industrial processors enforce commodity-specific moisture thresholds (e.g. Soybean $\le 12.0\%$, Cotton $\le 8.5\%$, Paddy $\le 12.5\%$). Produce exceeding moisture limits is rejected or flagged for pre-drying holding.

5. **Strict Scope Authorization:**  
   In `SINGLE_AGENT` mode (e.g. Buyer-only or Transport-only), the policy gatekeeper forbids downstream agent executions. Unauthorized agents cannot be scheduled via retries, copilot actions, or recovery steps.
