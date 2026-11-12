"""Punto de entrada: ejecuta `python main.py` para abrir la aplicación."""
from __future__ import annotations

import argparse
import sys


def comprobar_dependencias() -> None:
    faltan = []
    for modulo, paquete in (("tkinter", "tkinter (Linux: sudo apt install python3-tk)"),
                            ("pandas", "pandas"), ("matplotlib", "matplotlib"), ("yfinance", "yfinance")):
        try:
            __import__(modulo)
        except ImportError:
            faltan.append(paquete)
    if faltan:
        sys.exit("Faltan dependencias: " + ", ".join(faltan) +
                 "\nInstale las de Python con:  pip install -r requirements.txt")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seguimiento de portafolio de inversión")
    parser.add_argument("--datos", help="Ruta del archivo JSON donde se guardan las operaciones "
                                        "(por defecto datos/cartera.json)")
    argumentos = parser.parse_args()
    comprobar_dependencias()

    import tkinter as tk

    from portafolio.almacen import Almacen
    from portafolio.cartera import Cartera
    from portafolio.configuracion import Configuracion
    from portafolio.interfaz_grafica import InterfazGrafica
    from portafolio.portafolio import Portafolio
    from portafolio.proveedor_cop import ProveedorCOP
    from portafolio.proveedor_yahoo import ProveedorYahoo
    from portafolio.servicio_precios import ServicioPrecios

    config = Configuracion.cargar(argumentos.datos)
    # Yahoo Finance entrega precios en USD; ProveedorCOP los convierte a pesos con la tasa USD/COP de cada día.
    servicio = ServicioPrecios([ProveedorCOP(ProveedorYahoo())])

    raiz = tk.Tk()
    try:
        portafolio = Portafolio(Almacen(config.ruta_datos))
    except ValueError as exc:
        raiz.destroy()
        sys.exit(f"No se pudo abrir el portafolio: {exc}")
    InterfazGrafica(raiz, Cartera(portafolio, servicio))
    raiz.mainloop()


if __name__ == "__main__":
    main()
