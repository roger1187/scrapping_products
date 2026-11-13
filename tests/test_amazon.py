"""parse() contra un recorte real de la búsqueda de Amazon (tests/fixtures/amazon_busqueda.html, nov-2026)."""
from pathlib import Path

from scraper.models import filtrar_usa
from scraper.sources.usa import amazon

HTML = (Path(__file__).parent / "fixtures" / "amazon_busqueda.html").read_text(encoding="utf-8")


def test_parse_junta_marca_y_titulo():
    o = amazon.parse(HTML)
    assert len(o) == 3
    assert o[0].titulo == "Simple Joys by Carter's Baby 4-Pack Neutral Pant"
    assert o[0].precio == 17.50 and o[0].moneda == "USD"
    assert o[0].url == "https://www.amazon.com/dp/B0744PN2W1"
    assert all("OEKO-TEX" not in x.titulo for x in o)


def test_resultados_reales_pasan_el_filtro_de_relevancia():
    p = {"id": "carters", "marca": "Carter's", "nombre": "Pack", "pack": "4-pack"}
    assert len(filtrar_usa(amazon.parse(HTML), p)) == 3
