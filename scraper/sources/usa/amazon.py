"""Amazon.com: scraping básico de la página de búsqueda. Versión base; ver CLAUDE.md para endurecerla."""
import random
import re
import time

import requests
from bs4 import BeautifulSoup

from scraper.models import Offer, contiene_marca

TIENDA = "Amazon"
UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
]


def get_offers(query: str, marca: str, limit: int = 5) -> list[Offer]:
    for _ in range(3):
        r = requests.get(
            "https://www.amazon.com/s",
            params={"k": query},
            headers={"User-Agent": random.choice(UAS), "Accept-Language": "en-US,en;q=0.9"},
            timeout=20,
        )
        if r.status_code != 200 or "captcha" in r.text.lower():
            time.sleep(10)
            continue
        soup = BeautifulSoup(r.text, "lxml")
        out = []
        for card in soup.select("div[data-component-type='s-search-result']"):
            h = card.select_one("h2 span")
            w = card.select_one("span.a-price > span.a-offscreen")
            a = card.select_one("a.a-link-normal[href*='/dp/']") or card.select_one("h2 a")
            if not (h and w and a):
                continue
            titulo = h.get_text(strip=True)
            if not contiene_marca(titulo, marca):
                continue
            if re.search(r"\b(used|renewed|refurbished)\b", titulo, re.I):
                continue
            try:
                precio = float(re.sub(r"[^0-9.]", "", w.get_text()))
            except ValueError:
                continue
            href = a["href"]
            url = href if href.startswith("http") else "https://www.amazon.com" + href
            out.append(Offer(TIENDA, titulo, precio, "USD", url))
            if len(out) >= limit:
                break
        return out
    return []
