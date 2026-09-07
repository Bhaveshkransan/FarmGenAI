from negotiation_engine.offer_generator import OfferGenerator
from shared.event_bus import event_bus
import time
from backend.agents.graph_orchestrator import graph_orchestrator

# ------------------------------------------------
# Safe Memory Class
# ------------------------------------------------

class SafeMemory:
    def __init__(self):
        self.price_series = []
        self.offers = []
        self.events = []

    def store_offer(self, agent, offer):
        self.offers.append({"agent": agent, "offer": offer})

    def get_offers(self):
        return self.offers

    def store_event(self, event_type, payload):
        self.events.append({"type": event_type, "payload": payload})

    def get_events(self):
        return self.events

    def add_price(self, agent, price):
        self.price_series.append({"agent": agent, "price": price})

    def get_price_series(self):
        return self.price_series


# ------------------------------------------------
# Negotiation Manager (Full Supply Chain Optimizer)
# ------------------------------------------------

class NegotiationManager:
    def __init__(
        self,
        farmer=None,
        buyers=None,
        warehouse=None,
        compost=None,
        processor=None,
        transporter=None,
        max_rounds=5,
        live_event_callback=None,
        **kwargs
    ):
        self.farmer = farmer
        self.buyers = buyers if isinstance(buyers, list) else []
        self.warehouse = warehouse
        self.compost = compost
        self.processor = processor
        self.transporter = transporter

        self.offer_generator = OfferGenerator()
        self.memory = SafeMemory()
        self.max_rounds = max_rounds
        self.logs = []
        self.live_event_callback = live_event_callback

    def _emit_live(self, event_type, data):
        event_bus.emit(event_type, data)
        if self.live_event_callback:
            try:
                self.live_event_callback({"type": event_type, "data": data})
            except:
                pass

    # ------------------------------------------------
    # Strategic Negotiation Start
    # ------------------------------------------------

    async def start_negotiation(self, market_price: float, quantity: float = 500, **kwargs):
        self.logs.append("🔍 PHASE 1: Multi-Agent Marketplace Scan & Bid Invitation")
        self._emit_live("status_update", {"message": "Farmer calling for strategic bids from all networks via LangGraph..."})
        
        # Prepare inputs for the LangGraph State Machine
        state_buyers = []
        for b in self.buyers:
            state_buyers.append({
                "id": getattr(b, "id", f"buyer_{getattr(b, 'name', 'default').lower()}"),
                "name": b.name,
                "target_price": b.target_price,
                "budget": b.budget,
                "max_quantity": b.max_quantity,
                "location": getattr(b, "location", "Market"),
                "strategy": getattr(b, "strategy", "default")
            })

        initial_state = {
            "crop": self.farmer.crop if hasattr(self.farmer, 'crop') else "Tomato",
            "quantity": float(quantity),
            "min_price": float(self.farmer.min_price) if hasattr(self.farmer, 'min_price') else 18.0,
            "target_price": float(self.farmer.min_price * 1.1) if hasattr(self.farmer, 'min_price') else 20.0,
            "spoilage_days": int(self.farmer.shelf_life) if hasattr(self.farmer, 'shelf_life') else 4,
            "location": self.farmer.location if hasattr(self.farmer, 'location') else "Nashik",
            "market_price": float(market_price),
            "round": 0,
            "max_rounds": self.max_rounds,
            "history": [],
            "buyer_profile": None,
            "logs": [],
            "status": "ACTIVE",
            "proposed_scenario": kwargs.get("scenario", "direct-sale"),
            "next_action": "",
            "deal": None,
            "plan": None,
            "reflection": None,
            "selected_buyer": None,
            "market_offers": [],
            "user_id": kwargs.get("user_id"),
            "latest_farmer_ask": None,
            "latest_buyer_offer": None,
            "buyers_list": state_buyers,
            "farmer_agent_obj": self.farmer,
            "buyer_agent_objs": self.buyers
        }

        # Invoke state graph orchestrator
        final_state = await graph_orchestrator.ainvoke(initial_state, config={"recursion_limit": 50})

        # Merge logs and history events
        self.logs.extend(final_state["logs"])
        
        for h in final_state["history"]:
            self.memory.add_price(h["agent"], h["price"])
            self.memory.store_offer(h["agent"], h)
            self._emit_live("counter_offer", h)

        final_status = final_state["status"]
        deal = final_state.get("deal")
        m_offers = final_state.get("market_offers", [])

        if final_status == "DEAL" and deal:
            deal_data = {
                "buyer_name": deal.get("buyer_name", "Buyer"),
                "price": deal.get("price"),
                "quantity": deal.get("quantity"),
                "transport_partner": self.transporter.name if self.transporter else "Local-Self"
            }
            self._emit_live("agreement", deal_data)
            return {
                "state": "DEAL",
                "summary": f"Deal negotiated successfully via LangGraph with {deal_data['buyer_name']}.",
                "partnerships": [deal_data],
                "deal": deal_data,
                "remaining_quantity": 0.0,
                "logs": self.logs,
                "price_series": self.memory.get_price_series(),
                "next_action": "Logistics Dispatch",
                "market_offers": m_offers
            }
            
        elif final_status in ("ESCALATED_STORAGE", "ESCALATED_PROCESSING", "ESCALATED_COMPOST"):
            esc_deal = deal or {}
            self._emit_live("status_update", {"message": f"Escalated to supply chain: {final_status}"})
            return {
                "state": final_status,
                "summary": f"Negotiation escalated to fallback channel: {final_status}.",
                "deal": esc_deal,
                "logs": self.logs,
                "price_series": self.memory.get_price_series(),
                "next_action": "Trigger Fallback",
                "market_offers": m_offers
            }

        return {
            "state": "FAILED",
            "summary": "Negotiation failed. No deal could be reached with any buyer.",
            "deal": None,
            "logs": self.logs,
            "price_series": self.memory.get_price_series(),
            "next_action": "Retry Match",
            "market_offers": m_offers
        }

    def _handle_escalation(self, market_price, quantity):
        self.logs.append("⚠️ Market saturation detected. Escalating to Supply Chain fallbacks...")
        
        if self.warehouse:
            self.logs.append(f"🏗️ Analyzing Warehouse Storage Strategy at {self.warehouse.name}...")
            response = self.warehouse.respond_to_offer({"quantity": quantity, "type": "STORAGE"})
            if response.get("type") != "REJECT":
                self._emit_live("storage", response)
                return {"state": "ESCALATED_STORAGE", "summary": "Produce moved to cold storage.", "deal": response, "logs": self.logs, "price_series": self.memory.get_price_series()}

        if self.processor:
            self.logs.append(f"⚙️ Analyzing Alternative Value-Added Processing at {self.processor.name}...")
            response = self.processor.respond_to_offer({"price": market_price * 0.8, "quantity": quantity})
            if response.get("type") == "ACCEPT_PROCESSING":
                 self._emit_live("processing", response)
                 return {"state": "ESCALATED_PROCESSING", "summary": "Produce sold to food processor.", "deal": response, "logs": self.logs, "price_series": self.memory.get_price_series()}

        if self.compost:
            self.logs.append("♻️ Zero-Waste Fallback: Engaging Ecological Recovery Agents...")
            response = self.compost.respond_to_offer({"quantity": quantity})
            self._emit_live("compost", response)
            return {"state": "ESCALATED_COMPOST", "summary": "Produce sent to compost. Zero-waste recovery.", "deal": response, "logs": self.logs, "price_series": self.memory.get_price_series()}

        return {"state": "FAILED", "summary": "All fallback channels exhausted.", "deal": None, "logs": self.logs, "price_series": self.memory.get_price_series()}