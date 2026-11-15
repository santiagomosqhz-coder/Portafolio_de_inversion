"""Gráfica de precios en tema oscuro: al hacer clic en un punto se muestra el precio de la acción."""
from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from typing import Callable, Optional

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from .datos_mercado import DatosMercado
from .tema import Tema
from .utilidades import fmt_cop, fmt_porcentaje