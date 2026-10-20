import logging
from typing import Dict, Set, Optional
from fastapi import WebSocket

logger = logging.getLogger("backend.websocket.agent_updates")


class AgentUpdateHub:
    """
    Thread-safe & session-isolated WebSocket hub for real-time negotiation event streaming.
    Supports scoping broadcasts by negotiation_id to maintain client session isolation.
    """

    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self.subscriptions: Dict[str, Set[WebSocket]] = {}
        self.client_negotiations: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket, negotiation_id: Optional[str] = None):
        await websocket.accept()
        self.connections.add(websocket)
        self.client_negotiations[websocket] = set()
        if negotiation_id:
            self.subscribe(websocket, negotiation_id)

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)
        
        # Clean up subscriptions
        subscribed_negs = self.client_negotiations.pop(websocket, set())
        for neg_id in subscribed_negs:
            if neg_id in self.subscriptions:
                self.subscriptions[neg_id].discard(websocket)
                if not self.subscriptions[neg_id]:
                    del self.subscriptions[neg_id]

    def subscribe(self, websocket: WebSocket, negotiation_id: str):
        if not negotiation_id:
            return
        if negotiation_id not in self.subscriptions:
            self.subscriptions[negotiation_id] = set()
        self.subscriptions[negotiation_id].add(websocket)
        if websocket in self.client_negotiations:
            self.client_negotiations[websocket].add(negotiation_id)

    def unsubscribe(self, websocket: WebSocket, negotiation_id: str):
        if negotiation_id in self.subscriptions:
            self.subscriptions[negotiation_id].discard(websocket)
            if not self.subscriptions[negotiation_id]:
                del self.subscriptions[negotiation_id]
        if websocket in self.client_negotiations:
            self.client_negotiations[websocket].discard(negotiation_id)

    async def broadcast(self, payload: dict, strict_isolation: bool = False):
        neg_id = payload.get("negotiation_id")
        
        # Determine target recipients: strictly isolated by negotiation_id when specific subscribers exist.
        # Wildcard "*" subscribers (e.g. admin dashboards or monitoring listeners) receive all events.
        wildcard_subs = set(self.subscriptions.get("*", set()))
        if neg_id:
            specific_subs = set(self.subscriptions.get(neg_id, set()))
            if specific_subs or wildcard_subs:
                recipients = specific_subs | wildcard_subs
            elif strict_isolation:
                recipients = set()
            else:
                recipients = set(self.connections)
        else:
            recipients = set(self.connections)

        disconnected = []
        for connection in recipients:
            try:
                await connection.send_json(payload)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            await self.disconnect(connection)

    async def broadcast_threadsafe(self, payload: dict, loop=None):
        """Thread-safe way to broadcast from a worker thread or background task."""
        import asyncio
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return

        asyncio.run_coroutine_threadsafe(self.broadcast(payload), loop)


agent_update_hub = AgentUpdateHub()
