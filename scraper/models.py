from dataclasses import dataclass, asdict


@dataclass
class Offer:
    tienda: str
    titulo: str
    precio: float      # en la moneda de la tienda
    moneda: str        # "USD" o "PEN"
    url: str

    def to_dict(self) -> dict:
        return asdict(self)


def contiene_marca(titulo: str, marca: str) -> bool:
    """True si el título menciona la marca (sin importar mayúsculas ni apóstrofes)."""
    limpio = lambda s: s.lower().replace("'", "").replace("’", "")
    return limpio(marca) in limpio(titulo)
