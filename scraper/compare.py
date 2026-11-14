"""Regla de negocio: mejor oferta USA vs. precio de referencia en Lima -> costo, venta objetivo, margen y semáforo."""
import os

from scraper.models import Offer, filtrar_lima, filtrar_usa, ordenar_ofertas

FACTOR_DEFAULT = 1.25
DESCUENTO_VS_LIMA = 0.92   # vendemos 8 % debajo del más barato en Lima
UMBRAL_VERDE = 35.0
UMBRAL_AMARILLO = 20.0


def factor_importacion() -> float:
    """Se lee en cada llamada (no al importar) para respetar .env y los cambios en tests."""
    try:
        return float(os.getenv("FACTOR_IMPORTACION") or FACTOR_DEFAULT)
    except ValueError:
        return FACTOR_DEFAULT


def semaforo(margen_pct: float) -> str:
    if margen_pct >= UMBRAL_VERDE:
        return "VERDE"
    if margen_pct >= UMBRAL_AMARILLO:
        return "AMARILLO"
    return "ROJO"


def evaluar(producto: dict, ofertas_usa: list[Offer], ofertas_lima: list[Offer], tc: float) -> dict:
    """Filtra ofertas irrelevantes, elige la USA más barata (de cualquier tienda) y calcula costo y margen."""
    base = {"id": producto["id"], "marca": producto["marca"], "nombre": producto["nombre"]}

    usa = ordenar_ofertas(filtrar_usa(ofertas_usa, producto), producto["marca"])
    lima = sorted(filtrar_lima(ofertas_lima, producto), key=lambda o: o.precio)

    # precio_lima_manual solo cuando no hay ningún resultado real en Lima
    lima_estimado = False
    if lima:
        precio_lima_ref = lima[0].precio
    elif producto.get("precio_lima_manual"):
        precio_lima_ref = float(producto["precio_lima_manual"])
        lima_estimado = True
    else:
        precio_lima_ref = None

    fila = {
        **base,
        "tc": tc,
        "ranking_tiendas": _ranking_por_tienda(usa),
        "lima_estimado": lima_estimado,
        "busqueda_lima": producto.get("lima") or f"{producto['marca']} {producto['nombre']}",
        "ofertas_lima": _sin_repetidas(lima),
    }
    if usa:
        g = usa[0]
        fila.update({
            "precio_usa_usd": round(g.precio, 2),
            "tienda_ganadora": g.tienda,
            "url_ganadora": g.url,
            "titulo_ganador": g.titulo,
            "envio_gratis": g.envio_gratis,
            "fecha_precio_usa": g.fecha,     # None = consultado hoy
            "nota_usa": g.nota,
        })
    if precio_lima_ref is not None:
        fila["precio_lima_ref_pen"] = round(precio_lima_ref)
        fila["tienda_lima_ref"] = lima[0].tienda if lima else "Referencia manual"

    if not usa or precio_lima_ref is None:
        fila["estado"] = "SIN DATOS"
        fila["falta"] = "USA" if not usa else "Lima"
        return fila

    costo_lima = usa[0].precio * tc * factor_importacion()
    venta = precio_lima_ref * DESCUENTO_VS_LIMA
    margen = venta - costo_lima
    pct = round(margen / venta * 100, 1)
    fila.update({
        "costo_lima_pen": round(costo_lima),
        "venta_objetivo_pen": round(venta),
        "margen_pen": round(margen),
        "margen_pct": pct,
        "estado": semaforo(pct),
    })
    return fila


def _sin_repetidas(lima: list[Offer]) -> list[dict]:
    """Todas las publicaciones de Lima que pasaron los filtros (más barata primero), sin duplicados."""
    vistas, out = set(), []
    for o in lima:
        clave = (o.tienda, o.url or o.titulo, round(o.precio, 2))
        if clave in vistas:
            continue
        vistas.add(clave)
        out.append({"tienda": o.tienda, "precio_pen": round(o.precio, 2), "url": o.url, "titulo": o.titulo})
    return out


def _ranking_por_tienda(ofertas_ordenadas: list[Offer]) -> list[dict]:
    """La mejor oferta de cada tienda, en el mismo orden que el desempate."""
    vistas, ranking = set(), []
    for o in ofertas_ordenadas:
        if o.tienda in vistas:
            continue
        vistas.add(o.tienda)
        ranking.append({
            "tienda": o.tienda, "precio_usd": round(o.precio, 2), "url": o.url, "titulo": o.titulo,
            "envio_gratis": o.envio_gratis, "fecha": o.fecha, "nota": o.nota,
        })
    return ranking
