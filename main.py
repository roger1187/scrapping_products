"""Orquesta la corrida diaria: tipo de cambio -> tiendas USA -> tiendas Lima -> margen -> data/."""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

from scraper import notify  # noqa: E402
from scraper.compare import evaluar  # noqa: E402
from scraper.cuota import Cupos, es_limitada, nombre_fuente  # noqa: E402
from scraper.fx import tipo_cambio  # noqa: E402
from scraper.sources.lima import mercadolibre  # noqa: E402
from scraper.sources.usa import amazon, google_shopping  # noqa: E402

# Ninguna tienda es la favorita: se consultan todas y gana la más barata.
# Cada módulo nuevo (walmart, target, brand_site...) se agrega aquí y no hay que tocar nada más.
# Un módulo puede definir disponible() -> bool para omitirse (p. ej. sin API key) y ENV_MAX_DIARIO para tener cupo.
USA_SOURCES = [google_shopping, amazon]
LIMA_SOURCES = [mercadolibre]

DATA = Path("data")
PRODUCTOS = Path("products.yaml")
OBLIGATORIOS = ("id", "marca", "nombre")
SECRETOS = ("SERPAPI_KEY", "KEEPA_API_KEY", "TELEGRAM_TOKEN", "ML_CLIENT_SECRET")


def ocultar_secretos(texto: str) -> str:
    for var in SECRETOS:
        valor = os.getenv(var)
        if valor and len(valor) >= 6:
            texto = texto.replace(valor, "***")
    return texto


def cargar_productos(ruta: Path = PRODUCTOS) -> list[dict]:
    """Lee y valida products.yaml. Un error de configuración sí detiene la corrida, con un mensaje claro."""
    if not ruta.exists():
        sys.exit(f"No encuentro {ruta}. Ejecuta desde la carpeta del proyecto.")
    try:
        cfg = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        sys.exit(f"{ruta} tiene un error de formato YAML:\n{e}")
    productos, vistos = [], set()
    for i, p in enumerate(cfg.get("products") or [], 1):
        faltan = [c for c in OBLIGATORIOS if not (isinstance(p, dict) and p.get(c))]
        if faltan:
            print(f"[config] producto #{i} sin {', '.join(faltan)}; se omite")
            continue
        p["id"] = str(p["id"])
        if p["id"] in vistos:
            print(f"[config] id repetido '{p['id']}'; se omite el duplicado")
            continue
        vistos.add(p["id"])
        productos.append(p)
    if not productos:
        sys.exit(f"{ruta} no tiene productos válidos.")
    return productos


def consultar(fuentes: list, producto: dict, campo: str, cupos: Cupos | None, errores: list) -> list:
    """Junta las ofertas de todas las fuentes; si una falla, se registra y se sigue."""
    query = producto.get(campo)
    if not query:
        return []
    ofertas = []
    for fuente in fuentes:
        nombre = nombre_fuente(fuente)
        if hasattr(fuente, "disponible") and not fuente.disponible():
            continue
        try:
            if cupos and es_limitada(fuente):
                ofertas += cupos.obtener(fuente, producto["id"], lambda: fuente.get_offers(query, producto["marca"]))
            else:
                ofertas += fuente.get_offers(query, producto["marca"])
        except Exception as e:
            msg = ocultar_secretos(f"{e}")[:300]
            print(f"[{nombre}] falló con '{query}': {msg}")
            errores.append({"fuente": nombre, "producto": producto["id"], "error": msg})
    return ofertas


def cargar_ayer(hoy: str) -> dict:
    archivos = sorted((DATA / "history").glob("*.json"), reverse=True)
    for a in archivos:
        if a.stem >= hoy:
            continue
        try:
            filas = json.loads(a.read_text(encoding="utf-8")).get("productos", [])
            return {f["id"]: f for f in filas}
        except (OSError, ValueError, KeyError) as e:
            print(f"[historial] {a} ilegible ({e}); pruebo el anterior")
    return {}


def comparar_con_ayer(fila: dict, previo: dict) -> None:
    if previo.get("precio_usa_usd") and fila.get("precio_usa_usd"):
        fila["precio_usa_ayer"] = previo["precio_usa_usd"]
        fila["delta_pct_vs_ayer"] = round((fila["precio_usa_usd"] / previo["precio_usa_usd"] - 1) * 100, 1)
    fila["estado_ayer"] = previo.get("estado")
    fila["tienda_ayer"] = previo.get("tienda_ganadora")


def main(dry_run: bool) -> None:
    productos = cargar_productos()
    hoy = dt.date.today().isoformat()
    tc, tc_fuente = tipo_cambio()
    ayer = cargar_ayer(hoy)

    cupos = Cupos(DATA / "cache_fuentes.json", hoy)
    for fuente in USA_SOURCES + LIMA_SOURCES:
        if es_limitada(fuente) and (not hasattr(fuente, "disponible") or fuente.disponible()):
            campo = "usa" if fuente in USA_SOURCES else "lima"
            plan = cupos.preparar(fuente, [p["id"] for p in productos if p.get(campo)])
            print(f"[{nombre_fuente(fuente)}] hoy se consultan {len(plan)}: {', '.join(plan) or '-'}"
                  " (el resto usa el último precio conocido)")

    filas, errores = [], []
    for p in productos:
        try:
            usa = consultar(USA_SOURCES, p, "usa", cupos, errores)
            lima = consultar(LIMA_SOURCES, p, "lima", cupos, errores)
            fila = evaluar(p, usa, lima, tc)
        except Exception as e:   # un producto roto no tumba la corrida
            msg = ocultar_secretos(str(e))[:300]
            print(f"[{p['id']}] error inesperado: {msg}")
            errores.append({"fuente": "main", "producto": p["id"], "error": msg})
            fila = {"id": p["id"], "marca": p["marca"], "nombre": p["nombre"], "estado": "SIN DATOS",
                    "falta": "error", "ranking_tiendas": [], "ofertas_lima": [], "lima_estimado": False}
        comparar_con_ayer(fila, ayer.get(p["id"], {}))
        filas.append(fila)

    filas.sort(key=lambda f: f.get("margen_pct", -999), reverse=True)
    print(f"Tipo de cambio: {tc} ({tc_fuente})")
    print(tabulate(
        [[f["marca"], f["nombre"], f.get("precio_usa_usd"), f.get("tienda_ganadora"), f.get("costo_lima_pen"),
          f.get("precio_lima_ref_pen"), "estimado" if f.get("lima_estimado") else "",
          f.get("margen_pen"), f.get("margen_pct"), f["estado"]] for f in filas],
        headers=["Marca", "Producto", "USA $", "Tienda", "Costo Lima S/", "Ref Lima S/", "", "Margen S/", "%",
                 "Estado"],
    ))
    if dry_run:
        print("--dry-run: no se escribe data/ ni se avisa por Telegram")
        return

    salida = {
        "fecha": hoy,
        "generado": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "tipo_cambio": tc,
        "tipo_cambio_fuente": tc_fuente,
        "productos": filas,
        "errores": errores,
    }
    (DATA / "history").mkdir(parents=True, exist_ok=True)
    texto = json.dumps(salida, ensure_ascii=False, indent=2)
    (DATA / "latest.json").write_text(texto, encoding="utf-8")
    (DATA / "history" / f"{hoy}.json").write_text(texto, encoding="utf-8")
    cupos.guardar()

    msg = notify.mensaje_diario(filas, hoy, tc, os.getenv("SITE_BASE_URL") or "")
    if msg:
        notify.telegram(msg)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="solo imprime la tabla, no escribe archivos ni avisa")
    main(ap.parse_args().dry_run)
