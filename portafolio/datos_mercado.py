from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Tuple

import pandas as pd

from .error_precios import ErrorPrecios

@dataclass
class DatosMercado:
    simbolo: str
    cierres: pd.Series            # precio de cierre diario; índice = fecha (sin zona horaria)
    dividendos: pd.Series         # dividendo por acción en la fecha ex-dividendo
    splits: pd.Series             # razón de cada split (2.0 = 2 por 1)
    moneda: Optional[str]         # None si la fuente no la informa
    nombre: Optional[str]
    fuente: str
    consultado_en: datetime
    soporta_dividendos: bool = True
    soporta_splits: bool = True

    def precio_en(self, fecha: date) -> Tuple[date, float]:
        """Último cierre disponible en `fecha` o antes (fines de semana y festivos)."""
        serie = self.cierres[self.cierres.index <= pd.Timestamp(fecha)]
        if serie.empty:
            raise ErrorPrecios(
                f"{self.simbolo}: la fuente '{self.fuente}' no tiene precios hasta el {fecha.isoformat()}."
            )
        return serie.index[-1].date(), float(serie.iloc[-1])

    @property
    def lista_splits(self):
        return [(ts.date(), float(r)) for ts, r in self.splits.items()]

    @property
    def lista_dividendos(self):
        return [(ts.date(), float(v)) for ts, v in self.dividendos.items()]
