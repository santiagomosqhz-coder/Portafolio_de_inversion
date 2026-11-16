"""Convierte a pesos colombianos (COP) los precios de otra fuente, día por día."""
from __future__ import annotations

import dataclasses
from datetime import date

import pandas as pd

from .datos_mercado import DatosMercado
from .error_precios import ErrorPrecios
from .proveedor_precios import ProveedorPrecios



class ProveedorCOP(ProveedorPrecios):
    """Multiplica cada cierre en USD por la tasa USD/COP de ese mismo día.

    La tasa sale de Yahoo Finance (símbolo `COP=X`): es la tasa de mercado de Yahoo,
    no la TRM oficial certificada por la Superintendencia Financiera.
    """

    requiere_clave = False
    base: ProveedorPrecios
    simbolo_fx: str
    moneda_por_defecto: str

    def __init__(self, base: ProveedorPrecios, simbolo_fx: str = "COP=X", moneda_por_defecto: str = "USD"):
        self.base = base
        self.simbolo_fx = simbolo_fx
        self.moneda_por_defecto = moneda_por_defecto
        self.nombre = f"{base.nombre} + tasa USD/COP ({simbolo_fx})"

    def obtener(self, simbolo: str, inicio: date, fin: date) -> DatosMercado:
        datos = self.base.obtener(simbolo, inicio, fin)
        moneda = (datos.moneda or self.moneda_por_defecto).upper()
        if moneda == "COP":
            return datos
        if moneda != "USD":
            raise ErrorPrecios(f"{simbolo} cotiza en {moneda}; el programa solo convierte desde USD a COP.")
        try:
            tasa = self.base.obtener(self.simbolo_fx, inicio, fin).cierres
        except ErrorPrecios as exc:
            raise ErrorPrecios(f"No se pudo obtener la tasa de cambio USD/COP para convertir {simbolo}: {exc}") from exc

        indice = tasa.index.union(datos.cierres.index).union(datos.dividendos.index)
        tasa_diaria = tasa.reindex(indice).ffill().bfill()
        if tasa_diaria.isna().any():
            raise ErrorPrecios("La fuente no entregó la tasa USD/COP para el período pedido.")
        return dataclasses.replace(
            datos,
            cierres=datos.cierres * tasa_diaria.reindex(datos.cierres.index),
            dividendos=datos.dividendos * tasa_diaria.reindex(datos.dividendos.index),
            moneda="COP", fuente=self.nombre,
        )
