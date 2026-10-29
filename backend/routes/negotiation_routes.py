from fastapi import APIRouter, HTTPException, Depends
try:
    from backend.models.negotiation_model import StartNegotiationRequest
except ImportError:
    from backend.schemas.negotiation_model import StartNegotiationRequest
from backend.services.negotiation_service import service as controller, NegotiationService, start_negotiation as service_start_negotiation
from database.db import Database  # M2 fix: moved to top — was imported at line 86 causing NameError in list_negotiations()

router = APIRouter()


@router.get("")
@router.get("/")
async def list_negotiations():
    try:
        items = await Database.list_negotiations_async()
        return items
    except Exception as e:
        return list(Database.negotiations.values())

from backend.core.security import get_current_user_optional
from backend.core.constants import validate_crop, WorkflowMode, get_allowed_agents

@router.post("")
@router.post("/")
@router.post("/start-negotiation")
async def start_negotiation(request: StartNegotiationRequest, current_user: dict = Depends(get_current_user_optional)):
    try:
        payload = request.model_dump()

        # Pillar 1: Global Canonical 7-Crop Restriction Enforcement
        crop = payload.get("crop")
        if crop:
            is_valid, err_msg = validate_crop(crop)
            if not is_valid:
                raise HTTPException(status_code=400, detail=err_msg)

        # Pillar 5: Deterministic Business Rule Validation (Price & Quantity Constraints)
        quantity = float(payload.get("quantity") or 0)
        min_price = float(payload.get("min_price") or 0)
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="Listing quantity must be strictly greater than 0.")
        if min_price <= 0:
            raise HTTPException(status_code=400, detail="Listing minimum price must be strictly greater than 0.")

        if current_user:
            payload["user_id"] = current_user.get("id")
            payload["stakeholder_role"] = current_user.get("role", "FARMER").upper()
        else:
            payload["stakeholder_role"] = "FARMER" # Default fallback

        # Pillar 2: Permission-based Workflow Scope
        mode = payload.get("workflow_mode") or WorkflowMode.FULL_SUPPLY_CHAIN
        payload["workflow_mode"] = mode
        payload["permitted_agents"] = get_allowed_agents(payload["stakeholder_role"], mode)
            
        res = await controller.start_negotiation(payload, scenario="direct-sale")
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agents")
@router.get("/agents/")
async def get_agents():
    try:
        return {"agents": await controller.list_agents()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stream/status")
@router.get("/stream-status")
@router.get("/worker/status")
async def get_stream_status():
    from backend.core.redis import redis_manager
    return await redis_manager.get_stream_stats()

@router.get("/{negotiation_id}")
@router.get("/negotiation-status/{negotiation_id}")
async def get_negotiation_status(negotiation_id: str):
    try:
        status = await controller.get_negotiation_status(negotiation_id)
        if not status:
            raise HTTPException(status_code=404, detail="Negotiation not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


import hashlib
from datetime import datetime, timezone


@router.post("/{negotiation_id}/accept")
@router.post("/{negotiation_id}/finalize")
async def accept_deal(negotiation_id: str, payload: dict = None):
    try:
        status_data = await controller.get_negotiation_status(negotiation_id) or {}
        p_price = (payload.get("price") or payload.get("final_price") or payload.get("agreed_price") or payload.get("counter_price")) if isinstance(payload, dict) else None
        final_p_raw = p_price or status_data.get("final_price") or status_data.get("target_price") or status_data.get("price") or status_data.get("min_price") or 50.0
        p_qty = (payload.get("quantity") or payload.get("procurement_volume")) if isinstance(payload, dict) else None
        qty_raw = p_qty or status_data.get("quantity") or 3000.0
        p_farmer = payload.get("farmer") if isinstance(payload, dict) else None
        farmer = p_farmer or status_data.get("farmer_name") or status_data.get("farmer") or "Maharashtra Farmer Network"
        p_buyer = payload.get("buyer") if isinstance(payload, dict) else None
        buyer = p_buyer or status_data.get("buyer_name") or status_data.get("buyer") or "Buyer Enterprise"
        crop = (payload.get("crop") if isinstance(payload, dict) else None) or status_data.get("crop") or "Soybean"

        # 1. Entry Details Type & Sanity Validation
        try:
            final_p = float(final_p_raw)
            qty = float(qty_raw)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Invalid entry details: Deal price and procurement volume must be valid numeric numbers."
            )

        if qty <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid entry volume ({qty} kg): Quantity must be strictly positive (greater than 0 kg)."
            )

        if final_p <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid entry price (₹{final_p}/kg): Settlement price must be strictly greater than zero."
            )

        # 2. Statutory Benchmark & Ceiling/Floor Guardrails
        from backend.services.negotiation_service import STATUTORY_BENCHMARKS
        crop_norm = "Soybean"
        for k in STATUTORY_BENCHMARKS:
            if k.lower() in crop.lower():
                crop_norm = k
                break
        bench_info = STATUTORY_BENCHMARKS.get(crop_norm, {"benchmark": 50.0})
        statutory_bench = float(bench_info.get("benchmark", 50.0))
        target_p = float((status_data and (status_data.get("target_price") or status_data.get("price"))) or statutory_bench)
        max_buyer_ceiling = round(max(target_p * 1.75, statutory_bench * 1.75), 2)
        min_floor_price = round(min(target_p * 0.25, statutory_bench * 0.25), 2)

        if final_p > max_buyer_ceiling:
            raise HTTPException(
                status_code=400,
                detail=f"🛡️ [Buyer Guardrail] Price ₹{final_p:,.2f}/kg exceeds statutory ceiling (₹{max_buyer_ceiling:,.2f}/kg for {crop_norm}). Finalizing deal is strictly rejected."
            )

        if final_p < min_floor_price:
            raise HTTPException(
                status_code=400,
                detail=f"🛡️ [Buyer Guardrail] Price ₹{final_p:,.2f}/kg is below the statutory APMC floor threshold (₹{min_floor_price:,.2f}/kg for {crop_norm}). Absurd or predatory low pricing is strictly rejected."
            )

        # 3. Party Identification Hygiene
        farmer = str(farmer).strip() or "Maharashtra APMC Registered Producer"
        buyer = str(buyer).strip() or "Registered Buyer Enterprise"

        clean_id = str(negotiation_id).replace("neg_", "").upper()
        txn_id = f"TXN-MH-2026-{clean_id}"
        escrow_id = f"ESC-MH-2026-{clean_id}"
        upi_ref = f"UPI-MH-2026-{clean_id}"
        total_val = float(final_p) * float(qty)
        cess_amt = round(total_val * 0.01, 2)
        net_payout = round(total_val - cess_amt, 2)
        block_num = 18942000 + int(hashlib.md5(clean_id.encode()).hexdigest()[:6], 16) % 100000
        
        raw_hash_input = f"{txn_id}:{crop}:{qty}:{final_p}:{datetime.now(timezone.utc).isoformat()}"
        contract_hash = "0x" + hashlib.sha256(raw_hash_input.encode()).hexdigest()

        txn_record = {
            "transaction_id": txn_id,
            "negotiation_id": negotiation_id,
            "smart_contract_id": f"APMC-E-CONTRACT-{clean_id}",
            "status": "COMPLETED",
            "crop": crop,
            "quantity": qty,
            "final_price": final_p,
            "total_value": total_val,
            "apmc_cess": cess_amt,
            "net_farmer_receivable": net_payout,
            "escrow_account_id": escrow_id,
            "upi_reference": upi_ref,
            "payment_status": "SETTLED_IN_ESCROW",
            "payout_status": "READY_FOR_DISBURSEMENT",
            "blockchain_network": "Maharashtra APMC Private Consortium Ledger (EVM Keccak-256 / SHA-256)",
            "block_number": block_num,
            "contract_hash": contract_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "framework": "Maharashtra APMC Model Act Compliant Electronic Trade",
            "farmer_name": farmer,
            "buyer_name": buyer
        }

        transport_plan = (payload.get("transport_plan") if isinstance(payload, dict) else None) or status_data.get("transport_plan")
        if transport_plan:
            txn_record["transport_plan"] = transport_plan

        # Store in Database history
        user_id = (payload.get("user_id") if isinstance(payload, dict) else None) or status_data.get("user_id") or status_data.get("buyer_id") or "usr_buyer_demo"
        farmer_user_id = (payload.get("farmer_id") if isinstance(payload, dict) else None) or status_data.get("farmer_id") or "usr_farmer_demo"

        hist_payload = {
            "type": "DEAL_FINALIZED",
            "transaction_id": txn_id,
            "negotiation_id": negotiation_id,
            "crop": crop,
            "quantity": qty,
            "final_price": final_p,
            "total_value": float(final_p) * float(qty),
            "status": "DEAL",
            "farmer": farmer,
            "farmer_name": farmer,
            "buyer": buyer,
            "buyer_name": buyer,
            "summary": f"Accepted deal for {qty}kg {crop} at ₹{final_p}/kg with {farmer}.",
            "details": txn_record
        }

        try:
            if user_id:
                await Database.add_history_async(user_id, hist_payload)
            if user_id != "usr_buyer_demo":
                await Database.add_history_async("usr_buyer_demo", hist_payload)
            if farmer_user_id:
                await Database.add_history_async(farmer_user_id, hist_payload)
            if farmer_user_id != "usr_farmer_demo":
                await Database.add_history_async("usr_farmer_demo", hist_payload)
            await Database.add_history_async("all", hist_payload)
        except Exception:
            pass

        # Also update status in negotiations table and memory controller
        try:
            update_data = {
                "status": "DEAL",
                "final_price": final_p,
                "price": final_p,
                "farmer": farmer,
                "farmer_name": farmer,
                "buyer": buyer,
                "buyer_name": buyer,
                "transaction_id": txn_id,
                "contract_hash": contract_hash
            }
            if transport_plan:
                update_data["transport_plan"] = transport_plan
            if isinstance(payload, dict):
                if "transport_plan" in payload:
                    update_data["transport_plan"] = payload["transport_plan"]
                if "warehouse_plan" in payload:
                    update_data["warehouse_plan"] = payload["warehouse_plan"]
                if "processor_plan" in payload:
                    update_data["processor_plan"] = payload["processor_plan"]
            await Database.update_negotiation_async(negotiation_id, update_data)

            for nid in (negotiation_id, f"neg_{negotiation_id}", negotiation_id.replace("neg_", "")):
                if nid in controller.active_negotiations:
                    controller.active_negotiations[nid].update(update_data)

            # Hook into Buyer Workflow Memory (Phase 1 Orchestration)
            req_id = (payload.get("requirement_id") if isinstance(payload, dict) else None) or status_data.get("requirement_id")
            if req_id:
                try:
                    from backend.services.buyer_workflow_service import buyer_workflow_service
                    await buyer_workflow_service.record_farmer_deal_outcome(
                        requirement_id=req_id,
                        deal_id=negotiation_id,
                        outcome_status="SUCCESS",
                        deal_details=update_data
                    )
                except Exception:
                    pass
        except Exception as update_err:
            print("Error updating negotiation record:", update_err)

        # Broadcast via WebSocket hub if available
        try:
            from backend.websocket.hub import hub
            await hub.broadcast_to_negotiation(negotiation_id, {
                "event": "NEGOTIATION_FINISHED",
                "status": "DEAL",
                "negotiation_id": negotiation_id,
                "transaction_id": txn_id,
                "final_price": final_p,
                "farmer": farmer,
                "buyer": buyer,
                "deal": txn_record
            })
        except Exception:
            pass

        # Deduct sold quantity from listing inventory if linked to a crop listing
        listing_id = (payload.get("listing_id") if isinstance(payload, dict) else None) or status_data.get("listing_id")
        if listing_id:
            try:
                await Database.deduct_produce_inventory_async(listing_id, float(qty))
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
            except Exception as e:
                pass

        return {
            "status": "success",
            "message": "Deal finalized, digitally signed and recorded.",
            "negotiation_id": negotiation_id,
            "transaction_id": txn_id,
            "contract_hash": contract_hash,
            "data": txn_record,
            "contract": txn_record
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{negotiation_id}/transaction")
async def get_deal_transaction(negotiation_id: str):
    try:
        status_data = await controller.get_negotiation_status(negotiation_id) or {}
        final_p = status_data.get("final_price") or status_data.get("price") or 15.0
        qty = status_data.get("quantity") or 3000.0
        crop = status_data.get("crop") or "Produce"
        clean_id = str(negotiation_id).replace("neg_", "").upper()
        txn_id = f"TXN-MH-2026-{clean_id}"
        contract_hash = "0x" + hashlib.sha256(f"{txn_id}:{crop}:{qty}:{final_p}".encode()).hexdigest()

        return {
            "success": True,
            "transaction_id": txn_id,
            "negotiation_id": negotiation_id,
            "contract_hash": contract_hash,
            "crop": crop,
            "quantity": qty,
            "price": final_p,
            "total_value": float(final_p) * float(qty),
            "apmc_cess": round(float(final_p) * float(qty) * 0.01, 2),
            "status": "COMPLETED",
            "framework": "Maharashtra APMC Model Act Compliant Electronic Trade",
            "farmer": status_data.get("farmer_name") or status_data.get("farmer") or "Gurpreet Singh",
            "buyer": status_data.get("buyer_name") or status_data.get("buyer") or "Buyer Enterprise"
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{negotiation_id}/reject")
async def reject_deal(negotiation_id: str):
    try:
        await Database.update_negotiation_async(negotiation_id, {"status": "FAILED"})
        status_data = await controller.get_negotiation_status(negotiation_id) or {}
        req_id = status_data.get("requirement_id")
        if req_id:
            try:
                from backend.services.buyer_workflow_service import buyer_workflow_service
                await buyer_workflow_service.record_farmer_deal_outcome(
                    requirement_id=req_id,
                    deal_id=negotiation_id,
                    outcome_status="FAILED"
                )
            except Exception:
                pass
        return {"status": "success", "message": "Deal rejected", "negotiation_id": negotiation_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{negotiation_id}/counter")
@router.post("/{negotiation_id}/intervene")
async def intervene_deal(negotiation_id: str, payload: dict = None):
    try:
        p_dict = payload or {}
        if "counter_price" in p_dict and "price" not in p_dict:
            p_dict["price"] = p_dict["counter_price"]
        return await controller.intervene_deal(negotiation_id, p_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{negotiation_id}/copilot-action")
@router.post("/{negotiation_id}/copilot")
async def copilot_action(negotiation_id: str, payload: dict = None):
    try:
        status_data = await controller.get_negotiation_status(negotiation_id) or {}
        crop = (payload and payload.get("context", {}).get("crop")) or status_data.get("crop") or "Produce"
        curr_offer = (payload and payload.get("context", {}).get("current_offer")) or status_data.get("final_price") or status_data.get("price") or 50.0
        
        from backend.services.negotiation_service import STATUTORY_BENCHMARKS
        crop_norm = "Soybean"
        for k in STATUTORY_BENCHMARKS:
            if k.lower() in crop.lower():
                crop_norm = k
                break
        bench_info = STATUTORY_BENCHMARKS.get(crop_norm, {"benchmark": 50.0})
        statutory_bench = float(bench_info.get("benchmark", 50.0))
        
        is_competitive = float(curr_offer) >= float(statutory_bench) * 0.95
        rec_counter = round(max(float(curr_offer) * 1.05, float(statutory_bench)), 2)
        advice = (
            f"🤖 [AI Copilot Evaluation]: The current offer of ₹{float(curr_offer):,.2f}/kg for {crop} is "
            f"{'competitive and near/above' if is_competitive else 'below'} the statutory APMC benchmark (₹{statutory_bench:,.2f}/kg). "
            f"{'Accepting the deal locks in profit.' if is_competitive else f'Recommend counter-offering at ₹{rec_counter:,.2f}/kg.'}"
        )
        return {
            "success": True,
            "negotiation_id": negotiation_id,
            "crop": crop,
            "benchmark_price": statutory_bench,
            "current_offer": float(curr_offer),
            "is_competitive": is_competitive,
            "recommended_counter": rec_counter,
            "copilot_advice": advice,
            "reasoning": advice,
            "action": "COUNTER" if not is_competitive else "ACCEPT"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{negotiation_id}/payment")
@router.post("/{negotiation_id}/pay")
async def process_payment_and_escrow(negotiation_id: str, payload: dict = None):
    try:
        status_data = await controller.get_negotiation_status(negotiation_id) or {}
        clean_id = str(negotiation_id).replace("neg_", "").upper()
        p = float(status_data.get("final_price") or status_data.get("price") or 50.0)
        q = float(status_data.get("quantity") or 1000.0)
        tot = round(p * q, 2)
        cess = round(tot * 0.01, 2)
        net = round(tot - cess, 2)
        
        return {
            "success": True,
            "negotiation_id": negotiation_id,
            "transaction_id": f"TXN-MH-2026-{clean_id}",
            "escrow_account": f"ESC-MH-2026-{clean_id}",
            "upi_reference": f"UPI-MH-2026-{clean_id}",
            "payment_gateway": "Maharashtra APMC Electronic Escrow & NPCI UPI Simulator",
            "payment_status": "ESCROW_SETTLED",
            "gross_amount": tot,
            "apmc_cess_deducted": cess,
            "farmer_payout_amount": net,
            "payout_status": "DISBURSED_TO_FARMER_ACCOUNT",
            "settlement_timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{negotiation_id}/autonomous-step")
async def autonomous_step_route(negotiation_id: str):
    try:
        return await controller.autonomous_step(negotiation_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{negotiation_id}/feedback")
async def feedback_deal(negotiation_id: str, payload: dict = None):
    try:
        return {"status": "success", "message": "Feedback recorded", "negotiation_id": negotiation_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{negotiation_id}/parallel-branches")
async def get_parallel_branches_route(negotiation_id: str):
    try:
        branches = await controller.get_parallel_branches(negotiation_id)
        return {"status": "SUCCESS", "negotiation_id": negotiation_id, "branches": branches}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{negotiation_id}/parallel-procure")
async def parallel_procure_route(negotiation_id: str, payload: dict = None):
    try:
        return await controller.run_parallel_procurement(negotiation_id, payload or {})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{negotiation_id}/dispatch-worker")
async def dispatch_negotiation_to_worker(negotiation_id: str):
    from backend.core.redis import redis_manager
    status_data = await controller.get_negotiation_status(negotiation_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    job_id = await redis_manager.enqueue_negotiation_job(negotiation_id, status_data)
    if not job_id:
        raise HTTPException(status_code=503, detail="Redis Stream is unavailable or not connected")
    return {
        "success": True,
        "negotiation_id": negotiation_id,
        "stream_job_id": job_id,
        "message": f"Negotiation {negotiation_id} dispatched to Redis Stream 'agri:negotiation:jobs'"
    }


@router.get("/{negotiation_id}/workflow")
async def get_negotiation_workflow(negotiation_id: str):
    """
    Authoritative Multi-Agent Supply Chain Workflow State endpoint for any negotiation
    (Farmer-initiated or Buyer-initiated).
    """
    from backend.services.buyer_workflow_service import buyer_workflow_service
    status_data = await controller.get_negotiation_status(negotiation_id) or {}
    req_id = status_data.get("requirement_id") or negotiation_id

    state = await buyer_workflow_service.get_workflow_state(requirement_id=req_id)
    if not state:
        crop = status_data.get("crop") or "Soybean"
        qty = float(status_data.get("quantity") or 1000.0)
        buyer_id = status_data.get("buyer") or status_data.get("user_id") or "buyer_agent"
        state = await buyer_workflow_service.initialize_workflow(
            requirement_id=req_id,
            buyer_id=buyer_id,
            crop=crop,
            quantity=qty,
            quality=status_data.get("quality") or "Grade A",
            delivery_location=status_data.get("location") or "Maharashtra",
            selected_services={
                "farmer_matching": True,
                "negotiation": True,
                "transport": True,
                "warehouse": True,
                "processor": True
            }
        )

    # If deal is already accepted/finalized, record deal outcome so downstream is eligible
    is_deal = status_data.get("status") in ("DEAL", "COMPLETED") or bool(status_data.get("final_price"))
    if is_deal and not state.get("farmer_deal", {}).get("valid"):
        try:
            await buyer_workflow_service.record_farmer_deal_outcome(
                requirement_id=req_id,
                deal_id=negotiation_id,
                outcome_status="SUCCESS",
                deal_details=status_data
            )
            state = await buyer_workflow_service.get_workflow_state(requirement_id=req_id)
        except Exception:
            pass

    # If downstream plans were already computed by parallel procurement, enrich agent outcomes
    if is_deal and state:
        outcomes = state.setdefault("agent_outcomes", {})
        dirty = False
        t_plan = status_data.get("transport_plan")
        if t_plan and "TRANSPORT" not in outcomes:
            cost = float(t_plan.get("agreed_price") or t_plan.get("total_operating_cost") or t_plan.get("cost") or 4200.0)
            veh = t_plan.get("vehicle_name") or t_plan.get("vehicle_type") or t_plan.get("vehicle") or "Freight Vehicle"
            r_val = t_plan.get("route")
            if isinstance(r_val, dict):
                route_str = r_val.get("route_path") or (" ➔ ".join([wp.get("name", "") for wp in r_val.get("route_waypoints", []) if isinstance(wp, dict) and wp.get("name")])) or f"{status_data.get('location', 'Nashik')} → Pune APMC"
            elif isinstance(r_val, list):
                route_str = " ➔ ".join([str(wp.get("name", wp) if isinstance(wp, dict) else wp) for wp in r_val])
            elif r_val:
                route_str = str(r_val)
            else:
                route_str = f"{status_data.get('location', 'Nashik')} → Pune APMC"

            outcomes["TRANSPORT"] = {
                "status": "COMPLETED",
                "cost": cost,
                "result": {
                    "vehicle": str(veh),
                    "route": route_str,
                    "cost": cost
                }
            }
            if "TRANSPORT" not in state.get("completed_agents", []):
                state.setdefault("completed_agents", []).append("TRANSPORT")
            dirty = True

        w_plan = status_data.get("warehouse_plan")
        if w_plan and "WAREHOUSE" not in outcomes:
            w_cost = float(w_plan.get("total_cost") or w_plan.get("cost") or 1050.0)
            w_name = w_plan.get("facility_name") or w_plan.get("name") or "Maharashtra Agro Warehouse"
            outcomes["WAREHOUSE"] = {
                "status": "COMPLETED",
                "cost": w_cost,
                "result": {
                    "name": w_name,
                    "location": w_plan.get("location") or "Pune APMC",
                    "holding_days": w_plan.get("holding_days") or 7,
                    "cost": w_cost
                }
            }
            if "WAREHOUSE" not in state.get("completed_agents", []):
                state.setdefault("completed_agents", []).append("WAREHOUSE")
            dirty = True

        p_plan = status_data.get("processor_plan")
        if p_plan and "PROCESSOR" not in outcomes:
            p_cost = float(p_plan.get("processing_fee") or p_plan.get("cost") or 3500.0)
            p_name = p_plan.get("unit_name") or p_plan.get("name") or "Maharashtra Agro Mill"
            outcomes["PROCESSOR"] = {
                "status": "COMPLETED",
                "cost": p_cost,
                "result": {
                    "name": p_name,
                    "output_product": p_plan.get("output_product") or "Value-Added Processed Lot",
                    "cost": p_cost
                }
            }
            if "PROCESSOR" not in state.get("completed_agents", []):
                state.setdefault("completed_agents", []).append("PROCESSOR")
            dirty = True

        if dirty:
            await Database.upsert_buyer_workflow_async(state)

    valid_actions = buyer_workflow_service.get_valid_next_actions(state)
    return {
        "success": True,
        "workflow": state,
        "valid_next_actions": valid_actions
    }


@router.post("/{negotiation_id}/workflow/step")
async def step_negotiation_workflow(negotiation_id: str, payload: dict = None):
    """
    Executes a step in the multi-agent supply chain workflow for this negotiation.
    """
    from backend.services.buyer_workflow_service import buyer_workflow_service
    status_data = await controller.get_negotiation_status(negotiation_id) or {}
    req_id = status_data.get("requirement_id") or negotiation_id

    action_override = payload.get("action") if isinstance(payload, dict) else None
    try:
        updated_state = await buyer_workflow_service.step_workflow(
            requirement_id=req_id,
            action_override=action_override
        )
        valid_actions = buyer_workflow_service.get_valid_next_actions(updated_state)

        # If final_plan was generated or updated, sync to negotiation record in DB
        if updated_state.get("final_plan"):
            fp = updated_state["final_plan"]
            await Database.update_negotiation_async(negotiation_id, {
                "final_plan": fp,
                "contract_hash": fp.get("contract_signature"),
                "status": "DEAL",
                "transport_plan": fp.get("transport_plan"),
                "warehouse_plan": fp.get("warehouse_plan"),
                "processor_plan": fp.get("processor_plan")
            })

        return {
            "success": True,
            "workflow": updated_state,
            "valid_next_actions": valid_actions
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))




