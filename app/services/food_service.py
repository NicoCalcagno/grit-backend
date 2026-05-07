import time
from typing import Any, Dict, List, Optional

import httpx

BASE_URL = "https://world.openfoodfacts.org"
_cache: Dict[str, tuple[Any, float]] = {}
CACHE_TTL = 3600  # 1 ora


def _parse_product(product: Dict) -> Optional[Dict]:
    nutriments = product.get("nutriments", {})
    name = product.get("product_name") or product.get("product_name_it") or ""
    if not name:
        return None
    return {
        "barcode": product.get("code"),
        "name": name,
        "brand": product.get("brands"),
        "calories_per_100g": nutriments.get("energy-kcal_100g") or nutriments.get("energy_100g"),
        "protein_per_100g": nutriments.get("proteins_100g"),
        "carbs_per_100g": nutriments.get("carbohydrates_100g"),
        "fat_per_100g": nutriments.get("fat_100g"),
    }


async def get_by_barcode(barcode: str) -> Optional[Dict]:
    cache_key = f"barcode:{barcode}"
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[1] < CACHE_TTL:
        return cached[0]

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BASE_URL}/api/v0/product/{barcode}.json")
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") != 1:
        return None

    result = _parse_product(data.get("product", {}))
    if result:
        _cache[cache_key] = (result, time.time())
    return result


async def search_food(query: str, page_size: int = 20) -> List[Dict]:
    cache_key = f"search:{query}"
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[1] < CACHE_TTL:
        return cached[0]

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{BASE_URL}/cgi/search.pl",
            params={
                "search_terms": query,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": page_size,
                "fields": "code,product_name,product_name_it,brands,nutriments",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    products = data.get("products", [])
    results = [p for p in (_parse_product(prod) for prod in products) if p]
    _cache[cache_key] = (results, time.time())
    return results
