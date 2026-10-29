from fastapi import APIRouter

router = APIRouter()

CANONICAL_PRODUCTION_AGENTS = [
    {
        "id": "agt-farmer",
        "name": "Farmer Agent",
        "role": "farmer",
        "status": "ACTIVE",
        "latency": "42ms",
        "memory": "128MB",
        "throughput": "120 req/s",
        "errors": "0",
        "description": "Protects statutory MSP floors, models harvest spoilage urgency, and negotiates farmgate realization."
    },
    {
        "id": "agt-buyer",
        "name": "Buyer Procurement Agent",
        "role": "buyer",
        "status": "ACTIVE",
        "latency": "58ms",
        "memory": "256MB",
        "throughput": "95 req/s",
        "errors": "0",
        "description": "Multi-agent LangGraph orchestrator evaluating candidates across 327 Mandis to minimize landed cost."
    },
    {
        "id": "agt-transport",
        "name": "Transport Logistics Agent",
        "role": "transport",
        "status": "ACTIVE",
        "latency": "38ms",
        "memory": "128MB",
        "throughput": "150 req/s",
        "errors": "0",
        "description": "Coordinates freight logistics, fuel indices, toll expenses, and carrier allocation."
    },
    {
        "id": "agt-warehouse",
        "name": "Warehouse Storage Agent",
        "role": "warehouse",
        "status": "ACTIVE",
        "latency": "29ms",
        "memory": "96MB",
        "throughput": "210 req/s",
        "errors": "0",
        "description": "Inspects MSWC godowns and cold-chain bays based on crop perishable shelf-life."
    },
    {
        "id": "agt-processor",
        "name": "Industrial Processor Agent",
        "role": "processor",
        "status": "ACTIVE",
        "latency": "34ms",
        "memory": "112MB",
        "throughput": "85 req/s",
        "errors": "0",
        "description": "Matches commercial agro-processing mills and calculates byproduct conversion yields."
    }
]

@router.get("/")
async def get_agents():
    """Get list of active production agents."""
    return {"agents": CANONICAL_PRODUCTION_AGENTS}

@router.get("/list")
async def get_agents_list():
    return await get_agents()
