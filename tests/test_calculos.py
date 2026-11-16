import tempfile
import unittest
from datetime import date
from pathlib import Path

from portafolio.almacen import Almacen
from portafolio.cartera import Cartera
from portafolio.cdt import Cdt
from portafolio.empresa import Empresa
from portafolio.proveedor_cop import ProveedorCOP
from portafolio.calculadora_rentabilidad import CalculadoraRentabilidad
from portafolio.error_precios import ErrorPrecios
from portafolio.operacion import Operacion
from portafolio.portafolio import Portafolio
from portafolio.renta_fija import InversionRentaFija
from portafolio.servicio_precios import ServicioPrecios
from portafolio.utilidades import parse_fecha, parse_numero
from tests.proveedor_falso import ProveedorFalso

HOY = date(2025, 6, 30)


def portafolio_vacio():
    carpeta = tempfile.mkdtemp()
    return Portafolio(Almacen(Path(carpeta) / "p.json"))


def op(tipo, f, q, p, c=0.0, s="AAA", m="USD"):
    return Operacion(simbolo=s, tipo=tipo, fecha=f, cantidad=q, precio=p, comision=c, moneda=m)

class PruebasAcciones(unittest.TestCase):
    def test_compra_venta_parcial_dividendos_y_comisiones(self):
        # Compra 10 @100 (+5) -> costo 1005. Venta 4 @120 (-3): costo prom. 100.5.
        p = portafolio_vacio()
        p.registrar_operacion(op("COMPRA", date(2025, 1, 2), 10, 100, 5), hoy=HOY)
        p.registrar_operacion(op("VENTA", date(2025, 3, 3), 4, 120, 3), hoy=HOY)
        prov = ProveedorFalso(cierres={"AAA": {date(2025, 1, 2): 100, date(2025, 6, 30): 130}},
                              dividendos={"AAA": {date(2025, 2, 10): 0.5, date(2025, 4, 10): 0.5}})
        a = p.analizar(ServicioPrecios([prov]), HOY)
        pos = a.posiciones[0]
        self.assertAlmostEqual(pos.cantidad, 6)
        self.assertAlmostEqual(pos.realizada, 75.0)          # 477 - 402
        self.assertAlmostEqual(pos.costo_abierto, 603.0)
        self.assertAlmostEqual(pos.valor_actual, 780.0)
        self.assertAlmostEqual(pos.no_realizada, 177.0)
        self.assertAlmostEqual(pos.dividendos, 5.0 + 3.0)    # 10 acc. en feb, 6 en abr
        self.assertAlmostEqual(pos.ganancia_total, 75 + 177 + 8)
        self.assertAlmostEqual(pos.rentabilidad_acumulada, 260 / 1005)
        r = a.resumenes["USD"]
        self.assertAlmostEqual(r.total_invertido, 1005.0)
        self.assertAlmostEqual(r.valor_actual, 780.0)
        self.assertAlmostEqual(r.ganancia_total, 260.0)

    def test_compra_en_fecha_ex_dividendo_no_recibe_dividendo(self):
        p = portafolio_vacio()
        p.registrar_operacion(op("COMPRA", date(2025, 2, 10), 10, 100), hoy=HOY)
        prov = ProveedorFalso(cierres={"AAA": {date(2025, 2, 10): 100, date(2025, 6, 30): 100}},
                              dividendos={"AAA": {date(2025, 2, 10): 1.0}})
        pos = p.analizar(ServicioPrecios([prov]), HOY).posiciones[0]
        self.assertAlmostEqual(pos.dividendos, 0.0)

    def test_split_ajusta_cantidades(self):
        p = portafolio_vacio()
        p.registrar_operacion(op("COMPRA", date(2025, 1, 2), 10, 100), hoy=HOY)
        prov = ProveedorFalso(cierres={"AAA": {date(2025, 1, 2): 50, date(2025, 6, 30): 60}},
                              splits={"AAA": {date(2025, 3, 1): 2.0}})
        pos = p.analizar(ServicioPrecios([prov]), HOY).posiciones[0]
        self.assertAlmostEqual(pos.cantidad, 20)
        self.assertAlmostEqual(pos.valor_actual, 1200)
        self.assertAlmostEqual(pos.no_realizada, 200)

    def test_posicion_cerrada_solo_tiene_ganancia_realizada(self):
        p = portafolio_vacio()
        p.registrar_operacion(op("COMPRA", date(2025, 1, 2), 5, 10), hoy=HOY)
        p.registrar_operacion(op("VENTA", date(2025, 2, 3), 5, 12), hoy=HOY)
        prov = ProveedorFalso(cierres={"AAA": {date(2025, 1, 2): 10, date(2025, 6, 30): 99}})
        pos = p.analizar(ServicioPrecios([prov]), HOY).posiciones[0]
        self.assertFalse(pos.esta_abierta)
        self.assertAlmostEqual(pos.realizada, 10.0)
        self.assertAlmostEqual(pos.no_realizada, 0.0)
        self.assertAlmostEqual(pos.valor_actual, 0.0)

    def test_venta_mayor_a_lo_que_se_tiene_se_rechaza(self):
        p = portafolio_vacio()
        p.registrar_operacion(op("COMPRA", date(2025, 1, 2), 5, 10), hoy=HOY)
        with self.assertRaises(ValueError):
            p.registrar_operacion(op("VENTA", date(2025, 2, 3), 6, 12), hoy=HOY)
        with self.assertRaises(ValueError):   # vender antes de comprar
            p.registrar_operacion(op("VENTA", date(2024, 12, 1), 1, 12), hoy=HOY)

    def test_venta_posterior_a_split_con_cantidades_como_se_operaron(self):
        p = portafolio_vacio()
        p.registrar_operacion(op("COMPRA", date(2025, 1, 2), 10, 100), hoy=HOY)
        venta = op("VENTA", date(2025, 4, 1), 15, 60)       # ya hay 20 acciones tras el split 2:1
        p.registrar_operacion(venta, splits=[(date(2025, 3, 1), 2.0)], hoy=HOY)
        with self.assertRaises(ValueError):                 # sin considerar el split sería inválida
            p2 = portafolio_vacio()
            p2.registrar_operacion(op("COMPRA", date(2025, 1, 2), 10, 100), hoy=HOY)
            p2.registrar_operacion(venta, hoy=HOY)

    def test_validaciones(self):
        p = portafolio_vacio()
        with self.assertRaises(ValueError):
            p.registrar_operacion(op("COMPRA", date(2025, 1, 2), 0, 10), hoy=HOY)
        with self.assertRaises(ValueError):
            p.registrar_operacion(op("COMPRA", date(2026, 1, 2), 1, 10), hoy=HOY)
        p.registrar_operacion(op("COMPRA", date(2025, 1, 2), 1, 10), hoy=HOY)
        with self.assertRaises(ValueError):                 # misma empresa, otra moneda
            p.registrar_operacion(op("COMPRA", date(2025, 1, 3), 1, 10, m="COP"), hoy=HOY)

    def test_monedas_distintas_no_se_suman(self):
        p = portafolio_vacio()
        p.registrar_operacion(op("COMPRA", date(2025, 1, 2), 1, 10, s="AAA", m="USD"), hoy=HOY)
        p.registrar_operacion(op("COMPRA", date(2025, 1, 2), 1, 10, s="BBB", m="COP"), hoy=HOY)
        prov = ProveedorFalso(cierres={"AAA": {date(2025, 1, 2): 10}, "BBB": {date(2025, 1, 2): 10}})
        a = p.analizar(ServicioPrecios([prov]), HOY)
        self.assertEqual(set(a.resumenes), {"USD", "COP"})
        self.assertTrue(any("varias monedas" in x for x in a.advertencias))

