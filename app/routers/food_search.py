from fastapi import APIRouter, HTTPException, Query

from app.services import food_service

router = APIRouter(prefix="/food", tags=["food-search"])


@router.get("/barcode/{barcode}")
async def get_by_barcode(barcode: str):
    try:
        result = await food_service.get_by_barcode(barcode)
    except Exception:
        raise HTTPException(status_code=502, detail="Errore Open Food Facts")
    if not result:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")
    return result


@router.get("/search")
async def search_food(q: str = Query(..., min_length=2)):
    try:
        results = await food_service.search_food(q)
    except Exception:
        raise HTTPException(status_code=502, detail="Errore Open Food Facts")
    return {"results": results, "count": len(results)}
