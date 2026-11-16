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