"""
backend/services/negotiation_memory_service.py
------------------------------------------------------------------------
Intelligent Negotiation Memory & Adaptive Bidding Service for FarmGenAI Buyer Agent.

Capabilities:
  1. Strict Buyer Data Isolation: Queries historical negotiations filtered strictly by buyer_id.
  2. Historical Experience Retrieval: Gathers past round progressions, concessions, agreed prices, and failure reasons.
  3. Dynamic Bidding Strategy Adaptation:
     - Calibrates opening bid based on prior deal outcomes vs statutory/mandi benchmarks.
     - Recommends concession schedule (Boulware, Linear, Conceder, Aggressive) based on past supplier flexibility.
     - Prevents blindly copying past prices by benchmarking against current spot market conditions.
  4. Deterministic Guardrails:
     - Never allows memory recommendations or LLM suggestions to exceed buyer reservation ceiling (P_max) or budget.
     - Enforces mathematical floor and walk-away conditions.
  5. Persistent Storage:
     - Persists negotiation events, round progression, counteroffers, and final contracts in the PostgreSQL 'negotiations' table.
"""

import math
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from sqlalchemy import text
from database.db import AsyncSessionLocal
from shared.crop_catalog import (
    BUYER_SUPPORTED_CROPS,
    normalize_crop_name,
    is_supported_buyer_crop,
    get_crop_benchmark_info
)

logger = logging.getLogger("NegotiationMemoryService")


