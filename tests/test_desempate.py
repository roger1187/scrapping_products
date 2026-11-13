from scraper.models import confianza, ordenar_ofertas
from tests.helpers import usd

MARCA = "Kyte Baby"


def tiendas(ofertas):
    return [o.tienda for o in ordenar_ofertas(ofertas, MARCA)]


def test_mas_barata_gana_siempre():
    assert tiendas([usd(20.0, "Kyte Baby", envio_gratis=True), usd(19.99, "eBay")])[0] == "eBay"


def test_empate_gana_envio_gratis():
    assert tiendas([usd(20.0, "Amazon"), usd(20.0, "Walmart", envio_gratis=True)])[0] == "Walmart"


def test_empate_con_mismo_envio_sigue_orden_de_confianza():
    ofertas = [usd(20.0, t) for t in ("Kohl's", "Target", "Walmart", "Amazon", "Kyte Baby")]
    assert tiendas(ofertas) == ["Kyte Baby", "Amazon", "Walmart", "Target", "Kohl's"]


def test_empate_ignora_diferencias_menores_a_un_centavo():
    assert tiendas([usd(20.001, "Target"), usd(19.999, "Amazon")])[0] == "Amazon"


def test_sitio_de_la_marca_se_reconoce_aunque_venga_como_dominio():
    assert confianza("kytebaby", MARCA) == 0
    assert confianza("Kyte BABY", MARCA) == 0
    assert confianza("Amazon", MARCA) == 1
    assert confianza("Nordstrom", MARCA) == 4
