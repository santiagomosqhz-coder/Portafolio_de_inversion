from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from .datos_mercado import DatosMercado
from .error_precios import ErrorPrecios
from .proveedor_precios import ProveedorPrecios



class ProveedorYahoo(ProveedorPrecios):
    nombre = "Yahoo Finance (yfinance)"
    requiere_clave = False

    def obtener(self, simbolo: str, inicio: date, fin: date) -> DatosMercado:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise ErrorPrecios("Falta instalar yfinance (pip install -r requirements.txt).") from exc

        try:
            ticker = yf.Ticker(simbolo)
            # auto_adjust=False: "Close" queda ajustado solo por splits, no por dividendos.
            # Los dividendos se cuentan aparte, así no se cuentan dos veces.
            hist = ticker.history(
                start=inicio.isoformat(), end=(fin + timedelta(days=1)).isoformat(),
                auto_adjust=False, actions=True, raise_errors=True,
            )
        except Exception as exc:  # yfinance lanza varios tipos de error según la causa
            raise ErrorPrecios(
                f"Yahoo Finance no pudo entregar datos de '{simbolo}': {exc}. "
                "Revise su conexión a internet y el símbolo (acciones de otras bolsas llevan sufijo, "
                "por ejemplo '.CL' para la Bolsa de Colombia). Yahoo es una fuente no oficial y "
                "puede limitar el acceso temporalmente."
            ) from exc

        if hist is None or hist.empty or "Close" not in hist:
            raise ErrorPrecios(
                f"Yahoo Finance no devolvió precios de '{simbolo}' entre {inicio} y {fin}. "
                "Verifique que el símbolo exista y que la fecha sea posterior a su listado."
            )

        indice = pd.DatetimeIndex(hist.index)
        if indice.tz is not None:
            indice = indice.tz_localize(None)
        hist.index = indice.normalize()
        hist = hist[~hist.index.duplicated(keep="last")]

        cierres = hist["Close"].dropna().astype(float)
        dividendos = hist["Dividends"][hist["Dividends"] > 0].astype(float) if "Dividends" in hist else pd.Series(dtype=float)
        splits = hist["Stock Splits"][hist["Stock Splits"] > 0].astype(float) if "Stock Splits" in hist else pd.Series(dtype=float)
        if cierres.empty:
            raise ErrorPrecios(f"Yahoo Finance devolvió '{simbolo}' sin precios de cierre.")

        return DatosMercado(
            simbolo=simbolo, cierres=cierres, dividendos=dividendos, splits=splits,
            moneda=self._moneda(ticker), nombre=self._nombre(ticker),
            fuente=self.nombre, consultado_en=datetime.now(),
            soporta_dividendos=True, soporta_splits=True,
        )

    @staticmethod
    def _moneda(ticker):
        try:
            moneda = ticker.fast_info["currency"]
            if moneda:
                return str(moneda).upper()
        except Exception:
            pass
        try:
            moneda = ticker.get_history_metadata().get("currency")
            return str(moneda).upper() if moneda else None
        except Exception:
            return None

    @staticmethod
    def _nombre(ticker):
        try:
            info = ticker.info
            return info.get("longName") or info.get("shortName")
        except Exception:
            return None
