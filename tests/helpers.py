"""Ofertas sintéticas para probar la lógica (no son precios reales)."""
from scraper.models import Offer


def usd(precio, tienda="Amazon", titulo="Kyte Baby Zippered Footie", **kw):
    return Offer(tienda, titulo, precio, "USD", f"https://example.com/{tienda}", **kw)


def pen(precio, tienda="MercadoLibre", titulo="Kyte Baby pijama", **kw):
    return Offer(tienda, titulo, precio, "PEN", f"https://example.pe/{tienda}", **kw)


PRODUCTO = {"id": "kyte", "marca": "Kyte Baby", "nombre": "Pijama", "precio_lima_manual": 230}
