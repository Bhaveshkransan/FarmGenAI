from fastapi import APIRouter, Body, HTTPException, Depends
from ..services.storage_service import assign_storage, list_warehouses
from ..services.transport_service import assign_transport, list_fleet
from backend.services.security import get_current_user_optional

router = APIRouter()

@router.get("/list")
async def get_warehouses(current_user: dict = Depends(get_current_user_optional)):
    warehouses = await list_warehouses()
    total_capacity = sum(warehouse["capacity_kg"] for warehouse in warehouses)
    used_capacity = sum(warehouse["used_capacity_kg"] for warehouse in warehouses)
    return {
        "warehouses": warehouses,
        "summary": {
            "total_capacity_kg": round(total_capacity, 2),
            "used_capacity_kg": round(used_capacity, 2),
            "available_capacity_kg": round(total_capacity - used_capacity, 2),
        },
    }


@router.post("/book")
async def assign_storage_route(payload: dict = Body(...), current_user: dict = Depends(get_current_user_optional)):
    try:
        assignment = await assign_storage(payload)
        return assignment
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/assign-transport")
async def assign_transport_route(payload: dict = Body(...), current_user: dict = Depends(get_current_user_optional)):
    try:
        assignment = await assign_transport(payload)
        return assignment
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/fleet")
async def get_transport_fleet(current_user: dict = Depends(get_current_user_optional)):
    return {"fleet": list_fleet()}
