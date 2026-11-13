"""Modelo de oferta y reglas comunes a todas las fuentes: relevancia, nombre de tienda y desempate."""
import re
from dataclasses import asdict, dataclass, fields


@dataclass
class Offer:
    tienda: str
    titulo: str
    precio: float               # en la moneda de la tienda
    moneda: str                 # "USD" o "PEN"
    url: str
    envio_gratis: bool = False
    condicion: str = "new"      # "new", "used", "refurbished"... si la fuente lo sabe
    fecha: str | None = None    # fecha del precio si viene de caché (None = consultado hoy)
    nota: str = ""              # cupón, vendedor, etc.

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Offer":
        validos = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in validos})


# ---------- relevancia ----------

def _limpio(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().replace("'", "").replace("’", "").replace("`", "")).strip()


def contiene_marca(titulo: str, marca: str) -> bool:
    """True si el título menciona la marca (sin importar mayúsculas, apóstrofes ni espacios)."""
    t, m = _limpio(titulo), _limpio(marca)
    return m in t or m.replace(" ", "") in t.replace(" ", "")


# "used" solo cuenta como condición, no en frases como "can be used as a blanket".
_USADO = re.compile(
    r"\b(renewed|refurbished|pre-?owned|second[- ]hand|reacondicionad[oa]|usad[oa])\b"
    r"|\bused\b(?!\s+(as|to|for|with|in|on|by|from|during|at)\b)",
    re.I,
)


def es_usado(oferta: Offer) -> bool:
    return oferta.condicion.lower() not in ("", "new", "nuevo") or bool(_USADO.search(oferta.titulo))


def _norm_variante(s: str) -> str:
    """'4-Pack' -> '4 pack', '0-3 Months' -> '0 3 months'."""
    return re.sub(r"\s+", " ", re.sub(r"[-_/]", " ", str(s).lower())).strip()


def cumple_variante(titulo: str, producto: dict) -> bool:
    """Si el producto define size o pack en el YAML, el título debe contenerlos."""
    t = _norm_variante(titulo)
    return all(_norm_variante(producto[c]) in t for c in ("size", "pack") if producto.get(c))


def filtrar_usa(ofertas: list[Offer], producto: dict) -> list[Offer]:
    return [
        o for o in ofertas
        if o.moneda == "USD" and o.precio > 0
        and contiene_marca(o.titulo, producto["marca"])
        and not es_usado(o)
        and cumple_variante(o.titulo, producto)
    ]


def filtrar_lima(ofertas: list[Offer], producto: dict) -> list[Offer]:
    return [
        o for o in ofertas
        if o.moneda == "PEN" and o.precio > 0
        and contiene_marca(o.titulo, producto["marca"])
        and not es_usado(o)
    ]


# ---------- tiendas ----------

_TIENDAS = {
    "amazon": "Amazon", "walmart": "Walmart", "target": "Target", "kohls": "Kohl's", "macys": "Macy's",
    "nordstrom": "Nordstrom", "nordstromrack": "Nordstrom Rack", "zappos": "Zappos", "ebay": "eBay",
    "buybuybaby": "buybuy BABY", "bestbuy": "Best Buy", "costco": "Costco", "samsclub": "Sam's Club",
    "dillards": "Dillard's", "bloomingdales": "Bloomingdale's", "saksfifthavenue": "Saks Fifth Avenue",
    "potterybarnkids": "Pottery Barn Kids",
}


def normalizar_tienda(nombre: str) -> str:
    """'Walmart - Seller' -> 'Walmart', 'Amazon.com' -> 'Amazon', 'Kohl's' -> 'Kohl's'."""
    base = re.split(r"\s+-\s+", (nombre or "").strip())[0]
    base = re.sub(r"\.(com|net|co|us)$", "", base, flags=re.I).strip()
    clave = re.sub(r"[^a-z0-9]", "", base.lower())
    for k, v in _TIENDAS.items():
        if clave == k or (k in ("amazon", "walmart", "target") and clave.startswith(k)):
            return v
    return base or "Desconocida"


ORDEN_CONFIANZA = ["Amazon", "Walmart", "Target"]   # la web de la marca va antes que todas


def confianza(tienda: str, marca: str) -> int:
    """0 = sitio de la marca, 1 Amazon, 2 Walmart, 3 Target, 4 resto."""
    t = re.sub(r"[^a-z0-9]", "", _limpio(tienda))
    m = re.sub(r"[^a-z0-9]", "", _limpio(marca))
    if m and m in t:
        return 0
    if tienda in ORDEN_CONFIANZA:
        return ORDEN_CONFIANZA.index(tienda) + 1
    return len(ORDEN_CONFIANZA) + 1


def ordenar_ofertas(ofertas: list[Offer], marca: str) -> list[Offer]:
    """Más barata primero. Empate de precio: envío gratis, luego marca > Amazon > Walmart > Target > resto."""
    return sorted(ofertas, key=lambda o: (round(o.precio, 2), not o.envio_gratis, confianza(o.tienda, marca)))
