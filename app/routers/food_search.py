import logging

from fastapi import APIRouter, HTTPException, Query

from app.services import food_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/food", tags=["food-search"])


@router.get("/barcode/{barcode}")
async def get_by_barcode(barcode: str):
    try:
        result = await food_service.get_by_barcode(barcode)
    except Exception as e:
        logger.error("Open Food Facts barcode error: %s", e)
        raise HTTPException(status_code=502, detail="Errore Open Food Facts")
    if not result:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")
    return result


@router.get("/search")
async def search_food(q: str = Query(..., min_length=2)):
    try:
        results = await food_service.search_food(q)
    except Exception as e:
        logger.error("Open Food Facts search error for '%s': %s", q, e)
        raise HTTPException(status_code=502, detail="Errore Open Food Facts")
    return {"results": results, "count": len(results)}
