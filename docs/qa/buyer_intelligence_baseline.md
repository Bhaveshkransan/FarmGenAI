# FarmGenAI Buyer Agent — Baseline Architecture and Intelligence Gap Analysis

**Date:** October 17, 2026  
**Document ID:** `docs/qa/buyer_intelligence_baseline.md`  
**Author:** AI/ML Supply-Chain & QA Engineering Team  
**Scope:** Buyer Agent Decision Logic, Supply-Chain Optimization, and Negotiation Memory Baseline  

---

## 1. Executive Summary

This document establishes the technical baseline of the **FarmGenAI Buyer Agent** system prior to the implementation of intelligent end-to-end supply-chain decision logic. The system currently features robust foundational components—including a multi-agent negotiation orchestrator, canonical 7-crop catalog, multi-attribute utility models, and a seeded PostgreSQL database. However, significant gaps exist in dynamic warehouse selection, crop-specific shelf-life degradation modeling, multi-trip vehicle allocation, integrated landed cost optimization, and persistent cross-session negotiation memory.

---

## 2. Repository & System Inventory

### 2.1 Git Branch & Working Tree
* **Branch:** `main` (ahead of `origin/main` by 54 commits).
* **Workspace:** `D:\Projects\FarmGenAI_AgriNegotiator` / `D:\Projects\Code_Repositories\FarmGenAI`.
* **Services Active (Docker):**
  - `farmgenai-backend` (FastAPI / Uvicorn on port 8000)
  - `farmgenai-frontend` (Vite / React / Nginx on port 8080)
  - `farmgenai-postgres` (PostgreSQL 16 on port 5433)
  - `farmgenai-redis` (Redis 7 on port 6379)
  - `farmgenai-chroma` (ChromaDB on port 8001)
  - `farmgenai-worker` (Async Celery/Redis worker)

### 2.2 Seeded Database Records (PostgreSQL `agrinegotiator`)
* **Farmers (`farmers` table):** 153 rows (authentic + synthetic across 20 Maharashtra districts).
* **Produce Listings (`produce` table):** 287 active multi-grade lots covering all 7 crops.
* **Buyer Requirements (`buyers` table):** 125 buyer requirements and commercial profiles.
* **Warehouses (`warehouses` table):** 61 active warehouses (ambient grain silos and cold storage).
* **Agro-Processors (`processors` table):** 39 industrial processing plants (sugar, solvent, ginning, milling).
* **Transport Fleet (`vehicles` & `transporters` tables):** 56 vehicles across 6 classes, 166 transport records.
* **Negotiations (`negotiations` table):** 28 persisted negotiation sessions with multi-round logs.

### 2.3 Existing Synthetic Datasets (`backend/dataset/synthetic/`)
* `synthetic_farmers.json` (119 records)
* `synthetic_produce_listings.json` (249 records)
* `synthetic_warehouses.json` (40 records)
* `synthetic_processors.json` (24 records)
* `synthetic_vehicles.json` (40 records)
* `synthetic_buyer_requirements.json` (80 records)
* `synthetic_negotiations.json` (20 records)

---

## 3. Component-by-Component Baseline Audit

### 3.1 Buyer Agent (`agents/buyer_agent.py` & `backend/services/buyer_orchestrator.py`)
* **Existing Strengths:**
  - Multi-attribute utility function evaluating Price, Quantity, and Freshness.
  - Concession schedule algorithms: `Boulware`, `Linear`, `Conceder`, and `Aggressive`.
  - Deterministic reservation ceiling ($P_{\max}$) and strict budget constraints.
  - Isolated parallel multi-branch negotiation engine (`_negotiate_single_seller_branch`).
* **Identified Gaps:**
  - Lacks persistent retrieval of historical negotiation outcomes when initializing opening bids for a new session.
  - Concession schedule does not adapt dynamically based on previous supplier counter-offer behavior in past sessions.
  - Landed cost calculation in orchestrator uses a static linear approximation (`dist * 6.50 + req_qty * 0.35`) rather than the actual vehicle fleet and warehouse selection.

### 3.2 Warehouse Selection (`backend/services/storage_service.py` & `agents/warehouse_agent.py`)
* **Existing State:**
  - `storage_service.py` contains a legacy `_WAREHOUSE_PROFILES` array with only 3 hardcoded warehouses (`wh_nashik_cold`, `wh_pune_hub`, `wh_mumbai_port`).
  - Does not query the 61 active warehouses in PostgreSQL.
