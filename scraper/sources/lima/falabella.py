"""Falabella Perú: la búsqueda trae los resultados en el JSON __NEXT_DATA__ del HTML (verificado nov-2026).

No hace falta Playwright. Se toma el menor precio no tachado, sin contar el precio exclusivo con tarjeta CMR.
"""
import json
import re

import requests

from scraper.models import Offer

TIENDA = "Falabella"
URL = "https://www.falabella.com.pe/falabella-pe/search"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
EXCLUIR = {"cmrPrice"}   # requiere tarjeta Falabella


def get_offers(query: str, marca: str, limit: int = 20) -> list[Offer]:
    r = requests.get(URL, params={"Ntt": query}, headers={"User-Agent": UA, "Accept-Language": "es-PE,es;q=0.9"},
                     timeout=25)
    r.raise_for_status()
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        raise RuntimeError("la página no trae __NEXT_DATA__ (¿cambió el sitio o hubo bloqueo?)")
    return parse(json.loads(m.group(1)), limit)


def _precio(texto: str) -> float:
    return float(str(texto).replace(",", ""))


def parse(datos: dict, limit: int = 20) -> list[Offer]:
    out = []
    for r in (datos.get("props", {}).get("pageProps", {}).get("results") or [])[:limit]:
        precios = [_precio(p["price"][0]) for p in r.get("prices", [])
                   if not p.get("crossed") and p.get("type") not in EXCLUIR and p.get("price")]
        if not precios:
            continue
        titulo = f"{r.get('brand', '')} {r.get('displayName', '')}".strip()
        nota = r.get("sellerName") or ""
        out.append(Offer(TIENDA, titulo, min(precios), "PEN", r.get("url", ""),
                         nota=f"vende {nota}" if nota and nota != "Falabella" else ""))
    return out
