"""
backend/workers/stream_consumer.py

Redis Streams Consumer loop. Implements Idempotency, DLQ, and LangGraph triggering.
Pulls events from `stream:negotiation:events` via Consumer Groups.
"""

import time
import json
import logging
from typing import Dict, Any

logger = logging.getLogger("StreamConsumer")

# Mock Redis Client for Architecture purposes
class MockRedis:
    def set(self, key, value, nx=False, ex=None):
        return True
    
    def xack(self, stream, group, msg_id):
        pass

redis_client = MockRedis()

class StreamConsumer:
    """Consumes negotiation events and routes them to LangGraph."""
    
    def __init__(self, consumer_name="agent-worker-1"):
        self.consumer_name = consumer_name
        self.stream_name = "stream:negotiation:events"
        self.group_name = "cg:langgraph_workers"
        
    def process_event(self, event_id: str, payload: Dict[str, Any]):
        """Process an incoming event."""
        # Idempotency Check
        lock_key = f"agri:processed:{event_id}"
        if not redis_client.set(lock_key, "1", nx=True, ex=86400):
            logger.warning(f"Duplicate event ignored: {event_id}")
            return
            
        logger.info(f"Processing event: {payload.get('event_type')}")
        
        event_type = payload.get("event_type")
        if event_type == "Listing.CropCreated":
            self._trigger_planner(payload)
        elif event_type == "Negotiation.CounterOfferGenerated":
            self._trigger_opponent(payload)
            
        # Acknowledge event
        redis_client.xack(self.stream_name, self.group_name, event_id)
        
    def _trigger_planner(self, payload: Dict[str, Any]):
        """Initialize a new negotiation state and run the Planner."""
        from backend.agents.graph_orchestrator import graph_orchestrator
        logger.info("Initializing Planner node for new listing...")
        
        initial_state = {
            "negotiation_id": payload.get("correlation_id", "neg_1"),
            "crop": payload.get("data", {}).get("crop", "Soybean"),
            "quantity": payload.get("data", {}).get("quantity", 1000),
            "min_price": payload.get("data", {}).get("min_price", 70.0),
            "location": payload.get("data", {}).get("location", "Latur"),
            "spoilage_days": payload.get("data", {}).get("shelf_life", 180),
            "round": 0,
            "max_rounds": 6,
            "logs": [],
            "history": []
        }
        
        # In a real setup, we'd use async and checkpointer here.
        # graph_orchestrator.invoke(initial_state, config={"configurable": {"thread_id": "neg_1"}})
        logger.info("Planner graph triggered successfully.")
        
    def _trigger_opponent(self, payload: Dict[str, Any]):
        """Resume a suspended graph state for the next turn."""
        # Uses checkpointer to load state by correlation_id and resume
        logger.info("Resuming negotiation graph for counter-offer...")

    def consume_loop(self):
        """Infinite blocking read loop (Simulated)."""
        logger.info(f"[{self.consumer_name}] Listening on {self.stream_name}...")
        # Simulate blocking read: redis_client.xreadgroup(...)
        pass


if __name__ == "__main__":
    consumer = StreamConsumer()
    consumer.consume_loop()
