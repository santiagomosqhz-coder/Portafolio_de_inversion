"""Una compra de acciones y, si ya ocurrió, la venta que la cerró."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .operacion import Operacion
