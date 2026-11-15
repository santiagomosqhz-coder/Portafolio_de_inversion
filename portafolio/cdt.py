from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

@dataclass
class Cdt:
    monto: float             # dinero depositado, en COP
    tasa_ea: float           # tasa efectiva anual como fracción (0.115 = 11,5 %)
    fuente: str              # de dónde salió la tasa (banco, Superfinanciera, DTF, etc.)
    fecha_tasa: date         # fecha en que se consultó o se ofreció esa tasa
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    def validar(self, hoy: Optional[date] = None) -> None:
        hoy = hoy or date.today()
        if self.monto <= 0:
            raise ValueError("El monto del CDT debe ser mayor que cero.")
        if not 0 < self.tasa_ea < 1:
            raise ValueError("La tasa E.A. debe estar entre 0 % y 100 %. Escríbala en porcentaje, por ejemplo 11,5.")
        if not (self.fuente or "").strip():
            raise ValueError("Indique la fuente de la tasa (por ejemplo, el banco que la ofrece).")
        if self.fecha_tasa > hoy:
            raise ValueError("La fecha de la tasa no puede ser futura.")

    @property
    def rentabilidad_diaria(self) -> float:
        """(1 + tasa_anual)^(1/365) − 1"""
        return (1.0 + self.tasa_ea) ** (1.0 / 365.0) - 1.0

    @property

