import json

from build_site import construir, url_segura

FILA = {"id": "kyte", "marca": "Kyte Baby", "nombre": "Pijama <b>", "estado": "VERDE", "precio_usa_usd": 20.0,
        "tienda_ganadora": "Walmart", "url_ganadora": "javascript:alert(1)", "costo_lima_pen": 95,
        "precio_lima_ref_pen": 230, "lima_estimado": True, "venta_objetivo_pen": 212, "margen_pen": 117,
        "margen_pct": 55.0, "delta_pct_vs_ayer": -10.0, "ofertas_lima": [],
        "ranking_tiendas": [{"tienda": "Walmart", "precio_usd": 20.0, "url": "https://w.example/1"}]}


def test_url_segura():
    assert url_segura("https://a.com") == "https://a.com"
    assert url_segura("javascript:alert(1)") == "" and url_segura(None) == ""


def test_genera_index_y_paginas(tmp_path):
    data = tmp_path / "data"
    (data / "history").mkdir(parents=True)
    latest = {"fecha": "2026-11-13", "tipo_cambio": 3.75, "productos": [FILA, {
        "id": "halo/x", "marca": "Halo", "nombre": "Saco", "estado": "SIN DATOS", "falta": "USA",
        "ranking_tiendas": [], "ofertas_lima": []}]}
    (data / "latest.json").write_text(json.dumps(latest))
    (data / "history" / "2026-11-13.json").write_text(json.dumps(latest))
    out = tmp_path / "site"
    construir(data, out, __import__("pathlib").Path("templates"))

    index = (out / "index.html").read_text()
    assert "referencia estimada" in index
    assert "javascript:alert" not in index           # link peligroso no se renderiza
    assert "Pijama &lt;b&gt;" in index               # autoescape
    assert "▼ 10.0 %" in index
    assert (out / "producto" / "kyte.html").exists()
    assert (out / "producto" / "halo_x.html").exists()   # id saneado como nombre de archivo
    assert "chart.js" in (out / "producto" / "kyte.html").read_text()
