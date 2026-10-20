import asyncio
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "c:/PROJECT/FarmGenAI")

from backend.agents.graph_orchestrator import knowledge_manager_node, market_intelligence_node

async def run_market_test():
    state = {
        "crop": "Tomato",
        "quantity": 500,
        "min_price": 15.0,
        "location": "Pune",
        "spoilage_days": 4,
        "market_price": 18.0,
        "round": 0,
        "max_rounds": 3,
        "status": "NEGOTIATING",
        "history": [],
        "logs": [],
        "buyers_list": []
    }
    
    print("Testing Knowledge Manager Node (Live Data Fetch)...")
    knowledge_res = await knowledge_manager_node(state)
    state.update(knowledge_res)
    print("Weather retrieved:", state.get("weather"))
    print("Mandi Data retrieved:", state.get("live_mandi"))
    
    print("\nTesting Market Intelligence Node (LLM Prompting with Live Data)...")
    market_res = await market_intelligence_node(state)
    print("Market Intelligence generated:\n", market_res.get("market_intelligence"))
    
if __name__ == "__main__":
    asyncio.run(run_market_test())
