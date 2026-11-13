"""Mercado Libre Perú: API de búsqueda.

Desde 2025 la API puede responder 401/403 sin token. Si existen ML_CLIENT_ID y ML_CLIENT_SECRET se pide un
token de aplicación (client_credentials) y se reintenta. Pendiente para cuando haya red: fallback a scraping de
listado.mercadolibre.com.pe (no se implementa a ciegas sin poder verificar los selectores).
"""
import os

import requests

from scraper.models import Offer

TIENDA = "MercadoLibre"
API = "https://api.mercadolibre.com/sites/MPE/search"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
_token: str | None = None


def _obtener_token() -> str | None:
    global _token
    cid, secret = os.getenv("ML_CLIENT_ID"), os.getenv("ML_CLIENT_SECRET")
    if _token or not (cid and secret):
        return _token
    r = requests.post(TOKEN_URL, data={"grant_type": "client_credentials", "client_id": cid,
                                       "client_secret": secret}, timeout=15)
    r.raise_for_status()
    _token = r.json()["access_token"]
    return _token


def get_offers(query: str, marca: str, limit: int = 20) -> list[Offer]:
    params = {"q": query, "limit": limit, "condition": "new"}
    r = requests.get(API, params=params, timeout=15)
    if r.status_code in (401, 403):
        token = _obtener_token()
        if not token:
            raise RuntimeError(f"HTTP {r.status_code}: la API pide token; configura ML_CLIENT_ID y ML_CLIENT_SECRET")
        r = requests.get(API, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    r.raise_for_status()
    return parse(r.json())


def parse(datos: dict) -> list[Offer]:
    out = []
    for it in datos.get("results", []):
        if it.get("price") is None:
            continue
        out.append(Offer(
            TIENDA, it.get("title", ""), float(it["price"]), it.get("currency_id", "PEN"), it.get("permalink", ""),
            envio_gratis=bool((it.get("shipping") or {}).get("free_shipping")),
            condicion=it.get("condition") or "new",
        ))
    return out   # la relevancia (marca, usados) se filtra en compare