class PruebasRentaFija(unittest.TestCase):
    def cdt(self, **kw):
        base = dict(tipo="CDT", nombre="Banco X", fecha_compra=date(2025, 1, 1), capital=1_000_000,
                    tasa_ea=0.12, fecha_vencimiento=date(2026, 1, 1), comision=0.0, moneda="COP")
        base.update(kw)
        return InversionRentaFija(**base)

    def test_cdt_vigente_causa_intereses_a_tasa_ea(self):
        c = self.cdt()
        dias = (HOY - c.fecha_compra).days
        esperado = 1_000_000 * 1.12 ** (dias / 365)
        self.assertAlmostEqual(c.valor_actual(HOY), esperado, places=4)
        self.assertEqual(c.estado(HOY), "VIGENTE")
        self.assertFalse(c.es_realizada(HOY))

    def test_cdt_vencido_cobra_capital_mas_intereses(self):
        c = self.cdt(fecha_vencimiento=date(2026, 1, 1))
        hoy = date(2026, 3, 1)
        self.assertEqual(c.estado(hoy), "VENCIDA")
        self.assertAlmostEqual(c.valor_actual(hoy), 1_120_000, places=2)  # 365 días exactos
        self.assertAlmostEqual(c.ganancia(hoy), 120_000, places=2)
        self.assertEqual(c.valor_vigente(hoy), 0.0)

    def test_comision_y_venta_anticipada(self):
        c = self.cdt(comision=2_000, fecha_venta=date(2025, 4, 1), valor_venta=1_020_000, comision_venta=1_000)
        c.validar(HOY)
        self.assertEqual(c.estado(HOY), "VENDIDA")
        self.assertAlmostEqual(c.ganancia(HOY), 1_020_000 - 1_000 - 1_002_000)

    def test_valor_de_mercado_manual(self):
        c = self.cdt(tipo="TES", valor_mercado=1_050_000, fecha_valor_mercado=date(2025, 6, 1))
        self.assertEqual(c.valor_actual(HOY), 1_050_000)
    def test_resumen_mezcla_acciones_y_renta_fija(self):
        p = portafolio_vacio()
        p.registrar_operacion(op("COMPRA", date(2025, 1, 2), 10, 100, m="COP"), hoy=HOY)
        p.registrar_renta_fija(self.cdt(), hoy=HOY)
        prov = ProveedorFalso(cierres={"AAA": {date(2025, 1, 2): 100, date(2025, 6, 30): 110}})
        r = p.analizar(ServicioPrecios([prov]), HOY).resumenes["COP"]
        self.assertAlmostEqual(r.invertido_rv, 1000)
        self.assertAlmostEqual(r.invertido_rf, 1_000_000)
        self.assertAlmostEqual(r.valor_rv, 1100)
        self.assertAlmostEqual(r.pct_rv + r.pct_rf, 1.0)
        self.assertGreater(r.valor_rf, 1_000_000)


