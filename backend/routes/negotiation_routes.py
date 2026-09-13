from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.v1.dependencies import get_db
from backend.core.exceptions import AppException, NotFoundException
from backend.services.negotiation_service import NegotiationService, start_negotiation as service_start_negotiation
from ..schemas.negotiation_model import StartNegotiationRequest

router = APIRouter()

@router.get("/debug")
async def debug():
    from agents.farmer_agent import FarmerAgent
    import inspect
    return {
        "file": inspect.getfile(FarmerAgent),
        "signature": str(inspect.signature(FarmerAgent.__init__))
    }

@router.post("/")
async def start_negotiation(
    request: StartNegotiationRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await service_start_negotiation(request.model_dump(), scenario="direct-sale", db=db)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise AppException(message=str(e), error_code="NEGOTIATION_START_FAILED")

@router.get("/{negotiation_id}")
async def get_negotiation_status(
    negotiation_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        status = await NegotiationService(db).get_negotiation_status(negotiation_id)
        if not status:
            raise NotFoundException(resource="Negotiation")
        return status
    except AppException:
        raise
    except Exception as e:
        raise AppException(message=str(e), error_code="NEGOTIATION_STATUS_FAILED")

@router.get("/agents/")
async def get_agents(db: AsyncSession = Depends(get_db)):
    try:
        return {"agents": await NegotiationService(db).list_agents()}
    except Exception as e:
        raise AppException(message=str(e), error_code="AGENTS_FETCH_FAILED")


@router.post("/{negotiation_id}/accept")
async def accept_negotiation(
    negotiation_id: str,
    payload: dict = {},
    db: AsyncSession = Depends(get_db)
):
    """Farmer manually accepts a deal. Updates status to DEAL."""
    try:
        service = NegotiationService(db)
        final_price = payload.get("final_price") if payload else None
        update = {"status": "DEAL"}
        if final_price:
            update["final_price"] = float(final_price)
        await service.db_repo.update_negotiation_async(negotiation_id, update)
        return {"success": True, "negotiation_id": negotiation_id, "status": "DEAL"}
    except Exception as e:
        raise AppException(message=str(e), error_code="ACCEPT_FAILED")


@router.post("/{negotiation_id}/reject")
async def reject_negotiation(
    negotiation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Farmer rejects the current deal. Updates status to NO_DEAL."""
    try:
        service = NegotiationService(db)
        await service.db_repo.update_negotiation_async(negotiation_id, {"status": "NO_DEAL"})
        return {"success": True, "negotiation_id": negotiation_id, "status": "NO_DEAL"}
    except Exception as e:
        raise AppException(message=str(e), error_code="REJECT_FAILED")


@router.post("/{negotiation_id}/intervene")
async def intervene_negotiation(
    negotiation_id: str,
    payload: dict = {},
    db: AsyncSession = Depends(get_db)
):
    """Farmer manually overrides the AI with a custom offer price."""
    try:
        service = NegotiationService(db)
        override_price = payload.get("override_price") if payload else None
        if override_price is None:
            raise AppException(message="override_price is required", error_code="INVALID_PAYLOAD")
        row = await service.db_repo.get_negotiation_async(negotiation_id)
        if not row:
            raise NotFoundException(resource="Negotiation")
        # Append as a new offer round
        current_offers = await service.db_repo.get_offers_for_negotiation_async(negotiation_id)
        next_round = len(current_offers) + 1
        await service.db_repo.append_offer_async(negotiation_id, {
            "round": next_round,
            "sender": "Farmer (Manual)",
            "price": float(override_price),
            "quantity": row.get("quantity", 0),
            "message": f"Manual intervention: Farmer offers ₹{override_price}/kg"
        })
        return {"success": True, "negotiation_id": negotiation_id, "override_price": override_price, "round": next_round}
    except AppException:
        raise
    except Exception as e:
        raise AppException(message=str(e), error_code="INTERVENE_FAILED")
