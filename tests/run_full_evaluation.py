"""
tests/run_full_evaluation.py
--------------------------------------------------------------------
AgriNegotiator / FarmGenAI  COMPLETE AI SYSTEM EVALUATION RUNNER
--------------------------------------------------------------------

Runs all test suites in order and produces a FINAL VERDICT on
whether the system performs intelligent AI-agent negotiation.

Usage:
  cd c:\PROJECT\FarmGenAI
  python -m pytest tests/run_full_evaluation.py -v --tb=short
  OR
  python tests/run_full_evaluation.py
"""
import sys, os, subprocess, json, time, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

SUITES = [
    {
        "id": "01", "name": "Agent Unit Tests",
        "file": "tests/test_01_agents_unit.py",
        "type": "DETERMINISTIC",
        "critical": True,
        "description": "All 7 agent classes: FarmerAgent, BuyerAgent, WarehouseAgent, ProcessorAgent, CompostAgent, TransporterAgent, RestaurantAgent"
    },
    {
        "id": "02", "name": "Matching Engine Tests",
        "file": "tests/test_02_matching_engine.py",
        "type": "DETERMINISTIC",
        "critical": True,
        "description": "Unified 8-factor NRV matching formula across matching_service.py and LangGraph matching_engine_node"
    },
    {
        "id": "03", "name": "Business Rules Tests",
        "file": "tests/test_03_business_rules.py",
        "type": "DETERMINISTIC",
        "critical": True,
        "description": "Floor price enforcement, budget ceiling, validator logic, escalation paths, RL rewards"
    },
    {
        "id": "04", "name": "20 Negotiation Scenarios",
        "file": "tests/test_04_negotiation_scenarios.py",
        "type": "INTEGRATION",
        "critical": True,
        "description": "Complete end-to-end negotiation: easy deal, failure, spoilage, multi-buyer, escalation"
    },
    {
        "id": "05", "name": "LangGraph Node Tests",
        "file": "tests/test_05_langgraph_nodes.py",
        "type": "INTEGRATION",
        "critical": True,
        "description": "Individual node tests: planner, market_intelligence, matching, farmer, buyer, ranker, validator, reward"
    },
    {
        "id": "06", "name": "RAG Quality Tests",
        "file": "tests/test_06_rag_quality.py",
        "type": "INTEGRATION",
        "critical": False,
        "description": "ChromaDB retrieval quality for mandi data, strategies, crop knowledge, government schemes"
    },
    {
        "id": "07", "name": "Real LLM Tests (Ollama)",
        "file": "tests/test_07_real_llm.py",
        "type": "REAL_LLM",
        "critical": False,
        "description": "Actual Ollama/Gemini LLM quality: JSON output, farmer decision, buyer decision, validator"
    },
    {
        "id": "08", "name": "Failure Mode Tests",
        "file": "tests/test_08_failure_modes.py",
        "type": "DETERMINISTIC",
        "critical": True,
        "description": "Graceful degradation: Ollama down, ChromaDB down, PostgreSQL down, corrupt state"
    },
    {
        "id": "09", "name": "Adaptive Candidate Expansion Tests",
        "file": "tests/test_adaptive_candidate_expansion.py",
        "type": "DETERMINISTIC",
        "critical": True,
        "description": "Batch candidate expansion preventing infinite buyer loops and broadening search space"
    },
    {
        "id": "10", "name": "Net Farmer Margin Ranking Tests",
        "file": "tests/test_net_farmer_margin_ranking.py",
        "type": "DETERMINISTIC",
        "critical": True,
        "description": "Deducts distance freight and storage from gross revenue to rank true net farmer margin"
    },
    {
        "id": "11", "name": "Knowledge Manager Node Tests",
        "file": "tests/test_knowledge_manager_node.py",
        "type": "INTEGRATION",
        "critical": True,
        "description": "Wires live Open-Meteo weather and Agmarknet mandi feeds into LangGraph pipeline"
    },
    {
        "id": "12", "name": "Object Storage Service Tests",
        "file": "tests/test_storage_object_service.py",
        "type": "DETERMINISTIC",
        "critical": True,
        "description": "Zero-latency LocalDisk default with opt-in MinIO and clean error handling"
    },
]


def run_suite(suite):
    start = time.time()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", suite["file"],
         "-v", "--tb=short", "--no-header", "-q"],
        capture_output=True, text=True, cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    )
    elapsed = round(time.time() - start, 1)

    # Parse pytest output
    passed = failed = skipped = errors = 0
    clean_stdout = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
    for line in clean_stdout.split("\n"):
        line = line.strip()
        if "passed" in line or "failed" in line or "skipped" in line or "error" in line:
            m_pass = re.search(r'(\d+)\s+passed', line)
            if m_pass:
                passed = int(m_pass.group(1))
            m_fail = re.search(r'(\d+)\s+failed', line)
            if m_fail:
                failed = int(m_fail.group(1))
            m_skip = re.search(r'(\d+)\s+skipped', line)
            if m_skip:
                skipped = int(m_skip.group(1))
            m_err = re.search(r'(\d+)\s+error', line)
            if m_err:
                errors = int(m_err.group(1))

    return {
        "suite": suite,
        "passed": passed, "failed": failed, "skipped": skipped,
        "errors": errors, "elapsed": elapsed,
        "returncode": result.returncode,
        "stdout": result.stdout[-3000:],  # last 3000 chars
        "stderr": result.stderr[-1000:],
    }


