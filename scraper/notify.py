import os

import requests

UMBRAL_BAJA_PCT = 15.0   # avisar si el mejor precio USA baja más que esto vs. ayer


def armar_avisos(filas: list[dict]) -> list[str]:
    """Una línea por producto que: pasó a VERDE, cambió de tienda ganadora o bajó más de 15 % vs. ayer."""
    lineas = []
    for f in filas:
        motivos = []
        if f.get("estado") == "VERDE" and f.get("estado_ayer") != "VERDE":
            motivos.append("pasó a VERDE")
        if f.get("tienda_ayer") and f.get("tienda_ganadora") and f["tienda_ayer"] != f["tienda_ganadora"]:
            motivos.append(f"ahora más barato en {f['tienda_ganadora']} (antes {f['tienda_ayer']})")
        delta = f.get("delta_pct_vs_ayer")
        if delta is not None and delta < -UMBRAL_BAJA_PCT:
            motivos.append(f"bajó {abs(delta):.1f} % vs. ayer")
        if not motivos:
            continue
        linea = f"• {f['marca']} {f['nombre']}: {', '.join(motivos)}. ${f['precio_usa_usd']} en {f['tienda_ganadora']}"
        if f.get("margen_pen") is not None:
            linea += f" → margen S/ {f['margen_pen']} ({f['margen_pct']} %)"
        lineas.append(linea)
    return lineas


def mensaje_diario(filas: list[dict], fecha: str, tc: float, link: str = "") -> str | None:
    avisos = armar_avisos(filas)
    if not avisos:
        return None
    partes = [f"Precios bebé {fecha} (TC {tc})", *avisos]
    if link:
        partes.append(link)
    return "\n".join(partes)


def telegram(msg: str) -> None:
    """Envía un mensaje al chat configurado; si no hay credenciales no hace nada."""
    tok, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        print("[telegram] sin TELEGRAM_TOKEN/TELEGRAM_CHAT_ID; no se envía")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            json={"chat_id": chat, "text": msg, "disable_web_page_preview": True},
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:  # nunca abortar la corrida por un aviso
        # no imprimir la URL: lleva el token
        print(f"[telegram] no se pudo enviar: {type(e).__name__}")