class NegotiationMemoryService:
    """
    Provides isolated historical memory retrieval and adaptive bidding calibration
    for autonomous and copilot-assisted buyer agents.
    """

    @classmethod
    async def get_buyer_negotiation_history(
        cls,
        buyer_id: str,
        crop: Optional[str] = None,
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Retrieves past negotiations for a specific buyer from PostgreSQL.
        Strictly isolates data to the requested buyer_id (or user_id).
        """
        if not buyer_id:
            return []

        norm_crop = normalize_crop_name(crop) if crop else None

        query_str = """
            SELECT 
                negotiation_id,
                crop,
                quantity,
                farmer_name,
                status,
                current_round,
                final_price,
                market_price,
                min_price,
                logs,
                summary
            FROM negotiations
            WHERE (buyer_id = :buyer_id OR user_id = :buyer_id)
        """
        params: Dict[str, Any] = {"buyer_id": str(buyer_id)}

        if norm_crop:
            query_str += " AND (LOWER(crop) = LOWER(:crop))"
            params["crop"] = norm_crop

        query_str += " ORDER BY negotiation_id DESC LIMIT :limit;"
        params["limit"] = limit

        results = []
        try:
            async with AsyncSessionLocal() as session:
                rows = await session.execute(text(query_str), params)
                for r in rows.fetchall():
                    results.append({
                        "negotiation_id": r[0],
                        "crop": r[1],
                        "quantity": float(r[2]) if r[2] is not None else 0.0,
                        "farmer_name": r[3] or "APMC Supplier",
                        "status": str(r[4] or "UNKNOWN").upper(),
                        "rounds_completed": int(r[5] or 1),
                        "final_price": float(r[6]) if r[6] is not None else None,
                        "market_price": float(r[7]) if r[7] is not None else None,
                        "supplier_min_price": float(r[8]) if r[8] is not None else None,
                        "has_logs": bool(r[9]),
                        "summary": r[10] or ""
                    })
        except Exception as e:
            logger.warning(f"Error querying buyer negotiation history: {e}")

        return results

    @classmethod
    async def calibrate_adaptive_strategy(
        cls,
        buyer_id: str,
        crop: str,
        target_price: float,
        reservation_price: float,
        current_market_price: float,
        budget: float,
        quantity: float
    ) -> Dict[str, Any]:
        """
        Analyzes buyer historical memory to calibrate opening bid and concession curve.
        Enforces strict deterministic boundaries:
          1. opening_bid <= target_price
          2. target_price <= reservation_price (P_max)
          3. Total procurement cost (opening_bid * quantity) <= budget
        """
        norm_crop = normalize_crop_name(crop) or crop
        history = await cls.get_buyer_negotiation_history(buyer_id=buyer_id, crop=norm_crop, limit=20)

        # Baseline parameters
        opening_bid = round(target_price * 0.90, 2)
        recommended_strategy = "balanced"
        concession_rate = 0.20
        historical_deals_found = 0
        accepted_deals = []
        rejected_deals = []

        for h in history:
            st = h.get("status")
            fp = h.get("final_price")
            if st in ("ACCEPTED", "DEAL", "SETTLED") and fp is not None and fp > 0:
                accepted_deals.append(fp)
            elif st in ("REJECTED", "FAILED", "NO_EXECUTABLE_DEAL", "STALLED"):
                rejected_deals.append(h)

        historical_deals_found = len(accepted_deals) + len(rejected_deals)
        memory_insights = []

        if accepted_deals:
            avg_past_deal = sum(accepted_deals) / len(accepted_deals)
            memory_insights.append(
                f"Historical memory found {len(accepted_deals)} past deals for {norm_crop} with average agreed price of ₹{avg_past_deal:.2f}/kg."
            )

            # If historical prices were significantly below current market, be more conservative
            if avg_past_deal < target_price:
                # Prior success at lower prices -> Use Boulware strategy (concede slowly)
                recommended_strategy = "boulware"
                concession_rate = 0.12
                # Anchor opening bid between historical average and current target
                opening_bid = round(max(target_price * 0.85, (avg_past_deal + target_price) / 2 * 0.92), 2)
                memory_insights.append(
                    f"Prior buyer success at lower price (avg ₹{avg_past_deal:.2f}/kg) informs Boulware tactic: opening at ₹{opening_bid:.2f}/kg with slow concessions."
                )
            else:
                # Past deals required paying near or above target -> Concede more moderately
                recommended_strategy = "linear"
                concession_rate = 0.22
                opening_bid = round(target_price * 0.92, 2)
                memory_insights.append(
                    f"Past settlements clustered near ₹{avg_past_deal:.2f}/kg; calibrated opening bid to ₹{opening_bid:.2f}/kg with Linear schedule."
                )
        elif rejected_deals:
            # All past deals were rejected -> might have been bidding too low
            recommended_strategy = "conceder"
            concession_rate = 0.30
            opening_bid = round(target_price * 0.94, 2)
            memory_insights.append(
                f"Previous {len(rejected_deals)} negotiations stalled/failed. Adjusting opening bid higher to ₹{opening_bid:.2f}/kg with Conceder schedule to reach consensus."
            )
        else:
            # Cold start (no buyer history on this crop) -> Use APMC statutory benchmark
            benchmark = get_crop_benchmark_info(norm_crop)
            bench_price = benchmark.get("benchmark_price", current_market_price)
            recommended_strategy = "balanced"
            concession_rate = 0.20
            opening_bid = round(min(target_price * 0.90, bench_price * 0.95), 2)
            memory_insights.append(
                f"No prior negotiation records for buyer '{buyer_id}' on {norm_crop}. Initializing cold-start baseline using APMC benchmark (₹{bench_price:.2f}/kg)."
            )

        # Enforce deterministic price boundaries
        max_allowed_bid = min(reservation_price, budget / max(1.0, quantity))
        opening_bid = max(1.0, min(opening_bid, target_price, max_allowed_bid))
        walk_away_price = reservation_price

        return {
            "buyer_id": buyer_id,
            "crop": norm_crop,
            "historical_records_count": historical_deals_found,
            "past_accepted_count": len(accepted_deals),
            "past_rejected_count": len(rejected_deals),
            "recommended_strategy": recommended_strategy,
            "concession_rate": concession_rate,
            "calibrated_opening_bid": opening_bid,
            "target_price": target_price,
            "reservation_ceiling_pmax": walk_away_price,
            "budget_limit_per_kg": round(budget / max(1.0, quantity), 2),
            "memory_insights": memory_insights,
            "deterministic_guardrail_applied": bool(opening_bid >= max_allowed_bid),
        }

    @classmethod
    async def persist_negotiation_record(
        cls,
        negotiation_id: str,
        buyer_id: str,
        crop: str,
        quantity: float,
        farmer_name: str,
        status: str,
        current_round: int,
        final_price: Optional[float],
        market_price: float,
        min_price: Optional[float],
        logs: List[Any],
        summary: str,
        transport_plan: Optional[str] = None
    ) -> bool:
        """
        Persists full negotiation audit trail into the PostgreSQL 'negotiations' table.
        Ensures idempotent insertion or update.
        """
        try:
            async with AsyncSessionLocal() as session:
                # Check if negotiation already exists
                check_stmt = text("SELECT negotiation_id FROM negotiations WHERE negotiation_id = :nid;")
                row = await session.execute(check_stmt, {"nid": negotiation_id})
                existing = row.fetchone()

                if existing:
                    update_stmt = text("""
                        UPDATE negotiations SET
                            crop = :crop,
                            quantity = :quantity,
                            buyer_id = :buyer_id,
                            farmer_name = :farmer_name,
                            status = :status,
                            current_round = :current_round,
                            final_price = :final_price,
                            market_price = :market_price,
                            min_price = :min_price,
                            logs = :logs,
                            summary = :summary,
                            transport_plan = :transport_plan
                        WHERE negotiation_id = :nid;
                    """)
                    await session.execute(update_stmt, {
                        "nid": negotiation_id,
                        "crop": crop,
                        "quantity": quantity,
                        "buyer_id": buyer_id,
                        "farmer_name": farmer_name,
                        "status": status,
                        "current_round": current_round,
                        "final_price": final_price,
                        "market_price": market_price,
                        "min_price": min_price,
                        "logs": json.dumps(logs) if logs else "[]",
                        "summary": summary,
                        "transport_plan": transport_plan
                    })
                else:
                    insert_stmt = text("""
                        INSERT INTO negotiations (
                            negotiation_id,
                            crop,
                            quantity,
                            buyer_id,
                            user_id,
                            farmer_name,
                            status,
                            current_round,
                            final_price,
                            market_price,
                            min_price,
                            logs,
                            summary,
                            transport_plan
                        ) VALUES (
                            :nid,
                            :crop,
                            :quantity,
                            :buyer_id,
                            :buyer_id,
                            :farmer_name,
                            :status,
                            :current_round,
                            :final_price,
                            :market_price,
                            :min_price,
                            :logs,
                            :summary,
                            :transport_plan
                        );
                    """)
                    await session.execute(insert_stmt, {
                        "nid": negotiation_id,
                        "crop": crop,
                        "quantity": quantity,
                        "buyer_id": buyer_id,
                        "farmer_name": farmer_name,
                        "status": status,
                        "current_round": current_round,
                        "final_price": final_price,
                        "market_price": market_price,
                        "min_price": min_price,
                        "logs": json.dumps(logs) if logs else "[]",
                        "summary": summary,
                        "transport_plan": transport_plan
                    })

                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to persist negotiation record {negotiation_id}: {e}")
            return False

