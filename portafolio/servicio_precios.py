"""Obtiene precios probando las fuentes en orden y guarda lo consultado en memoria."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from .datos_mercado import DatosMercado
from .error_precios import ErrorPrecios
from .proveedor_precios import ProveedorPrecios