"""Amazon.com: scraping de la página de búsqueda.

Amazon bloquea con captcha a menudo. Si eso pasa, la fuente se desactiva por el resto de la corrida para no
gastar ~30 s por producto (el job tiene 25 min). Pendiente: Keepa (KEEPA_API_KEY) cuando haya red para probarlo.
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


def disponible() -> bool:
    return not _bloqueado


def get_offers(query: str, marca: str, limit: int = 8) -> list[Offer]:
    global _bloqueado
    for intento in range(2):
        r = requests.get(
            "https://www.amazon.com/s",
            params={"k": query},
            headers={"User-Agent": random.choice(UAS), "Accept-Language": "en-US,en;q=0.9"},
            timeout=20,
        )
        if r.status_code == 200 and "captcha" not in r.text.lower():
            time.sleep(1)   # cortesía entre productos
            return parse(r.text, limit)
        time.sleep(5 * (intento + 1))
    _bloqueado = True
    raise RuntimeError("bloqueado por captcha/HTTP; Amazon se omite el resto de la corrida")


def parse(html: str, limit: int = 8) -> list[Offer]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    for card in soup.select("div[data-component-type='s-search-result']"):
        h = card.select_one("h2 span")
        w = card.select_one("span.a-price > span.a-offscreen")
        a = card.select_one("a.a-link-normal[href*='/dp/']") or card.select_one("h2 a")
        if not (h and w and a):
            continue
        try:
            precio = float(re.sub(r"[^0-9.]", "", w.get_text()))
        except ValueError:
            continue
        asin = card.get("data-asin")
        if asin:
            url = f"https://www.amazon.com/dp/{asin}"
        else:
            href = a["href"]
            url = href if href.startswith("http") else "https://www.amazon.com" + href
        out.append(Offer(TIENDA, h.get_text(strip=True), precio, "USD", url,
                         envio_gratis="free delivery" in card.get_text(" ").lower()))
        if len(out) >= limit:
            break
    return out
