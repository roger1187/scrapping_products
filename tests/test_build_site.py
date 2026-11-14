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


def test_panel_de_referencias_lima(tmp_path):
    import pathlib
    data = tmp_path / "data"
    (data / "history").mkdir(parents=True)
    con = {**FILA, "id": "carters", "lima_estimado": False, "busqueda_lima": "Carters pantalon pack x4",
           "ofertas_lima": [
               {"tienda": "Falabella", "precio_pen": 74.9, "url": "https://f.example/1", "titulo": "CARTERS Pantalón x4"},
               {"tienda": "Oechsle", "precio_pen": 89.9, "url": "javascript:x", "titulo": "Carters pack x4"}]}
    latest = {"fecha": "2026-11-14", "tipo_cambio": 3.4, "productos": [con, FILA]}
    (data / "latest.json").write_text(json.dumps(latest))
    construir(data, tmp_path / "site", pathlib.Path("templates"))
    html = (tmp_path / "site" / "index.html").read_text()
    assert 'aria-controls="lima-carters"' in html and 'id="lima-carters" hidden' in html
    assert "CARTERS Pantalón x4" in html and "S/ 89.90" in html            # todas las publicaciones
    assert "javascript:x" not in html                                     # links inseguros fuera
    assert "falabella.com.pe/falabella-pe/search?Ntt=Carters%20pantalon%20pack%20x4" in html
    assert "Ninguna publicación de Lima pasó los filtros" in html         # FILA es estimada


def test_compare_guarda_busqueda_y_quita_duplicados():
    from scraper.compare import evaluar
    from tests.helpers import PRODUCTO, pen, usd
    p = {**PRODUCTO, "lima": "Kyte Baby pijama"}
    f = evaluar(p, [usd(20.0)], [pen(250.0), pen(250.0), pen(300.0, tienda="Oechsle")], 3.8)
    assert f["busqueda_lima"] == "Kyte Baby pijama"
    assert [(o["tienda"], o["precio_pen"]) for o in f["ofertas_lima"]] == [("MercadoLibre", 250.0), ("Oechsle", 300.0)]
