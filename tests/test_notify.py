from scraper.notify import armar_avisos, mensaje_diario

BASE = {"marca": "Kyte Baby", "nombre": "Pijama", "precio_usa_usd": 20.0, "tienda_ganadora": "Walmart",
        "margen_pen": 89, "margen_pct": 48.4}


def test_pasa_a_verde_avisa():
    assert "pasó a VERDE" in armar_avisos([{**BASE, "estado": "VERDE", "estado_ayer": "AMARILLO"}])[0]


def test_sigue_verde_no_avisa():
    assert armar_avisos([{**BASE, "estado": "VERDE", "estado_ayer": "VERDE", "tienda_ayer": "Walmart"}]) == []


def test_cambio_de_tienda_avisa():
    a = armar_avisos([{**BASE, "estado": "ROJO", "estado_ayer": "ROJO", "tienda_ayer": "Amazon"}])
    assert "ahora más barato en Walmart (antes Amazon)" in a[0]


def test_baja_mayor_a_15_avisa_y_15_justo_no():
    assert "bajó 15.1 %" in armar_avisos([{**BASE, "estado": "ROJO", "estado_ayer": "ROJO",
                                           "delta_pct_vs_ayer": -15.1}])[0]
    assert armar_avisos([{**BASE, "estado": "ROJO", "estado_ayer": "ROJO", "delta_pct_vs_ayer": -15.0}]) == []
    assert armar_avisos([{**BASE, "estado": "ROJO", "estado_ayer": "ROJO", "delta_pct_vs_ayer": 30.0}]) == []


def test_varios_motivos_en_una_linea():
    a = armar_avisos([{**BASE, "estado": "VERDE", "estado_ayer": "ROJO", "tienda_ayer": "Amazon",
                       "delta_pct_vs_ayer": -20.0}])
    assert len(a) == 1 and "pasó a VERDE" in a[0] and "bajó 20.0 %" in a[0] and "antes Amazon" in a[0]


def test_sin_datos_sin_margen_no_rompe():
    f = {**BASE, "estado": "SIN DATOS", "tienda_ayer": "Amazon"}
    del f["margen_pen"]
    assert "margen" not in armar_avisos([f])[0]


def test_mensaje_incluye_link_y_es_none_si_no_hay_avisos():
    assert mensaje_diario([], "2026-11-13", 3.75) is None
    m = mensaje_diario([{**BASE, "estado": "VERDE"}], "2026-11-13", 3.75, "https://x.github.io/p/")
    assert m.startswith("Precios bebé 2026-11-13") and m.endswith("https://x.github.io/p/")
