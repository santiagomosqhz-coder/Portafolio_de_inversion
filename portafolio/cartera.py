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
    SALDO_INICIAL = 10_000_000.0   # COP
    MAX_DIAS_SIN_PRECIO = 7

    portafolio: Portafolio
    servicio: ServicioPrecios

    def __init__(self, portafolio: Portafolio, servicio: ServicioPrecios):
        self.portafolio = portafolio
        self.servicio = servicio
    def saldo(self) -> float:
        """10.000.000 − compras + ventas (solo operaciones ya registradas)."""
        return self.SALDO_INICIAL + sum(o.flujo_caja for o in self.portafolio.operaciones)
    
    def datos_en_cop(self, simbolo: str, desde: date, hoy: date) -> DatosMercado:
        datos = self.servicio.obtener(simbolo, desde, hoy)
        if datos.moneda and datos.moneda.upper() != "COP":
            raise ErrorPrecios(f"{simbolo}: la fuente entregó precios en {datos.moneda}, no en COP.")
        return datos


