"""Inversión de renta fija: CDT, bono o título de deuda pública (TES)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple

Flujo = Tuple[date, float]



@dataclass
class InversionRentaFija:
    tipo: str                         # "CDT", "BONO" o "TES"
    nombre: str                       # emisor o descripción
    fecha_compra: date
    capital: float                    # valor invertido (sin comisión)
    tasa_ea: float                    # tasa efectiva anual pactada, como fracción (0.12 = 12 %)
    fecha_vencimiento: date
    comision: float = 0.0
    moneda: str = "COP"
    # Opcionales: valoración de mercado manual y venta anticipada
    valor_mercado: Optional[float] = None
    fecha_valor_mercado: Optional[date] = None
    fecha_venta: Optional[date] = None
    valor_venta: Optional[float] = None
    comision_venta: float = 0.0
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    TIPOS = ("CDT", "BONO", "TES")
    VIGENTE = "VIGENTE"
    VENCIDA = "VENCIDA"
    VENDIDA = "VENDIDA"

    def validar(self, hoy: Optional[date] = None) -> None:
        hoy = hoy or date.today()
        if self.tipo not in self.TIPOS:
            raise ValueError("El tipo debe ser CDT, BONO o TES.")
        if not (self.nombre or "").strip():
            raise ValueError("Indique el emisor o una descripción.")
        if self.capital <= 0:
            raise ValueError("El capital debe ser mayor que cero.")
        if self.tasa_ea <= -1:
            raise ValueError("La tasa E.A. no es válida.")
        if self.comision < 0 or self.comision_venta < 0:
            raise ValueError("Las comisiones no pueden ser negativas.")
        if self.fecha_compra > hoy:
            raise ValueError("La fecha de compra no puede ser futura.")
        if self.fecha_vencimiento <= self.fecha_compra:
            raise ValueError("El vencimiento debe ser posterior a la fecha de compra.")
        if (self.valor_mercado is None) != (self.fecha_valor_mercado is None):
            raise ValueError("Indique el valor de mercado junto con su fecha (o deje ambos vacíos).")
        if self.valor_mercado is not None and self.valor_mercado <= 0:
            raise ValueError("El valor de mercado debe ser mayor que cero.")
        if (self.fecha_venta is None) != (self.valor_venta is None):
            raise ValueError("Indique la fecha de venta junto con el valor recibido (o deje ambos vacíos).")
        if self.fecha_venta is not None:
            if not (self.fecha_compra <= self.fecha_venta <= hoy):
                raise ValueError("La fecha de venta debe estar entre la compra y hoy.")
            if self.fecha_venta > self.fecha_vencimiento:
                raise ValueError("La venta no puede ser posterior al vencimiento.")
            if self.valor_venta <= 0:
                raise ValueError("El valor recibido en la venta debe ser mayor que cero.")

    # ---- valoración contractual -------------------------------------------
    @property
    def costo(self) -> float:
        """Capital más comisión de compra."""
        return self.capital + self.comision

    def valor_causado(self, fecha: date) -> float:
        """Capital capitalizado a la tasa E.A. pactada hasta `fecha` (máx. el vencimiento)."""
        fin = min(fecha, self.fecha_vencimiento)
        dias = max((fin - self.fecha_compra).days, 0)
        return self.capital * (1.0 + self.tasa_ea) ** (dias / 365.0)

    @property
    def valor_al_vencimiento(self) -> float:
        return self.valor_causado(self.fecha_vencimiento)

    def estado(self, hoy: date) -> str:
        if self.fecha_venta is not None and self.fecha_venta <= hoy:
            return self.VENDIDA
        if self.fecha_vencimiento <= hoy:
            return self.VENCIDA
        return self.VIGENTE

    def valor_actual(self, hoy: date) -> float:
        """Valor de la inversión hoy: valoración vigente o dinero ya cobrado (neto de comisión)."""
        estado = self.estado(hoy)
        if estado == self.VENDIDA:
            return self.valor_venta - self.comision_venta
        if estado == self.VENCIDA:
            return self.valor_al_vencimiento
        if self.valor_mercado is not None and self.fecha_valor_mercado <= hoy:
            return self.valor_mercado
        return self.valor_causado(hoy)

    def valor_vigente(self, hoy: date) -> float:
        """Valor que todavía está invertido (0 si ya se cobró)."""
        return self.valor_actual(hoy) if self.estado(hoy) == self.VIGENTE else 0.0

    def ganancia(self, hoy: date) -> float:
        return self.valor_actual(hoy) - self.costo

    def es_realizada(self, hoy: date) -> bool:
        return self.estado(hoy) != self.VIGENTE

    def flujos(self, hoy: date) -> List[Flujo]:
        """Flujos de caja para el cálculo de la rentabilidad E.A. (XIRR)."""
        estado = self.estado(hoy)
        salida = [(self.fecha_compra, -self.costo)]
        if estado == self.VENDIDA:
            return salida + [(self.fecha_venta, self.valor_venta - self.comision_venta)]
        if estado == self.VENCIDA:
            return salida + [(self.fecha_vencimiento, self.valor_al_vencimiento)]
        return salida + [(hoy, self.valor_actual(hoy))]

    # ---- persistencia -------------------------------------------------------
    def a_dict(self) -> dict:
        f = lambda x: x.isoformat() if x else None  # noqa: E731
        return {
            "id": self.id, "tipo": self.tipo, "nombre": self.nombre,
            "fecha_compra": f(self.fecha_compra), "capital": self.capital,
            "tasa_ea": self.tasa_ea, "fecha_vencimiento": f(self.fecha_vencimiento),
            "comision": self.comision, "moneda": self.moneda,
            "valor_mercado": self.valor_mercado, "fecha_valor_mercado": f(self.fecha_valor_mercado),
            "fecha_venta": f(self.fecha_venta), "valor_venta": self.valor_venta,
            "comision_venta": self.comision_venta,
        }

    @classmethod
    def desde_dict(cls, d: dict) -> "InversionRentaFija":
        g = lambda k: date.fromisoformat(d[k]) if d.get(k) else None  # noqa: E731
        return cls(
            tipo=d["tipo"], nombre=d["nombre"], fecha_compra=g("fecha_compra"),
            capital=float(d["capital"]), tasa_ea=float(d["tasa_ea"]),
            fecha_vencimiento=g("fecha_vencimiento"), comision=float(d.get("comision", 0.0)),
            moneda=d.get("moneda", "COP"), valor_mercado=d.get("valor_mercado"),
            fecha_valor_mercado=g("fecha_valor_mercado"), fecha_venta=g("fecha_venta"),
            valor_venta=d.get("valor_venta"), comision_venta=float(d.get("comision_venta") or 0.0),
            id=d["id"],
        )
