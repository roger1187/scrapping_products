import json
import types

import pytest

from scraper.cuota import Cupos, planificar
from tests.helpers import usd


def fuente_falsa(max_default=3, dias_cache=14):
    return types.SimpleNamespace(__name__="scraper.sources.usa.falsa", ENV_MAX_DIARIO="FALSA_MAX",
                                 MAX_DIARIO_DEFAULT=max_default, MAX_DIAS_CACHE=dias_cache)


IDS = ["a", "b", "c", "d"]


def test_planificar_prioriza_nunca_consultados_y_luego_los_mas_antiguos():
    estado = {"a": {"fecha": "2026-11-10"}, "b": {"fecha": "2026-11-08"}, "d": {"fecha": "2026-11-12"}}
    assert planificar(IDS, estado, 2) == ["c", "b"]
    assert planificar(IDS, estado, 0) == []


def test_rotacion_completa_en_varios_dias(tmp_path, monkeypatch):
    monkeypatch.delenv("FALSA_MAX", raising=False)
    f = fuente_falsa(max_default=2)
    vistos = []
    for dia in ("2026-11-01", "2026-11-02", "2026-11-03"):
        c = Cupos(tmp_path / "cache.json", dia)
        plan = c.preparar(f, IDS)
        vistos.append(plan)
        for pid in IDS:
            c.obtener(f, pid, lambda pid=pid: [usd(10.0, titulo=f"Kyte Baby {pid}")])
        c.guardar()
    assert vistos == [["a", "b"], ["c", "d"], ["a", "b"]]


def test_reutiliza_ultimo_precio_con_su_fecha(tmp_path, monkeypatch):
    monkeypatch.setenv("FALSA_MAX", "1")
    f = fuente_falsa()
    c1 = Cupos(tmp_path / "cache.json", "2026-11-01")
    c1.preparar(f, ["a", "b"])
    assert c1.obtener(f, "a", lambda: [usd(10.0)])[0].fecha is None   # hoy: dato fresco
    c1.guardar()

    c2 = Cupos(tmp_path / "cache.json", "2026-11-02")
    assert c2.preparar(f, ["a", "b"]) == ["b"]
    llamado = []
    cache = c2.obtener(f, "a", lambda: llamado.append(1) or [])
    assert not llamado                                   # no gasta búsqueda
    assert cache[0].precio == 10.0 and cache[0].fecha == "2026-11-01"


def test_cupo_diario_se_respeta_entre_corridas_del_mismo_dia(tmp_path, monkeypatch):
    monkeypatch.setenv("FALSA_MAX", "2")
    f = fuente_falsa()
    c1 = Cupos(tmp_path / "cache.json", "2026-11-01")
    c1.preparar(f, IDS)
    c1.obtener(f, "a", lambda: [usd(1.0)])
    c1.guardar()
    c2 = Cupos(tmp_path / "cache.json", "2026-11-01")
    assert c2.preparar(f, IDS) == ["b"]                  # solo queda 1 búsqueda hoy


def test_cache_vencido_no_se_usa(tmp_path, monkeypatch):
    monkeypatch.setenv("FALSA_MAX", "0")
    f = fuente_falsa(dias_cache=7)
    (tmp_path / "cache.json").write_text(json.dumps({"falsa": {"productos": {
        "a": {"fecha": "2026-11-01", "ofertas": [usd(10.0).to_dict()]},
        "b": {"fecha": "2026-11-07", "ofertas": [usd(12.0).to_dict()]},
    }}}))
    c = Cupos(tmp_path / "cache.json", "2026-11-10")
    c.preparar(f, ["a", "b"])
    assert c.obtener(f, "a", lambda: pytest.fail("no debe consultar")) == []   # 9 días > 7
    assert c.obtener(f, "b", lambda: pytest.fail("no debe consultar"))[0].precio == 12.0


def test_si_la_consulta_falla_usa_cache_y_cuenta_la_busqueda(tmp_path, monkeypatch):
    monkeypatch.setenv("FALSA_MAX", "5")
    f = fuente_falsa()
    (tmp_path / "cache.json").write_text(json.dumps({"falsa": {"productos": {
        "a": {"fecha": "2026-11-05", "ofertas": [usd(10.0).to_dict()]}}}}))
    c = Cupos(tmp_path / "cache.json", "2026-11-06")
    c.preparar(f, ["a"])

    def falla():
        raise RuntimeError("timeout")

    assert c.obtener(f, "a", falla)[0].fecha == "2026-11-05"
    assert c.estado["falsa"]["uso"]["busquedas"] == 1


def test_cache_corrupto_no_rompe(tmp_path):
    (tmp_path / "cache.json").write_text("{no es json")
    assert Cupos(tmp_path / "cache.json", "2026-11-06").estado == {}
