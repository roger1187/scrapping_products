"""Fuentes con cupo limitado (p. ej. SerpAPI: 100 búsquedas/mes en el plan gratis).

Una fuente se declara limitada definiendo en su módulo:
    ENV_MAX_DIARIO = "SERPAPI_MAX_DIARIO"   # variable de entorno con el máximo de búsquedas por día
    MAX_DIARIO_DEFAULT = 3
    MAX_DIAS_CACHE = 14                     # pasado esto, el último precio conocido ya no se usa

Cada día se consultan de verdad solo N productos, rotando: primero los que nunca se consultaron y luego los
de dato más antiguo. Para el resto se reutilizan las últimas ofertas guardadas en data/cache_fuentes.json,
marcadas con su fecha para que la web muestre que es un precio de días anteriores.
"""
import datetime as dt
import json
import os
from pathlib import Path
from typing import Callable

from scraper.models import Offer


def nombre_fuente(fuente) -> str:
    return fuente.__name__.rsplit(".", 1)[-1]


def es_limitada(fuente) -> bool:
    return hasattr(fuente, "ENV_MAX_DIARIO")


def max_diario(fuente) -> int:
    valor = os.getenv(fuente.ENV_MAX_DIARIO) or ""
    try:
        return max(0, int(valor))
    except ValueError:
        return getattr(fuente, "MAX_DIARIO_DEFAULT", 3)


def planificar(ids: list[str], productos_estado: dict, cupo: int) -> list[str]:
    """Elige qué productos consultar hoy: nunca consultados primero (orden del YAML), luego los más antiguos."""
    if cupo <= 0:
        return []
    orden = sorted(range(len(ids)), key=lambda i: (productos_estado.get(ids[i], {}).get("fecha") or "", i))
    return [ids[i] for i in orden[:cupo]]


class Cupos:
    def __init__(self, ruta: Path, hoy: str | None = None):
        self.ruta = Path(ruta)
        self.hoy = hoy or dt.date.today().isoformat()
        self.estado = self._cargar()
        self.planes: dict[str, set[str]] = {}

    def _cargar(self) -> dict:
        try:
            return json.loads(self.ruta.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as e:
            print(f"[cuota] {self.ruta} ilegible ({e}); empiezo de cero")
            return {}

    def guardar(self) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.ruta.write_text(json.dumps(self.estado, ensure_ascii=False, indent=2), encoding="utf-8")

    def _de(self, fuente) -> dict:
        e = self.estado.setdefault(nombre_fuente(fuente), {})
        e.setdefault("uso", {"fecha": self.hoy, "busquedas": 0})
        e.setdefault("productos", {})
        if e["uso"].get("fecha") != self.hoy:
            e["uso"] = {"fecha": self.hoy, "busquedas": 0}
        return e

    def preparar(self, fuente, ids: list[str]) -> list[str]:
        """Decide los productos que la fuente consultará hoy, descontando lo ya gastado hoy en otra corrida."""
        e = self._de(fuente)
        restante = max_diario(fuente) - e["uso"]["busquedas"]
        plan = planificar(ids, e["productos"], restante)
        self.planes[nombre_fuente(fuente)] = set(plan)
        return plan

    def obtener(self, fuente, producto_id: str, consultar: Callable[[], list[Offer]]) -> list[Offer]:
        """Consulta de verdad si al producto le toca hoy; si no (o si falla), devuelve el último precio conocido."""
        e = self._de(fuente)
        nombre = nombre_fuente(fuente)
        if producto_id in self.planes.get(nombre, set()):
            self.planes[nombre].discard(producto_id)
            e["uso"]["busquedas"] += 1          # se cuenta aunque falle: la API la cobra igual
            try:
                ofertas = consultar()
            except Exception as ex:
                print(f"[{nombre}] falló para {producto_id}: {ex}; uso el último precio conocido")
            else:
                e["productos"][producto_id] = {"fecha": self.hoy, "ofertas": [o.to_dict() for o in ofertas]}
                return ofertas
        return self._cacheadas(fuente, e["productos"].get(producto_id))

    def _cacheadas(self, fuente, guardado: dict | None) -> list[Offer]:
        if not guardado:
            return []
        fecha = guardado.get("fecha", "")
        try:
            dias = (dt.date.fromisoformat(self.hoy) - dt.date.fromisoformat(fecha)).days
        except ValueError:
            return []
        if dias > getattr(fuente, "MAX_DIAS_CACHE", 14):
            return []
        out = []
        for d in guardado.get("ofertas", []):
            o = Offer.from_dict(d)
            o.fecha = None if fecha == self.hoy else fecha
            out.append(o)
        return out
