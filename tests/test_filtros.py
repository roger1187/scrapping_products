import pytest

from scraper.models import contiene_marca, cumple_variante, es_usado, filtrar_lima, filtrar_usa, normalizar_tienda
from tests.helpers import PRODUCTO, pen, usd


@pytest.mark.parametrize("titulo,marca", [
    ("CARTERS Baby 4-Pack Pants", "Carter's"),
    ("Carter’s baby pants", "Carter's"),
    ("kyte baby footie", "Kyte Baby"),
    ("SkipHop Forma Backpack", "Skip Hop"),
    ("aden + anais muslin swaddle", "Aden"),
])
def test_marca_coincide(titulo, marca):
    assert contiene_marca(titulo, marca)


def test_marca_no_coincide():
    assert not contiene_marca("Generic bamboo footie", "Kyte Baby")


@pytest.mark.parametrize("titulo", [
    "Kyte Baby footie (Used - Good)", "Kyte Baby footie Renewed", "Kyte Baby Refurbished", "Kyte Baby Pre-Owned",
    "Kyte Baby pijama usado",
])
def test_usados_se_descartan(titulo):
    assert es_usado(usd(10.0, titulo=titulo))


def test_used_como_verbo_no_descarta():
    assert not es_usado(usd(10.0, titulo="Kyte Baby swaddle, can be used as a blanket"))


def test_condicion_de_la_fuente_descarta():
    assert es_usado(usd(10.0, condicion="used"))
    assert not es_usado(usd(10.0, condicion="new"))


def test_size_y_pack_se_exigen():
    p = {**PRODUCTO, "size": "0-3 Months", "pack": "4 pack"}
    assert cumple_variante("Kyte Baby Footie 0-3 months 4-Pack", p)
    assert not cumple_variante("Kyte Baby Footie 3-6 months 4-Pack", p)
    assert not cumple_variante("Kyte Baby Footie 0-3 months", p)
    assert cumple_variante("cualquier cosa", PRODUCTO)   # sin size/pack no se exige nada


def test_filtrar_usa_aplica_todo():
    p = {**PRODUCTO, "pack": "2 pack"}
    ofertas = [
        usd(10.0, titulo="Kyte Baby footie 2-pack"),               # ok
        usd(5.0, titulo="Generic footie 2-pack"),                  # sin marca
        usd(6.0, titulo="Kyte Baby footie 2-pack (Renewed)"),      # renewed
        usd(7.0, titulo="Kyte Baby footie"),                       # sin pack
        pen(8.0, titulo="Kyte Baby footie 2-pack"),                # moneda equivocada
        usd(0.0, titulo="Kyte Baby footie 2-pack"),                # precio inválido
    ]
    assert [o.precio for o in filtrar_usa(ofertas, p)] == [10.0]


def test_filtrar_lima_no_exige_size_pack():
    p = {**PRODUCTO, "pack": "2 pack"}
    assert len(filtrar_lima([pen(100.0, titulo="Kyte Baby pijama")], p)) == 1


@pytest.mark.parametrize("crudo,limpio", [
    ("Walmart - Seller", "Walmart"), ("Walmart.com", "Walmart"), ("Amazon.com", "Amazon"),
    ("Amazon.com - Seller", "Amazon"), ("Target", "Target"), ("Kohl's", "Kohl's"), ("macys.com", "Macy's"),
    ("Kyte BABY", "Kyte BABY"), ("", "Desconocida"),
])
def test_normalizar_tienda(crudo, limpio):
    assert normalizar_tienda(crudo) == limpio
