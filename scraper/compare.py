import os

FACTOR = float(os.getenv("FACTOR_IMPORTACION") or "1.25")
DESCUENTO_VS_LIMA = 0.92   # vendemos 8 % debajo del más barato en Lima


def evaluar(producto: dict, ofertas_usa: list, ofertas_lima: list, tc: float) -> dict:
    """Elige la oferta USA más barata (de cualquier tienda) y calcula costo en Lima y margen."""
    base = {"id": producto["id"], "marca": producto["marca"], "nombre": producto["nombre"]}

    usa = sorted((o for o in ofertas_usa if o.moneda == "USD"), key=lambda o: o.precio)
    lima_vals = [o.precio for o in ofertas_lima if o.moneda == "PEN"]
    if producto.get("precio_lima_manual"):
        lima_vals.append(float(producto["precio_lima_manual"]))

    ranking = _ranking_por_tienda(usa)
    if not usa or not lima_vals:
        return {**base, "estado": "SIN DATOS", "ranking_tiendas": ranking}

    ganadora = usa[0]
    precio_lima_ref = min(lima_vals)
    costo_lima = ganadora.precio * tc * FACTOR
    venta = precio_lima_ref * DESCUENTO_VS_LIMA
    margen = venta - costo_lima
    pct = margen / venta
    estado = "VERDE" if pct >= 0.35 else "AMARILLO" if pct >= 0.20 else "ROJO"

    return {
        **base,
        "precio_usa_usd": round(ganadora.precio, 2),
        "tienda_ganadora": ganadora.tienda,
        "url_ganadora": ganadora.url,
        "titulo_ganador": ganadora.titulo,
        "tc": tc,
        "costo_lima_pen": round(costo_lima),
        "precio_lima_ref_pen": round(precio_lima_ref),
        "venta_objetivo_pen": round(venta),
        "margen_pen": round(margen),
        "margen_pct": round(pct * 100, 1),
        "estado": estado,
        "ranking_tiendas": ranking,
    }


def _ranking_por_tienda(ofertas_ordenadas: list) -> list[dict]:
    """La oferta más barata de cada tienda, de menor a mayor precio."""
    vistas, ranking = set(), []
    for o in ofertas_ordenadas:
        if o.tienda in vistas:
            continue
        vistas.add(o.tienda)
        ranking.append({"tienda": o.tienda, "precio_usd": round(o.precio, 2), "url": o.url})
    return ranking
