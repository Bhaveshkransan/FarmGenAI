import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.websocket.agent_updates import agent_update_hub

logger = logging.getLogger("backend.websocket.manager")
router = APIRouter()

async def redis_pubsub_listener(redis_client):
    if not redis_client:
        return
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("agri:telemetry:updates")
    logger.info("📡 Redis Pub/Sub listener subscribed to 'agri:telemetry:updates'.")
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                try:
                    data = json.loads(message["data"])
                    neg_id = data["negotiation_id"]
                    event = data["event"]
                    event_type = event.get("type")
                    event_data = event.get("data", {})

                    if event_type == "scenario_ready":
                        await agent_update_hub.broadcast({
                            "event": "SCENARIO_READY",
                            "negotiation_id": neg_id,
                            "farmer": event_data.get("farmer"),
                            "crop": event_data.get("crop"),
                            "status": event_data.get("status")
                        })
                    elif event_type == "counter_offer":
                        agent_name = str(event_data.get("agent", "")).lower()
                        agent_type = "farmer" if "farmer" in agent_name else "buyer"
                        await agent_update_hub.broadcast({
                            "event": "NEGOTIATION_LOG",
                            "negotiation_id": neg_id,
                            "message": event_data.get("message") or f"{event_data.get('agent')}: Proposing ₹{event_data.get('price')}/kg.",
                            "agent_type": agent_type,
                            "agent_name": str(event_data.get("agent", "")),
                            "offer": event_data.get("price"),
                        })
                    elif event_type == "agreement":
                        await agent_update_hub.broadcast({
                            "event": "NEGOTIATION_LOG",
                            "negotiation_id": neg_id,
                            "message": f"Deal reached at ₹{event_data.get('price')}/kg for {event_data.get('quantity')}kg",
                            "agent_type": "system",
                            "offer": event_data.get("price")
                        })
                    elif event_type == "negotiation_finished":
                        await agent_update_hub.broadcast({
                            "event": "NEGOTIATION_FINISHED",
                            "negotiation_id": neg_id,
                            "status": event_data.get("status"),
                            "final_price": event_data.get("final_price"),
                            "summary": event_data.get("summary"),
                            "logs": event_data.get("logs", []),
                            "market_offers": event_data.get("market_offers", []),
                            "selected_buyer": event_data.get("selected_buyer")
                        })
                    elif event_type == "status_update":
                        await agent_update_hub.broadcast({
                            "event": "NEGOTIATION_LOG",
                            "negotiation_id": neg_id,
                            "message": event_data.get("message", ""),
                            "agent_type": "system"
                        })
                except Exception as ex:
                    logger.info(f"Error parsing pubsub message data: {ex}")
            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.info(f"Error in Redis Pub/Sub listener: {e}")

@router.websocket("/ws/negotiation")
async def negotiation_updates(websocket: WebSocket, token: str = None):
    if not token:
        token = websocket.query_params.get("token")
    
    from backend.services.security import verify_token
    from fastapi import WebSocketException, status
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    payload = await verify_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await agent_update_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await agent_update_hub.disconnect(websocket)


@router.websocket("/ws/{token}")
async def negotiation_updates_fallback(websocket: WebSocket, token: str):
    """Fallback route for frontend clients attempting connection with path parameter tokens."""
    await negotiation_updates(websocket, token)
