# FarmGenAI: Farmer-Side UI Control Inventory Matrix

**Audit Target:** AgriNegotiator Farmer Frontend  
**Auditor:** Senior QA Lead (Production-Readiness Audit)  
**Environment:** Vite 5.4.21 + React 18 / Node.js on Windows (Port 8080)  
**Backend:** FastAPI 0.110.0 + PostgreSQL 16 (Docker port 5433) + Redis 7  
**Canonical Crops Audited:** Sugarcane, Soybean, Cotton, Jowar, Onion, Bajra, Rice  
**Date of Audit:** October 2026  

---

## 1. Executive Summary & Page Inventory

The Farmer interface is primarily centralized within the authenticated dashboard (`/dashboard/farmer`), supported by dedicated negotiation rooms (`/negotiations/:id` and `/farmer/negotiations/:id`), transaction tracking (`/transactions`), supply chain deal tracker (`/supply-chain/:id` and `/deal/:id/track`), analytics (`/analytics`), user profile (`/profile`), and authentication entry points (`/login`, `/register`).

| Page / Route | Primary Role & Accessibility | Rendering Mode | Layout & Responsiveness |
|---|---|---|---|
| `/login` | Public Auth Entry | Client Component | Form centered card; responsive flex layout |
| `/register` | Public Account Registration | Client Component | Responsive grid; role selector tab |
| `/dashboard/farmer` | Central Farmer Command Center | Protected (Farmer Role) | 3-column / 2-column responsive layout, live WS feed |
| `/negotiations/:id` | Real-Time Multi-Agent Negotiation Room | Protected (Farmer/Buyer) | Live chat, offer cards, Copilot drawer, APMC modal |
| `/transactions` | APMC Contract & Escrow History | Protected | Table & card view, hash verification |
| `/supply-chain/:id` | Full Lifecycle Logistics & Deal Tracker | Protected | Stage progression timeline, carrier tracking |
| `/analytics` | Market & Platform GMV Analytics | Protected | Recharts SVG charts, price trend filters |
| `/profile` | Farmer KYC, Trust Score, Location | Protected | Form inputs, verification badge |

---

## 2. Complete Farmer UI Control Coverage Matrix

Every interactive control discovered across the farmer-facing routes was inspected, clicked, and tested against backend and database side effects.

