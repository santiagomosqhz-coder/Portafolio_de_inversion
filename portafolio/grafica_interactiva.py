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


MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def fecha_corta(f: date) -> str:
    return f"{f.day} {MESES[f.month - 1]} {f.year}"


class GraficaInteractiva(tk.Frame):
    """AlSeleccionar(fecha, precio, variación_vs_compra) se llama al hacer clic en la línea."""

    al_seleccionar: Optional[Callable[[date, float, Optional[float]], None]]

    def __init__(self, padre, al_seleccionar: Optional[Callable[[date, float, Optional[float]], None]] = None):
        super().__init__(padre, bg=Tema.PANEL)
        self.al_seleccionar = al_seleccionar
        self.figura = Figure(figsize=(7.5, 3.8), dpi=100, facecolor=Tema.PANEL)
        self.lienzo = FigureCanvasTkAgg(self.figura, master=self)
        self.lienzo.get_tk_widget().configure(bg=Tema.PANEL, highlightthickness=0)
        self.lienzo.get_tk_widget().pack(fill="both", expand=True)
        self._ejes = None
        self._x = np.array([])
        self._fechas: pd.DatetimeIndex = pd.DatetimeIndex([])
        self._precios = np.array([])
        self._precio_compra: Optional[float] = None
        self._marca = None
        self._nota = None
        self._guia = None
        self.lienzo.mpl_connect("button_press_event", self._al_clic)
        self.lienzo.mpl_connect("motion_notify_event", self._al_mover)
        self.limpiar("Elija una empresa y confirme una compra para ver la gráfica del precio.")

    # ------------------------------------------------------------------ dibujo
    def limpiar(self, mensaje: str) -> None:
        self.figura.clear()
        self._ejes = None
        self._x = np.array([])
        ax = self.figura.add_subplot(111)
        ax.set_facecolor(Tema.PANEL)
        ax.axis("off")
        ax.text(0.5, 0.5, mensaje, ha="center", va="center", color=Tema.SUAVE, fontsize=11, wrap=True)
        self.lienzo.draw_idle()

    def mostrar(self, datos: DatosMercado, titulo: str, fecha_compra: date, fecha_venta_prevista: date,
                hoy: date, venta_ocurrida: bool) -> None:
        """Precio histórico en COP desde la compra hasta la venta (o hasta hoy si la venta aún no llega)."""
        fin = min(fecha_venta_prevista, hoy)
        serie = datos.cierres[(datos.cierres.index >= pd.Timestamp(fecha_compra)) & (datos.cierres.index <= pd.Timestamp(fin))]
        if serie.empty:
            self.limpiar("La fuente no tiene precios para ese período.")
            return
        _, precio_compra = datos.precio_en(fecha_compra)
        self._precio_compra = precio_compra
        self._fechas, self._precios = pd.DatetimeIndex(serie.index), serie.to_numpy(dtype=float)
        self._x = mdates.date2num(self._fechas.to_pydatetime())

        color = Tema.VERDE if self._precios[-1] >= precio_compra else Tema.ROJO
        self.figura.clear()
        ax = self.figura.add_subplot(111)
        self._ejes = ax
        ax.set_facecolor(Tema.PANEL)
        ax.plot(self._fechas, self._precios, color=color, linewidth=1.8, zorder=3)
        ax.fill_between(self._fechas, self._precios, self._precios.min() * 0.995, color=color, alpha=0.10, zorder=2)
        ax.axhline(precio_compra, color=Tema.SUAVE, linestyle=":", linewidth=1, zorder=1)
        ax.scatter([pd.Timestamp(fecha_compra)], [precio_compra], marker="^", s=90, color=Tema.VERDE,
                   edgecolor=Tema.FONDO, zorder=5, label="Compra")
        if venta_ocurrida:
            ax.scatter([self._fechas[-1]], [self._precios[-1]], marker="v", s=90, color=Tema.ROJO,
                       edgecolor=Tema.FONDO, zorder=5, label="Venta")
        else:
            ax.axvline(pd.Timestamp(fecha_venta_prevista), color=Tema.DORADO, linestyle="--", linewidth=1.2, zorder=1)
            ax.scatter([self._fechas[-1]], [self._precios[-1]], s=40, color=Tema.ACENTO, zorder=5, label="Hoy")
            ax.set_xlim(pd.Timestamp(fecha_compra) - pd.Timedelta(days=1),
                        pd.Timestamp(fecha_venta_prevista) + pd.Timedelta(days=2))
            ax.text(pd.Timestamp(fecha_venta_prevista), 0.98, " Venta prevista", color=Tema.DORADO, fontsize=8,
                    transform=ax.get_xaxis_transform(), ha="right", va="top", rotation=90)
        ax.set_title(f"{titulo} · precio de la acción en COP", loc="left", color=Tema.TEXTO, fontsize=11, pad=12)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: fmt_cop(v)))
        localizador = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(localizador)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(localizador))
        ax.tick_params(colors=Tema.SUAVE, labelsize=8)
        ax.grid(color=Tema.BORDE, alpha=0.6, linewidth=0.6)
        for lado, espina in ax.spines.items():
            espina.set_color(Tema.BORDE)
            espina.set_visible(lado in ("left", "bottom"))
        ax.legend(loc="best", fontsize=8, frameon=False, labelcolor=Tema.SUAVE, scatterpoints=1)
        self.figura.text(0.01, 0.01, f"Fuente: {datos.fuente} · consultado el {datos.consultado_en:%Y-%m-%d %H:%M} · "
                         "cierres diarios, no es tiempo real", fontsize=7, color=Tema.SUAVE)
        self.figura.tight_layout(rect=(0, 0.04, 1, 1))
        self._marca = self._nota = self._guia = None
        self.lienzo.draw_idle()

    # -------------------------------------------------------------- interacción
    def _indice_cercano(self, xdata: float) -> int:
        return int(np.abs(self._x - xdata).argmin())

    def _al_clic(self, evento) -> None:
        if self._ejes is None or evento.inaxes is not self._ejes or evento.xdata is None:
            return
        self.seleccionar(self._indice_cercano(evento.xdata))

    def _al_mover(self, evento) -> None:
        if self._ejes is None or evento.inaxes is not self._ejes or evento.xdata is None:
            return
        indice = self._indice_cercano(evento.xdata)
        if evento.button == 1:                       # arrastrar con el botón apretado también selecciona
            self.seleccionar(indice)
            return
        if self._guia is None:
            self._guia = self._ejes.axvline(self._fechas[indice], color=Tema.SUAVE, linewidth=0.8, alpha=0.6)
        else:
            self._guia.set_xdata([self._fechas[indice], self._fechas[indice]])
        self.lienzo.draw_idle()

    def seleccionar(self, indice: int) -> None:
        """Marca el punto `indice` en la gráfica y avisa su fecha y precio."""
        ax = self._ejes
        fecha, precio = self._fechas[indice], float(self._precios[indice])
        for artista in (self._marca, self._nota):
            if artista is not None:
                artista.remove()
        self._marca = ax.scatter([fecha], [precio], s=70, color=Tema.TEXTO, edgecolor=Tema.ACENTO, linewidth=2, zorder=6)
        a_la_derecha = indice > len(self._fechas) * 0.65
        self._nota = ax.annotate(
            f"{fecha_corta(fecha.date())}\n{fmt_cop(precio)} COP", (fecha, precio),
            xytext=(-12 if a_la_derecha else 12, 18), textcoords="offset points",
            ha="right" if a_la_derecha else "left", color=Tema.TEXTO, fontsize=9, zorder=7,
            bbox={"boxstyle": "round,pad=0.4", "fc": Tema.TARJETA, "ec": Tema.ACENTO, "lw": 1},
            arrowprops={"arrowstyle": "-", "color": Tema.ACENTO})
        self.lienzo.draw_idle()
        if self.al_seleccionar:
            variacion = precio / self._precio_compra - 1 if self._precio_compra else None
            self.al_seleccionar(fecha.date(), precio, variacion)
