from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

from .datos_mercado import DatosMercado
from .empresa import Empresa
from .error_precios import ErrorPrecios
from .estado_cartera import EstadoCartera
from .lote import Lote
from .operacion import Operacion
from .portafolio import Portafolio
from .servicio_precios import ServicioPrecios
from .utilidades import fmt_cop


VentaPendiente = Tuple[Operacion, list]   # (operación de venta, splits para validarla)

class Cartera:
