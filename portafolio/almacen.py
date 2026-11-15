"""Guarda y lee el portafolio en un archivo JSON local."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Tuple

from .cdt import Cdt
from .operacion import Operacion
from .renta_fija import InversionRentaFija


class Almacen: