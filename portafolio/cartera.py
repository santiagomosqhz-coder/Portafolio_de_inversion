from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

from .datos_mercado import DatosMercado
from .empresa import Empresa
from .error_precios import ErrorPrecios
from .estado_cartera import EstadoCartera
from .lote import Lote
from .operacion import Operacion
from .portafolio import Portafolio
from .servicio_precios import ServicioPrecios
from .utilidades import fmt_cop


VentaPendiente = Tuple[Operacion, list]   # (operación de venta, splits para validarla)

class Cartera:
    SALDO_INICIAL = 10_000_000.0   # COP
    MAX_DIAS_SIN_PRECIO = 7

    portafolio: Portafolio
    servicio: ServicioPrecios

    def __init__(self, portafolio: Portafolio, servicio: ServicioPrecios):
        self.portafolio = portafolio
        self.servicio = servicio
    def saldo(self) -> float:
        """10.000.000 − compras + ventas (solo operaciones ya registradas)."""
        return self.SALDO_INICIAL + sum(o.flujo_caja for o in self.portafolio.operaciones)
    
    def datos_en_cop(self, simbolo: str, desde: date, hoy: date) -> DatosMercado:
        datos = self.servicio.obtener(simbolo, desde, hoy)
        if datos.moneda and datos.moneda.upper() != "COP":
            raise ErrorPrecios(f"{simbolo}: la fuente entregó precios en {datos.moneda}, no en COP.")
        return datos
    def preparar_compra(self, empresa: Empresa, cantidad: float, fecha_compra: date,
                        fecha_venta: date, hoy: Optional[date] = None) -> Tuple[Operacion, DatosMercado]:
        """Valida y calcula la compra (consulta internet). No guarda nada todavía."""
        hoy = hoy or date.today()
        if cantidad <= 0:
            raise ValueError("La cantidad de acciones debe ser mayor que cero.")
        if fecha_compra > hoy:
            raise ValueError("La fecha de compra no puede ser futura: solo se compra a precios ya conocidos.")
        if fecha_venta <= fecha_compra:
            raise ValueError("La fecha de venta prevista debe ser posterior a la fecha de compra.")

        datos = self.datos_en_cop(empresa.simbolo, fecha_compra, hoy)
        fecha_precio, precio_ajustado = datos.precio_en(fecha_compra)
        if (fecha_compra - fecha_precio).days > self.MAX_DIAS_SIN_PRECIO:
            raise ErrorPrecios(f"No hay precios de {empresa.nombre} cerca del {fecha_compra}: "
                               f"el más cercano es del {fecha_precio}.")
        # Yahoo entrega precios ajustados por splits posteriores; el precio realmente pagado era mayor.
        precio_real = precio_ajustado * Portafolio.factor_split(datos.lista_splits, fecha_compra)
        costo = cantidad * precio_real
        if costo > self.saldo() + 1e-6:
            raise ValueError(f"Saldo insuficiente: la compra cuesta {fmt_cop(costo)} "
                             f"y su saldo disponible es {fmt_cop(self.saldo())}.")
        operacion = Operacion(simbolo=empresa.simbolo, tipo=Operacion.COMPRA, fecha=fecha_compra,
                              cantidad=cantidad, precio=precio_real, comision=0.0, moneda="COP",
                              fecha_venta_prevista=fecha_venta)
        return operacion, datos
    def registrar_compra(self, operacion: Operacion, datos: DatosMercado, hoy: Optional[date] = None) -> None:
        self.portafolio.registrar_operacion(operacion, splits=datos.lista_splits, hoy=hoy)
    def preparar_ventas_pendientes(self, hoy: Optional[date] = None) -> Tuple[List[VentaPendiente], Dict[str, str]]:
        """Ventas cuya fecha prevista ya llegó y aún no se registraron (consulta internet).

        Una venta con fecha futura NO se prepara: solo se registra cuando su fecha llega.
        """
        hoy = hoy or date.today()
        ops = list(self.portafolio.operaciones)
        vendidas = {o.compra_id for o in ops if not o.es_compra and o.compra_id}
        pendientes = [o for o in ops if o.es_compra and o.id not in vendidas
                      and o.fecha_venta_prevista is not None and o.fecha_venta_prevista <= hoy]
        listas: List[VentaPendiente] = []
        errores: Dict[str, str] = {}
        for compra in pendientes:
            nombre = (Empresa.por_simbolo(compra.simbolo) or Empresa(compra.simbolo, compra.simbolo)).nombre
            try:
                datos = self.datos_en_cop(compra.simbolo, compra.fecha, hoy)
                fecha_precio, precio_ajustado = datos.precio_en(compra.fecha_venta_prevista)
                splits = datos.lista_splits
                f_compra = Portafolio.factor_split(splits, compra.fecha)
                f_venta = Portafolio.factor_split(splits, compra.fecha_venta_prevista)
                venta = Operacion(
                    simbolo=compra.simbolo, tipo=Operacion.VENTA, fecha=compra.fecha_venta_prevista,
                    cantidad=compra.cantidad * f_compra / f_venta, precio=precio_ajustado * f_venta,
                    comision=0.0, moneda="COP", compra_id=compra.id)
                listas.append((venta, splits))
            except (ErrorPrecios, ValueError) as exc:
                errores[nombre] = f"No se pudo registrar la venta del {compra.fecha_venta_prevista}: {exc}"
        return listas, errores
    def registrar_ventas(self, ventas: List[VentaPendiente], hoy: Optional[date] = None) -> Dict[str, str]:
        errores: Dict[str, str] = {}
        for venta, splits in ventas:
            try:
                self.portafolio.registrar_operacion(venta, splits=splits, hoy=hoy)
            except ValueError as exc:
                errores[venta.simbolo] = str(exc)
        return errores
    def estado(self, hoy: Optional[date] = None) -> EstadoCartera:
        """Saldo, posiciones abiertas (a precio actual) y cerradas, con sus ganancias."""
        hoy = hoy or date.today()
        ops = list(self.portafolio.operaciones)
        ventas = {o.compra_id: o for o in ops if not o.es_compra and o.compra_id}
        estado = EstadoCartera(hoy=hoy, saldo=self.SALDO_INICIAL + sum(o.flujo_caja for o in ops))

        abiertas_por_simbolo: Dict[str, List[Lote]] = defaultdict(list)
        for compra in sorted((o for o in ops if o.es_compra), key=lambda o: (o.fecha, o.id)):
            empresa = Empresa.por_simbolo(compra.simbolo) or Empresa(compra.simbolo, compra.simbolo)
            lote = Lote(empresa=empresa.nombre, simbolo=compra.simbolo, compra=compra,
                        venta=ventas.get(compra.id), acciones=compra.cantidad)
            estado.lotes.append(lote)
            if lote.abierta:
                abiertas_por_simbolo[compra.simbolo].append(lote)

        for simbolo, lotes in abiertas_por_simbolo.items():
            try:
                datos = self.datos_en_cop(simbolo, min(l.compra.fecha for l in lotes), hoy)
                fecha_precio, precio = datos.precio_en(hoy)
            except (ErrorPrecios, ValueError) as exc:
                estado.errores[lotes[0].empresa] = str(exc)
                continue
            for lote in lotes:
                lote.acciones = lote.compra.cantidad * Portafolio.factor_split(datos.lista_splits, lote.compra.fecha)
                lote.precio_actual, lote.fecha_precio = precio, fecha_precio
            estado.fuente = datos.fuente
            if estado.consultado_en is None or datos.consultado_en > estado.consultado_en:
                estado.consultado_en = datos.consultado_en
        return estado



