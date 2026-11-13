"""Amazon.com: scraping de la página de búsqueda.

Amazon limita la frecuencia (HTTP 503 "automated access") o pide captcha. Se reintenta con espera; tras 3 productos
seguidos bloqueados la fuente se desactiva por el resto de la corrida (el job tiene 25 min).
Estructura verificada en nov-2026: cada resultado tiene un <h2> con la marca (a-size-mini) y otro con el título
(a-text-normal, con aria-label). Pendiente: Keepa (KEEPA_API_KEY).
"""
import random
import re
import time

import requests
from bs4 import BeautifulSoup

from scraper.models import Offer

TIENDA = "Amazon"
UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
]
_bloqueado = False
_fallos_seguidos = 0
MAX_FALLOS_SEGUIDOS = 3


def disponible() -> bool:
    return not _bloqueado


def get_offers(query: str, marca: str, limit: int = 8) -> list[Offer]:
    global _bloqueado, _fallos_seguidos
    for intento in range(3):
        r = requests.get(
            "https://www.amazon.com/s",
            params={"k": query},
            headers={"User-Agent": random.choice(UAS), "Accept-Language": "en-US,en;q=0.9"},
            timeout=20,
        )
        if r.status_code == 200 and "captcha" not in r.text.lower():
            _fallos_seguidos = 0
            time.sleep(random.uniform(2, 4))   # cortesía entre productos
            return parse(r.text, limit)
        time.sleep(4 * (intento + 1) + random.uniform(0, 2))
    _fallos_seguidos += 1
    if _fallos_seguidos >= MAX_FALLOS_SEGUIDOS:
        _bloqueado = True
        raise RuntimeError(f"HTTP {r.status_code}/captcha {MAX_FALLOS_SEGUIDOS} veces seguidas; "
                           "Amazon se omite el resto de la corrida")
    raise RuntimeError(f"HTTP {r.status_code}/captcha tras 3 intentos")


def parse(html: str, limit: int = 8) -> list[Offer]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    for card in soup.select("div[data-component-type='s-search-result']"):
        h = card.select_one("h2.a-text-normal") or card.select_one("h2[aria-label]") or card.select_one("h2 span")
        m = card.select_one("h2.a-size-mini")
        w = card.select_one("span.a-price > span.a-offscreen")
        a = card.select_one("a.a-link-normal[href*='/dp/']") or card.select_one("h2 a")
        asin = card.get("data-asin")
        if not (h and w and (asin or a)):   # los patrocinados no traen link /dp/, pero sí data-asin
            continue
        titulo = h.get("aria-label") or h.get_text(" ", strip=True)
        if m and m is not h:
            titulo = f"{m.get_text(' ', strip=True)} {titulo}"   # la marca va en un <h2> aparte
        try:
            precio = float(re.sub(r"[^0-9.]", "", w.get_text()))
        except ValueError:
            continue
        if asin:
            url = f"https://www.amazon.com/dp/{asin}"
        else:
            href = a["href"]
            url = href if href.startswith("http") else "https://www.amazon.com" + href
        out.append(Offer(TIENDA, titulo, precio, "USD", url,
                         envio_gratis="free delivery" in card.get_text(" ").lower()))
        if len(out) >= limit:
            break
    return out
