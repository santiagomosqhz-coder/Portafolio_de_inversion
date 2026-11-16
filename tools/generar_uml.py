"""Genera el diagrama UML leyendo las clases REALES del paquete `portafolio`.

Como el diagrama sale del propio código (atributos, métodos, herencia, asociaciones
e importaciones), siempre coincide con él. Vuelva a ejecutarlo tras cambiar clases:

    python tools/generar_uml.py

Escribe: wiki/imagenes/diagrama_uml.png, wiki/diagrama_uml.dot y wiki/diagrama_uml.mmd (Mermaid).
Requiere Graphviz (comando `dot`) solo para el PNG; los otros dos archivos se generan siempre.
"""
from __future__ import annotations

import ast
import dataclasses
import importlib
import inspect
import pkgutil
import re
import shutil
import subprocess
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import portafolio  # noqa: E402

COLOR = {"modelo": "#DCEBF7", "calculo": "#E2F0D9", "datos": "#FFF2CC", "interfaz": "#F4DFF0"}
CAPA = {
    "Operacion": "modelo", "InversionRentaFija": "modelo", "Posicion": "modelo", "Resumen": "modelo",
    "AnalisisPortafolio": "modelo", "DatosMercado": "modelo", "Empresa": "modelo", "Cdt": "modelo",
    "Lote": "modelo", "EstadoCartera": "modelo",
    "Portafolio": "calculo", "CalculadoraRentabilidad": "calculo", "Cartera": "calculo",
    "ProveedorPrecios": "datos", "ProveedorYahoo": "datos", "ProveedorAlphaVantage": "datos", "ProveedorCOP": "datos",
    "ServicioPrecios": "datos", "ErrorPrecios": "datos", "Almacen": "datos", "Configuracion": "datos",
    "InterfazGrafica": "interfaz", "GraficaInteractiva": "interfaz", "Tema": "interfaz", "TareaSegundoPlano": "interfaz",
}


def cargar_clases():
    clases = {}
    for info in pkgutil.iter_modules(portafolio.__path__):
        modulo = importlib.import_module(f"portafolio.{info.name}")
        for nombre, cls in inspect.getmembers(modulo, inspect.isclass):
            if cls.__module__ == modulo.__name__:
                clases[nombre] = (cls, info.name)
    return clases


def atributos(cls):
    if dataclasses.is_dataclass(cls):
        return [(f.name, str(f.type)) for f in dataclasses.fields(cls)]
    return [(n, str(t)) for n, t in cls.__dict__.get("__annotations__", {}).items()]


def metodos(cls):
    salida = []
    for nombre, miembro in cls.__dict__.items():
        if nombre.startswith("_"):
            continue
        if isinstance(miembro, property):
            salida.append((nombre, None, "propiedad"))
            continue
        tipo = ""
        if isinstance(miembro, staticmethod):
            miembro, tipo = miembro.__func__, "estático"
        elif isinstance(miembro, classmethod):
            miembro, tipo = miembro.__func__, "clase"
        if inspect.isfunction(miembro):
            params = [p for p in inspect.signature(miembro).parameters if p not in ("self", "cls")]
            salida.append((nombre, params, tipo))
    return salida


def relaciones(clases):
    herencia, asociacion, dependencia = set(), set(), set()
    nombres = set(clases)
    for nombre, (cls, modulo) in clases.items():
        for base in cls.__bases__:
            if base.__name__ in nombres:
                herencia.add((nombre, base.__name__))
        texto_attrs = " ".join(t for _, t in atributos(cls))
        for otro in nombres - {nombre}:
            if re.search(rf"\b{otro}\b", texto_attrs):
                asociacion.add((nombre, otro))
        arbol = ast.parse(Path(inspect.getsourcefile(cls)).read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and nodo.level == 1:
                for alias in nodo.names:
                    if alias.name in nombres and alias.name != nombre:
                        dependencia.add((nombre, alias.name))
    # lo ya expresado como herencia o asociación no se repite como dependencia
    dependencia -= asociacion | herencia
    for hija, madre in herencia:
        dependencia.discard((hija, madre))
    return herencia, asociacion, dependencia

