"""Mercado Libre Perú: API pública de búsqueda."""
import requests

from scraper.models import Offer, contiene_marca

TIENDA = "MercadoLibre"
API = "https://api.mercadolibre.com/sites/MPE/search"


def get_offers(query: str, marca: str, limit: int = 5) -> list[Offer]:
    r = requests.get(API, params={"q": query, "limit": 20}, timeout=15)
    r.raise_for_status()
    out = []
    for it in r.json().get("results", []):
        titulo = it.get("title", "")
        if not contiene_marca(titulo, marca) or it.get("price") is None:
            continue
        out.append(Offer(TIENDA, titulo, float(it["price"]), it.get("currency_id", "PEN"), it.get("permalink", "")))
        if len(out) >= limit:
            break
    return out
