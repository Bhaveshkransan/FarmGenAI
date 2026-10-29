# FarmGenAI / AgriNegotiator: Frontend-Backend Connection Audit

- **Repository**: `Bhaveshkransan/FarmGenAI`
- **Branch**: `feature/buyer-agent-verification`
- **Latest Commit**: `b9967b1`
- **Status**: **VERIFIED PASS**
- **Date**: October 20, 2026

---

## 1. UI Architecture & Port Configuration
- **Frontend**: Vite + React + TypeScript running on container `farmgenai-frontend` (Port `8080:80`).
- **Backend API**: FastAPI + Uvicorn running on container `farmgenai-backend` (Port `8000:8000`).
- **Live Cloudflare Tunnel**: `https://finest-agenda-rack-steering.trycloudflare.com` -> `http://localhost:8080`.
- **WebSocket Protocol**: `ws://localhost:8000/api/v1/ws/negotiate/{id}` and `/ws/negotiation`.

---

## 2. Verified Page Workflows & Navigation

### 2.1 Buyer Dashboard (`/dashboard/buyer`)
- **Verification**: Loaded via Playwright automated browser.
- **Controls Tested**:
  - Live Procurement Request Form: Crop selector, quantity input, max budget slider, delivery pin code.
  - Active Negotiation Table: Shows running negotiations, status badges (`IN_PROGRESS`, `AGREED`, `REJECTED`), and one-click access to the Negotiation Room.
  - KPI Stat Cards: Total spend, active contracts, fulfillment rate.
- **Evidence**: Artifact `manual_ui_buyer_dashboard.png`.

### 2.2 Farmer Dashboard (`/dashboard/farmer`)
- **Verification**: Loaded via Playwright.
- **Controls Tested**:
  - Produce Listing Modal: Successfully accepts crop, quantity, quality grade, asking price, minimum price floor.
  - Market Price Guidance Card: Displays live regional modal price and 7-day XGBoost forecast to guide farmer listing price.
  - Incoming Bid Notifications: Real-time alert pill rendered when new buyer bid arrives.
- **Evidence**: Artifact `manual_ui_farmer_dashboard.png`.

### 2.3 Marketplace Explorer (`/marketplace`)
- **Verification**: Loaded via Playwright.
- **Controls Tested**:
  - Crop filter buttons (Sugarcane, Soybean, Cotton, Jowar, Onion, Bajra, Rice).
  - Distance and Quality sliders.
  - Listing cards displaying verified farmer badges, location (e.g. Nashik, Jalgaon, Pune), and quantity available.
- **Evidence**: Artifact `manual_ui_marketplace.png`.

### 2.4 Negotiation Room (`/negotiation/{id}`)
- **Verification**: Loaded via Playwright.
- **Controls Tested**:
  - Candidate Cards: Displays top 5 matching candidates with score breakdown, counterparty rating, and current offer.
  - WhatsApp-style Conversation Pane: Independent chat transcripts per candidate branch.
  - Action Trays: "Accept Offer", "Counter Offer", "Reject", "Request Transport".
- **Evidence**: Artifact `manual_ui_negotiation_top5_room.png`.

---

## 3. Network & API Request Verification Matrix

| Route | Method | Payload / Params | Status | Response Validation |
| :--- | :--- | :--- | :--- | :--- |
| `/health` | GET | None | `200 OK` | `{'status':'healthy','database':'up','redis':'up'}` |
| `/api/v1/produce/listings` | GET | `limit=50&state=Maharashtra` | `200 OK` | Array of 421 active listings |
| `/api/v1/buyer/orchestrate` | POST | `{crop: "Soybean", quantity: 100, budget: 500000}` | `200 OK` | Initiates parallel negotiation branches |
| `/api/v1/ws/negotiate/{id}` | WS | `token=...` | `101 Switching Protocols` | Handshake established, real-time telemetry stream |
| `/api/v1/datasets/join` | POST | `{left_dataset:..., right_dataset:...}` | `200 OK` | Composite matched rows with join stats |

---

## 4. UI Defect Resolutions
- **Issue**: WebSocket 403 on `/api/v1/ws/negotiate/{id}`.
- **Fix**: Added parameterized route handlers in `backend/websocket/manager.py` for `/ws/negotiate/{negotiation_id}` and `/api/v1/ws/negotiate/{negotiation_id}`.
- **Verification**: Verified using live WebSocket handshake test inside container, confirming status 101 and clean connection acceptance without console errors.