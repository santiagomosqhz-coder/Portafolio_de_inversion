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
    def xirr(flujos: Sequence[Flujo]) -> Optional[float]:
        """Tasa efectiva anual que hace cero el valor presente neto de los flujos.

        Resuelve  sum( monto_i / (1+r)^(dias_i/365) ) = 0  por bisección.
        Es la tasa E.A. ponderada por dinero (considera cuándo entra y sale cada peso).
        Devuelve None si no hay al menos una salida y una entrada de dinero.
        """
        flujos = [(d, m) for d, m in flujos if abs(m) > 1e-12]
        if len(flujos) < 2 or not (any(m < 0 for _, m in flujos) and any(m > 0 for _, m in flujos)):
            return None
        d0 = min(d for d, _ in flujos)
        tiempos = [((d - d0).days / 365.0, m) for d, m in flujos]
        def valor_presente(r: float) -> float:
            total = 0.0
            log_base = math.log1p(r)
            for t, m in tiempos:
                try:
                    total += m * math.exp(-t * log_base)
                except OverflowError:
                    total += math.copysign(float("inf"), m)
            return total

        bajo, alto = -0.999999, 1.0
        f_bajo, f_alto = valor_presente(bajo), valor_presente(alto)
        while f_bajo * f_alto > 0 and alto < 1e9:
            alto *= 2
            f_alto = valor_presente(alto)
        if f_bajo * f_alto > 0:
            return None
        for _ in range(300):
            medio = (bajo + alto) / 2
            f_medio = valor_presente(medio)
            if f_bajo * f_medio <= 0:
                alto = medio
            else:
                bajo, f_bajo = medio, f_medio
        return (bajo + alto) / 2

    @classmethod
    def rentabilidad_ea(cls, flujos: Sequence[Flujo]) -> Optional[float]:
        """XIRR si el historial cubre al menos DIAS_MINIMOS_EA días; si no, None."""
        fechas: List[date] = [d for d, m in flujos if abs(m) > 1e-12]
        if len(fechas) < 2 or (max(fechas) - min(fechas)).days < cls.DIAS_MINIMOS_EA:
            return None
        return cls.xirr(flujos)

