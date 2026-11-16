"""Proveedor con datos SINTÉTICOS, usado únicamente en las pruebas automáticas.

La aplicación nunca lo usa: en ejecución normal los precios vienen de Yahoo Finance
o de Alpha Vantage, y si ambos fallan se muestra un error.
"""
from datetime import date, datetime

import pandas as pd

from portafolio.datos_mercado import DatosMercado
from portafolio.error_precios import ErrorPrecios
from portafolio.proveedor_precios import ProveedorPrecios