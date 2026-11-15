"""Inversión de renta fija: CDT, bono o título de deuda pública (TES)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple

Flujo = Tuple[date, float]

