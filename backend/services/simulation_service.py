import asyncio
from ..services.negotiation_service import start_negotiation
from negotiation_engine.scoring import calculate_scenario_score


def _get_scenario_payload(scenario: str, user_id: str = None):
    """Return a preset payload dict for a named scenario (sync, pure data)."""
    scenarios = {
        "direct-sale": {
            "user_id": user_id,
            "farmer_name": "Ramesh",
            "crop": "Soybean",
            "quantity": 1000,
            "min_price": 70,
            "target_price": 78,
            "shelf_life": 180,
            "location": "Latur",
            "quality": "A",
            "language": "Marathi",
            "scenario_type": "direct-sale",
        },
        "storage": {
            "user_id": user_id,
            "farmer_name": "Suresh",
            "crop": "Onion",
            "quantity": 1200,
            "min_price": 20,
            "target_price": 26,
            "shelf_life": 60,
            "location": "Nashik",
            "quality": "A",
            "language": "Marathi",
            "scenario_type": "storage",
        },
        "processing": {
            "user_id": user_id,
            "farmer_name": "Mahesh",
            "crop": "Sugarcane",
            "quantity": 5000,
            "min_price": 3.5,
            "target_price": 4.2,
            "shelf_life": 7,
            "location": "Kolhapur",
            "quality": "A",
            "language": "Marathi",
            "scenario_type": "processing",
        },
    }
    scenarios["processor"] = scenarios["processing"]
    return scenarios.get(scenario)


async def run_simulation(payload: dict, db=None):
    """Async simulation runner — wraps the async start_negotiation correctly."""
    scenario = payload.get("scenario", "direct-sale")
    user_id = payload.get("user_id")

    # ── "all" scenario: run every preset and pick the best ──────────────────
    if scenario == "all":
        scenario_keys = ["direct-sale", "storage", "processing"]
        results = []

        base_payload = {
            "user_id": user_id,
            "farmer_name": payload.get("farmer_name") or "Farmer",
            "crop": payload.get("crop"),
            "quantity": payload.get("quantity"),
            "min_price": payload.get("min_price"),
            "location": payload.get("location"),
            "quality": payload.get("quality", "A"),
            "language": payload.get("language", "English"),
        }

        for skey in scenario_keys:
            if base_payload["crop"]:
                sp = {**base_payload, "scenario_type": skey}
            else:
                sp = _get_scenario_payload(skey, user_id) or {}

            res = await start_negotiation(sp, scenario=sp.get("scenario_type", "direct-sale"), db=db)

            score_data = calculate_scenario_score({
                "status": res.get("status"),
                "scenario_type": skey,
                "final_price": res.get("final_price"),
                "min_price": sp.get("min_price"),
                "target_price": sp.get("target_price"),
                "shelf_life": sp.get("shelf_life"),
                "quantity": sp.get("quantity"),
                "offered_quantity": res.get("quantity"),
            })
            res["score"] = score_data["score"]
            res["score_breakdown"] = score_data["breakdown"]
            res["scenario_type"] = skey
            results.append(res)

        best_scenario = (
            max(results, key=lambda x: x["score"])["scenario_type"] if results else None
        )
        try:
            from llm.llm_client import client as llm_client
            explanation = llm_client.explain_scenarios(results, best_scenario)
        except Exception:
            explanation = f"Best scenario: {best_scenario}"

        return {"scenarios": results, "best_scenario": best_scenario, "explanation": explanation}

    # ── single scenario ──────────────────────────────────────────────────────
    selected = _get_scenario_payload(scenario, user_id)
    if not selected:
        selected = payload.copy()
        selected["scenario_type"] = scenario
    else:
        for k, v in payload.items():
            if v is not None and k not in ("scenario", "user_id"):
                selected[k] = v

    result = await start_negotiation(selected, scenario=selected.get("scenario_type", "direct-sale"), db=db)

    score_data = calculate_scenario_score({
        "status": result.get("status"),
        "scenario_type": scenario,
        "final_price": result.get("final_price"),
        "min_price": selected.get("min_price"),
        "target_price": selected.get("target_price"),
        "shelf_life": selected.get("shelf_life"),
        "quantity": selected.get("quantity"),
        "offered_quantity": result.get("quantity"),
    })
    result["score"] = score_data["score"]
    result["score_breakdown"] = score_data["breakdown"]

    return result

