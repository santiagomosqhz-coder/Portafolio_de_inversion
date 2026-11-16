"""Empresas disponibles para invertir, con el nombre por el que se conocen."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, List, Optional, Tuple


@dataclass(frozen=True)
class Empresa:
    nombre: str      # nombre conocido (no abreviado) que ve el usuario
    simbolo: str     # símbolo en Yahoo Finance (uso interno)

    # Todas cotizan en dólares (NYSE o Nasdaq); el programa las convierte a COP.
    CATALOGO: ClassVar[Tuple[Tuple[str, str], ...]] = (
        ("Amazon", "AMZN"), ("Apple", "AAPL"), ("Bancolombia", "CIB"), ("Coca-Cola", "KO"),
        ("Disney", "DIS"), ("Ecopetrol", "EC"), ("Google (Alphabet)", "GOOGL"), ("McDonald's", "MCD"),
        ("Meta (Facebook)", "META"), ("Microsoft", "MSFT"), ("Netflix", "NFLX"), ("Nike", "NKE"),
        ("NVIDIA", "NVDA"), ("Starbucks", "SBUX"), ("Tesla", "TSLA"), ("Walmart", "WMT"),
    )

    @classmethod
    def todas(cls) -> List["Empresa"]:
        return [cls(nombre, simbolo) for nombre, simbolo in cls.CATALOGO]

    @classmethod
    def por_simbolo(cls, simbolo: str) -> Optional["Empresa"]:
        return next((e for e in cls.todas() if e.simbolo == simbolo.upper()), None)

    @classmethod
    def por_nombre(cls, nombre: str) -> Optional["Empresa"]:
        return next((e for e in cls.todas() if e.nombre == nombre), None)
