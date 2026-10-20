"""
Load and Concurrency Benchmark for FarmGenAI Intelligent Workflow Pipeline.
Tests concurrency levels: 10, 50, 100, 200, 500 workflows.
Measures:
- Latency (min, p50, p95, p99, max, mean)
- Throughput (workflows / second)
- Error rate
- System memory delta
- Observed capacity vs Production-proven limits
"""
import sys, os, time, asyncio, statistics, tracemalloc
from typing import Dict, List, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.matching_service import compute_match_score_sync, compute_match_breakdown_sync
from backend.core.constants import WorkflowMode, get_allowed_agents
from backend.agents.graph_orchestrator import compute_net_farmer_margin

def generate_pool(size=100):
    pool = []
    crops = ["Onion", "Soybean", "Cotton", "Sugarcane", "Bajra"]
    locations = ["Nashik", "Pune", "Nagpur", "Aurangabad", "Solapur"]
    for i in range(size):
        pool.append({
            "buyer_id": f"buyer_{i:04d}",
            "crop": crops[i % len(crops)],
            "min_quantity": 500.0,
            "max_quantity": 10000.0,
            "offered_price_range": [22.0 + (i % 8), 26.0 + (i % 8)],
            "location": locations[i % len(locations)],
            "rating": 3.5 + ((i % 15) / 10.0),
            "verification_status": "VERIFIED"
        })
    return pool

async def simulate_workflow_request(workflow_id: int, buyer_pool: List[Dict[str, Any]]) -> Dict[str, Any]:
    t0 = time.perf_counter()
    try:
        # Step 1: Policy Scope Validation
        allowed = get_allowed_agents("FARMER", WorkflowMode.BUYER_ONLY)
        if "buyer_agent" not in allowed:
            return {"success": False, "error": "SCOPE_DENIED", "latency": time.perf_counter() - t0}
            
        # Step 2: Intelligent Multi-factor Candidate Matching
        listing = {
            "crop": "Onion",
            "quantity": 3000.0,
            "min_price": 24.0,
            "expected_price": 28.0,
            "location": "Nashik",
            "shelf_life_days": 10
        }
        
        scored = []
        for c in buyer_pool:
            score = compute_match_score_sync(listing, c)
            if score > 0.30:
                scored.append((score, c))
                
        scored.sort(key=lambda x: x[0], reverse=True)
        shortlist = scored[:5]
        
        if not shortlist:
            return {"success": False, "error": "NO_CANDIDATES", "latency": time.perf_counter() - t0}
            
        # Step 3: Economic Net Margin Evaluation
        best_candidate = shortlist[0][1]
        offer_price = best_candidate.get("offered_price_range", [25.0, 27.0])[1]
        
        offer = {
            "buyer_id": best_candidate["buyer_id"],
            "price": offer_price
        }
        state = {
            "quantity": listing["quantity"],
            "location": listing["location"],
            "has_transport": False,
            "active_buyers": [best_candidate]
        }
        econ = compute_net_farmer_margin(offer, state)
        
        # Step 4: Verification of hard floor invariant
        if econ["net_price"] < listing["min_price"]:
            return {"success": False, "error": "FLOOR_VIOLATED", "latency": time.perf_counter() - t0}
            
        t1 = time.perf_counter()
        return {
            "success": True,
            "latency": t1 - t0,
            "workflow_id": workflow_id,
            "net_price": econ["net_price"]
        }
    except Exception as e:
        return {"success": False, "error": str(e), "latency": time.perf_counter() - t0}

async def benchmark_concurrency_level(concurrency: int, buyer_pool: List[Dict[str, Any]]) -> Dict[str, Any]:
    tracemalloc.start()
    mem_before, _ = tracemalloc.get_traced_memory()
    
    start_time = time.perf_counter()
    tasks = [simulate_workflow_request(i, buyer_pool) for i in range(concurrency)]
    results = await asyncio.gather(*tasks)
    total_duration = time.perf_counter() - start_time
    
    _, mem_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    mem_delta_mb = round((mem_peak - mem_before) / (1024 * 1024), 2)
    
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    latencies = [r["latency"] for r in results]
    
    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    
    return {
        "concurrency": concurrency,
        "total_requests": concurrency,
        "success_count": len(successes),
        "failure_count": len(failures),
        "error_rate_pct": (len(failures) / concurrency) * 100.0,
        "total_duration_sec": round(total_duration, 4),
        "throughput_req_per_sec": round(concurrency / total_duration, 2),
        "latency_min_ms": round(min(latencies) * 1000, 2),
        "latency_mean_ms": round(statistics.mean(latencies) * 1000, 2),
        "latency_p50_ms": round(p50 * 1000, 2),
        "latency_p95_ms": round(p95 * 1000, 2),
        "latency_p99_ms": round(p99 * 1000, 2),
        "latency_max_ms": round(max(latencies) * 1000, 2),
        "mem_delta_mb": mem_delta_mb
    }

def run_load_test():
    print("=" * 80)
    print("FARMGENAI CONCURRENCY AND LOAD STRESS BENCHMARK")
    print("=" * 80)
    
    buyer_pool = generate_pool(size=100)
    concurrency_levels = [10, 50, 100, 200, 500]
    benchmarks = []
    
    for c in concurrency_levels:
        res = asyncio.run(benchmark_concurrency_level(c, buyer_pool))
        benchmarks.append(res)
        print(f"Concurrency: {c:4d} | Throughput: {res['throughput_req_per_sec']:7.2f} req/s | "
              f"p50: {res['latency_p50_ms']:6.2f}ms | p95: {res['latency_p95_ms']:6.2f}ms | "
              f"Errors: {res['failure_count']} ({res['error_rate_pct']}%) | Mem Delta: {res['mem_delta_mb']}MB")
              
    print("=" * 80)
    return benchmarks

if __name__ == "__main__":
    run_load_test()

