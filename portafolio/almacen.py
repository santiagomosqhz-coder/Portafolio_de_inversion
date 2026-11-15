"""Guarda y lee el portafolio en un archivo JSON local."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Tuple

from .cdt import Cdt
from .operacion import Operacion
from .renta_fija import InversionRentaFija


class Almacen:
    VERSION = 2

    def __init__(self, ruta: Path):
        self.ruta = Path(ruta)

    def _leer(self) -> dict:
        if not self.ruta.exists():
            return {}
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ValueError(f"El archivo de datos {self.ruta} está dañado: {exc}") from exc
        if not isinstance(datos, dict):
            raise ValueError(f"El archivo de datos {self.ruta} no tiene el formato esperado.")
        return datos
