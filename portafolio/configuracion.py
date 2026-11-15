from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

RAIZ = Path(__file__).resolve().parent.parent

class Configuracion:
    ruta_datos: Path
    alphavantage_clave: Optional[str]

    def __init__(self, ruta_datos: Path, alphavantage_clave: Optional[str] = None):
        self.ruta_datos = ruta_datos
        self.alphavantage_clave = alphavantage_clave