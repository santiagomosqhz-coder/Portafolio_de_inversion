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
