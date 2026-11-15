"""Convierte a pesos colombianos (COP) los precios de otra fuente, día por día."""
from __future__ import annotations

import dataclasses
from datetime import date

import pandas as pd

from .datos_mercado import DatosMercado
from .error_precios import ErrorPrecios
from .proveedor_precios import ProveedorPrecios

