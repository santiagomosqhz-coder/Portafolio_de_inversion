from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Tuple

import pandas as pd

from .posicion import Posicion
from .renta_fija import InversionRentaFija
from .resumen import Resumen

@dataclass
class AnalisisPortafolio:
    fecha_calculo: date
    posiciones: List[Posicion] = field(default_factory=list)
    renta_fija: List[InversionRentaFija] = field(default_factory=list)
    resumenes: Dict[str, Resumen] = field(default_factory=dict)          # por moneda
    evolucion: Dict[str, pd.DataFrame] = field(default_factory=dict)     # por moneda
    advertencias: List[str] = field(default_factory=list)
    errores: Dict[str, str] = field(default_factory=dict)                # por símbolo
    fuentes: Dict[str, Tuple[str, datetime]] = field(default_factory=dict)  # símbolo -> (fuente, consulta)

    @property
    def esta_completo(self) -> bool:
        return not self.errores
