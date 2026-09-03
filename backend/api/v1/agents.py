import random
from fastapi import APIRouter

router = APIRouter()

MOCK_AGENTS_BASE = [
    {"id": "agt-1", "name": "Coordinator Agent", "status": "ACTIVE", "memory_base": 128, "throughput_base": 450},
    {"id": "agt-2", "name": "Farmer Agent", "status": "ACTIVE", "memory_base": 256, "throughput_base": 120},
    {"id": "agt-3", "name": "Buyer Agent", "status": "ACTIVE", "memory_base": 256, "throughput_base": 115},
    {"id": "agt-4", "name": "Market Intel Agent", "status": "ACTIVE", "memory_base": 512, "throughput_base": 45},
    {"id": "agt-5", "name": "Weather Agent", "status": "IDLE", "memory_base": 64, "throughput_base": 10},
    {"id": "agt-6", "name": "Warehouse Agent", "status": "ACTIVE", "memory_base": 128, "throughput_base": 80},
    {"id": "agt-7", "name": "Transport Agent", "status": "ACTIVE", "memory_base": 128, "throughput_base": 85},
    {"id": "agt-8", "name": "Trust Scoring Agent", "status": "ACTIVE", "memory_base": 256, "throughput_base": 300},
    {"id": "agt-9", "name": "RL Agent", "status": "TRAINING", "memory_base": 2400, "throughput_base": 5},
    {"id": "agt-10", "name": "Reflection Agent", "status": "ACTIVE", "memory_base": 1200, "throughput_base": 15},
    {"id": "agt-11", "name": "Validator Agent", "status": "ACTIVE", "memory_base": 128, "throughput_base": 450},
    {"id": "agt-12", "name": "Agreement Agent", "status": "IDLE", "memory_base": 64, "throughput_base": 2},
    {"id": "agt-13", "name": "Recommendation Agent", "status": "ACTIVE", "memory_base": 512, "throughput_base": 40},
]

@router.get("/")
async def get_agents():
    # Simulate live telemetry with jitter
    live_agents = []
    for agent in MOCK_AGENTS_BASE:
        jitter_ms = random.randint(10, 50) if agent["status"] == "ACTIVE" else random.randint(1, 5)
        if agent["name"] == "RL Agent":
            jitter_ms = random.randint(800, 900)
        elif agent["name"] == "Reflection Agent":
            jitter_ms = random.randint(400, 500)
            
        throughput_jitter = random.randint(-5, 5)
        memory_jitter = random.uniform(-0.1, 0.1) * agent["memory_base"]
        
        errors = str(random.randint(0, 2)) if random.random() > 0.8 else "0"

        mem_val = agent["memory_base"] + memory_jitter
        mem_str = f"{mem_val:.1f}MB" if mem_val < 1000 else f"{(mem_val/1024):.1f}GB"
        
        live_agents.append({
            "id": agent["id"],
            "name": agent["name"],
            "status": agent["status"],
            "latency": f"{jitter_ms}ms",
            "memory": mem_str,
            "throughput": f"{max(0, agent['throughput_base'] + throughput_jitter)} req/s",
            "errors": errors
        })

    return {"agents": live_agents}
