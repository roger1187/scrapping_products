"""Web oficial de la marca: abre brand_url del YAML con Playwright y lee el precio.

Verificado en nov-2026 con Kyte Baby, Little Sleepies, Posh Peanut, Solly Baby y Freshly Picked (Shopify): el
precio está en <meta property="og:price:amount"> y en el JSON-LD Product/offers (con disponibilidad).
Requests directos reciben un desafío anti-bot (403); el navegador lo pasa. Respeta robots.txt y 1 request/seg.
"""
import json
import time
import urllib.robotparser
from urllib.parse import urljoin, urlparse

from scraper import navegador
from scraper.models import Offer

CAMPO = "brand_url"          # main.py le pasa producto["brand_url"] en lugar del texto de búsqueda
PAUSA_SEG = 1.0
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
_ultimo = 0.0


def _permitido(url: str) -> bool:
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    if base not in _robots:
        rp = None
        try:
            r = navegador.contexto().request.get(urljoin(base, "/robots.txt"), timeout=15000)
            if r.ok:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(r.text().splitlines())
        except Exception:
            pass
        _robots[base] = rp
    rp = _robots[base]
    return rp is None or rp.can_fetch(navegador.UA, url)


def _pausa() -> None:
    global _ultimo
    espera = PAUSA_SEG - (time.monotonic() - _ultimo)
    if espera > 0:
        time.sleep(espera)
    _ultimo = time.monotonic()


def get_offers(brand_url: str, marca: str) -> list[Offer]:
    if not _permitido(brand_url):
        raise RuntimeError(f"robots.txt no permite {brand_url}")
    _pausa()
    page = navegador.contexto().new_page()
    try:
        page.goto(brand_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)   # deja pasar el desafío anti-bot
        datos = page.evaluate("""() => ({
            titulo: document.querySelector('meta[property="og:title"]')?.content || document.title,
            og_precio: document.querySelector('meta[property="og:price:amount"]')?.content || null,
            og_moneda: document.querySelector('meta[property="og:price:currency"]')?.content || null,
            ld: [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => s.textContent),
            url: location.href,
        })""")
    finally:
        page.close()
    return parse(datos, marca)


def _productos_ld(textos: list[str]) -> list[dict]:
    out = []
    for t in textos:
        try:
            d = json.loads(t)
        except ValueError:
            continue
        for x in d if isinstance(d, list) else [d]:
            for y in x.get("@graph", [x]) if isinstance(x, dict) else []:
                if isinstance(y, dict) and y.get("@type") in ("Product", "ProductGroup"):
                    out.append(y)
    return out


def _ofertas_ld(prod: dict) -> list[dict]:
    ofertas = prod.get("offers") or [v.get("offers") for v in prod.get("hasVariant", [])]
    plano = []
    for o in ofertas if isinstance(ofertas, list) else [ofertas]:
        plano += o if isinstance(o, list) else [o] if o else []
    return [o for o in plano if isinstance(o, dict)]


def parse(datos: dict, marca: str) -> list[Offer]:
    """Precio más bajo en stock del JSON-LD; si no hay JSON-LD, og:price. Agotado = sin oferta."""
    titulo = datos.get("titulo") or ""
    if marca.lower() not in titulo.lower():
        titulo = f"{marca} {titulo}"
    url = datos.get("url") or ""
    tienda = f"{marca} (sitio oficial)"

    prods = _productos_ld(datos.get("ld") or [])
    ofertas = [o for p in prods for o in _ofertas_ld(p)]
    if ofertas:
        en_stock = [o for o in ofertas if "OutOfStock" not in str(o.get("availability", ""))
                    and (o.get("price") or o.get("lowPrice")) is not None
                    and (o.get("priceCurrency") or "USD") == "USD"]
        if not en_stock:
            return []
        precio = min(float(o.get("price") or o.get("lowPrice")) for o in en_stock)
        return [Offer(tienda, titulo, precio, "USD", url)]
    if datos.get("og_precio") and (datos.get("og_moneda") or "USD") == "USD":
        return [Offer(tienda, titulo, float(str(datos["og_precio"]).replace(",", "")), "USD", url)]
    return []
