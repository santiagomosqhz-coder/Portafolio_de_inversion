from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

from .almacen import Almacen
from .analisis_portafolio import AnalisisPortafolio
from .calculadora_rentabilidad import CalculadoraRentabilidad
from .cdt import Cdt
from .datos_mercado import DatosMercado
from .error_precios import ErrorPrecios
from .operacion import Operacion
from .posicion import Posicion
from .renta_fija import InversionRentaFija
from .resumen import Resumen
from .servicio_precios import ServicioPrecios

Splits = Sequence[Tuple[date, float]]
EPS = 1e-9



class Portafolio:
    almacen: Almacen
    operaciones: List[Operacion]
    renta_fija: List[InversionRentaFija]
    cdts: List[Cdt]

    def __init__(self, almacen: Almacen):
        self.almacen = almacen
        self.operaciones, self.renta_fija = almacen.cargar()
        self.cdts = almacen.cargar_cdt()

    # ------------------------------------------------------------------ registro
    def _guardar(self) -> None:
        self.almacen.guardar(self.operaciones, self.renta_fija)

    @property
    def simbolos(self) -> List[str]:
        return sorted({o.simbolo for o in self.operaciones})

    def registrar_operacion(self, op: Operacion, splits: Optional[Splits] = None,
                            hoy: Optional[date] = None) -> None:
        """Valida y guarda una operación. `splits` permite comprobar bien las ventas."""
        op.validar(hoy)
        previas = [o for o in self.operaciones if o.simbolo == op.simbolo]
        if any(o.moneda != op.moneda for o in previas):
            raise ValueError(f"{op.simbolo} ya está registrada en {previas[0].moneda}; "
                             "use la misma moneda en todas sus operaciones.")
        self._verificar_ventas(op.simbolo, previas + [op], splits or [])
        self.operaciones.append(op)
        self._guardar()

    def eliminar_operacion(self, id_operacion: str) -> None:
        self.operaciones = [o for o in self.operaciones if o.id != id_operacion]
        self._guardar()

    def registrar_renta_fija(self, inversion: InversionRentaFija, hoy: Optional[date] = None) -> None:
        inversion.validar(hoy)
        self.renta_fija.append(inversion)
        self._guardar()

    def actualizar_renta_fija(self, inversion: InversionRentaFija, hoy: Optional[date] = None) -> None:
        inversion.validar(hoy)
        self.renta_fija = [inversion if r.id == inversion.id else r for r in self.renta_fija]
        self._guardar()

    def eliminar_renta_fija(self, id_inversion: str) -> None:
        self.renta_fija = [r for r in self.renta_fija if r.id != id_inversion]
        self._guardar()

    def registrar_cdt(self, cdt: Cdt, hoy: Optional[date] = None) -> None:
        cdt.validar(hoy)
        self.cdts.append(cdt)
        self.almacen.guardar_cdt(self.cdts)

    def eliminar_cdt(self, id_cdt: str) -> None:
        self.cdts = [c for c in self.cdts if c.id != id_cdt]
        self.almacen.guardar_cdt(self.cdts)

    # ------------------------------------------------------------ utilidades internas
    @staticmethod
    def _ordenar(ops: Sequence[Operacion]) -> List[Operacion]:
        """Por fecha; el mismo día las compras van antes que las ventas."""
        return sorted(ops, key=lambda o: (o.fecha, 0 if o.es_compra else 1))

    @staticmethod
    def factor_split(splits: Splits, fecha: date) -> float:
        """Cuántas acciones de hoy equivalen a 1 acción comprada en `fecha`."""
        factor = 1.0
        for fecha_split, razon in splits:
            if fecha_split > fecha:
                factor *= razon
        return factor

    def _verificar_ventas(self, simbolo: str, ops: Sequence[Operacion], splits: Splits) -> None:
        disponibles = 0.0
        for op in self._ordenar(ops):
            q = op.cantidad * self.factor_split(splits, op.fecha)
            if op.es_compra:
                disponibles += q
            else:
                if q > disponibles * (1 + EPS) + EPS:
                    raise ValueError(
                        f"{simbolo}: la venta del {op.fecha.isoformat()} ({op.cantidad:g} acciones) "
                        "supera las acciones que se tenían en esa fecha."
                    )
                disponibles -= q

    # ------------------------------------------------------------------ cálculo
    def _calcular_posicion(self, simbolo: str, ops: Sequence[Operacion],
                           datos: DatosMercado, hoy: date) -> Posicion:
        """Método de costo promedio. Comisiones: las de compra suman al costo, las de venta restan al ingreso."""
        splits = datos.lista_splits
        cantidad = costo_abierto = 0.0
        total_comprado = ventas_netas = costo_vendido = realizada = 0.0
        flujos: List[Tuple[date, float]] = []

        for op in self._ordenar(ops):
            q = op.cantidad * self.factor_split(splits, op.fecha)
            if op.es_compra:
                costo = op.monto_bruto + op.comision
                cantidad += q
                costo_abierto += costo
                total_comprado += costo
            else:
                if q > cantidad * (1 + EPS) + EPS:
                    raise ValueError(
                        f"{simbolo}: la venta del {op.fecha.isoformat()} ({op.cantidad:g} acciones) "
                        "supera las acciones que se tenían en esa fecha."
                    )
                costo_dado_de_baja = costo_abierto * (q / cantidad)
                neto = op.monto_bruto - op.comision
                realizada += neto - costo_dado_de_baja
                costo_vendido += costo_dado_de_baja
                ventas_netas += neto
                cantidad -= q
                costo_abierto -= costo_dado_de_baja
                if cantidad < EPS:
                    cantidad = costo_abierto = 0.0
            flujos.append((op.fecha, op.flujo_caja))

        dividendos = 0.0
        if datos.soporta_dividendos:
            for fecha_ex, por_accion in datos.lista_dividendos:
                if fecha_ex > hoy:
                    continue
                # Quien compra desde la fecha ex-dividendo no lo recibe: se cuenta lo que había el día anterior.
                acciones = sum(
                    (1 if o.es_compra else -1) * o.cantidad * self.factor_split(splits, o.fecha)
                    for o in ops if o.fecha < fecha_ex
                )
                if acciones > EPS:
                    monto = acciones * por_accion
                    dividendos += monto
                    flujos.append((fecha_ex, monto))

        fecha_precio, precio = datos.precio_en(hoy)
        if cantidad > EPS:
            flujos.append((fecha_precio, cantidad * precio))

        return Posicion(
            simbolo=simbolo, moneda=ops[0].moneda, nombre=datos.nombre, cantidad=cantidad,
            costo_abierto=costo_abierto, precio_actual=precio, fecha_precio=fecha_precio,
            total_comprado=total_comprado, ventas_netas=ventas_netas, costo_vendido=costo_vendido,
            realizada=realizada, dividendos=dividendos, flujos=flujos,
        )

    def _resumir(self, moneda: str, posiciones: Sequence[Posicion],
                 renta_fija: Sequence[InversionRentaFija], hoy: date) -> Resumen:
        r = Resumen(moneda=moneda)
        flujos: List[Tuple[date, float]] = []
        for p in posiciones:
            r.invertido_rv += p.total_comprado
            r.valor_rv += p.valor_actual
            r.realizada_rv += p.realizada
            r.no_realizada_rv += p.no_realizada
            r.dividendos += p.dividendos
            flujos += p.flujos
        for inv in renta_fija:
            r.invertido_rf += inv.costo
            r.valor_rf += inv.valor_vigente(hoy)
            if inv.es_realizada(hoy):
                r.realizada_rf += inv.ganancia(hoy)
            else:
                r.no_realizada_rf += inv.ganancia(hoy)
            flujos += inv.flujos(hoy)
        if flujos:
            r.dias = (max(max(d for d, _ in flujos), hoy) - min(d for d, _ in flujos)).days
        r.rentabilidad_ea = CalculadoraRentabilidad.rentabilidad_ea(flujos)
        return r

    def _serie_evolucion(self, moneda: str, ops_por_simbolo: Dict[str, List[Operacion]],
                         datos_por_simbolo: Dict[str, DatosMercado], hoy: date) -> Optional[pd.DataFrame]:
        """Valor de mercado diario de las acciones y dinero neto aportado (compras − ventas)."""
        valores = []
        movimientos = []
        for simbolo, ops in ops_por_simbolo.items():
            if ops[0].moneda != moneda or simbolo not in datos_por_simbolo:
                continue
            datos = datos_por_simbolo[simbolo]
            splits = datos.lista_splits
            primera = pd.Timestamp(min(o.fecha for o in ops))
            acciones = defaultdict(float)
            for o in ops:
                acciones[pd.Timestamp(o.fecha)] += (1 if o.es_compra else -1) * o.cantidad * self.factor_split(splits, o.fecha)
                movimientos.append((pd.Timestamp(o.fecha), -o.flujo_caja))
            q = pd.Series(acciones).sort_index().cumsum()
            cierres = datos.cierres[(datos.cierres.index >= primera) & (datos.cierres.index <= pd.Timestamp(hoy))]
            if cierres.empty:
                continue
            q = q.reindex(q.index.union(cierres.index)).ffill().reindex(cierres.index).fillna(0.0)
            valores.append((q * cierres).rename(simbolo))
        if not valores:
            return None
        valor = pd.concat(valores, axis=1).sort_index().ffill().fillna(0.0).sum(axis=1)
        aporte = pd.Series(dict_sum(movimientos)).sort_index().cumsum()
        aporte = aporte.reindex(aporte.index.union(valor.index)).ffill().reindex(valor.index).fillna(0.0)
        return pd.DataFrame({"valor": valor, "aporte_neto": aporte})

    def analizar(self, servicio: ServicioPrecios, hoy: Optional[date] = None) -> AnalisisPortafolio:
        """Calcula posiciones, resúmenes por moneda y evolución. Nunca inventa precios."""
        hoy = hoy or date.today()
        analisis = AnalisisPortafolio(fecha_calculo=hoy)

        ops_por_simbolo: Dict[str, List[Operacion]] = defaultdict(list)
        operaciones, renta_fija = list(self.operaciones), list(self.renta_fija)   # instantánea
        for op in self._ordenar(operaciones):
            if op.fecha <= hoy:
                ops_por_simbolo[op.simbolo].append(op)

        datos_por_simbolo: Dict[str, DatosMercado] = {}
        for simbolo, ops in sorted(ops_por_simbolo.items()):
            try:
                datos = servicio.obtener(simbolo, ops[0].fecha, hoy)
                posicion = self._calcular_posicion(simbolo, ops, datos, hoy)
            except (ErrorPrecios, ValueError) as exc:
                analisis.errores[simbolo] = str(exc)
                continue
            datos_por_simbolo[simbolo] = datos
            analisis.posiciones.append(posicion)
            analisis.fuentes[simbolo] = (datos.fuente, datos.consultado_en)
            if not datos.soporta_dividendos or not datos.soporta_splits:
                analisis.advertencias.append(
                    f"{simbolo}: la fuente '{datos.fuente}' no entrega dividendos ni splits; "
                    "los dividendos NO están incluidos y un split posterior a la compra distorsionaría el resultado."
                )
            if (hoy - posicion.fecha_precio).days > 7:
                analisis.advertencias.append(
                    f"{simbolo}: el último precio disponible es del {posicion.fecha_precio.isoformat()}."
                )

        analisis.renta_fija = [r for r in renta_fija if r.fecha_compra <= hoy]

        monedas = {p.moneda for p in analisis.posiciones} | {r.moneda for r in analisis.renta_fija}
        for moneda in sorted(monedas):
            posiciones = [p for p in analisis.posiciones if p.moneda == moneda]
            renta_fija = [r for r in analisis.renta_fija if r.moneda == moneda]
            analisis.resumenes[moneda] = self._resumir(moneda, posiciones, renta_fija, hoy)
            serie = self._serie_evolucion(moneda, ops_por_simbolo, datos_por_simbolo, hoy)
            if serie is not None:
                analisis.evolucion[moneda] = serie

        if len(monedas) > 1:
            analisis.advertencias.append(
                "El portafolio tiene varias monedas (" + ", ".join(sorted(monedas)) + "). No se hace conversión "
                "de moneda: los totales se muestran por separado para cada una."
            )
        if analisis.errores:
            analisis.advertencias.append(
                "Resultados INCOMPLETOS: no se pudieron calcular " + ", ".join(sorted(analisis.errores)) +
                ". Los totales excluyen esas empresas."
            )
        return analisis


def dict_sum(pares) -> Dict[pd.Timestamp, float]:
    """Suma los montos que caen en la misma fecha."""
    total: Dict[pd.Timestamp, float] = defaultdict(float)
    for fecha, monto in pares:
        total[fecha] += monto
    return dict(total)