class PruebasRentabilidad(unittest.TestCase):
    def test_xirr_un_anio(self):
        r = CalculadoraRentabilidad.xirr([(date(2024, 1, 1), -100), (date(2025, 1, 1) if False else date(2024, 12, 31), 110)])
        self.assertAlmostEqual(r, 0.10, places=6)   # 365 días

    def test_xirr_dos_aportes(self):
        flujos = [(date(2024, 1, 1), -100), (date(2024, 7, 1), -100), (date(2025, 1, 1), 230)]
        r = CalculadoraRentabilidad.xirr(flujos)
        d = lambda x: (x - date(2024, 1, 1)).days / 365  # noqa: E731
        vpn = sum(m / (1 + r) ** d(f) for f, m in flujos)
        self.assertAlmostEqual(vpn, 0.0, places=6)

    def test_ea_no_se_calcula_con_menos_de_30_dias_o_sin_entradas(self):
        self.assertIsNone(CalculadoraRentabilidad.rentabilidad_ea([(date(2025, 1, 1), -100), (date(2025, 1, 10), 101)]))
        self.assertIsNone(CalculadoraRentabilidad.xirr([(date(2025, 1, 1), -100), (date(2025, 6, 1), -5)]))

    def test_perdida_da_ea_negativa(self):
        r = CalculadoraRentabilidad.rentabilidad_ea([(date(2024, 1, 1), -100), (date(2025, 1, 1), 90)])
        self.assertLess(r, 0)


