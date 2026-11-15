from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

from .almacen import Almacen
from .analisis_portafolio import AnalisisPortafolio
from .calculadora_rentabilidad import CalculadoraRentabilidad
from .cdt import Cdt
from .datos_mercado import DatosMercado
from .error_precios import ErrorPrecios
from .operacion import Operacion
from .posicion import Posicion
from .renta_fija import InversionRentaFija
from .resumen import Resumen
from .servicio_precios import ServicioPrecios

Splits = Sequence[Tuple[date, float]]
EPS = 1e-9
