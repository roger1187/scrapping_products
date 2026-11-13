import json
import types

import pytest

import main
from tests.helpers import pen, usd

YAML = """
products:
  - {id: kyte, marca: Kyte Baby, nombre: Pijama, usa: "kyte footie", lima: "kyte pijama", precio_lima_manual: 230}
  - {id: halo, marca: Halo, nombre: Saco, usa: "halo sleepsack", lima: "halo", precio_lima_manual: 180}
  - {id: kyte, marca: Kyte Baby, nombre: Duplicado}
  - {marca: SinId, nombre: X}
"""


def fuente(nombre, fn, **attrs):
    return types.SimpleNamespace(__name__=f"scraper.sources.x.{nombre}", get_offers=fn, **attrs)


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "products.yaml").write_text(YAML, encoding="utf-8")
    monkeypatch.setattr(main, "tipo_cambio", lambda: (3.8, "SUNAT"))
    enviados = []
    monkeypatch.setattr(main.notify, "telegram", enviados.append)
    monkeypatch.setenv("SERPAPI_KEY", "clave-super-secreta")

    def rota(q, m):
        raise RuntimeError("fallo con api_key=clave-super-secreta")

    def buena(q, m):
        return [usd(20.0, "Walmart", titulo="Kyte Baby footie")] if "kyte" in q else []

    monkeypatch.setattr(main, "USA_SOURCES", [fuente("rota", rota), fuente("buena", buena)])
    monkeypatch.setattr(main, "LIMA_SOURCES", [fuente("lima", lambda q, m: [pen(300.0, titulo="Kyte Baby pijama")]
                                                       if "kyte" in q else [])])
    return tmp_path, enviados


def test_corrida_completa_no_aborta_y_escribe_data(entorno, capsys):
    tmp, enviados = entorno
    main.main(dry_run=False)
    out = json.loads((tmp / "data" / "latest.json").read_text(encoding="utf-8"))
    assert [p["id"] for p in out["productos"]] == ["kyte", "halo"]     # duplicado y sin id omitidos
    kyte = out["productos"][0]
    assert kyte["tienda_ganadora"] == "Walmart" and kyte["estado"] == "VERDE"
    halo = out["productos"][1]
    assert halo["estado"] == "SIN DATOS" and halo["falta"] == "USA"
    assert any(e["fuente"] == "rota" for e in out["errores"])
    assert "clave-super-secreta" not in json.dumps(out) + capsys.readouterr().out
    assert len(list((tmp / "data" / "history").glob("*.json"))) == 1
    assert enviados and "pasó a VERDE" in enviados[0]


def test_dry_run_no_escribe_ni_avisa(entorno):
    tmp, enviados = entorno
    main.main(dry_run=True)
    assert not (tmp / "data").exists() and not enviados


def test_falta_products_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match="No encuentro"):
        main.cargar_productos()


def test_compara_con_ayer(entorno):
    tmp, _ = entorno
    hist = tmp / "data" / "history"
    hist.mkdir(parents=True)
    (hist / "2000-01-01.json").write_text(json.dumps({"productos": [
        {"id": "kyte", "precio_usa_usd": 25.0, "estado": "VERDE", "tienda_ganadora": "Amazon"}]}))
    (hist / "1999-12-31.json").write_text("{roto")
    main.main(dry_run=False)
    kyte = json.loads((tmp / "data" / "latest.json").read_text())["productos"][0]
    assert kyte["precio_usa_ayer"] == 25.0 and kyte["delta_pct_vs_ayer"] == -20.0
    assert kyte["tienda_ayer"] == "Amazon"
