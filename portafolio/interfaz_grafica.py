"""Ventana principal: dos pestañas (Invertir y Resumen e historial), tema oscuro."""
from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk
from typing import Callable, List, Optional, Tuple

from .cartera import Cartera
from .cdt import Cdt
from .datos_mercado import DatosMercado
from .empresa import Empresa
from .error_precios import ErrorPrecios
from .estado_cartera import EstadoCartera
from .grafica_interactiva import GraficaInteractiva, fecha_corta
from .operacion import Operacion
from .portafolio import Portafolio
from .tarea_segundo_plano import TareaSegundoPlano
from .tema import Tema
from .utilidades import fmt_cantidad, fmt_cop, fmt_porcentaje, parse_fecha, parse_nume