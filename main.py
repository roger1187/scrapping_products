"""Orquesta la corrida diaria: tipo de cambio -> tiendas USA -> tiendas Lima -> margen -> data/."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

from scraper import notify  # noqa: E402
from scraper.compare import evaluar  # noqa: E402
from scraper.fx import tipo_cambio_sunat  # noqa: E402
from scraper.sources.lima import mercadolibre  # noqa: E402
from scraper.sources.usa import amazon  # noqa: E402

# Ninguna tienda es la favorita: se consultan todas y gana la más barata.
# Cada módulo nuevo (google_shopping, walmart, target, brand_site...) se agrega aquí.
USA_SOURCES = [amazon]
LIMA_SOURCES = [mercadolibre]

DATA = Path("data")


def consultar(fuentes: list, query: str, marca: str) -> list:
    """Junta las ofertas de todas las fuentes; si una falla, se registra y se sigue."""
    ofertas = []
    for fuente in fuentes:
        try:
            ofertas += fuente.get_offers(query, marca)
        except Exception as e:
            print(f"[{fuente.__name__}] falló con '{query}': {e}")
    return ofertas


def cargar_ayer() -> dict:
    archivos = sorted((DATA / "history").glob("*.json"))
    hoy = dt.date.today().isoformat()
    previos = [a for a in archivos if a.stem < hoy]
    if not previos:
        return {}
    filas = json.loads(previos[-1].read_text(encoding="utf-8")).get("productos", [])
    return {f["id"]: f for f in filas}


def main(dry_run: bool) -> None:
    cfg = yaml.safe_load(Path("products.yaml").read_text(encoding="utf-8"))
    tc = tipo_cambio_sunat()
    ayer = cargar_ayer()

    filas = []
    for p in cfg["products"]:
        usa = consultar(USA_SOURCES, p["usa"], p["marca"]) if p.get("usa") else []
        lima = consultar(LIMA_SOURCES, p["lima"], p["marca"]) if p.get("lima") else []
        fila = evaluar(p, usa, lima, tc)
        previo = ayer.get(p["id"], {})
        if previo.get("precio_usa_usd") and fila.get("precio_usa_usd"):
            fila["precio_usa_ayer"] = previo["precio_usa_usd"]
            fila["delta_pct_vs_ayer"] = round((fila["precio_usa_usd"] / previo["precio_usa_usd"] - 1) * 100, 1)
        fila["estado_ayer"] = previo.get("estado")
        fila["tienda_ayer"] = previo.get("tienda_ganadora")
        filas.append(fila)

    filas.sort(key=lambda f: f.get("margen_pct", -999), reverse=True)
    print(f"Tipo de cambio: {tc}")
    print(tabulate(
        [[f["marca"], f["nombre"], f.get("precio_usa_usd"), f.get("tienda_ganadora"), f.get("costo_lima_pen"),
          f.get("precio_lima_ref_pen"), f.get("margen_pen"), f.get("margen_pct"), f["estado"]] for f in filas],
        headers=["Marca", "Producto", "USA $", "Tienda", "Costo Lima S/", "Ref Lima S/", "Margen S/", "%", "Estado"],
    ))
    if dry_run:
        return

    hoy = dt.date.today().isoformat()
    salida = {"fecha": hoy, "tipo_cambio": tc, "productos": filas}
    (DATA / "history").mkdir(parents=True, exist_ok=True)
    texto = json.dumps(salida, ensure_ascii=False, indent=2)
    (DATA / "latest.json").write_text(texto, encoding="utf-8")
    (DATA / "history" / f"{hoy}.json").write_text(texto, encoding="utf-8")

    avisos = []
    for f in filas:
        if f["estado"] == "VERDE" and f.get("estado_ayer") != "VERDE":
            avisos.append(f"VERDE: {f['marca']} {f['nombre']} en {f['tienda_ganadora']} "
                          f"${f['precio_usa_usd']} -> margen S/ {f['margen_pen']} ({f['margen_pct']}%)")
        elif f.get("tienda_ayer") and f.get("tienda_ganadora") and f["tienda_ayer"] != f["tienda_ganadora"]:
            avisos.append(f"Cambió la tienda más barata: {f['marca']} {f['nombre']} "
                          f"{f['tienda_ayer']} -> {f['tienda_ganadora']} (${f['precio_usa_usd']})")
    if avisos:
        link = os.getenv("SITE_BASE_URL") or ""
        notify.telegram("\n".join(avisos) + (f"\n{link}" if link else ""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="solo imprime la tabla, no escribe archivos ni avisa")
    main(ap.parse_args().dry_run)