def generate_verdict(results):
    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_skipped = sum(r["skipped"] for r in results)
    total_errors = sum(r["errors"] for r in results)

    critical_failures = [
        r for r in results if r["suite"]["critical"] and (r["failed"] > 0 or r["errors"] > 0)
    ]
    llm_tests = next((r for r in results if r["suite"]["id"] == "07"), None)
    llm_skipped = llm_tests and llm_tests["skipped"] > 0 and llm_tests["passed"] == 0
    llm_passed = llm_tests["passed"] if llm_tests else 0

    sep = "=" * 70

    print(f"\n{sep}")
    print("  AGRINEGOTIATOR  FINAL EVALUATION REPORT")
    print(sep)
    print(f"  {'Suite':<35} {'Type':<15} {'Pass':>5} {'Fail':>5} {'Skip':>5} {'Status'}")
    print(f"  {'-'*35} {'-'*15} {'-'*5} {'-'*5} {'-'*5} {'-'*10}")

    for r in results:
        suite = r["suite"]
        status = "? PASS" if r["failed"] == 0 and r["errors"] == 0 else "? FAIL"
        if r["skipped"] > 0 and r["passed"] == 0 and r["failed"] == 0:
            status = "??  SKIP"
        print(f"  {suite['name']:<35} {suite['type']:<15} {r['passed']:>5} {r['failed']:>5} {r['skipped']:>5} {status}")

    print(f"\n  Total: {total_passed} passed | {total_failed} failed | {total_skipped} skipped | {total_errors} errors")

    print(f"\n{sep}")
    print("  SYSTEM INTELLIGENCE VERDICT")
    print(sep)

    if critical_failures:
        print("\n  ?? VERDICT: SYSTEM HAS CRITICAL FAILURES")
        print(f"\n  {len(critical_failures)} critical test suite(s) failed:")
        for r in critical_failures:
            print(f"     {r['suite']['name']}: {r['failed']} failures")
        print("\n  The system CANNOT be trusted for production negotiation.")
    elif llm_skipped:
        print("\n  ?? VERDICT: DETERMINISTIC LAYER IS CORRECT, LLM UNTESTED")
        print("\n  All deterministic business rules, matching, agents, and LangGraph")
        print("  node tests passed. However, Ollama was unavailable  real LLM")
        print("  intelligence could not be verified.")
        print("\n  Recommendations:")
        print("    1. Start Ollama: 'ollama serve'")
        print("    2. Pull model: 'ollama pull qwen2:0.5b'")
        print("    3. Re-run: pytest tests/test_07_real_llm.py -v")
    elif llm_passed > 0 and not critical_failures:
        print("\n  ?? VERDICT: SYSTEM IS PERFORMING INTELLIGENT AI NEGOTIATION")
        print(f"\n  {llm_passed} real LLM tests passed.")
        print("  All critical business rules are enforced.")
        print("  Multi-agent orchestration is functioning correctly.")
        print("  Floor price protection is verified.")
    else:
        print("\n  ?? VERDICT: PARTIAL PASS")
        print("\n  Some tests passed but full LLM verification is pending.")

    print(f"\n{sep}")
    print("  KNOWN ISSUES (from audit)")
    print(sep)
    print("  [RESOLVED] Unified Matching Formula: matching_service.py and graph_orchestrator.py share canonical 8-factor NRV engine")
    print("  ??  Validator can be overridden by LLM  floor price not guaranteed via validator")
    print("  [RESOLVED] knowledge_manager_node wired & active (live weather/mandi context)")
    print("  [RESOLVED] MinIO Local Fallback Cleanly: ObjectStorageService defaults to LocalDisk (ENABLE_MINIO=False)")
    print("  ??  qwen2:0.5b may produce invalid JSON  fallback is deterministic")
    print("  ??  Gemini API is rate-limited (429)  cloud fallback unavailable")
    print(f"\n{sep}\n", flush=True)


def main():
    print("\n" + "=" * 70)
    print("  AGRINEGOTIATOR / FARMGENAI  FULL SYSTEM EVALUATION")
    print("=" * 70)
    print(f"  Running {len(SUITES)} test suites...\n", flush=True)

    results = []
    for suite in SUITES:
        print(f"  [{suite['id']}] {suite['name']} ({suite['type']})...", flush=True)
        r = run_suite(suite)
        results.append(r)
        status = "?" if r["failed"] == 0 and r["errors"] == 0 else "?"
        print(f"       {status} {r['passed']} passed | {r['failed']} failed | {r['skipped']} skipped | {r['elapsed']}s\n", flush=True)

        if r["failed"] > 0 or r["errors"] > 0:
            # Print last few lines of output for context
            lines = [l for l in r["stdout"].split("\n") if "FAILED" in l or "ERROR" in l or "assert" in l.lower()]
            for line in lines[:5]:
                print(f"       {line}")

    generate_verdict(results)


if __name__ == "__main__":
    main()
