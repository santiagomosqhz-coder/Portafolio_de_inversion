"""Obtiene precios probando las fuentes en orden y guarda lo consultado en memoria."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from .datos_mercado import DatosMercado
from .error_precios import ErrorPrecios
from .proveedor_precios import ProveedorPrecios


class ServicioPrecios:
    MARGEN_DIAS = 7   # para tener un cierre previo cuando la compra cae en fin de semana

    proveedores: List[ProveedorPrecios]

    def __init__(self, proveedores: List[ProveedorPrecios]):
        self.proveedores = list(proveedores)
        self._cache: Dict[str, Tuple[DatosMercado, date, date]] = {}

    def obtener(self, simbolo: str, inicio: date, fin: Optional[date] = None) -> DatosMercado:
        """Primera fuente que responda. Si todas fallan, lanza ErrorPrecios (nunca inventa datos)."""
        simbolo = simbolo.strip().upper()
        fin = fin or date.today()
        desde = inicio - timedelta(days=self.MARGEN_DIAS)
        if simbolo in self._cache:
            datos, cache_desde, cache_hasta = self._cache[simbolo]
            if cache_desde <= desde and cache_hasta >= fin:
                return datos

        fallos = []
        for proveedor in self.proveedores:
            try:
                datos = proveedor.obtener(simbolo, desde, fin)
            except ErrorPrecios as exc:
                fallos.append(f"• {proveedor.nombre}: {exc}")
                continue
            self._cache[simbolo] = (datos, desde, fin)
            return datos

        if not fallos:
            fallos.append("• No hay fuentes de precios configuradas.")
        raise ErrorPrecios(f"No se pudieron obtener precios reales de {simbolo}.\n" + "\n".join(fallos))

    def limpiar(self) -> None:
        """Descarta lo consultado para que la próxima consulta vaya a la fuente."""
        self._cache.clear()
