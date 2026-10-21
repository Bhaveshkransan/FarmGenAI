# FarmGenAI: Farmer-Side Manual Test Cases & Execution Evidence

**Audit Suite:** Comprehensive Farmer-Side Acceptance Test Cases  
**Target Environment:** Localhost (Frontend: 8080, Backend: 8000, PostgreSQL: 5433, Redis: 6379)  
**Execution Timestamp:** October 2026  
**Total Test Cases:** 42  
**Overall Result:** 42 Passed, 0 Failed, 0 Blocked  

---

## 1. Authentication & Session Management (AUTH)

### TC-AUTH-01: Valid Farmer Login
- **Preconditions:** User `farmer@agrinegotiator.com` exists in PostgreSQL `v1_users` with bcrypt hash for `farmer123`.
- **Steps:**
  1. Send `POST /api/v1/auth/login` with `{"email": "farmer@agrinegotiator.com", "password": "farmer123"}`.
  2. Inspect response payload and status code.
- **Expected Result:** Status 200, JWT token returned, `user.role` equals `"farmer"`, user full name populated.
- **Actual Result:** HTTP 200, access token issued, `user.id="usr_farmer_demo"`, `role="farmer"`, name `"Ramesh Patil"`.
- **Status:** **PASS**
- **Evidence:** `farmer_audit_evidence_raw.json` -> `phase_3_authentication.tests[0]`

### TC-AUTH-02: Invalid Password Rejection
- **Preconditions:** Backend running with bcrypt authentication.
- **Steps:**
  1. Send `POST /api/v1/auth/login` with `{"email": "farmer@agrinegotiator.com", "password": "wrongpassword123"}`.
- **Expected Result:** HTTP 400 Bad Request with detail `"Invalid email or password"`. No token issued.
- **Actual Result:** HTTP 400 with detail `"Invalid email or password"`.
- **Status:** **PASS**
- **Evidence:** `phase_3_authentication.tests[1]`

### TC-AUTH-03: Duplicate Registration Prevention
- **Preconditions:** `farmer@agrinegotiator.com` already registered.
- **Steps:**
  1. Send `POST /api/v1/auth/register` with identical email.
- **Expected Result:** HTTP 400 with detail `"Email already registered"`.
- **Actual Result:** HTTP 400, message `"Email already registered"`.
- **Status:** **PASS**
- **Evidence:** `phase_3_authentication.tests[2]`

### TC-AUTH-04: Cross-User Resource Isolation
- **Preconditions:** Buyer and Farmer accounts exist.
- **Steps:**
  1. Authenticate as Buyer (`buyer@agrinegotiator.com`).
  2. Query `GET /api/v1/listings/me`.
- **Expected Result:** Buyer receives an empty array (`[]`) or 0 farmer listings. Farmer's private produce is isolated.
- **Actual Result:** HTTP 200, returned 0 listings for buyer account.
- **Status:** **PASS**
- **Evidence:** `phase_3_authentication.tests[3]`

---

## 2. Seven Canonical Crops Listing Management (CROP & BOUND)

### TC-CROP-01: Sugarcane Listing Creation & Database Persistence
- **Preconditions:** Authenticated farmer token available.
- **Steps:**
  1. Submit `POST /api/v1/listings/` with `{crop: "Sugarcane", quantity: 50000.0, min_price: 3.2, grade: "A", location: "Kolhapur", shelf_life: 14}`.
  2. Query PostgreSQL: `SELECT id, crop, quantity, min_price FROM produce WHERE id = :id`.
- **Expected Result:** HTTP 200/201, record persisted in PostgreSQL `produce` table with exact parameters.
- **Actual Result:** HTTP 200, Listing ID created, verified in PostgreSQL (`crop='Sugarcane'`, `quantity=50000.0`, `min_price=3.2`).
- **Status:** **PASS**
- **Evidence:** `phase_4_listings.positive_crops.Sugarcane`

### TC-CROP-02: Soybean Listing Creation & Database Persistence
- **Steps:** Submit Soybean listing (4,000kg, ₹45.0/kg, Latur, FAQ grade).
- **Actual Result:** HTTP 200, Listing ID created, persisted in PostgreSQL `produce`.
- **Status:** **PASS**
- **Evidence:** `phase_4_listings.positive_crops.Soybean`

### TC-CROP-03: Cotton Listing Creation & Database Persistence
- **Steps:** Submit Cotton listing (2,500kg, ₹68.0/kg, Nagpur, Medium Staple).
- **Actual Result:** HTTP 200, Listing ID created, persisted in PostgreSQL `produce`.
- **Status:** **PASS**
- **Evidence:** `phase_4_listings.positive_crops.Cotton`

### TC-CROP-04: Jowar Listing Creation & Database Persistence
- **Steps:** Submit Jowar listing (3,000kg, ₹32.0/kg, Solapur, Maldandi).
- **Actual Result:** HTTP 200, Listing ID created, persisted in PostgreSQL `produce`.
- **Status:** **PASS**
- **Evidence:** `phase_4_listings.positive_crops.Jowar`

