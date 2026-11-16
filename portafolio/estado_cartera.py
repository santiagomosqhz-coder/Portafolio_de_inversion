"""Fotografía de la cartera en una fecha: saldo, posiciones y ganancias."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from .lote import Lote


@dataclass
class EstadoCartera:
    hoy: date
    saldo: float
    lotes: List[Lote] = field(default_factory=list)
    errores: Dict[str, str] = field(default_factory=dict)   # empresa -> motivo
    fuente: Optional[str] = None
    consultado_en: Optional[datetime] = None

    @property
    def abiertas(self) -> List[Lote]:
        return [l for l in self.lotes if l.abierta]

    @property
    def cerradas(self) -> List[Lote]:
        return [l for l in self.lotes if not l.abierta]

    @property
    def valor_abiertas(self) -> float:
        return sum(l.valor_actual for l in self.abiertas if l.valor_actual is not None)

    @property
    def valor_total(self) -> float:
        """Saldo disponible + valor de las acciones que se tienen."""
        return self.saldo + self.valor_abiertas

    @property
    def realizada(self) -> float:
        return sum(l.ganancia_realizada for l in self.cerradas if l.ganancia_realizada is not None)

    @property
    def no_realizada(self) -> float:
        return sum(l.ganancia_no_realizada for l in self.abiertas if l.ganancia_no_realizada is not None)

    @property
    def esta_completo(self) -> bool:
        return not self.errores
