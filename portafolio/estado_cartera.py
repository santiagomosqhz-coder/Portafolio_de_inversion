"""Fotografía de la cartera en una fecha: saldo, posiciones y ganancias."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from .lote import Lote
