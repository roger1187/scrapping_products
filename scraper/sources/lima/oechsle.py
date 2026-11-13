"""Oechsle: tienda VTEX con API pública de catálogo (verificado nov-2026); no hace falta Playwright."""
from urllib.parse import quote

import requests

from scraper.models import Offer

TIENDA = "Oechsle"
API = "https://www.oechsle.pe/api/catalog_system/pub/products/search"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def get_offers(query: str, marca: str, limit: int = 20) -> list[Offer]:
    # VTEX rechaza (400) los espacios codificados como "+": se arma la URL con %20
    r = requests.get(f"{API}?ft={quote(query)}&_from=0&_to={limit - 1}", headers={"User-Agent": UA}, timeout=20)
    if r.status_code not in (200, 206):   # VTEX responde 206 en búsquedas paginadas
        r.raise_for_status()
    return parse(r.json())


def parse(datos: list) -> list[Offer]:
    out = []
    for p in datos:
        mejor = None
        for item in p.get("items", []):
            for s in item.get("sellers", []):
                o = s.get("commertialOffer", {})
                if o.get("AvailableQuantity", 0) > 0 and o.get("Price"):
                    mejor = o["Price"] if mejor is None else min(mejor, o["Price"])
        if mejor is None:
            continue
        titulo = p.get("productName", "")
        if p.get("brand") and p["brand"].lower() not in titulo.lower():
            titulo = f"{p['brand']} {titulo}"
        out.append(Offer(TIENDA, titulo, float(mejor), "PEN", p.get("link", "")))
    return out