class PruebasFuentesYAlmacen(unittest.TestCase):
    def test_respaldo_usa_segunda_fuente(self):
        malo, bueno = ProveedorFalso(falla=True), ProveedorFalso(cierres={"AAA": {date(2025, 1, 2): 1.0}})
        datos = ServicioPrecios([malo, bueno]).obtener("AAA", date(2025, 1, 2), HOY)
        self.assertEqual(datos.simbolo, "AAA")
        self.assertEqual((malo.llamadas, bueno.llamadas), (1, 1))

    def test_si_todo_falla_hay_error_claro_y_no_datos_inventados(self):
        with self.assertRaises(ErrorPrecios) as ctx:
            ServicioPrecios([ProveedorFalso(falla=True)]).obtener("AAA", date(2025, 1, 2), HOY)
        self.assertIn("No se pudieron obtener precios reales", str(ctx.exception))
        p = portafolio_vacio()
        p.registrar_operacion(op("COMPRA", date(2025, 1, 2), 1, 10), hoy=HOY)
        a = p.analizar(ServicioPrecios([ProveedorFalso(falla=True)]), HOY)
        self.assertEqual(a.posiciones, [])
        self.assertIn("AAA", a.errores)
        self.assertFalse(a.esta_completo)

    def test_cache_evita_consultar_dos_veces(self):
        prov = ProveedorFalso(cierres={"AAA": {date(2025, 1, 2): 1.0}})
        s = ServicioPrecios([prov])
        s.obtener("AAA", date(2025, 1, 2), HOY)
        s.obtener("aaa", date(2025, 1, 2), HOY)
        self.assertEqual(prov.llamadas, 1)
        s.limpiar()
        s.obtener("AAA", date(2025, 1, 2), HOY)
        self.assertEqual(prov.llamadas, 2)

    def test_guardado_y_recarga(self):
        carpeta = Path(tempfile.mkdtemp()) / "sub" / "p.json"
        p = Portafolio(Almacen(carpeta))
        p.registrar_operacion(op("COMPRA", date(2025, 1, 2), 3, 10.5, 1.0), hoy=HOY)
        p.registrar_renta_fija(InversionRentaFija("BONO", "Emisor", date(2025, 1, 1), 100.0, 0.08,
                                                  date(2027, 1, 1)), hoy=HOY)
        q = Portafolio(Almacen(carpeta))
        self.assertEqual(q.operaciones[0], p.operaciones[0])
        self.assertEqual(q.renta_fija[0], p.renta_fija[0])
        q.eliminar_operacion(q.operaciones[0].id)
        self.assertEqual(Portafolio(Almacen(carpeta)).operaciones, [])


class PruebasEntradas(unittest.TestCase):
    def test_numeros(self):
        for texto, esperado in [("1234.5", 1234.5), ("1,234.5", 1234.5), ("1.234,5", 1234.5),
                                ("2.000.000", 2_000_000), ("11,5", 11.5), ("0", 0.0)]:
            self.assertAlmostEqual(parse_numero(texto), esperado, msg=texto)
        for malo in ("", "abc", "nan", "inf"):
            with self.assertRaises(ValueError):
                parse_numero(malo)

    def test_fechas(self):
        self.assertEqual(parse_fecha("2025-03-04"), date(2025, 3, 4))
        self.assertEqual(parse_fecha("04/03/2025"), date(2025, 3, 4))
        with self.assertRaises(ValueError):
            parse_fecha("2025-13-45")


NIKE = Empresa.por_nombre("Nike")


def cartera_con(cierres, splits=None):
    p = portafolio_vacio()
    prov = ProveedorFalso(cierres={"NKE": cierres}, splits={"NKE": splits or {}}, moneda="COP")
    return Cartera(p, ServicioPrecios([prov])), p


