from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime

import pandas as pd

from .datos_mercado import DatosMercado
from .error_precios import ErrorPrecios
from .proveedor_precios import ProveedorPrecios