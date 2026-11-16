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