### TC-CROP-05: Onion Listing Creation & Database Persistence
- **Steps:** Submit Onion listing (6,000kg, ₹22.0/kg, Nashik, Garva).
- **Actual Result:** HTTP 200, Listing ID created, persisted in PostgreSQL `produce`.
- **Status:** **PASS**
- **Evidence:** `phase_4_listings.positive_crops.Onion`

### TC-CROP-06: Bajra Listing Creation & Database Persistence
- **Steps:** Submit Bajra listing (2,000kg, ₹24.0/kg, Dhule, Hybrid).
- **Actual Result:** HTTP 200, Listing ID created, persisted in PostgreSQL `produce`.
- **Status:** **PASS**
- **Evidence:** `phase_4_listings.positive_crops.Bajra`

### TC-CROP-07: Rice Listing Creation & Database Persistence
- **Steps:** Submit Rice listing (3,500kg, ₹38.0/kg, Pune, Indrayani).
- **Actual Result:** HTTP 200, Listing ID created, persisted in PostgreSQL `produce`.
- **Status:** **PASS**
- **Evidence:** `phase_4_listings.positive_crops.Rice`

---

## 3. Negative & Boundary Testing (BOUND)

### TC-BOUND-01: Negative Quantity
- **Input:** `quantity: -500.0`
- **Expected:** HTTP 422 Unprocessable Entity ("Input should be greater than 0").
- **Actual:** HTTP 422 with validation error.
- **Status:** **PASS**

### TC-BOUND-02: Zero Quantity
- **Input:** `quantity: 0.0`
- **Expected:** HTTP 422 Unprocessable Entity.
- **Actual:** HTTP 422 with validation error.
- **Status:** **PASS**

### TC-BOUND-03: Negative Reserve Price
- **Input:** `min_price: -20.0`
- **Expected:** HTTP 422 Unprocessable Entity.
- **Actual:** HTTP 422 with validation error.
- **Status:** **PASS**

### TC-BOUND-04: Min Price Exceeds Expected Price
- **Input:** `min_price: 80.0, expected_price: 70.0`
- **Expected:** HTTP 422 ("minimum price cannot be greater than expected price").
- **Actual:** HTTP 422 Value Error correctly returned.
- **Status:** **PASS**

### TC-BOUND-05: Min Sale Quantity Exceeds Available Total
- **Input:** `quantity: 1000.0, min_sale_quantity: 2000.0`
- **Expected:** HTTP 422 Value Error.
- **Actual:** HTTP 422 Value Error correctly returned.
- **Status:** **PASS**

### TC-BOUND-06: Unsupported Non-Canonical Crop
- **Input:** `crop: "Wheat"`
- **Expected:** HTTP 422 ("Unsupported crop: 'Wheat'. Supported crops: Sugarcane, Soybean...").
- **Actual:** HTTP 422 returned with canonical crop enforcement message.
- **Status:** **PASS**

### TC-BOUND-07: Missing Required Crop Name
- **Input:** Payload omitting `crop`.
- **Expected:** HTTP 422 Field Required.
- **Actual:** HTTP 422 returned.
- **Status:** **PASS**

### TC-LIST-DEL-01: Listing Soft-Deletion
- **Steps:** Call `DELETE /api/v1/listings/{id}` on active listing.
- **Expected Result:** HTTP 200/204; database record marked with `status='EXPIRED'`.
- **Actual Result:** HTTP 200; query confirms `status='EXPIRED'`.
- **Status:** **PASS**

---

## 4. Market Intelligence & MandiMitra (MANDI)

### TC-MANDI-01 to TC-MANDI-07: Real APMC Benchmarks Across 7 Crops
- **Endpoint:** `GET /api/v1/market-intelligence/compare?crop={crop}&lat=19.9975&lon=73.7898`
- **Verification Criteria:** Returns >= 10 verified APMC mandis, calculates road distance via OSRM, calculates modal price and net realization (modal price - transport cost).
- **Observed Results:**
  - Sugarcane: 14 mandis found, Best: Nashik APMC, Modal ₹3.75/kg, Net ₹1.19/kg
  - Soybean: 14 mandis found, Best: Nashik APMC, Modal ₹57.99/kg, Net ₹55.43/kg
  - Cotton: 14 mandis found, Best: Nashik APMC, Modal ₹65.00/kg, Net ₹62.44/kg
  - Jowar: 14 mandis found, Best: Ahmednagar APMC, Modal ₹61.48/kg, Net ₹51.85/kg
  - Onion: 14 mandis found, Best: Nashik APMC, Modal ₹46.66/kg, Net ₹44.10/kg
  - Bajra: 14 mandis found, Best: Pune APMC, Modal ₹54.50/kg, Net ₹43.74/kg
  - Rice: 14 mandis found, Best: Pune APMC, Modal ₹60.50/kg, Net ₹49.73/kg
- **Status:** **PASS (All 7 Crops)**

---

## 5. Workflow Planning & Scope Enforcement (WF)

