from __future__ import annotations

import math
from datetime import date
from typing import List, Optional, Sequence, Tuple

Flujo = Tuple[date, float]


class CalculadoraRentabilidad:
    # Con menos días de historia, anualizar sería extrapolar demasiado: no se calcula.
    DIAS_MINIMOS_EA = 30

    @staticmethod
    def rentabilidad_simple(ganancia: float, base: float) -> Optional[float]:
        """ganancia / base, o None si no hay base sobre la cual calcular."""
        if base is None or base <= 0:
            return None
        return ganancia / base

    @staticmethod
