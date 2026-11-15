"""Contrato común de las fuentes de precios históricos."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from .datos_mercado import DatosMercado


class ProveedorPrecios(ABC):
    """Una fuente de precios. Cada fuente concreta vive en su propio archivo."""

    nombre: str = ""
    requiere_clave: bool = False

    @abstractmethod
    def obtener(self, simbolo: str, inicio: date, fin: date) -> DatosMercado:
        """Devuelve cierres diarios entre `inicio` y `fin` o lanza ErrorPrecios."""