class PruebasCartera(unittest.TestCase):
    def test_saldo_inicial_y_compra_abierta(self):
        cartera, _ = cartera_con({date(2026, 1, 5): 100_000, date(2026, 6, 30): 110_000})
        self.assertEqual(cartera.saldo(), 10_000_000)
        op, datos = cartera.preparar_compra(NIKE, 10, date(2026, 1, 5), date(2026, 12, 1), HOY_26)
        cartera.registrar_compra(op, datos, HOY_26)
        self.assertAlmostEqual(cartera.saldo(), 9_000_000)
        e = cartera.estado(HOY_26)
        self.assertEqual(len(e.abiertas), 1)
        self.assertAlmostEqual(e.valor_abiertas, 1_100_000)
        self.assertAlmostEqual(e.no_realizada, 100_000)
        self.assertAlmostEqual(e.realizada, 0.0)
        self.assertAlmostEqual(e.valor_total, 9_000_000 + 1_100_000)
        self.assertEqual(e.abiertas[0].empresa, "Nike")

    def test_venta_futura_no_se_registra_y_al_llegar_su_fecha_abona_el_dinero(self):
        cartera, p = cartera_con({date(2026, 1, 5): 100_000, date(2026, 3, 2): 120_000, date(2026, 6, 30): 110_000})
        op, datos = cartera.preparar_compra(NIKE, 10, date(2026, 1, 5), date(2026, 3, 2), date(2026, 2, 1))
        cartera.registrar_compra(op, datos, date(2026, 2, 1))
        ventas, errores = cartera.preparar_ventas_pendientes(date(2026, 2, 1))   # la fecha aún no llega
        self.assertEqual((ventas, errores), ([], {}))
        self.assertEqual(len(p.operaciones), 1)
        ventas, errores = cartera.preparar_ventas_pendientes(HOY_26)             # ya llegó
        self.assertEqual(cartera.registrar_ventas(ventas, HOY_26), {})
        self.assertEqual(len(p.operaciones), 2)
        self.assertAlmostEqual(cartera.saldo(), 10_000_000 - 1_000_000 + 1_200_000)
        e = cartera.estado(HOY_26)
        self.assertEqual((len(e.abiertas), len(e.cerradas)), (0, 1))
        self.assertAlmostEqual(e.realizada, 200_000)
        self.assertAlmostEqual(e.valor_abiertas, 0.0)
        self.assertEqual(cartera.preparar_ventas_pendientes(HOY_26)[0], [])      # no se repite

    def test_saldo_insuficiente_y_fechas_invalidas(self):
        cartera, _ = cartera_con({date(2026, 1, 5): 1_000_000, date(2026, 6, 30): 1_000_000})
        with self.assertRaisesRegex(ValueError, "Saldo insuficiente"):
            cartera.preparar_compra(NIKE, 11, date(2026, 1, 5), date(2026, 12, 1), HOY_26)
        with self.assertRaises(ValueError):
            cartera.preparar_compra(NIKE, 1, date(2026, 1, 5), date(2026, 1, 5), HOY_26)   # venta no posterior
        with self.assertRaises(ValueError):
            cartera.preparar_compra(NIKE, 1, date(2026, 8, 1), date(2026, 9, 1), HOY_26)   # compra futura
        with self.assertRaises(ValueError):
            cartera.preparar_compra(NIKE, 0, date(2026, 1, 5), date(2026, 12, 1), HOY_26)

    def test_split_posterior_a_la_compra(self):
        # Precio ajustado 50.000 y split 2:1 posterior: se pagaron 100.000 por acción, hoy hay el doble de acciones
        cartera, _ = cartera_con({date(2026, 1, 5): 50_000, date(2026, 6, 30): 60_000}, {date(2026, 3, 1): 2.0})
        op, datos = cartera.preparar_compra(NIKE, 10, date(2026, 1, 5), date(2026, 12, 1), HOY_26)
        self.assertAlmostEqual(op.precio, 100_000)
        cartera.registrar_compra(op, datos, HOY_26)
        e = cartera.estado(HOY_26)
        self.assertAlmostEqual(e.abiertas[0].acciones, 20)
        self.assertAlmostEqual(e.valor_abiertas, 1_200_000)
        self.assertAlmostEqual(e.no_realizada, 200_000)

    def test_sin_precios_no_hay_datos_inventados(self):
        p = portafolio_vacio()
        cartera = Cartera(p, ServicioPrecios([ProveedorFalso(falla=True, moneda="COP")]))
        with self.assertRaises(ErrorPrecios):
            cartera.preparar_compra(NIKE, 1, date(2026, 1, 5), date(2026, 12, 1), HOY_26)

    def test_dos_compras_de_la_misma_empresa_se_miden_por_separado(self):
        cartera, _ = cartera_con({date(2026, 1, 5): 100_000, date(2026, 2, 2): 200_000, date(2026, 6, 30): 150_000})
        for f in (date(2026, 1, 5), date(2026, 2, 2)):
            op, datos = cartera.preparar_compra(NIKE, 1, f, date(2026, 12, 1), HOY_26)
            cartera.registrar_compra(op, datos, HOY_26)
        e = cartera.estado(HOY_26)
        self.assertEqual([round(l.ganancia_no_realizada) for l in e.abiertas], [50_000, -50_000])
        self.assertAlmostEqual(e.no_realizada, 0.0)


