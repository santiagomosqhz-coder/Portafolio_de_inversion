from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime

import pandas as pd

from .datos_mercado import DatosMercado
from .error_precios import ErrorPrecios
from .proveedor_precios import ProveedorPrecios



class ProveedorAlphaVantage(ProveedorPrecios):
    """Usa TIME_SERIES_DAILY (cierres sin ajustar).

    Limitaciones conocidas (se informan al usuario en los resultados):
    - No entrega dividendos ni splits en este endpoint, así que no se incluyen.
    - No informa la moneda: debe indicarla el usuario.
    - La clave gratuita tiene un tope diario de consultas y puede restringir el
      historial completo; consulte https://www.alphavantage.co/premium/ para los límites vigentes.
    """

    nombre = "Alpha Vantage"
    requiere_clave = True
    URL = "https://www.alphavantage.co/query"

    def __init__(self, clave: str):
        self.clave = clave

    def obtener(self, simbolo: str, inicio: date, fin: date) -> DatosMercado:
        parametros = urllib.parse.urlencode({
            "function": "TIME_SERIES_DAILY", "symbol": simbolo,
            "outputsize": "full", "apikey": self.clave,
        })
        try:
            with urllib.request.urlopen(f"{self.URL}?{parametros}", timeout=20) as respuesta:
                datos = json.loads(respuesta.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise ErrorPrecios(f"Alpha Vantage no respondió para '{simbolo}': {exc}") from exc

        serie = datos.get("Time Series (Daily)")
        if not serie:
            motivo = datos.get("Error Message") or datos.get("Information") or datos.get("Note") or "respuesta vacía"
            raise ErrorPrecios(f"Alpha Vantage no entregó precios de '{simbolo}': {motivo}")

        cierres = pd.Series(
            {pd.Timestamp(dia): float(valores["4. close"]) for dia, valores in serie.items()}
        ).sort_index()
        cierres = cierres[(cierres.index >= pd.Timestamp(inicio)) & (cierres.index <= pd.Timestamp(fin))]
        if cierres.empty:
            raise ErrorPrecios(
                f"Alpha Vantage no tiene precios de '{simbolo}' entre {inicio} y {fin} "
                "(la clave gratuita puede limitar el historial)."
            )
        vacio = pd.Series(dtype=float)
        return DatosMercado(
            simbolo=simbolo, cierres=cierres, dividendos=vacio, splits=vacio,
            moneda=None, nombre=None, fuente=self.nombre, consultado_en=datetime.now(),
            soporta_dividendos=False, soporta_splits=False,
        )
