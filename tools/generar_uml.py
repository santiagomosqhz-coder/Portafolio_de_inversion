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
