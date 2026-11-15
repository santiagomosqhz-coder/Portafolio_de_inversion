"""Totales consolidados del portafolio en una moneda."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Resumen:
    moneda: str
    invertido_rv: float = 0.0          # compras de acciones (con comisiones)
    invertido_rf: float = 0.0          # capital + comisiones de renta fija
    valor_rv: float = 0.0              # valor de mercado de las acciones que se tienen
    valor_rf: float = 0.0              # valor vigente de la renta fija
    realizada_rv: float = 0.0
    realizada_rf: float = 0.0          # intereses ya cobrados (vencidas o vendidas)
    no_realizada_rv: float = 0.0
    no_realizada_rf: float = 0.0       # intereses causados de lo que sigue vigente
    dividendos: float = 0.0
    rentabilidad_ea: Optional[float] = None
    dias: int = 0                      # días entre el primer flujo y hoy

    @property
    def total_invertido(self) -> float:
        return self.invertido_rv + self.invertido_rf

    @property
    def valor_actual(self) -> float:
        return self.valor_rv + self.valor_rf

    @property
    def realizada(self) -> float:
        return self.realizada_rv + self.realizada_rf

    @property
    def no_realizada(self) -> float:
        return self.no_realizada_rv + self.no_realizada_rf

    @property
    def ganancia_rv(self) -> float:
        return self.realizada_rv + self.no_realizada_rv + self.dividendos

    @property
    def ganancia_rf(self) -> float:
        return self.realizada_rf + self.no_realizada_rf

    @property
    def ganancia_total(self) -> float:
        return self.ganancia_rv + self.ganancia_rf

    @property
    def rentabilidad_acumulada(self) -> Optional[float]:
        return self.ganancia_total / self.total_invertido if self.total_invertido > 0 else None

    @property
    def pct_rv(self) -> Optional[float]:
        return self.valor_rv / self.valor_actual if self.valor_actual > 0 else None

    @property
    def pct_rf(self) -> Optional[float]:
        return self.valor_rf / self.valor_actual if self.valor_actual > 0 else None
