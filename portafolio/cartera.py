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
    def preparar_compra(self, empresa: Empresa, cantidad: float, fecha_compra: date,
                        fecha_venta: date, hoy: Optional[date] = None) -> Tuple[Operacion, DatosMercado]:
        """Valida y calcula la compra (consulta internet). No guarda nada todavía."""
        hoy = hoy or date.today()
        if cantidad <= 0:
            raise ValueError("La cantidad de acciones debe ser mayor que cero.")
        if fecha_compra > hoy:
            raise ValueError("La fecha de compra no puede ser futura: solo se compra a precios ya conocidos.")
        if fecha_venta <= fecha_compra:
            raise ValueError("La fecha de venta prevista debe ser posterior a la fecha de compra.")

        datos = self.datos_en_cop(empresa.simbolo, fecha_compra, hoy)
        fecha_precio, precio_ajustado = datos.precio_en(fecha_compra)
        if (fecha_compra - fecha_precio).days > self.MAX_DIAS_SIN_PRECIO:
            raise ErrorPrecios(f"No hay precios de {empresa.nombre} cerca del {fecha_compra}: "
                               f"el más cercano es del {fecha_precio}.")
        # Yahoo entrega precios ajustados por splits posteriores; el precio realmente pagado era mayor.
        precio_real = precio_ajustado * Portafolio.factor_split(datos.lista_splits, fecha_compra)
        costo = cantidad * precio_real
        if costo > self.saldo() + 1e-6:
            raise ValueError(f"Saldo insuficiente: la compra cuesta {fmt_cop(costo)} "
                             f"y su saldo disponible es {fmt_cop(self.saldo())}.")
        operacion = Operacion(simbolo=empresa.simbolo, tipo=Operacion.COMPRA, fecha=fecha_compra,
                              cantidad=cantidad, precio=precio_real, comision=0.0, moneda="COP",
                              fecha_venta_prevista=fecha_venta)
        return operacion, datos


