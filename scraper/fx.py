import requests

FALLBACK = 3.80
URL = "https://api.apis.net.pe/v1/tipo-cambio-sunat"


def tipo_cambio() -> tuple[float, str]:
    """(valor, fuente): venta SUNAT del día, o el valor fijo conservador si la API falla o responde algo absurdo."""
    try:
        r = requests.get(URL, timeout=10)
        r.raise_for_status()
        venta = float(r.json()["venta"])
        if not 2.5 < venta < 6.0:
            raise ValueError(f"valor fuera de rango: {venta}")
        return venta, "SUNAT"
    except Exception as e:
        print(f"[fx] uso tipo de cambio fijo {FALLBACK}: {e}")
        return FALLBACK, "fijo"


def tipo_cambio_sunat() -> float:
    return tipo_cambio()[0]
