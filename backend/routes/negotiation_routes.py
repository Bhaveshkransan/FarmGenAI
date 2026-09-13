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

