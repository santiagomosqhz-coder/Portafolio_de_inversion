"""Una compra de acciones y, si ya ocurrió, la venta que la cerró."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .operacion import Operacion

@dataclass
class Lote:
    empresa: str                          # nombre conocido de la empresa
    simbolo: str
    compra: Operacion
    venta: Optional[Operacion]            # None mientras la venta no haya ocurrido
    acciones: float                       # acciones que se tienen (ajustadas por splits si es abierta)
    precio_actual: Optional[float] = None  # último cierre en COP (solo posiciones abiertas)
    fecha_precio: Optional[date] = None

    @property
    def abierta(self) -> bool:
        return self.venta is None

    @property
    def fecha_venta_prevista(self) -> Optional[date]:
        return self.compra.fecha_venta_prevista

    @property
    def costo(self) -> float:
        return self.compra.monto_bruto

    @property
    def valor_actual(self) -> Optional[float]:
        if self.abierta and self.precio_actual is not None:
            return self.acciones * self.precio_actual
        return None

    @property
    def dinero_recibido(self) -> Optional[float]:
        return self.venta.monto_bruto if self.venta else None

    @property
    def ganancia_no_realizada(self) -> Optional[float]:
        """Ganancia "en papel" de una posición abierta."""
        valor = self.valor_actual
        return valor - self.costo if valor is not None else None

    @property
    def ganancia_realizada(self) -> Optional[float]:
        """Ganancia ya cobrada de una posición vendida."""
        recibido = self.dinero_recibido
        return recibido - self.costo if recibido is not None else None

    @property
    def ganancia(self) -> Optional[float]:
        return self.ganancia_realizada if not self.abierta else self.ganancia_no_realizada

    @property
    def rentabilidad(self) -> Optional[float]:
        g = self.ganancia
        return g / self.costo if g is not None and self.costo > 0 else None