HOY_26 = date(2026, 6, 30)


class PruebasCdtYConversion(unittest.TestCase):
    def test_rentabilidad_diaria_y_anual(self):
        c = Cdt(monto=1_000_000, tasa_ea=0.12, fuente="Banco de ejemplo", fecha_tasa=date(2026, 6, 1))
        self.assertAlmostEqual(c.rentabilidad_diaria, 1.12 ** (1 / 365) - 1, places=12)
        self.assertAlmostEqual((1 + c.rentabilidad_diaria) ** 365 - 1, 0.12, places=9)
        self.assertAlmostEqual(c.ganancia_anual_estimada, 120_000, places=4)
        self.assertAlmostEqual(c.ganancia_diaria, 1_000_000 * c.rentabilidad_diaria)

    def test_validaciones_cdt(self):
        base = dict(monto=1000, tasa_ea=0.1, fuente="X", fecha_tasa=date(2026, 1, 1))
        for cambio in ({"monto": 0}, {"tasa_ea": 0}, {"tasa_ea": 11.5}, {"fuente": " "}, {"fecha_tasa": date(2030, 1, 1)}):
            with self.assertRaises(ValueError):
                Cdt(**{**base, **cambio}).validar(HOY_26)
        Cdt(**base).validar(HOY_26)

    def test_cdt_se_guarda_sin_borrar_operaciones(self):
        ruta = Path(tempfile.mkdtemp()) / "p.json"
        p = Portafolio(Almacen(ruta))
        p.registrar_operacion(op("COMPRA", date(2026, 1, 2), 1, 10, m="COP"), hoy=HOY_26)
        p.registrar_cdt(Cdt(5_000_000, 0.11, "Banco X", date(2026, 6, 1)), hoy=HOY_26)
        p.registrar_operacion(op("COMPRA", date(2026, 1, 3), 1, 10, m="COP"), hoy=HOY_26)
        q = Portafolio(Almacen(ruta))
        self.assertEqual((len(q.operaciones), len(q.cdts)), (2, 1))
        q.eliminar_cdt(q.cdts[0].id)
        self.assertEqual((len(Portafolio(Almacen(ruta)).operaciones), len(Portafolio(Almacen(ruta)).cdts)), (2, 0))

    def test_conversion_usd_a_cop_dia_por_dia(self):
        base = ProveedorFalso(cierres={"NKE": {date(2026, 1, 5): 100.0, date(2026, 1, 6): 110.0},
                                       "COP=X": {date(2026, 1, 5): 4000.0, date(2026, 1, 6): 4100.0}},
                              dividendos={"NKE": {date(2026, 1, 6): 1.0}})
        datos = ProveedorCOP(base).obtener("NKE", date(2026, 1, 1), date(2026, 1, 10))
        self.assertEqual(datos.moneda, "COP")
        self.assertEqual(list(datos.cierres.round(2)), [400_000.0, 451_000.0])
        self.assertAlmostEqual(float(datos.dividendos.iloc[0]), 4100.0)
        self.assertIn("COP=X", datos.fuente)

    def test_conversion_falla_si_no_hay_tasa(self):
        base = ProveedorFalso(cierres={"NKE": {date(2026, 1, 5): 100.0}})
        with self.assertRaisesRegex(ErrorPrecios, "tasa de cambio"):
            ProveedorCOP(base).obtener("NKE", date(2026, 1, 1), date(2026, 1, 10))



class PruebasCatalogo(unittest.TestCase):
    def test_nombres_conocidos_no_abreviaturas(self):
        nombres = [e.nombre for e in Empresa.todas()]
        self.assertIn("Nike", nombres)
        self.assertIn("Coca-Cola", nombres)
        self.assertNotIn("KO", nombres)
        self.assertEqual(Empresa.por_nombre("Coca-Cola").simbolo, "KO")


if __name__ == "__main__":
    unittest.main()
