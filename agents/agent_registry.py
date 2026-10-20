from agents.buyer_agent import BuyerAgent
from agents.compost_agent import CompostAgent
from backend.agents.stakeholders.farmer_agent import FarmerAgent
from agents.processor_agent import ProcessorAgent
from agents.warehouse_agent import WarehouseAgent
from agents.transporter_agent import TransporterAgent


class AgentRegistry:
    def __init__(self):
        self.agents = {}

    def register_agent(self, agent_type, agent_instance):
        self.agents[agent_type] = agent_instance

    def get_agent(self, agent_type):
        return self.agents.get(agent_type)

    def create_agents(self):
        # Baseline default agents for standalone simulations.
        self.register_agent(
            "buyer",
            BuyerAgent(name="BuyerAgent", budget=24000, max_quantity=1200, target_price=19)
        )
        farmer_agent = FarmerAgent()
        farmer_agent.name = "FarmerAgent"
        farmer_agent.crop = "Tomato"
        farmer_agent.quantity = 1000
        farmer_agent.min_price = 18
        farmer_agent.shelf_life = 3
        self.register_agent("farmer", farmer_agent)
        self.register_agent(
            "processor",
            ProcessorAgent(
                name="ProcessorAgent",
                crop_type="Tomato",
                processing_capacity=800,
                processing_cost_per_kg=2,
                target_price=17,
                max_price=20
            )
        )
        self.register_agent(
            "warehouse",
            WarehouseAgent(name="WarehouseAgent", capacity=3000, storage_cost_per_kg=1.8)
        )
        self.register_agent(
            "transporter",
            TransporterAgent(
                name="TransporterAgent",
                vehicle_capacity=2000,
                cost_per_km_per_kg=0.03,
                base_fee=450
            )
        )
        self.register_agent("compost", CompostAgent(name="CompostAgent", base_price=8))

    def list_agents(self):
        """List all registered agents with their roles."""
        return [
            {"name": agent.name, "role": agent.role}
            for agent in self.agents.values()
        ]
