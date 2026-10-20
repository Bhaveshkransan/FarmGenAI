# FarmGenAI / AgriNegotiator — Full Architecture Map

| Component | Purpose | Input | Output | Dependencies | Agent / Node | Failure Mode | Verification Status |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **Frontend UI** | Farmer & Buyer SPA dashboard | User actions | API calls, WS | Vite, React, Tailwind | NegotiationRoom, FarmerDashboard | Reconnects on disconnect | VERIFIED |
| **LangGraph Orchestrator** | 13-node compiled state machine | NegotiationState | Final deal state | langgraph, pydantic | graph_orchestrator.ainvoke | Escalates to storage/processor | VERIFIED |
| **Farmer Agent** | Economic agent protecting floor | Listing & market state | Counteroffer / Accept / Reject | LLM / Rule fallback | farmer_node | Floor protected by code | VERIFIED |
| **Buyer Engine** | Parallel multi-buyer evaluation | Active buyer pool | Ranked buyer offers | asyncio.gather | buyer_node, rank_responses_node | Expands candidate pool | VERIFIED |
| **Transport Agent** | Fleet matching & dispatch quote | Route & tonnage | Confirmed transport plan | OSRM, vehicle fleet | transport_agent | Floor revalidation on surge | VERIFIED |
| **Storage Agent** | Warehouse capacity & cold chain | Holding duration | Storage allocation | Warehouse db | escalated_storage_node | Falls back to processor | VERIFIED |
| **Processor Agent** | Industrial salvage bidding | Perishing lot context | Salvage purchase bid | Processor db | escalated_processing_node | Prevents item assignment crash | VERIFIED |
| **RAG Engine** | Agri knowledge retrieval | Query string | Context docs | ChromaDB, all-MiniLM | rag_service | Fallback to canonical MSP | VERIFIED |
| **ML Pricing Engine** | Optimal procurement forecasting | Market & distance features | Predicted optimal price | XGBoost | buyer_pricing_service | Bounded by hard MSP limits | VERIFIED |
| **PostgreSQL DB** | Authoritative source of truth | SQL queries | Persisted entities | PostgreSQL 16 | SQLAlchemy / Database | Rollback on transaction error | VERIFIED |
| **Redis Broker** | Task queue & cache | Celery / Worker tasks | Dispatched jobs | Redis 7 | agent_worker | Re-queues unacknowledged jobs | VERIFIED |
