"""Google Shopping vía SerpAPI: agregador principal, trae precios de decenas de tiendas de EE.UU. en una búsqueda.

Necesita SERPAPI_KEY. El plan gratis da 100 búsquedas/mes, así que esta fuente tiene cupo diario
(SERPAPI_MAX_DIARIO, default 3 ≈ 90/mes) y rota los productos; ver scraper/cuota.py.
"""
import os

import requests

from scraper.models import Offer, normalizar_tienda

TIENDA = "Google Shopping"
API = "https://serpapi.com/search.json"

ENV_MAX_DIARIO = "SERPAPI_MAX_DIARIO"
MAX_DIARIO_DEFAULT = 3
MAX_DIAS_CACHE = 14


def disponible() -> bool:
    return bool(os.getenv("SERPAPI_KEY"))


def get_offers(query: str, marca: str, limit: int = 40) -> list[Offer]:
    # Los errores de requests incluyen la URL, que lleva api_key: se relanzan sin ella para no filtrarla en logs.
    try:
        r = requests.get(
            API,
            params={"engine": "google_shopping", "q": query, "gl": "us", "hl": "en",
                    "api_key": os.environ["SERPAPI_KEY"]},
            timeout=30,
        )
        datos = r.json()
    except (requests.RequestException, ValueError) as e:
        raise RuntimeError(f"SerpAPI sin respuesta válida ({type(e).__name__})") from None
    if r.status_code != 200 and not datos.get("error"):
        raise RuntimeError(f"SerpAPI HTTP {r.status_code}")
    if datos.get("error"):
        # "Google hasn't returned any results" no es un fallo de la fuente; el resto sí
        if "hasn't returned any results" in datos["error"]:
            return []
        raise RuntimeError(f"SerpAPI: {datos['error']}")
    return parse(datos, limit)


def parse(datos: dict, limit: int = 40) -> list[Offer]:
    """Convierte la respuesta JSON de SerpAPI en ofertas (la relevancia se filtra después, en compare)."""
    out = []
    for it in datos.get("shopping_results", []) + datos.get("inline_shopping_results", []):
        precio = it.get("extracted_price")
        if precio is None:
            continue
        envio = (it.get("delivery") or "").lower()
        out.append(Offer(
            tienda=normalizar_tienda(it.get("source", "")),
            titulo=it.get("title", ""),
            precio=float(precio),
            moneda="USD",
            url=it.get("link") or it.get("product_link") or "",
            envio_gratis="free" in envio,
            condicion=(it.get("second_hand_condition") or "new").lower(),
            nota=it.get("tag") or "",
        ))
        if len(out) >= limit:
            break
    return out
