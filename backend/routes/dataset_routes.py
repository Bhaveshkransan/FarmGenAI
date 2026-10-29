"""
API Routes for Dataset Inventory and Relational Join Operations (Phase 8)
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from backend.services.dataset_join_service import DatasetJoinService

router = APIRouter(prefix="/datasets", tags=["Datasets & Relational Joins"])
join_service = DatasetJoinService()


class JoinRequest(BaseModel):
    dataset_a: str = Field(..., description="Filename of Dataset A (e.g., 'synthetic_produce_listings.json')")
    dataset_b: str = Field(..., description="Filename of Dataset B (e.g., 'synthetic_farmers.json')")
    join_keys_a: List[str] = Field(..., min_items=2, max_items=4, description="2 to 4 composite key columns in Dataset A")
    join_keys_b: List[str] = Field(..., min_items=2, max_items=4, description="2 to 4 composite key columns in Dataset B")
    join_type: str = Field("left", description="'left' or 'right'")
    normalize_text: bool = Field(False, description="Trim whitespace and lowercase strings before matching")
    limit: Optional[int] = Field(50, description="Max preview rows to return")
    save_output: bool = Field(False, description="Persist joined dataset to storage with audit log")


@router.get("/inventory", summary="Audit and list all datasets in repository")
async def get_dataset_inventory():
    """Returns detailed schema, row counts, candidate keys, and provenance for all datasets."""
    try:
        inv = join_service.get_inventory()
        return {
            "status": "SUCCESS",
            "total_datasets": len(inv),
            "datasets": inv
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate dataset inventory: {str(e)}")


@router.post("/join/preview", summary="Preview composite join with cardinality & multiplication checks")
async def preview_dataset_join(req: JoinRequest):
    """
    Simulates composite join across 2-4 keys.
    Audits matched/unmatched records, cardinality (1:1, 1:N, M:N), and warns on row multiplication.
    Never mutates original source datasets.
    """
    try:
        result = join_service.execute_join(
            dataset_a_name=req.dataset_a,
            dataset_b_name=req.dataset_b,
            join_keys_a=req.join_keys_a,
            join_keys_b=req.join_keys_b,
            join_type=req.join_type,
            normalize_text=req.normalize_text,
            limit_preview=req.limit or 25,
            save_output=False
        )
        return result
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Join execution error: {str(e)}")


@router.post("/join/execute", summary="Execute and optionally persist joined dataset")
async def execute_dataset_join(req: JoinRequest):
    """
    Executes full composite join, generating an immutable output artifact without touching source files.
    """
    try:
        result = join_service.execute_join(
            dataset_a_name=req.dataset_a,
            dataset_b_name=req.dataset_b,
            join_keys_a=req.join_keys_a,
            join_keys_b=req.join_keys_b,
            join_type=req.join_type,
            normalize_text=req.normalize_text,
            limit_preview=req.limit,
            save_output=req.save_output
        )
        return result
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Join execution error: {str(e)}")
