# FarmGenAI: Farmer-Side End-to-End Execution Report

**Audit Target:** Complete Farmer-Side User Journey & System Integration  
**Auditor:** Senior QA Lead (10+ Years Manual & Automated Testing Experience)  
**Execution Timestamp:** October 2026  
**Git Branch & Commit Tested:** `main` @ `6d63ba1a8fba53c66f1130b5578586f401a45adf`  
**Database Verified:** PostgreSQL 16 on `localhost:5433` (Docker: `farmgenai-postgres`)  
**Cache & Bus Verified:** Redis 7 on `localhost:6379` (Docker: `farmgenai-redis`)  
**LLM & Vector Infrastructure:** Google Gemini API + Ollama fallback (`qwen2:0.5b`) + Local ChromaDB PersistentClient  

---

## 1. Complete End-to-End Farmer User Journey

The audit executed an uninterrupted journey representing a real farmer selling Cotton in Maharashtra.

### Step 1: Authentication & Identity Establishment
- **Action:** User submits credentials at `/login`.
- **API Call:** `POST /api/v1/auth/login`
- **Payload:** `{"email": "farmer@agrinegotiator.com", "password": "farmer123"}`
- **Observed Response:** HTTP 200 OK.
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "user": {
      "id": "usr_farmer_demo",
      "email": "farmer@agrinegotiator.com",
      "role": "farmer",
      "full_name": "Ramesh Patil"
    }
  }
  ```
- **Database Verification:** PostgreSQL `v1_users` matched; password verified via bcrypt.

### Step 2: Dashboard Overview & Market Intelligence
- **Action:** Farmer opens `/dashboard/farmer`.
- **API Calls:**
  - `GET /api/v1/dashboards/farmer` -> Returned Trust Score `4.9`, Deals Closed `1`, Total Earnings `₹65,000.00`.
  - `GET /api/v1/listings/me` -> Loaded active crop listings.
  - `GET /api/v1/market-intelligence/compare?crop=Cotton&lat=19.9975&lon=73.7898` -> Loaded 14 APMC Mandis (Nashik APMC modal ₹65.0/kg, net realization ₹62.44/kg).
- **DOM Verification:** Header dynamically renders *"Welcome back, Ramesh Patil!"*, Trust Score *"4.9 / 5.0"*, and Live Market status dot pulses green.

### Step 3: Crop Listing Creation Across Canonical Crops
- **Action:** Farmer opens CreateListingForm and submits Cotton lot.
- **API Call:** `POST /api/v1/listings/`
- **Payload:**
  ```json
  {
    "crop": "Cotton",
    "quantity": 2500.0,
    "min_price": 68.0,
    "expected_price": 78.2,
    "grade": "Medium Staple",
    "shelf_life": 180,
    "location": "Nagpur"
  }
  ```
- **Observed Response:** HTTP 200 OK, `listing_id="e224cc7b-4ee"`.
- **Database Verification:**
  ```sql
  SELECT id, crop, quantity, min_price, location, status FROM produce WHERE id = 'e224cc7b-4ee';
  -- Result: ('e224cc7b-4ee', 'Cotton', 2500.0, 68.0, 'Nagpur', 'ACTIVE')
  ```

### Step 4: Autonomous Negotiation Initialization
- **Action:** Farmer clicks "AI Match & Negotiate" on the Cotton listing.
- **API Call:** `POST /api/v1/negotiations/`
- **Payload:**
  ```json
  {
    "user_id": "usr_farmer_demo",
    "farmer_name": "Ramesh Patil",
    "crop": "Cotton",
    "quantity": 2500.0,
    "min_price": 68.0,
    "shelf_life": 180,
    "location": "Nagpur",
    "quality": "Medium Staple",
    "language": "en",
    "listing_id": "e224cc7b-4ee"
  }
  ```
- **Observed Response:** HTTP 200 OK.
  - `negotiation_id`: `"neg_c0b963ab"`
  - `status`: `"ACTIVE"`
  - `matched_buyer`: `"Vidarbha Ginning & Spinning Mill"` (Match Score: 91.0%, Strategy: 👑 Best Profit)
  - `Round 1 Offer`: ₹68.00/kg

### Step 5: Floor Price Defense Under Predatory Counter-Offer
- **Scenario:** Buyer attempts a low-ball counter-offer below the farmer's reserve price (₹60.00/kg vs ₹68.00/kg reserve).
- **API Call:** `POST /api/v1/negotiations/neg_c0b963ab/counter`
- **Payload:**
  ```json
  {
    "sender": "buyer",
    "counter_price": 60.0,
    "quantity": 2500.0,
    "message": "Offering below floor price"
  }
  ```
- **Observed Response:** HTTP 200 OK.
  - `status`: `"ACTIVE"`
  - `decision`: `"COUNTER"`
  - `farmer_response.price`: `68.0`
  - `farmer_response.message`: `"Ramesh Patil: COUNTER ₹68.0/kg: Offer is below minimum. Standing firm at my floor price."`
- **Integrity Check:** The system **strictly defended** the farmer's minimum floor. The low offer was NOT accepted.

### Step 6: Commercial Offer Counter & Agreement
- **Scenario:** Buyer responds with a commercially viable offer above the floor price (₹72.00/kg).
- **API Call:** `POST /api/v1/negotiations/neg_c0b963ab/counter`
- **Payload:**
  ```json
  {
    "sender": "buyer",
    "counter_price": 72.0,
    "quantity": 2500.0,
    "message": "Offering fair commercial price"
  }
  ```
- **Observed Response:** HTTP 200 OK.
  - `status`: `"DEAL"`
  - `final_price`: `72.0`
  - `decision`: `"ACCEPT"`
  - `farmer_response.message`: `"Ramesh Patil: ACCEPTED ₹72.0/kg: Price meets our target expectation."`

### Step 7: AI Copilot Strategic Guidance
- **Action:** Farmer queries AI Copilot on offer competitiveness.
- **API Call:** `POST /api/v1/negotiations/neg_c0b963ab/copilot-action`
- **Prompt:** `"Evaluate if Rs 72 per kg is competitive compared to Vidarbha APMC modal price and advise counter."`
- **Observed Response:** HTTP 200 OK.
  ```json
  {
    "success": true,
    "benchmark_price": 71.21,
    "current_offer": 72.0,
    "is_competitive": true,
    "action": "ACCEPT",
    "copilot_advice": "🤖 [AI Copilot Evaluation]: The current offer of ₹72.00/kg for Cotton is competitive and near/above the statutory APMC benchmark (₹71.21/kg). Accepting the deal locks in profit."
  }
  ```

### Step 8: APMC Smart Contract Minting & Escrow Settlement
- **Action:** Farmer confirms deal execution via "Contract / Accept Deal".
- **API Call:** `POST /api/v1/negotiations/neg_c0b963ab/accept`
- **Observed Response:** HTTP 200 OK.
  - `transaction_id`: `"TXN-MH-2026-C0B963AB"`
  - `contract_hash`: `"0x367f0fec67c6999b24bcf84ecbb88c1c53e02047ff3a3399b2f6fb49fefaeef3"`
- **Database Verification:**
  ```sql
  SELECT negotiation_id, status, final_price, transaction_id, contract_hash 
  FROM negotiations WHERE negotiation_id = 'neg_c0b963ab';
  -- Result: ('neg_c0b963ab', 'DEAL', 72.0, 'TXN-MH-2026-C0B963AB', '0x367f0fec67c6999b24bcf84ecbb88c1c53e02047ff3a3399b2f6fb49fefaeef3')
  ```
- **Escrow Settlement:** `POST /api/v1/negotiations/neg_c0b963ab/settle` executed successfully; escrow account `ESC-MH-2026-C0B963AB` set to `ESCROW_SETTLED`.

---

## 2. Seven Canonical Crops Positive Listing Evidence

All 7 crops were created through the API, verified against Pydantic validators, and confirmed persisted in PostgreSQL `produce`:

| Crop | Quantity (kg) | Reserve Price (₹/kg) | Grade | Location | PostgreSQL Produce ID | Persisted? |
|---|---|---|---|---|---|---|
| Sugarcane | 50,000.0 | ₹3.20 | Grade A | Kolhapur | `aa2a0602-9b8` | **YES** |
| Soybean | 4,000.0 | ₹45.00 | FAQ | Latur | `b8e88344-ddc` | **YES** |
| Cotton | 2,500.0 | ₹68.00 | Medium Staple | Nagpur | `e224cc7b-4ee` | **YES** |
| Jowar | 3,000.0 | ₹32.00 | Maldandi | Solapur | `8c6ef5c7-e57` | **YES** |
| Onion | 6,000.0 | ₹22.00 | Garva | Nashik | `bdc3b941-cf7` | **YES** |
| Bajra | 2,000.0 | ₹24.00 | Hybrid | Dhule | `5651724d-355` | **YES** |
| Rice | 3,500.0 | ₹38.00 | Indrayani | Pune | `a706c960-3e6` | **YES** |

---

## 3. Negative & Boundary Execution Evidence

| Test Scenario | Submitted Payload | Observed Status Code | Error Message Truncation | Verdict |
|---|---|---|---|---|
| Negative Quantity | `quantity: -500.0` | 422 Unprocessable | `Input should be greater than 0` | **PASS** |
| Zero Quantity | `quantity: 0.0` | 422 Unprocessable | `Input should be greater than 0` | **PASS** |
| Negative Price | `min_price: -20.0` | 422 Unprocessable | `Input should be greater than 0` | **PASS** |
| Min > Expected Price | `min_price: 80, expected: 70` | 422 Unprocessable | `minimum price cannot be greater than expected price` | **PASS** |
| Oversized Lot Minimum | `qty: 1000, min_sale: 2000` | 422 Unprocessable | `minimum_sale_quantity cannot be greater than available`| **PASS** |
| Non-Canonical Crop | `crop: "Wheat"` | 422 Unprocessable | `Unsupported crop: 'Wheat'. Supported crops: Sugarcane...` | **PASS** |
| Missing Crop Field | `{quantity: 1000, min_price: 30}` | 422 Unprocessable | `Field required: crop` | **PASS** |
| Invalid JWT Token | `Authorization: Bearer bad_token`| 401 Unauthorized | `Invalid or expired token.` | **PASS** |
| Non-Existent Negotiation | `GET /negotiations/neg_fake_999`| 404 Not Found | `Negotiation not found` | **PASS** |
| Non-Existent Listing | `GET /listings/lst_fake_999` | 404 Not Found | `Listing not found` | **PASS** |

---

## 4. Downstream Logistics & Multi-Stakeholder Integration

- **Transport Search (`GET /transport/carriers`):** 3 live fleet providers retrieved with truck capacity, fuel cost adjustments, and ETA feasibility.
- **Warehouse Facilities (`GET /warehouse/nearby`):** 3 certified warehouses within 200km retrieved with licensed crop storage tags and per-day tariffs.
- **Processor Discovery (`GET /processors/matching`):** Matched industrial spinning and processing units in Vidarbha.
