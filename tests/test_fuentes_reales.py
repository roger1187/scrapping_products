"""Parsers contra datos reales capturados el 2026-11-13 (tests/fixtures/). Si un sitio cambia, fallan aquí."""
import json
from pathlib import Path

from scraper.models import filtrar_lima, filtrar_usa
from scraper.sources.lima import falabella, oechsle
from scraper.sources.usa import brand_site

FX = Path(__file__).parent / "fixtures"


def cargar(nombre):
    return json.loads((FX / nombre).read_text(encoding="utf-8"))


def test_falabella_toma_menor_precio_no_tachado():
    o = falabella.parse(cargar("falabella_busqueda.json"))
    pan = next(x for x in o if "Pañalero" in x.titulo)
    assert pan.titulo == "SKIP HOP Bolso Pañalero Unisex Bebé"
    assert pan.precio == 319.20 and pan.moneda == "PEN"       # eventPrice; el normalPrice tachado no cuenta
    assert pan.url.startswith("https://www.falabella.com.pe/")


def test_falabella_filtro_descarta_otra_marca_y_otro_producto():
    o = falabella.parse(cargar("falabella_busqueda.json"))
    mochila = {"id": "x", "marca": "Skip Hop", "nombre": "x", "requiere_lima": ["pañaler"]}
    assert [x.titulo for x in filtrar_lima(o, mochila)] == ["SKIP HOP Bolso Pañalero Unisex Bebé"]
    ergo = {"id": "y", "marca": "Ergobaby", "nombre": "y"}
    assert filtrar_lima(o, ergo) == []                          # "360 Cama Saltarina" no es Ergobaby


def test_oechsle_vtex():
    o = oechsle.parse(cargar("oechsle_busqueda.json"))
    assert [(x.titulo, x.precio) for x in o][:2] == [
        ("Set De Juego Skip Hop Waffle Zoo", 59.4), ("Estuche Para Pañitos Skip Hop Gris", 47.2)]
    # accesorios de la marca: sin requiere_lima pasarían y fijarían una referencia de Lima absurda
    assert filtrar_lima(o, {"id": "x", "marca": "Skip Hop", "nombre": "x", "requiere_lima": ["pañaler"]}) == []


def test_brand_site_lee_json_ld():
    o = brand_site.parse(cargar("brand_kyte.json"), "Kyte Baby")
    assert len(o) == 1
    assert o[0].precio == 38.0 and o[0].tienda == "Kyte Baby (sitio oficial)"
    assert filtrar_usa(o, {"id": "k", "marca": "Kyte Baby", "nombre": "k", "requiere": ["footie"]}) == o


def test_brand_site_agotado_no_es_oferta():
    datos = {"titulo": "Kyte Baby X", "url": "https://kytebaby.com/p", "ld": [json.dumps(
        {"@type": "Product", "offers": [{"price": "30", "priceCurrency": "USD",
                                         "availability": "http://schema.org/OutOfStock"}]})]}
    assert brand_site.parse(datos, "Kyte Baby") == []


def test_brand_site_sin_json_ld_usa_og_price():
    o = brand_site.parse({"titulo": "Zippy", "og_precio": "36.00", "og_moneda": "USD", "ld": [],
                          "url": "https://littlesleepies.com/p"}, "Little Sleepies")
    assert o[0].precio == 36.0 and o[0].titulo == "Little Sleepies Zippy"