| Page / Route | Control Name & Identifier | Type | Intended Behavior | Actual Behavior | Backend Dependency | Persistence | Result | Evidence Ref |
|---|---|---|---|---|---|---|---|---|
| `/login` | Email Input `#email` | Input (email) | User enters farmer email | Accepts input, client-side validates email format | None (Client state) | None | **PASS** | `AUTH-01` |
| `/login` | Password Input `#password` | Input (password) | User enters password | Obscures characters, accepts input | None (Client state) | None | **PASS** | `AUTH-01` |
| `/login` | Submit Button `#login-btn` | Button | Authenticates user and issues JWT | Dispatches `POST /api/v1/auth/login`, redirects to `/dashboard/farmer` | `POST /api/v1/auth/login` | LocalStorage JWT | **PASS** | `AUTH-01` |
| `/register` | Full Name `#name` | Input (text) | Captures farmer legal name | Stores name in state | None | None | **PASS** | `AUTH-03` |
| `/register` | Role Selector `#role` | Select / Tab | Selects "Farmer" role | Toggles active role to "farmer" | None | None | **PASS** | `AUTH-03` |
| `/register` | Register Button `#reg-btn` | Button | Creates account in PostgreSQL | Sends `POST /api/v1/auth/register`, returns 400 on duplicate | `POST /api/v1/auth/register` | PostgreSQL `v1_users` | **PASS** | `AUTH-03` |
| `/dashboard/farmer` | Trust Score Badge | Status Display | Shows dynamic farmer trust score | Rendered dynamically from `GET /api/v1/dashboards/farmer` (`4.9 / 5.0`) | `GET /api/v1/dashboards/farmer` | PostgreSQL `users.trust_score` | **PASS** | Verified post D-001 fix |
| `/dashboard/farmer` | Live Market Indicator | Status Dot | Shows WebSocket sync status | Green pulsing dot when WS connected, red when offline | `WS /ws/{user_id}` | Active socket state | **PASS** | `WS-01` |
| `/dashboard/farmer` | Stat Card 1: Active Listings | Metric Card | Displays count of farmer's active listings | Dynamically shows count of records from `/listings/me` | `GET /api/v1/listings/me` | PostgreSQL `produce` | **PASS** | `LIST-01` |
| `/dashboard/farmer` | Stat Card 2: Market Trend | Metric Card | Displays Bullish/Bearish/Stable trend | Updates with modal price delta from MandiMitra API | `GET /market-intelligence/compare` | Dynamic APMC data | **PASS** | `MANDI-01` |
| `/dashboard/farmer` | Stat Card 3: Deals Closed | Metric Card | Shows total finalized deals and gross earnings | Displays count of `status='DEAL'` and total revenue in ₹ | `GET /api/v1/dashboards/farmer` | PostgreSQL `negotiations` | **PASS** | Verified post D-002 fix |
| `/dashboard/farmer` | District Dropdown `#district-select` | Select (36 districts) | Selects Maharashtra APMC district | Updates coordinates (e.g. Nashik, Nagpur, Kolhapur) | None (Client constant) | Component state | **PASS** | UI check |
| `/dashboard/farmer` | Crop Dropdown `#crop-select` | Select (7 crops) | Selects one of 7 canonical crops | Updates `selectedCrop` state | Canonical crop dictionary | Component state | **PASS** | 7 crops verified |
| `/dashboard/farmer` | "Find Mandis" Button `#find-mandis` | Action Button | Fetches nearby APMCs within 500km with transport deductions | Dispatches `GET /market-intelligence/compare`, populates Mandi comparison table | `GET /market-intelligence/compare` | None (Live query) | **PASS** | `MANDI-01-07` |
| `/dashboard/farmer` | Mandi Sort Controls | Table Header Tabs | Sort by Distance, Modal Price, or Net Realization | Reorders table rows dynamically based on metric | Client JS sorting | Component state | **PASS** | Table sort verified |
| `/dashboard/farmer` | "New Listing" Button `#new-listing-btn` | Modal Trigger | Opens CreateListingForm modal | Renders modal overlay with all crop parameter inputs | None | Component state | **PASS** | `LIST-MODAL` |
| `CreateListingForm` | Crop Select `#listing-crop` | Select | Chooses canonical crop | Restricts to 7 crops; rejects non-canonical crops | Pydantic schema validation | Produce table | **PASS** | `CROP-VAL` |
| `CreateListingForm` | Quantity Input `#listing-qty` | Input (number) | Sets sale lot quantity in kg | Accepts positive floats; rejects <= 0 | Backend validation | Produce table | **PASS** | `BOUND-01` |
| `CreateListingForm` | Min Price Input `#listing-min-price` | Input (number) | Sets reserve floor price in ₹/kg | Accepts positive floats; rejects negative or > expected | Backend validation | Produce table | **PASS** | `BOUND-02` |
| `CreateListingForm` | Expected Price Input `#listing-exp-price`| Input (number) | Sets target initial price in ₹/kg | Must be >= min price; validated by Zod & Pydantic | Backend validation | Produce table | **PASS** | `BOUND-03` |
| `CreateListingForm` | Quality Grade `#listing-grade` | Select | Sets quality grade (FAQ, Grade A, etc.) | Stores grade string in metadata | Schema validation | Produce table | **PASS** | `LIST-01` |
| `CreateListingForm` | Shelf Life Days `#listing-shelf-life` | Input (number) | Sets perishable spoilage window in days | Determines storage/processing urgency in LangGraph | Schema validation | Produce table | **PASS** | `LIST-01` |
| `CreateListingForm` | Location Input `#listing-location` | Input (text) | Sets origin district/mandi | Used for OSRM routing and transport quote calculation | Geospatial resolver | Produce table | **PASS** | `LIST-01` |
| `CreateListingForm` | Submit Listing `#submit-listing-btn` | Button | Creates listing in backend & DB | Sends `POST /api/v1/listings/`, refreshes listing table | `POST /api/v1/listings/` | PostgreSQL `produce` | **PASS** | 7 crops verified |
| `/dashboard/farmer` | Listing Edit Icon `#edit-listing-btn` | Icon Button | Opens EditListingModal | Loads existing values, sends `PUT /listings/{id}` | `PUT /api/v1/listings/{id}` | PostgreSQL `produce` | **PASS** | `LIST-EDIT` |
| `/dashboard/farmer` | Listing Delete Icon `#delete-listing-btn` | Icon Button | Soft deletes listing | Confirms via dialog, sends `DELETE /listings/{id}` (status=EXPIRED) | `DELETE /api/v1/listings/{id}`| PostgreSQL `produce` | **PASS** | `LIST-DEL` |
| `/dashboard/farmer` | "AI Match & Negotiate" `#ai-negotiate-btn`| Action Button | Launches autonomous negotiation room | Sends `POST /api/v1/negotiations/`, matches top buyers, redirects to room | `POST /api/v1/negotiations/` | PostgreSQL `negotiations` | **PASS** | `NEG-01` |
| `/dashboard/farmer` | Negotiations Table: "View Room" | Link | Navigates to existing room | Navigates to `/negotiations/{id}` with full round history | `GET /api/v1/negotiations/{id}` | Session retrieval | **PASS** | UI navigation |
| `/dashboard/farmer` | Negotiations Table: "Contract" | Action Button | Opens APMC Smart Contract Modal | Displays verified transaction ID, cryptographic hash (0x...) | None (Uses loaded row) | None | **PASS** | `CONTRACT-01` |
| `/dashboard/farmer` | Live Updates Feed | Sidebar Container | Real-time stream of APMC insights and deals | Displays live WS updates, MandiMitra benchmark, and recent deals | `WS /ws/{id}` + `/dashboards/`| None | **PASS** | Verified post D-003 fix |
| `/negotiations/:id` | Counter Price Input `#counter-price` | Input (number) | Farmer or buyer inputs counter price | Accepts numeric price in ₹/kg | Client state | None | **PASS** | `NEG-COUNTER` |
| `/negotiations/:id` | Counter Message `#counter-message` | Input (text) | Enters tactical counter text | Serializes in offer payload | Client state | None | **PASS** | `NEG-COUNTER` |
| `/negotiations/:id` | "Send Counter" Button `#send-counter` | Action Button | Dispatches counter-offer to agent | Sends `POST /negotiations/{id}/counter`, agent responds | `POST /negotiations/{id}/counter`| PostgreSQL `offers` | **PASS** | `NEG-COUNTER` |
| `/negotiations/:id` | "Ask Copilot" Input `#copilot-input` | Input (text) | Queries AI Copilot on deal fairness | Sends natural language prompt to Gemini/Qwen RAG | `POST /copilot-action` | ChromaDB + LLM | **PASS** | `COPILOT-01` |
| `/negotiations/:id` | "Accept Deal" Button `#accept-deal` | Action Button | Finalizes deal and generates APMC contract | Dispatches `POST /negotiations/{id}/accept`, mints smart contract | `POST /negotiations/{id}/accept`| PostgreSQL `contracts` | **PASS** | `APMC-ACCEPT` |
| `/negotiations/:id` | "Settle Escrow" Button `#settle-escrow` | Action Button | Dispatches payment to farmer | Calls `POST /negotiations/{id}/settle`, sets `ESCROW_SETTLED` | `POST /settle` | Escrow state | **PASS** | `ESCROW-01` |

---

## 3. Responsive & Viewport Validation

| Viewport Resolution | Breakpoint | Layout Behavior Observed | Clipping / Overlap Defect? | Verdict |
|---|---|---|---|---|
| 1920 × 1080 | Desktop Large | 3-column layout; full table visibility, sidebar fixed height | None | **PASS** |
| 1366 × 768 | Desktop Laptop | 3-column layout; responsive grids stack neatly | None | **PASS** |
| 768 × 1024 | Tablet Portrait | Sidebar moves beneath listing table; Mandi table horizontally scrolls | None | **PASS** |
| 375 × 667 | Mobile (iPhone SE) | Single column vertical stack; modal full-screen overlay; touch targets >= 44px | None | **PASS** |
