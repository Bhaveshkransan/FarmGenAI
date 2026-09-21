"""
scripts/run_transport_tests.py
Runner script to execute Transport Agent tests and print clean ASCII results.
"""

import asyncio
import os
import sys
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_transport_agent import (
    test_valid_transport_request,
    test_vehicle_capacity_rejection,
    test_refrigeration_requirement,
    test_osrm_route_calculation,
    test_deterministic_cost_calculation,
    test_offer_below_floor_price,
    test_offer_above_floor_price,
    test_multi_round_negotiation,
    test_farmer_buyer_mvp_unaffected
)


async def main():
    print("=" * 60)
    print("RUNNING TRANSPORT AGENT TEST SUITE")
    print("=" * 60)

    tests = [
        ("Test 1: Valid transport request flow", test_valid_transport_request),
        ("Test 2: Vehicle capacity rejection", test_vehicle_capacity_rejection),
        ("Test 3: Refrigeration requirement filtering", test_refrigeration_requirement),
        ("Test 4: OSRM route calculation", test_osrm_route_calculation),
        ("Test 5: Deterministic cost calculation", test_deterministic_cost_calculation),
        ("Test 6: Offer below floor price handling", test_offer_below_floor_price),
        ("Test 7: Offer above floor price handling", test_offer_above_floor_price),
        ("Test 8: Multi-round price negotiation", test_multi_round_negotiation),
        ("Test 9: Regression check - Farmer/Buyer MVP unaffected", test_farmer_buyer_mvp_unaffected),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            await test_func()
            print(f"  [PASSED] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAILED] {name}: {e}")
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed} Passed, {failed} Failed out of {len(tests)} tests.")
    print("=" * 60)

    if failed > 0:
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
