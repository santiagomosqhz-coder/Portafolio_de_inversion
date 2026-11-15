from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

@dataclass
class Cdt:
    monto: float             # dinero depositado, en COP
    tasa_ea: float           # tasa efectiva anual como fracción (0.115 = 11,5 %)
    fuente: str              # de dónde salió la tasa (banco, Superfinanciera, DTF, etc.)
    fecha_tasa: date         # fecha en que se consultó o se ofreció esa tasa
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