* **Identified Gaps:**
  - No crop compatibility checks (e.g., Sugarcane cannot be stored in ambient grain silos; Onions require dry, ventilated or temperature-controlled cold storage).
  - No capacity validation against requested quantity.
  - No ranking or explanation of why one warehouse is selected over competing facilities.
  - No spoilage risk or shelf-life suitability calculation.

### 3.3 Shelf-Life & Storage-Duration Logic
* **Existing State:**
  - Shelf-life exists as a static integer attribute (`shelf_life` in days) on produce listings.
* **Identified Gaps:**
  - Does not compute elapsed days since harvest (`today - harvest_date`).
  - Does not factor in transit time and storage duration against the buyer's required delivery deadline.
  - Does not evaluate temperature-dependent decay rate (Arrhenius approximation: cold chain extends shelf-life by 2.5x to 4x for perishables like Onion, whereas ambient storage accelerates decay).
  - Does not reject infeasible options where usable life remaining at delivery is less than required.

### 3.4 Transport Vehicle Selection (`backend/services/transport_service.py`)
* **Existing State:**
  - `transport_service.py` defines `_FLEET` with 3 vehicles (max capacity 6,500 kg).
  - Crashes with `ValueError: No vehicle can handle this shipment quantity` if shipment > 6,500 kg.
* **Identified Gaps:**
  - No multiple-trip computation for quantities exceeding individual vehicle capacity (e.g. 15,000 kg or 35,000 kg).
  - Does not evaluate temperature-control (refrigerated van) constraints for perishable commodities.
  - Does not utilize the 56 vehicles available in the database across Maharashtra districts.
  - Does not calculate loading/unloading turnaround times and deadline feasibility.

### 3.5 Negotiation Memory & Learning
* **Existing State:**
  - `negotiations` table persists negotiation logs, final price, status, and summary.
* **Identified Gaps:**
  - No automated retrieval of prior negotiations for the same buyer, crop, or mandi during session initialization.
  - Prior discount rates and concession patterns are not used to tune BATNA or initial offers.
  - Buyer privacy isolation must be strictly enforced so that Buyer A's historical concession data is never used in negotiations on behalf of Buyer B.

---

## 4. Architectural Target & Implementation Plan

To close these gaps without disrupting existing functioning APIs:

1. **Intelligent Supply-Chain Engine (`backend/services/supply_chain_intelligence_service.py`):**
   - **Warehouse Selector:** Query real PostgreSQL warehouses, evaluate crop compatibility, check available capacity, calculate road distance, compute storage cost over duration, and output transparent ranked alternatives with rejection reasons.
   - **Shelf-Life Evaluator:** Calculate remaining freshness:
     $$\text{Remaining Usable Days} = \text{Base Shelf Life} - (\text{Today} - \text{Harvest Date}) - \text{Transit Days} - \text{Storage Days}$$
     Apply cold-chain deceleration multipliers where applicable. Reject lots that cannot meet buyer's delivery deadline and minimum usable life.
   - **Transport Optimizer:** Select optimal vehicle from the database fleet, compute required trips ($\lceil \text{Quantity} / \text{Capacity} \rceil$), check reefer requirements, calculate freight cost, fuel, and transit hours.
   - **Integrated Landed Cost:**
     $$\text{Landed Cost} = \text{Base Price} + \text{Freight Total} + \text{Storage Total} + \text{APMC Cess} + \text{Handling}$$
2. **Persistent Negotiation Memory (`backend/services/negotiation_memory_service.py`):**
   - Query PostgreSQL `negotiations` filtered by `user_id` / `buyer_id` and `crop`.
   - Calculate historical acceptance rate, average final discount percentage, and average concession velocity.
   - Adjust opening bid and BATNA dynamically within deterministic budget and ceiling bounds.
3. **Integration & API Exposure:**
   - Integrate with `buyer_orchestrator.py` and `matching_service.py`.
   - Expose endpoints via `/api/v1/requirements/orchestrate` and `/api/v1/matching/...`.
4. **Validation & 50-Case Visible Demonstration:**
   - Generate 50 reproducible randomized cases across all 7 crops and valid ranges.
   - Run visible test execution and generate evidence artifacts.
