"""
backend/routes/rag_routes.py

API endpoints for querying the RAG knowledge base.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from backend.services.security import get_current_user_optional
from backend.services.rag_service import rag_service
import asyncio

router = APIRouter(tags=["RAG"])

@router.get("/query")
async def query_rag(
    q: str = Query(..., description="Query string"),
    collection: str = Query("market_prices", description="Collection name to query"),
    limit: int = Query(3, description="Max results"),
    crop: str = Query(None, description="Filter by crop"),
    current_user: dict = Depends(get_current_user_optional)
):
    """Query a specific RAG collection."""
    try:
        if collection == "market_prices":
            res = await rag_service.query_mandi_records(q, n_results=limit, crop=crop)
        elif collection == "reflection_memory":
            res = await rag_service.query_strategies(q, n_results=limit, crop=crop)
        elif collection == "crop_knowledge":
            docs = rag_service.query_crop_knowledge(q, crop=crop, n_results=limit)
            return {"success": True, "data": docs}
        else:
            res = rag_service.query_collection(collection, q, limit)
            
        formatted = []
        if isinstance(res, dict) and "documents" in res:
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            for i in range(len(docs)):
                formatted.append({
                    "text": docs[i],
                    "metadata": metas[i] if i < len(metas) else {}
                })
        else:
            formatted = res
            
        return {"success": True, "data": formatted}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
