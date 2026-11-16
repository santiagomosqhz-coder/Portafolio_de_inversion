from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Operacion:
    simbolo: str
    tipo: str                      # "COMPRA" o "VENTA"
    fecha: date
    cantidad: float
    precio: float                  # precio por acción, en la moneda de la acción
    comision: float = 0.0          # comisión total del bróker en la misma moneda
    moneda: str = "USD"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    fecha_venta_prevista: Optional[date] = None   # solo compras: cuándo se planea vender
    compra_id: Optional[str] = None               # solo ventas: id de la compra que cierran

    COMPRA = "COMPRA"
    VENTA = "VENTA"

    def validar(self, hoy: Optional[date] = None) -> None:
        hoy = hoy or date.today()
        self.simbolo = (self.simbolo or "").strip().upper()
        self.moneda = (self.moneda or "").strip().upper()
        if not self.simbolo:
            raise ValueError("Indique el símbolo de la empresa.")
        if self.tipo not in (self.COMPRA, self.VENTA):
            raise ValueError("El tipo debe ser COMPRA o VENTA.")
        if self.cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero.")
        if self.precio <= 0:
            raise ValueError("El precio debe ser mayor que cero.")
        if self.comision < 0:
            raise ValueError("La comisión no puede ser negativa.")
        if self.fecha > hoy:
            raise ValueError("La fecha de la operación no puede ser futura.")
        if not self.moneda:
            raise ValueError("Indique la moneda de la operación.")

    @property
    def monto_bruto(self) -> float:
        return self.cantidad * self.precio

    @property
    def es_compra(self) -> bool:
        return self.tipo == self.COMPRA

    @property
    def flujo_caja(self) -> float:
        """Dinero que sale (negativo) o entra (positivo), incluida la comisión."""
        if self.es_compra:
            return -(self.monto_bruto + self.comision)
        return self.monto_bruto - self.comision

    def a_dict(self) -> dict:
        return {
            "id": self.id, "simbolo": self.simbolo, "tipo": self.tipo,
            "fecha": self.fecha.isoformat(), "cantidad": self.cantidad,
            "precio": self.precio, "comision": self.comision, "moneda": self.moneda,
            "fecha_venta_prevista": self.fecha_venta_prevista.isoformat() if self.fecha_venta_prevista else None,
            "compra_id": self.compra_id,
        }

    @classmethod
    def desde_dict(cls, d: dict) -> "Operacion":
        return cls(
            simbolo=d["simbolo"], tipo=d["tipo"], fecha=date.fromisoformat(d["fecha"]),
            cantidad=float(d["cantidad"]), precio=float(d["precio"]),
            comision=float(d.get("comision", 0.0)), moneda=d.get("moneda", "USD"), id=d["id"],
            fecha_venta_prevista=(date.fromisoformat(d["fecha_venta_prevista"])
                                  if d.get("fecha_venta_prevista") else None),
            compra_id=d.get("compra_id"),
        )