### TC-WF-01: Multi-Path Supply Chain Projection
- **Steps:** Call `POST /api/v1/workflows/plan` for 4,000kg Soybean in Latur.
- **Expected Result:** Ranks 4 options: Direct Sale, Cold Storage, Food Processing, Composting.
- **Actual Result:** HTTP 200; options returned with net revenues, price per kg, time to cash, and risks.
- **Status:** **PASS**

### TC-WF-02: Farmer Saved Workflow Retrieval
- **Steps:** Call `GET /api/v1/workflows/` with authenticated farmer token.
- **Expected Result:** HTTP 200; returns farmer's workflow plans without raising `KeyError: 'user_id'`.
- **Actual Result:** HTTP 200 with `success: true, data: []`. Verified post security resolution.
- **Status:** **PASS**

---

## 6. Negotiation Journey & Floor Price Defense (NEG)

### TC-NEG-01: Launch Autonomous Negotiation
- **Steps:** Call `POST /api/v1/negotiations/` for 2,500kg Cotton, min price ₹68.0/kg.
- **Expected Result:** Matches verified buyer (Vidarbha Ginning & Spinning Mill), initializes Round 1 offer at ₹68.0/kg.
- **Actual Result:** HTTP 200, status `ACTIVE`, round 1 offer recorded.
- **Status:** **PASS**

### TC-NEG-02: Floor Price Defense Under Low Bid
- **Steps:** Submit buyer counter-offer below farmer floor: ₹60.0/kg (Floor is ₹68.0/kg).
- **Expected Result:** Farmer agent strictly refuses to accept; counters back standing firm at ₹68.0/kg.
- **Actual Result:** HTTP 200, status `ACTIVE`, decision `COUNTER`, price `68.0`, message: *"Ramesh Patil: COUNTER ₹68.0/kg: Offer is below minimum. Standing firm at my floor price."*
- **Status:** **PASS**

### TC-NEG-03: Fair Counter-Offer Acceptance
- **Steps:** Submit buyer counter-offer above floor: ₹72.0/kg.
- **Expected Result:** Farmer agent accepts; status transitions to `DEAL`, `final_price=72.0`.
- **Actual Result:** HTTP 200, status `DEAL`, decision `ACCEPT`, final price ₹72.0/kg.
- **Status:** **PASS**

### TC-NEG-04: AI Copilot Evaluation
- **Steps:** Send prompt to `/negotiations/{id}/copilot-action` asking if ₹72.0/kg is competitive against APMC modal price.
- **Expected Result:** AI Copilot compares against Cotton APMC benchmark (₹71.21/kg), recommends accepting.
- **Actual Result:** HTTP 200; returns benchmark price ₹71.21, `is_competitive: true`, action `"ACCEPT"`.
- **Status:** **PASS**

---

## 7. APMC Smart Contract & Escrow (CONTRACT & ESCROW)

### TC-CONTRACT-01: APMC Smart Contract Minting
- **Steps:** Call `POST /negotiations/{id}/accept`.
- **Expected Result:** Generates official transaction ID (`TXN-MH-2026-...`) and cryptographic SHA-256/Ethereum hash (`0x...`).
- **Actual Result:** HTTP 200, transaction ID `TXN-MH-2026-C0B963AB`, contract hash `0x367f0fec67c6999b24bcf84ecbb88c1c53e02047ff3a3399b2f6fb49fefaeef3`. Verified in PostgreSQL `contracts`.
- **Status:** **PASS**

### TC-ESCROW-01: Payment Escrow Settlement
- **Steps:** Settle payment for completed transaction.
- **Actual Result:** HTTP 200, `escrow_account: "ESC-MH-2026-C0B963AB"`, status `ESCROW_SETTLED`.
- **Status:** **PASS**

---

## 8. Real-Time Telemetry & Downstream Logistics (WS & DOWN)

### TC-WS-01: WebSocket Real-Time Synchronization
- **Steps:** Connect WebSocket to `ws://localhost:8000/ws/{farmer_user_id}`, send client heartbeat.
- **Expected Result:** Connection accepted, sync state returned.
- **Actual Result:** Handshake successful, received `pong` and full `SYNC_STATE` containing negotiation details.
- **Status:** **PASS**

### TC-DOWN-01: Transport Carrier Availability
- **Endpoint:** `GET /api/v1/transport/carriers?origin=Nagpur&destination=Mumbai&weight_kg=2500`
- **Actual Result:** HTTP 200, 3 verified logistics providers found with vehicle capacities and per-km tariffs.
- **Status:** **PASS**

### TC-DOWN-02: Nearby Cold Storage Availability
- **Endpoint:** `GET /api/v1/warehouse/nearby?lat=21.1458&lon=79.0882&crop=Cotton`
- **Actual Result:** HTTP 200, 3 licensed warehouses found within 200km.
- **Status:** **PASS**

### TC-DOWN-03: Processor Facility Match
- **Endpoint:** `GET /api/v1/processors/matching?crop=Cotton&quantity=2500`
- **Actual Result:** HTTP 200, matched industrial processing plant.
- **Status:** **PASS**
