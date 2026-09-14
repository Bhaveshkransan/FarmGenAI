from backend.repositories.user_repository import UserRepository
import asyncio
import json
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.staticfiles import StaticFiles
import os
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.services.security import get_current_user
from backend.middleware.rate_limiter import RateLimitMiddleware
from backend.middleware.exception_handler import global_exception_handler
from backend.core.exceptions import AppException, app_exception_handler

# ── Core routes (existing) ──
from .routes.buyer_routes import router as buyer_router
from .routes.farmer_routes import router as farmer_router
from .routes.history_routes import router as history_router
from .routes.warehouse_routes import router as warehouse_router
from .routes.role_offer_routes import router as role_offer_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.p2p_routes import router as p2p_router
from .routes.agents_routes import router as agents_router
from .routes.negotiation_routes import router as negotiation_router

# ── New routes (session 2) ──
from .routes.analytics_routes import router as analytics_router
from .routes.trust_routes import router as trust_router
from .routes.notification_routes import router as notification_router
from .routes.recommendation_routes import router as recommendation_router
from .routes.admin_routes import router as admin_router
from .routes.crop_listing_routes import router as crop_listing_router
from .routes.buyer_requirement_routes import router as buyer_req_router

# ── New routes (session 3 – full FR coverage) ──
from .routes.profile_routes import router as profile_router
from .routes.matching_routes import router as matching_router
from .routes.integrations_routes import router as integrations_router
from .routes.workflow_routes import router as workflow_router
from .routes.transport_routes import router as transport_router
from .routes.processor_routes import router as processor_router
from .routes.dashboard_routes import router as dashboard_router
from .websocket.agent_updates import agent_update_hub
from database.db import Database, init_db, engine
from sqlalchemy import text
from nodes.node_hub import hub, bootstrap_peer_network
from nodes.farmer_node import FarmerNode

import redis.asyncio as aioredis
from config.settings import REDIS_URL

from backend.core.redis import redis_manager

logger = logging.getLogger("backend.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("dYs? API GLOBAL STARTUP INITIATED...")
    await init_db()
    
    from backend.services.negotiation_service import service as negotiation_service
    await negotiation_service.ensure_default_buyers()
    await negotiation_service.ensure_default_farmers_and_produce()
    
    await bootstrap_peer_network()
    
    # Pre-warm RAG embeddings model and vector stores to eliminate runtime cold starts
    try:
        from backend.services.rag_service import rag_service
        logger.info("RAG Service pre-warmed successfully.")
    except Exception as e:
        logger.warning(f"RAG Service pre-warm warning: {e}")
    
    await redis_manager.connect()
    if redis_manager.client:
        from backend.websocket.manager import redis_pubsub_listener
        asyncio.create_task(redis_pubsub_listener(redis_manager.client))
    
    yield
    
    await redis_manager.disconnect()

app = FastAPI(
    title="AgriNegotiator API",
    lifespan=lifespan,
    version="2.1.0",
    description="AI-powered agricultural negotiation platform with LangGraph multi-agent system.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Exception Handlers ──
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# ── Rate Limiting ──
app.add_middleware(RateLimitMiddleware, max_requests=120, window_seconds=60)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded crop images and documents
os.makedirs("./node_storage/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="./node_storage"), name="static")

# ── API v1 Routers ──────────────────────────────────────
# P2P
app.include_router(p2p_router, prefix="/api", tags=["P2P Network"])

# Auth
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])

# Farmers & Buyers
app.include_router(farmer_router, prefix="/api/v1/farmers", tags=["Farmers"])
app.include_router(buyer_router, prefix="/api/v1/buyers", tags=["Buyers"])

# Crop Listings & Buyer Requirements
app.include_router(crop_listing_router, prefix="/api/v1/listings", tags=["Crop Listings"])
app.include_router(buyer_req_router, prefix="/api/v1/requirements", tags=["Buyer Requirements"])

# Negotiation
app.include_router(negotiation_router, prefix="/api/v1/negotiations", tags=["Negotiations"])

# Supply Chain
app.include_router(warehouse_router, prefix="/api/v1/warehouse", tags=["Warehouse"])
app.include_router(role_offer_router, prefix="/api/v1/role-offers", tags=["Role Offers"])

# AI Agents
# Legacy agents_router removed to prevent conflict with v1/agents.py

# Analytics & Intelligence
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(recommendation_router, prefix="/api/v1/recommendations", tags=["Recommendations"])

# Trust
app.include_router(trust_router, prefix="/api/v1/trust", tags=["Trust"])

# Notifications
app.include_router(notification_router, prefix="/api/v1/notifications", tags=["Notifications"])

# History
app.include_router(history_router, prefix="/api/v1/history", tags=["History"])

# Admin
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin (legacy)"])

# Profiles
app.include_router(profile_router, prefix="/api/v1/profiles", tags=["Profiles"])

# Matching
app.include_router(matching_router, prefix="/api/v1/matching", tags=["Matching"])

# Workflows
app.include_router(workflow_router, prefix="/api/v1/workflows", tags=["Workflow Planning"])

# Transport
app.include_router(transport_router, prefix="/api/v1/transport", tags=["Transport"])

# Processors
app.include_router(processor_router, prefix="/api/v1/processors", tags=["Processor"])

# Dashboards
app.include_router(dashboard_router, prefix="/api/v1/dashboards", tags=["Dashboard"])

# Integrations (Object Storage, Mandi feeds)
app.include_router(integrations_router, prefix="/api/v1/integrations", tags=["Integrations"])

# Agents Telemetry
app.include_router(agents_router, prefix="/api/v1/agents", tags=["Agents"])

# Health check
@app.get("/health", tags=["System"])
async def health_check():
    db_ok = True
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    redis_ok = True
    if redis_manager.client:
        try:
            await redis_manager.client.ping()
        except Exception:
            redis_ok = False
    else:
        redis_ok = False

    status = "healthy" if (db_ok and redis_ok) else "degraded"
    return {
        "status": status,
        "database": "up" if db_ok else "down",
        "redis": "up" if redis_ok else "down"
    }


# ── WebSockets ──────────────────────────────────────
from backend.websocket.manager import router as websocket_router
app.include_router(websocket_router, tags=["WebSockets"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


