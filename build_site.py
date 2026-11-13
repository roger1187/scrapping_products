"""Genera la web estática site/ desde data/latest.json y data/history/ (últimos 30 días)."""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

DIAS_GRAFICO = 30
ESTADOS = ["VERDE", "AMARILLO", "ROJO", "SIN DATOS"]


def url_segura(url: str | None) -> str:
    """Solo http(s): un link raspado nunca debe poder ejecutar javascript: en la web."""
    return url if isinstance(url, str) and re.match(r"^https?://", url, re.I) else ""


def slug(producto_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", str(producto_id))


def cargar_historial(data: Path) -> list[dict]:
    dias = []
    for a in sorted((data / "history").glob("*.json"))[-DIAS_GRAFICO:]:
        try:
            dias.append(json.loads(a.read_text(encoding="utf-8")))
        except (OSError, ValueError) as e:
            print(f"[build] {a} ilegible ({e}); se omite")
    return dias


def series_por_producto(historial: list[dict]) -> dict[str, list[dict]]:
    series: dict[str, list[dict]] = {}
    for dia in historial:
        for f in dia.get("productos", []):
            series.setdefault(f["id"], []).append({
                "fecha": dia.get("fecha"),
                "precio": f.get("precio_usa_usd"),
                "tienda": f.get("tienda_ganadora"),
            })
    return series


def construir(data: Path, out: Path, templates: Path) -> None:
    latest_path = data / "latest.json"
    if not latest_path.exists():
        sys.exit(f"No existe {latest_path}: corre primero `python main.py`.")
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    series = series_por_producto(cargar_historial(data))

    env = Environment(loader=FileSystemLoader(templates), autoescape=select_autoescape(["html"]))
    env.filters["url_segura"] = url_segura
    env.filters["slug"] = slug

    productos = latest.get("productos", [])
    conteo = {e: sum(1 for p in productos if p.get("estado") == e) for e in ESTADOS}
    comun = {"fecha": latest.get("fecha"), "tc": latest.get("tipo_cambio"),
             "tc_fuente": latest.get("tipo_cambio_fuente", "SUNAT"), "generado": latest.get("generado")}

    if out.exists():
        shutil.rmtree(out)
    (out / "producto").mkdir(parents=True)
    (out / ".nojekyll").write_text("")

    (out / "index.html").write_text(env.get_template("index.html").render(
        **comun, productos=productos, conteo=conteo, estados=ESTADOS,
        errores=latest.get("errores", []), raiz="",
    ), encoding="utf-8")

    tpl = env.get_template("producto.html")
    for p in productos:
        (out / "producto" / f"{slug(p['id'])}.html").write_text(tpl.render(
            **comun, p=p, serie=series.get(p["id"], []), raiz="../",
        ), encoding="utf-8")
    print(f"Web generada en {out}/ ({len(productos)} productos)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="site")
    ap.add_argument("--templates", default=str(Path(__file__).parent / "templates"))
    a = ap.parse_args()
    construir(Path(a.data), Path(a.out), Path(a.templates))
