from datetime import datetime
from agents.base_agent import BaseAgent


class WarehouseAgent(BaseAgent):

    def __init__(
        self,
        name,
        capacity,
        storage_cost_per_kg,
        location=None
    ):
        super().__init__(name, "warehouse")
        self.capacity = capacity
        self.current_inventory = 0
        self.storage_cost_per_kg = storage_cost_per_kg
        self.storage_records = []
        self.location = location

    def available_capacity(self):
        return self.capacity - self.current_inventory

    def make_offer(self, context=None):
        message = self.log_action(f"Storage available at ₹{self.storage_cost_per_kg}/kg in {self.location}")
        return {
            "type": "OFFER_STORAGE",
            "price": self.storage_cost_per_kg,
            "message": message
        }

    def respond_to_offer(self, offer, context=None):
        quantity = float(offer.get("quantity", 0))
        crop = offer.get("crop", "Produce")
        
        # ── Autonomous Thinking Phase ────────────────────────
        thought = self.think(
            f"You are {self.name}, a Warehouse in {self.location}. Request to store {quantity}kg of {crop}. "
            f"Current Cap: {self.capacity}kg, Current Inv: {self.current_inventory}kg. "
            "Evaluate if you should accept this storage deal based on space and supply chain risks.",
            schema={"decision": "ACCEPT", "reason": "...", "risk": "low"}
        )

        decision = str(thought.get("decision", "ACCEPT")).upper()
        reason = thought.get("reason", "Storage requested.")

        # Physical capacity secondary check
        if quantity > self.available_capacity():
            decision = "REJECT"
            reason = "Strict physical capacity limit reached."

        if decision == "REJECT":
            return {
                "type": "REJECT",
                "message": self.log_action(f"REJECTED storage: {reason}")
            }

        # ── Execution Phase ──────────────────────────────────
        self.current_inventory += quantity
        storage_cost = round(quantity * self.storage_cost_per_kg, 2)

        record = {
            "crop": crop,
            "quantity": quantity,
            "cost": storage_cost,
            "timestamp": datetime.now().isoformat()
        }
        self.storage_records.append(record)

        return {
            "type": "ACCEPT_STORAGE",
            "quantity": quantity,
            "cost": storage_cost,
            "message": self.log_action(f"ACCEPTED storage for {quantity}kg: {reason}")
        }

    def release_stock(self, quantity):
        if quantity > self.current_inventory:
            return {
                "type": "REJECT",
                "message": self.log_action("Not enough stock in warehouse.")
            }
        self.current_inventory -= quantity
        return {
            "type": "RELEASE",
            "quantity": quantity,
            "message": self.log_action(f"Released {quantity}kg from storage.")
        }

    def store_crop(self, market_price, quantity):
        offer = {"quantity": quantity, "price": market_price}
        response = self.respond_to_offer(offer)
        if response["type"] == "ACCEPT_STORAGE":
            return {
                "type": "STORE",
                "price": market_price,
                "quantity": quantity,
                "cost": response["cost"],
                "message": response["message"]
            }
        return None

    def get_status(self):
        return {
            "capacity": self.capacity,
            "current_inventory": self.current_inventory,
            "available_capacity": self.available_capacity(),
            "storage_cost_per_kg": self.storage_cost_per_kg,
            "location": self.location
        }