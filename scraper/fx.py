import requests

FALLBACK = 3.80


def tipo_cambio_sunat() -> float:
    """Tipo de cambio venta SUNAT del día; si la API falla usa un valor fijo conservador."""
    try:
        r = requests.get("https://api.apis.net.pe/v1/tipo-cambio-sunat", timeout=10)
        r.raise_for_status()
        return float(r.json()["venta"])
    except Exception:
        return FALLBACK
