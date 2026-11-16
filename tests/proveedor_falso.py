"""Proveedor con datos SINTÉTICOS, usado únicamente en las pruebas automáticas.

La aplicación nunca lo usa: en ejecución normal los precios vienen de Yahoo Finance
o de Alpha Vantage, y si ambos fallan se muestra un error.
"""
from datetime import date, datetime

import pandas as pd

from portafolio.datos_mercado import DatosMercado
from portafolio.error_precios import ErrorPrecios
from portafolio.proveedor_precios import ProveedorPrecios

class ProveedorFalso(ProveedorPrecios):
    nombre = "Falso (solo pruebas)"

    def __init__(self, cierres=None, dividendos=None, splits=None, falla=False, moneda="USD"):
        self.cierres = cierres or {}
        self.dividendos = dividendos or {}
        self.splits = splits or {}
        self.falla = falla
        self.moneda = moneda
        self.llamadas = 0

    def obtener(self, simbolo, inicio, fin):
        self.llamadas += 1
        if self.falla or simbolo not in self.cierres:
            raise ErrorPrecios(f"sin datos de {simbolo}")
        serie = lambda d: pd.Series({pd.Timestamp(k): v for k, v in sorted(d.get(simbolo, {}).items())}, dtype=float)  # noqa: E731
        return DatosMercado(
            simbolo=simbolo, cierres=serie(self.cierres), dividendos=serie(self.dividendos),
            splits=serie(self.splits), moneda=self.moneda, nombre=f"{simbolo} Inc.",
            fuente=self.nombre, consultado_en=datetime.now(),
        )
