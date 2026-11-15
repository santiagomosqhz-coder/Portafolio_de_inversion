from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Tuple

import pandas as pd

from .posicion import Posicion
from .renta_fija import InversionRentaFija
from .resumen import Resumen