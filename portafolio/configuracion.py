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

    @classmethod
    def cargar(cls, ruta_datos: Optional[str] = None) -> "Configuracion":
        """Lee `config.json` (opcional) y la variable de entorno ALPHAVANTAGE_API_KEY."""
        clave = None
        archivo = RAIZ / "config.json"
        if archivo.exists():
            try:
                clave = json.loads(archivo.read_text(encoding="utf-8")).get("alphavantage_api_key")
            except (OSError, ValueError):
                clave = None
        clave = os.environ.get("ALPHAVANTAGE_API_KEY") or clave
        ruta = Path(ruta_datos or os.environ.get("PORTAFOLIO_DATOS") or RAIZ / "datos" / "cartera.json")
        return cls(ruta, clave.strip() if clave else None)
