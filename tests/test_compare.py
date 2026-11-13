import pytest

from scraper.compare import evaluar, semaforo
from tests.helpers import PRODUCTO, pen, usd

TC = 3.8


def test_formula_de_margen(monkeypatch):
    monkeypatch.delenv("FACTOR_IMPORTACION", raising=False)
    f = evaluar(PRODUCTO, [usd(20.0)], [pen(200.0)], TC)
    # costo = 20 * 3.8 * 1.25 = 95 ; venta = 200 * 0.92 = 184 ; margen = 89 ; 89/184 = 48.4 %
    assert f["costo_lima_pen"] == 95
    assert f["venta_objetivo_pen"] == 184
    assert f["margen_pen"] == 89
    assert f["margen_pct"] == 48.4
    assert f["estado"] == "VERDE"
    assert f["tienda_ganadora"] == "Amazon"


def test_factor_importacion_se_lee_en_tiempo_de_ejecucion(monkeypatch):
    monkeypatch.setenv("FACTOR_IMPORTACION", "1.5")
    f = evaluar(PRODUCTO, [usd(20.0)], [pen(200.0)], TC)
    assert f["costo_lima_pen"] == 114   # 20 * 3.8 * 1.5


def test_factor_invalido_usa_default(monkeypatch):
    monkeypatch.setenv("FACTOR_IMPORTACION", "abc")
    assert evaluar(PRODUCTO, [usd(20.0)], [pen(200.0)], TC)["costo_lima_pen"] == 95


@pytest.mark.parametrize("pct,estado", [
    (60, "VERDE"), (35.0, "VERDE"), (34.9, "AMARILLO"), (20.0, "AMARILLO"), (19.9, "ROJO"), (-10, "ROJO"),
])
def test_umbrales_del_semaforo(pct, estado):
    assert semaforo(pct) == estado


def test_amarillo_y_rojo_de_punta_a_punta(monkeypatch):
    monkeypatch.delenv("FACTOR_IMPORTACION", raising=False)
    assert evaluar(PRODUCTO, [usd(25.0)], [pen(170.0)], TC)["estado"] == "AMARILLO"   # 24.1 %
    assert evaluar(PRODUCTO, [usd(30.0)], [pen(160.0)], TC)["estado"] == "ROJO"       # 3.2 %


def test_precio_lima_manual_solo_si_no_hay_resultados():
    con_resultados = evaluar(PRODUCTO, [usd(20.0)], [pen(400.0)], TC)
    assert con_resultados["precio_lima_ref_pen"] == 400          # ignora el manual (230) aunque sea menor
    assert con_resultados["lima_estimado"] is False

    sin_resultados = evaluar(PRODUCTO, [usd(20.0)], [], TC)
    assert sin_resultados["precio_lima_ref_pen"] == 230
    assert sin_resultados["lima_estimado"] is True
    assert sin_resultados["tienda_lima_ref"] == "Referencia manual"


def test_manual_tambien_aplica_si_lima_solo_trae_irrelevantes():
    f = evaluar(PRODUCTO, [usd(20.0)], [pen(50.0, titulo="Pijama genérico sin marca")], TC)
    assert f["lima_estimado"] is True and f["precio_lima_ref_pen"] == 230


def test_lima_toma_el_minimo_de_los_resultados():
    f = evaluar(PRODUCTO, [usd(20.0)], [pen(300.0), pen(250.0, tienda="Falabella")], TC)
    assert f["precio_lima_ref_pen"] == 250 and f["tienda_lima_ref"] == "Falabella"


def test_sin_datos_si_falta_usa():
    f = evaluar(PRODUCTO, [], [pen(200.0)], TC)
    assert f["estado"] == "SIN DATOS" and f["falta"] == "USA"
    assert "margen_pct" not in f


def test_sin_datos_si_falta_lima_pero_muestra_precio_usa():
    sin_manual = {k: v for k, v in PRODUCTO.items() if k != "precio_lima_manual"}
    f = evaluar(sin_manual, [usd(20.0)], [], TC)
    assert f["estado"] == "SIN DATOS" and f["falta"] == "Lima"
    assert f["precio_usa_usd"] == 20.0


def test_gana_la_tienda_mas_barata_no_amazon():
    f = evaluar(PRODUCTO, [usd(30.0, "Amazon"), usd(22.5, "Walmart"), usd(25.0, "Target")], [pen(200.0)], TC)
    assert f["tienda_ganadora"] == "Walmart" and f["precio_usa_usd"] == 22.5
    assert [t["tienda"] for t in f["ranking_tiendas"]] == ["Walmart", "Target", "Amazon"]


def test_ranking_una_entrada_por_tienda():
    f = evaluar(PRODUCTO, [usd(30.0, "Amazon"), usd(28.0, "Amazon"), usd(29.0, "Walmart")], [pen(200.0)], TC)
    assert [(t["tienda"], t["precio_usd"]) for t in f["ranking_tiendas"]] == [("Amazon", 28.0), ("Walmart", 29.0)]


def test_precio_cacheado_lleva_su_fecha():
    f = evaluar(PRODUCTO, [usd(20.0, fecha="2026-11-10")], [pen(200.0)], TC)
    assert f["fecha_precio_usa"] == "2026-11-10"
