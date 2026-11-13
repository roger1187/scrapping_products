"""parse() con un dict mínimo armado según los campos documentados de SerpAPI (no es una respuesta real)."""
from scraper.sources.usa import google_shopping

DATOS = {"shopping_results": [
    {"title": "Kyte Baby Zippered Footie", "extracted_price": 38.0, "source": "Walmart - Seller",
     "link": "https://w.example/1", "delivery": "Free delivery"},
    {"title": "Kyte Baby Zippered Footie", "extracted_price": 40.0, "source": "Amazon.com",
     "product_link": "https://g.example/2"},
    {"title": "Kyte Baby Footie", "extracted_price": 15.0, "source": "eBay", "link": "https://e.example/3",
     "second_hand_condition": "used"},
    {"title": "Sin precio", "source": "Target"},
]}


def test_parse_normaliza_tienda_envio_y_condicion():
    o = google_shopping.parse(DATOS)
    assert [x.tienda for x in o] == ["Walmart", "Amazon", "eBay"]
    assert o[0].envio_gratis and not o[1].envio_gratis
    assert o[1].url == "https://g.example/2"
    assert o[2].condicion == "used"


def test_disponible_depende_de_la_key(monkeypatch):
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    assert not google_shopping.disponible()
    monkeypatch.setenv("SERPAPI_KEY", "x")
    assert google_shopping.disponible()


def test_error_de_red_no_filtra_la_api_key(monkeypatch):
    import pytest
    import requests

    monkeypatch.setenv("SERPAPI_KEY", "clave-secreta-123")

    def boom(*a, **k):
        raise requests.ConnectionError("https://serpapi.com/search.json?api_key=clave-secreta-123")

    monkeypatch.setattr(google_shopping.requests, "get", boom)
    with pytest.raises(RuntimeError) as e:
        google_shopping.get_offers("x", "y")
    assert "clave-secreta-123" not in str(e.value)
