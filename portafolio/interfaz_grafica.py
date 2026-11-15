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


T = Tema


class InterfazGrafica:
    raiz: tk.Tk
    cartera: Cartera
    estado: Optional[EstadoCartera]

    def __init__(self, raiz: tk.Tk, cartera: Cartera):
        self.raiz, self.cartera = raiz, cartera
        self.estado = None
        self._datos: Optional[DatosMercado] = None       # precios de la empresa elegida
        self._empresa: Optional[Empresa] = None
        self._token = 0                                  # descarta respuestas de selecciones viejas
        self._refrescando = False
        self._repetir = False
        self._callbacks: List[Callable[[EstadoCartera], None]] = []
        self._errores_venta: dict = {}
        self._compra_mostrada: Optional[Tuple[Operacion, DatosMercado]] = None

        raiz.title("Portafolio de inversión")
        raiz.geometry("1360x860")
        raiz.minsize(1180, 740)
        raiz.configure(bg=T.FONDO)
        self._estilos()
        self._encabezado()
        self.estado_barra = tk.Label(raiz, text="", bg=T.PANEL, fg=T.SUAVE, anchor="w", padx=14, pady=5, font=("", 8))
        self.estado_barra.pack(side="bottom", fill="x")
        self.cuaderno = ttk.Notebook(raiz, style="Oscuro.TNotebook")
        self.cuaderno.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._pestana_invertir()
        self._pestana_resumen()
        self._pintar_cdt()
        self._pintar_saldo(self.cartera.saldo())
        self._refrescar()

    # ------------------------------------------------------------------ estilos
    def _estilos(self) -> None:
        r = self.raiz
        e = ttk.Style()
        e.theme_use("clam")
        e.configure(".", background=T.FONDO, foreground=T.TEXTO, fieldbackground=T.TARJETA, bordercolor=T.BORDE,
                    lightcolor=T.BORDE, darkcolor=T.BORDE, troughcolor=T.PANEL, focuscolor=T.ACENTO)
        e.configure("Oscuro.TNotebook", background=T.FONDO, borderwidth=0, tabmargins=(0, 0, 0, 0))
        e.configure("Oscuro.TNotebook.Tab", background=T.PANEL, foreground=T.SUAVE, padding=(26, 10),
                    font=("", 10, "bold"), borderwidth=0)
        e.map("Oscuro.TNotebook.Tab", background=[("selected", T.TARJETA)], foreground=[("selected", T.ACENTO)])
        e.configure("Oscuro.TEntry", fieldbackground=T.TARJETA, foreground=T.TEXTO, insertcolor=T.TEXTO,
                    padding=6, bordercolor=T.BORDE)
        e.map("Oscuro.TEntry", bordercolor=[("focus", T.ACENTO)])
        e.configure("Oscuro.TCombobox", fieldbackground=T.TARJETA, background=T.BORDE, foreground=T.TEXTO,
                    arrowcolor=T.TEXTO, padding=6, selectbackground=T.TARJETA, selectforeground=T.TEXTO)
        e.map("Oscuro.TCombobox", fieldbackground=[("readonly", T.TARJETA)], foreground=[("readonly", T.TEXTO)],
              selectbackground=[("readonly", T.TARJETA)], selectforeground=[("readonly", T.TEXTO)],
              bordercolor=[("focus", T.ACENTO)])
        r.option_add("*TCombobox*Listbox.background", T.TARJETA)
        r.option_add("*TCombobox*Listbox.foreground", T.TEXTO)
        r.option_add("*TCombobox*Listbox.selectBackground", T.SELECCION)
        r.option_add("*TCombobox*Listbox.selectForeground", T.TEXTO)
        r.option_add("*TCombobox*Listbox.font", ("", 10))
        e.configure("Compra.TButton", background=T.VERDE, foreground="#04210F", font=("", 11, "bold"),
                    padding=(14, 10), borderwidth=0)
        e.map("Compra.TButton", background=[("active", "#34D970"), ("disabled", "#1B4D2E")],
              foreground=[("disabled", "#6B8F78")])
        e.configure("Accion.TButton", background=T.BORDE, foreground=T.TEXTO, padding=(12, 7), borderwidth=0)
        e.map("Accion.TButton", background=[("active", "#33445C"), ("disabled", T.PANEL)])
        e.configure("Treeview", background=T.TARJETA, fieldbackground=T.TARJETA, foreground=T.TEXTO,
                    rowheight=28, borderwidth=0)
        e.map("Treeview", background=[("selected", T.SELECCION)], foreground=[("selected", T.TEXTO)])
        e.configure("Treeview.Heading", background=T.PANEL, foreground=T.SUAVE, font=("", 9, "bold"),
                    padding=6, borderwidth=0)
        e.map("Treeview.Heading", background=[("active", T.PANEL)])
        e.configure("Vertical.TScrollbar", background=T.BORDE, darkcolor=T.BORDE, lightcolor=T.BORDE,
                    troughcolor=T.PANEL, bordercolor=T.PANEL, arrowcolor=T.SUAVE, gripcount=0, borderwidth=0)
        e.map("Vertical.TScrollbar", background=[("active", "#33445C")], darkcolor=[("active", "#33445C")],
              lightcolor=[("active", "#33445C")])

    # ------------------------------------------------------------ piezas comunes
    @staticmethod
    def _etiqueta(padre, texto="", tam=10, color=T.TEXTO, negrita=False, fondo=T.PANEL, **kw) -> tk.Label:
        return tk.Label(padre, text=texto, bg=fondo, fg=color, font=("", tam, "bold" if negrita else "normal"),
                        anchor=kw.pop("anchor", "w"), **kw)

    @staticmethod
    def _panel(padre, fondo=T.PANEL, **kw) -> tk.Frame:
        return tk.Frame(padre, bg=fondo, highlightbackground=T.BORDE, highlightthickness=1, **kw)

    def _campo(self, padre, titulo: str, variable: tk.StringVar, fila: int, pista: str = "") -> ttk.Entry:
        self._etiqueta(padre, titulo, 9, T.SUAVE).grid(row=fila, column=0, sticky="w", pady=(10, 2))
        entrada = ttk.Entry(padre, textvariable=variable, style="Oscuro.TEntry")
        entrada.grid(row=fila + 1, column=0, sticky="ew")
        if pista:
            self._etiqueta(padre, pista, 8, T.SUAVE).grid(row=fila + 2, column=0, sticky="w")
        return entrada

    def _tabla(self, padre, columnas: list, altura: int) -> ttk.Treeview:
        marco = tk.Frame(padre, bg=T.TARJETA)
        arbol = ttk.Treeview(marco, columns=[c[0] for c in columnas], show="headings", height=altura)
        for ident, titulo, ancho, ancla in columnas:
            arbol.heading(ident, text=titulo)
            arbol.column(ident, width=ancho, anchor=ancla, stretch=True, minwidth=40)
        barra = ttk.Scrollbar(marco, orient="vertical", command=arbol.yview)
        arbol.configure(yscrollcommand=barra.set)
        arbol.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        arbol.tag_configure("gana", foreground=T.VERDE)
        arbol.tag_configure("pierde", foreground=T.ROJO)
        arbol.tag_configure("neutro", foreground=T.TEXTO)
        arbol.marco = marco
        return arbol

    def _encabezado(self) -> None:
        cab = tk.Frame(self.raiz, bg=T.FONDO)
        cab.pack(fill="x", padx=20, pady=(14, 10))
        self._etiqueta(cab, "Portafolio de inversión", 19, T.TEXTO, True, T.FONDO).pack(side="left")
        self._etiqueta(cab, "  ·  acciones en pesos colombianos (COP)", 10, T.SUAVE, False, T.FONDO).pack(side="left", pady=(8, 0))
        self._etiqueta(cab, fecha_corta(date.today()), 10, T.SUAVE, False, T.FONDO).pack(side="right")

    def _mensaje(self, texto: str, color: str = T.SUAVE) -> None:
        self.lbl_mensaje.config(text=texto, fg=color)

    # ============================================================ PESTAÑA 1: INVERTIR
    def _pestana_invertir(self) -> None:
        tab = tk.Frame(self.cuaderno, bg=T.FONDO)
        self.cuaderno.add(tab, text="Invertir")
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(0, weight=1)

        izq = self._panel(tab, T.PANEL)
        izq.grid(row=0, column=0, sticky="ns", padx=(0, 10), pady=10)
        izq.configure(width=410)
        cont = tk.Frame(izq, bg=T.PANEL)
        cont.pack(fill="both", expand=True, padx=20, pady=16)
        cont.columnconfigure(0, weight=1)

        self._etiqueta(cont, "SALDO DISPONIBLE", 8, T.SUAVE, True).grid(row=0, column=0, sticky="w")
        self.lbl_saldo = self._etiqueta(cont, "—", 22, T.VERDE, True)
        self.lbl_saldo.grid(row=1, column=0, sticky="w")

        self._etiqueta(cont, "Empresa", 9, T.SUAVE).grid(row=2, column=0, sticky="w", pady=(14, 2))
        self.var_empresa = tk.StringVar()
        self.cmb_empresa = ttk.Combobox(cont, textvariable=self.var_empresa, state="readonly", style="Oscuro.TCombobox",
                                        values=[e.nombre for e in Empresa.todas()], height=16)
        self.cmb_empresa.grid(row=3, column=0, sticky="ew")
        self.cmb_empresa.bind("<<ComboboxSelected>>", lambda _e: self._consultar_precio())

        self._etiqueta(cont, "Precio actual de la acción", 9, T.SUAVE).grid(row=4, column=0, sticky="w", pady=(12, 0))
        self.lbl_precio = self._etiqueta(cont, "Elija una empresa", 17, T.TEXTO, True)
        self.lbl_precio.grid(row=5, column=0, sticky="w")
        self.lbl_precio_info = self._etiqueta(cont, "", 8, T.SUAVE, wraplength=360, justify="left")
        self.lbl_precio_info.grid(row=6, column=0, sticky="w")

        hoy = date.today()
        self.var_cantidad = tk.StringVar()
        self.var_compra = tk.StringVar(value=hoy.isoformat())
        self.var_venta = tk.StringVar(value=(hoy + timedelta(days=30)).isoformat())
        self._campo(cont, "Cantidad de acciones a comprar", self.var_cantidad, 7)
        entrada_compra = self._campo(cont, "Fecha de compra (AAAA-MM-DD)", self.var_compra, 9)
        self._campo(cont, "Fecha de venta prevista (AAAA-MM-DD)", self.var_venta, 11,
                    "Si esa fecha aún no llega, la posición queda abierta y la venta no se registra todavía.")
        for evento in ("<FocusOut>", "<Return>"):
            entrada_compra.bind(evento, lambda _e: self._consultar_precio())
        self.var_cantidad.trace_add("write", lambda *_: self._estimar())
        self.var_compra.trace_add("write", lambda *_: self._estimar())

        self.lbl_estimado = self._etiqueta(cont, "", 9, T.SUAVE, wraplength=360, justify="left")
        self.lbl_estimado.grid(row=14, column=0, sticky="w", pady=(10, 4))
        self.btn_comprar = ttk.Button(cont, text="Confirmar compra", style="Compra.TButton", command=self._confirmar)
        self.btn_comprar.grid(row=15, column=0, sticky="ew", pady=(4, 6))
        self.lbl_mensaje = self._etiqueta(cont, "", 9, T.SUAVE, wraplength=360, justify="left")
        self.lbl_mensaje.grid(row=16, column=0, sticky="w")


        der = self._panel(tab, T.PANEL)
        der.grid(row=0, column=1, sticky="nsew", pady=10)
        self.grafica = GraficaInteractiva(der, self._al_seleccionar_punto)
        self.lbl_punto = self._etiqueta(der, "Haga clic en un punto de la gráfica para ver el precio de la acción ese día.",
                                        10, T.SUAVE, anchor="w")

        # Posición de la compra más reciente: abierta (valor actual) o cerrada (venta ya ocurrida)
        pos = tk.Frame(der, bg=T.TARJETA, highlightbackground=T.BORDE, highlightthickness=1)
        pos.pack(side="bottom", fill="x", padx=12, pady=(0, 12))
        self.lbl_pos_estado = self._etiqueta(pos, "SIN POSICIÓN SELECCIONADA · confirme una compra para verla aquí",
                                             9, T.SUAVE, True, T.TARJETA)
        self.lbl_pos_estado.grid(row=0, column=0, columnspan=5, sticky="w", padx=14, pady=(10, 4))
        self.pos_valores = {}
        for n, clave in enumerate(["Acciones", "Costo de compra", "Valor actual", "Ganancia", "Venta prevista"]):
            pos.columnconfigure(n, weight=1, uniform="pos")
            self._etiqueta(pos, clave, 8, T.SUAVE, False, T.TARJETA).grid(row=1, column=n, sticky="w", padx=14)
            rotulo = self._etiqueta(pos, "—", 10, T.TEXTO, True, T.TARJETA, wraplength=170, justify="left")
            rotulo.grid(row=2, column=n, sticky="w", padx=14, pady=(0, 10))
            self.pos_valores[clave] = rotulo
        # orden de empaquetado: lo de abajo primero, la gráfica ocupa el espacio restante
        self.lbl_punto.pack(side="bottom", fill="x", padx=16, pady=(4, 8))
        self.grafica.pack(side="top", fill="both", expand=True, padx=8, pady=(8, 0))

    def _al_seleccionar_punto(self, fecha: date, precio: float, variacion: Optional[float]) -> None:
        extra = f"  ·  {fmt_porcentaje(variacion)} frente al precio de compra" if variacion is not None else ""
        self.lbl_punto.config(text=f"{fecha_corta(fecha)}: la acción valía {fmt_cop(precio)} COP{extra}",
                              fg=T.color_resultado(variacion) if variacion is not None else T.TEXTO)

    def _pintar_saldo(self, saldo: float) -> None:
        self.lbl_saldo.config(text=f"{fmt_cop(saldo)} COP", fg=T.VERDE if saldo >= 0 else T.ROJO)

    # --- precio de la empresa elegida
    def _consultar_precio(self) -> None:
        empresa = Empresa.por_nombre(self.var_empresa.get())
        if empresa is None:
            return
        hoy = date.today()
        try:
            f_compra = min(parse_fecha(self.var_compra.get()), hoy)
        except ValueError:
            f_compra = hoy
        self._token += 1
        token = self._token
        self._datos, self._empresa = None, empresa
        self.lbl_precio.config(text="Consultando…", fg=T.SUAVE)
        self.lbl_precio_info.config(text="")
        inicio = min(f_compra, hoy - timedelta(days=10))
        TareaSegundoPlano.ejecutar(self.raiz, lambda: self.cartera.datos_en_cop(empresa.simbolo, inicio, hoy),
                                   lambda datos, error: self._al_llegar_precio(token, empresa, datos, error))

    def _al_llegar_precio(self, token: int, empresa: Empresa, datos, error) -> None:
        if token != self._token:
            return
        if error is not None:
            self.lbl_precio.config(text="No disponible", fg=T.ROJO)
            self.lbl_precio_info.config(text="")
            self._mensaje(str(error), T.ROJO)
            return
        self._datos = datos
        fecha, precio = datos.precio_en(date.today())
        self.lbl_precio.config(text=f"{fmt_cop(precio)} COP", fg=T.TEXTO)
        self.lbl_precio_info.config(text=f"Último cierre disponible ({fecha_corta(fecha)}) · {datos.fuente}. "
                                         "No es un precio en tiempo real.")
        self._mensaje("")
        self._estimar()

    def _estimar(self) -> None:
        self.lbl_estimado.config(text="", fg=T.SUAVE)
        if self._datos is None:
            return
        try:
            cantidad = parse_numero(self.var_cantidad.get(), "la cantidad")
            f_compra = parse_fecha(self.var_compra.get())
            _, precio = self._datos.precio_en(f_compra)
        except (ValueError, ErrorPrecios):
            return
        if cantidad <= 0:
            return
        costo = cantidad * precio * Portafolio.factor_split(self._datos.lista_splits, f_compra)
        saldo = self.cartera.saldo()
        alcanza = costo <= saldo
        self.lbl_estimado.config(
            text=f"Costo estimado: {fmt_cop(costo)} COP\nSaldo después de comprar: {fmt_cop(saldo - costo)} COP"
                 + ("" if alcanza else "\nSaldo insuficiente para esta compra."),
            fg=T.TEXTO if alcanza else T.ROJO)

    # --- confirmar compra
    def _confirmar(self) -> None:
        empresa = Empresa.por_nombre(self.var_empresa.get())
        if empresa is None:
            self._mensaje("Elija primero una empresa de la lista.", T.ROJO)
            return
        try:
            cantidad = parse_numero(self.var_cantidad.get(), "la cantidad de acciones")
            f_compra = parse_fecha(self.var_compra.get())
            f_venta = parse_fecha(self.var_venta.get())
        except ValueError as exc:
            self._mensaje(str(exc), T.ROJO)
            return
        self.btn_comprar.config(state="disabled")
        self._mensaje("Consultando el precio histórico…", T.SUAVE)
        hoy = date.today()
        TareaSegundoPlano.ejecutar(
            self.raiz, lambda: self.cartera.preparar_compra(empresa, cantidad, f_compra, f_venta, hoy),
            lambda resultado, error: self._tras_preparar(empresa, resultado, error))

    def _tras_preparar(self, empresa: Empresa, resultado, error) -> None:
        self.btn_comprar.config(state="normal")
        if error is not None:
            self._mensaje(str(error) if isinstance(error, (ValueError, ErrorPrecios)) else f"Error inesperado: {error}", T.ROJO)
            return
        operacion, datos = resultado
        try:
            self.cartera.registrar_compra(operacion, datos)
        except ValueError as exc:
            self._mensaje(str(exc), T.ROJO)
            return
        self._compra_mostrada = (operacion, datos)
        self._mensaje(f"Compra registrada: {fmt_cantidad(operacion.cantidad)} acciones de {empresa.nombre} por "
                      f"{fmt_cop(operacion.monto_bruto)} COP.", T.VERDE)
        self._pintar_saldo(self.cartera.saldo())
        self._estimar()
        self._refrescar()

    def _mostrar_posicion(self) -> None:
        """Panel de la posición recién comprada y su gráfica; la venta solo cuenta si ya ocurrió."""
        if self._compra_mostrada is None or self.estado is None:
            return
        operacion, datos = self._compra_mostrada
        lote = next((l for l in self.estado.lotes if l.compra.id == operacion.id), None)
        if lote is None:
            return
        v = self.pos_valores
        v["Acciones"].config(text=fmt_cantidad(lote.acciones), fg=T.TEXTO)
        v["Costo de compra"].config(text=f"{fmt_cop(lote.costo)} COP", fg=T.TEXTO)
        if lote.abierta:
            self.lbl_pos_estado.config(text="● POSICIÓN ABIERTA", fg=T.ACENTO)
            valor, g = lote.valor_actual, lote.ganancia_no_realizada
            v["Valor actual"].config(text=f"{fmt_cop(valor)} COP" if valor is not None else "—", fg=T.TEXTO)
            v["Ganancia"].config(text=(f"{fmt_cop(g, True)}\n{fmt_porcentaje(lote.rentabilidad)} · no realizada"
                                       if g is not None else "—"), fg=T.color_resultado(g))
            v["Venta prevista"].config(text=f"{fecha_corta(lote.fecha_venta_prevista)}\naún no ocurre (no registrada)", fg=T.DORADO)
        else:
            self.lbl_pos_estado.config(text="● POSICIÓN CERRADA", fg=T.SUAVE)
            g = lote.ganancia_realizada
            v["Valor actual"].config(text=f"{fmt_cop(lote.dinero_recibido)} COP\nrecibidos", fg=T.TEXTO)
            v["Ganancia"].config(text=f"{fmt_cop(g, True)}\n{fmt_porcentaje(lote.rentabilidad)} · realizada",
                                 fg=T.color_resultado(g))
            v["Venta prevista"].config(text=f"vendida el {fecha_corta(lote.venta.fecha)}\n(venta registrada)", fg=T.TEXTO)
        self.lbl_punto.config(text="Haga clic en un punto de la gráfica para ver el precio de la acción ese día.", fg=T.SUAVE)
        self.grafica.mostrar(datos, lote.empresa, operacion.fecha, operacion.fecha_venta_prevista,
                             self.estado.hoy, venta_ocurrida=not lote.abierta)

    # ================================================= PESTAÑA 2: RESUMEN E HISTORIAL
    def _pestana_resumen(self) -> None:
        tab = tk.Frame(self.cuaderno, bg=T.FONDO)
        self.cuaderno.add(tab, text="Resumen e historial")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)

        barra = tk.Frame(tab, bg=T.FONDO)
        barra.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.lbl_aviso = tk.Label(barra, text="", bg=T.ERROR_FONDO, fg=T.ERROR_TEXTO, justify="left",
                                  anchor="w", padx=12, pady=6, wraplength=1000, font=("", 9))
        ttk.Button(barra, text="Actualizar precios", style="Accion.TButton", command=self._actualizar_precios).pack(side="right")

        tarjetas = tk.Frame(tab, bg=T.FONDO)
        tarjetas.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)
        self.tarjetas = {}
        for n, (clave, titulo) in enumerate([
                ("saldo", "SALDO DISPONIBLE"), ("abiertas", "POSICIONES ABIERTAS"), ("total", "VALOR TOTAL DEL PORTAFOLIO"),
                ("realizada", "GANANCIA REALIZADA"), ("no_realizada", "GANANCIA NO REALIZADA")]):
            tarjetas.columnconfigure(n, weight=1, uniform="tarjeta")
            marco = self._panel(tarjetas, T.TARJETA)
            marco.grid(row=0, column=n, sticky="nsew", padx=(0 if n == 0 else 6, 0))
            self._etiqueta(marco, titulo, 8, T.SUAVE, True, T.TARJETA).pack(anchor="w", padx=14, pady=(10, 0))
            valor = self._etiqueta(marco, "—", 16, T.TEXTO, True, T.TARJETA)
            valor.pack(anchor="w", padx=14)
            pie = self._etiqueta(marco, " ", 8, T.SUAVE, False, T.TARJETA)
            pie.pack(anchor="w", padx=14, pady=(0, 10))
            self.tarjetas[clave] = (valor, pie)

        izq = tk.Frame(tab, bg=T.FONDO)
        izq.grid(row=2, column=0, sticky="nsew", padx=(0, 10))
        izq.columnconfigure(0, weight=1)
        izq.rowconfigure(3, weight=1)
        self._etiqueta(izq, "Posiciones abiertas", 11, T.TEXTO, True, T.FONDO).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.tbl_abiertas = self._tabla(izq, [
            ("empresa", "Empresa", 120, "w"), ("acciones", "Acciones", 70, "e"), ("compra", "Comprada", 95, "center"),
            ("costo", "Costo", 105, "e"), ("valor", "Valor actual", 110, "e"), ("ganancia", "Ganancia no realizada", 140, "e"),
            ("pct", "%", 70, "e"), ("venta", "Venta prevista", 105, "center")], 4)
        self.tbl_abiertas.marco.grid(row=1, column=0, sticky="ew")
        self._etiqueta(izq, "Historial de compras y ventas", 11, T.TEXTO, True, T.FONDO).grid(row=2, column=0, sticky="w", pady=(12, 4))
        self.tbl_historial = self._tabla(izq, [
            ("fecha", "Fecha", 90, "center"), ("tipo", "Operación", 75, "center"), ("empresa", "Empresa", 105, "w"),
            ("acciones", "Acciones", 65, "e"), ("precio", "Precio por acción", 115, "e"), ("total", "Dinero", 110, "e"),
            ("resultado", "Ganancia / pérdida", 125, "e"), ("estado", "Estado", 190, "w")], 8)
        self.tbl_historial.marco.grid(row=3, column=0, sticky="nsew")
        self.lbl_nota = self._etiqueta(
            izq, "Realizada = dinero recibido al vender − costo. No realizada = valor actual − costo de lo que aún se tiene "
                 "(cambia con el precio; solo se cobra al vender). Precio en COP = precio en USD × tasa USD/COP del mismo día "
                 "(Yahoo Finance). No incluye comisiones, impuestos ni dividendos.",
            8, T.SUAVE, False, T.FONDO, wraplength=860, justify="left")
        self.lbl_nota.grid(row=4, column=0, sticky="w", pady=(6, 0))

        self._seccion_cdt(tab)

    # --- CDT (sección independiente y sencilla)
    def _seccion_cdt(self, tab) -> None:
        panel = self._panel(tab, T.PANEL)
        panel.grid(row=2, column=1, sticky="ns")
        panel.configure(width=400)
        c = tk.Frame(panel, bg=T.PANEL)
        c.pack(fill="both", expand=True, padx=16, pady=12)
        c.columnconfigure(0, weight=1)
        self._etiqueta(c, "CDT · Certificado de Depósito a Término", 11, T.DORADO, True).grid(row=0, column=0, sticky="w")
        self._etiqueta(
            c, "Un CDT es un instrumento de deuda, no una acción: usted presta dinero a un banco por un plazo y este le "
               "paga intereses. Es independiente: no usa ni cambia el saldo de las acciones.",
            8, T.SUAVE, wraplength=365, justify="left").grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.var_cdt_monto, self.var_cdt_tasa = tk.StringVar(), tk.StringVar()
        self.var_cdt_fuente, self.var_cdt_fecha = tk.StringVar(), tk.StringVar(value=date.today().isoformat())
        form = tk.Frame(c, bg=T.PANEL)
        form.grid(row=2, column=0, sticky="ew")
        form.columnconfigure((0, 1), weight=1, uniform="cdt")
        for col, (titulo, var) in enumerate([("Monto (COP)", self.var_cdt_monto), ("Tasa efectiva anual (%)", self.var_cdt_tasa)]):
            self._etiqueta(form, titulo, 9, T.SUAVE).grid(row=0, column=col, sticky="w", pady=(5, 2))
            ttk.Entry(form, textvariable=var, style="Oscuro.TEntry", width=14).grid(row=1, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0))
        for col, (titulo, var) in enumerate([("Fuente de la tasa", self.var_cdt_fuente), ("Fecha de la tasa", self.var_cdt_fecha)]):
            self._etiqueta(form, titulo, 9, T.SUAVE).grid(row=2, column=col, sticky="w", pady=(5, 2))
            ttk.Entry(form, textvariable=var, style="Oscuro.TEntry", width=14).grid(row=3, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0))
        self.lbl_cdt_previa = self._etiqueta(c, "", 9, T.SUAVE, wraplength=365, justify="left")
        self.lbl_cdt_previa.grid(row=3, column=0, sticky="w", pady=(5, 3))
        ttk.Button(c, text="Registrar CDT", style="Accion.TButton", command=self._registrar_cdt).grid(row=4, column=0, sticky="ew")
        self.lbl_cdt_msg = self._etiqueta(c, "", 9, T.SUAVE, wraplength=365, justify="left")
        self.lbl_cdt_msg.grid(row=5, column=0, sticky="w", pady=(2, 4))
        for var in (self.var_cdt_monto, self.var_cdt_tasa):
            var.trace_add("write", lambda *_: self._previa_cdt())

        self.tbl_cdt = self._tabla(c, [("monto", "Monto", 95, "e"), ("tasa", "Tasa E.A.", 62, "e"),
                                      ("diaria", "Rent. diaria", 85, "e"), ("anual", "Estim. anual", 95, "e")], 3)
        self.tbl_cdt.marco.grid(row=6, column=0, sticky="ew")
        self.tbl_cdt.bind("<<TreeviewSelect>>", lambda _e: self._detalle_cdt())
        self.lbl_cdt_detalle = self._etiqueta(c, "", 8, T.SUAVE, wraplength=365, justify="left")
        self.lbl_cdt_detalle.grid(row=7, column=0, sticky="w", pady=(6, 0))
        self.lbl_cdt_total = self._etiqueta(c, "", 9, T.TEXTO, True, wraplength=365, justify="left")
        self.lbl_cdt_total.grid(row=8, column=0, sticky="w", pady=(4, 0))
        ttk.Button(c, text="Eliminar CDT seleccionado", style="Accion.TButton", command=self._eliminar_cdt).grid(row=9, column=0, sticky="ew", pady=(6, 4))
        self._etiqueta(
            c, "Rentabilidad diaria = (1 + tasa anual)^(1/365) − 1. Estimación anual sin retención ni impuestos. "
               "Use tasas reales (banco o Superfinanciera) e indique fuente y fecha; el programa no inventa tasas.",
            8, T.SUAVE, wraplength=365, justify="left").grid(row=10, column=0, sticky="w")

    def _leer_cdt(self) -> Cdt:
        monto = parse_numero(self.var_cdt_monto.get(), "el monto")
        tasa = parse_numero(self.var_cdt_tasa.get(), "la tasa") / 100.0
        return Cdt(monto=monto, tasa_ea=tasa, fuente=self.var_cdt_fuente.get().strip(),
                   fecha_tasa=parse_fecha(self.var_cdt_fecha.get()))

    def _previa_cdt(self) -> None:
        try:
            monto = parse_numero(self.var_cdt_monto.get(), "el monto")
            tasa = parse_numero(self.var_cdt_tasa.get(), "la tasa") / 100.0
            if monto <= 0 or not 0 < tasa < 1:
                raise ValueError
            c = Cdt(monto, tasa, "x", date.today())
        except ValueError:
            self.lbl_cdt_previa.config(text="")
            return
        self.lbl_cdt_previa.config(
            text=f"Rentabilidad diaria: {fmt_porcentaje(c.rentabilidad_diaria, 4, False)}  ≈ {fmt_cop(c.ganancia_diaria)} por día\n"
                 f"Estimación anual: {fmt_cop(c.ganancia_anual_estimada, True)}", fg=T.VERDE)

    def _registrar_cdt(self) -> None:
        try:
            self.cartera.portafolio.registrar_cdt(self._leer_cdt())
        except ValueError as exc:
            self.lbl_cdt_msg.config(text=str(exc), fg=T.ROJO)
            return
        for var in (self.var_cdt_monto, self.var_cdt_tasa, self.var_cdt_fuente):
            var.set("")
        self.lbl_cdt_msg.config(text="CDT registrado.", fg=T.VERDE)
        self._pintar_cdt()

    def _eliminar_cdt(self) -> None:
        seleccion = self.tbl_cdt.selection()
        if not seleccion:
            self.lbl_cdt_msg.config(text="Seleccione un CDT de la lista para eliminarlo.", fg=T.SUAVE)
            return
        self.cartera.portafolio.eliminar_cdt(seleccion[0])
        self.lbl_cdt_msg.config(text="CDT eliminado.", fg=T.SUAVE)
        self._pintar_cdt()

    def _detalle_cdt(self) -> None:
        seleccion = self.tbl_cdt.selection()
        cdt = next((x for x in self.cartera.portafolio.cdts if seleccion and x.id == seleccion[0]), None)
        if cdt is None:
            self.lbl_cdt_detalle.config(text="")
            return
        self.lbl_cdt_detalle.config(text=f"Ganancia diaria estimada: {fmt_cop(cdt.ganancia_diaria)} · "
                                         f"Fuente de la tasa: {cdt.fuente} ({cdt.fecha_tasa.isoformat()})")

    def _pintar_cdt(self) -> None:
        self.tbl_cdt.delete(*self.tbl_cdt.get_children())
        cdts = self.cartera.portafolio.cdts
        for c in cdts:
            self.tbl_cdt.insert("", "end", iid=c.id, tags=("gana",), values=(
                fmt_cop(c.monto), fmt_porcentaje(c.tasa_ea, 2, False), fmt_porcentaje(c.rentabilidad_diaria, 4, False),
                fmt_cop(c.ganancia_anual_estimada, True)))
        total = sum(c.monto for c in cdts)
        diaria = sum(c.ganancia_diaria for c in cdts)
        anual = sum(c.ganancia_anual_estimada for c in cdts)
        self.lbl_cdt_total.config(text=(f"Total en CDT: {fmt_cop(total)} · {fmt_cop(diaria)}/día · {fmt_cop(anual, True)}/año"
                                        if cdts else "Aún no hay CDT registrados."), fg=T.TEXTO if cdts else T.SUAVE)
        self.lbl_cdt_detalle.config(text="")

    # ================================================================ actualización
    def _actualizar_precios(self) -> None:
        self.cartera.servicio.limpiar()
        self._refrescar()

    def _refrescar(self, al_terminar: Optional[Callable[[EstadoCartera], None]] = None) -> None:
        """1) registra ventas cuya fecha ya llegó  2) calcula el estado con precios actuales."""
        if al_terminar:
            self._callbacks.append(al_terminar)
        if self._refrescando:
            self._repetir = True
            return
        self._refrescando = True
        self.estado_barra.config(text="Consultando precios históricos…")
        TareaSegundoPlano.ejecutar(self.raiz, lambda: self.cartera.preparar_ventas_pendientes(date.today()), self._tras_pendientes)

    def _tras_pendientes(self, resultado, error) -> None:
        if error is not None:
            self._errores_venta = {"Ventas": str(error)}
        else:
            ventas, errores = resultado
            errores.update(self.cartera.registrar_ventas(ventas))
            self._errores_venta = errores
        TareaSegundoPlano.ejecutar(self.raiz, lambda: self.cartera.estado(date.today()), self._tras_estado)

    def _tras_estado(self, estado, error) -> None:
        self._refrescando = False
        if error is not None:
            self.estado_barra.config(text=f"Error al calcular la cartera: {error}")
        else:
            self.estado = estado
            self._pintar()
            for callback in self._callbacks:
                callback(estado)
        self._callbacks.clear()
        if self._repetir:
            self._repetir = False
            self._refrescar()

    # ---------------------------------------------------------------- pintar datos
    def _pintar(self) -> None:
        e = self.estado
        self._pintar_saldo(e.saldo)
        avisos = [f"{nombre}: {motivo}" for nombre, motivo in {**e.errores, **self._errores_venta}.items()]
        if avisos:
            self.lbl_aviso.config(text="Resultados incompletos — " + "\n".join(avisos))
            self.lbl_aviso.pack(side="left", fill="x", expand=True, padx=(0, 10))
        else:
            self.lbl_aviso.pack_forget()

        t = self.tarjetas
        t["saldo"][0].config(text=fmt_cop(e.saldo), fg=T.TEXTO)
        t["saldo"][1].config(text=f"Inicio: {fmt_cop(Cartera.SALDO_INICIAL)}")
        t["abiertas"][0].config(text=fmt_cop(e.valor_abiertas), fg=T.TEXTO)
        t["abiertas"][1].config(text=f"{len(e.abiertas)} posición(es) abierta(s)")
        variacion = e.valor_total - Cartera.SALDO_INICIAL
        t["total"][0].config(text=fmt_cop(e.valor_total), fg=T.color_resultado(variacion))
        t["total"][1].config(text=f"{fmt_cop(variacion, True)} frente al saldo inicial")
        t["realizada"][0].config(text=fmt_cop(e.realizada, True), fg=T.color_resultado(e.realizada))
        t["realizada"][1].config(text="Ventas ya cobradas")
        t["no_realizada"][0].config(text=fmt_cop(e.no_realizada, True), fg=T.color_resultado(e.no_realizada))
        t["no_realizada"][1].config(text="En papel: cambia con el precio")

        self.tbl_abiertas.delete(*self.tbl_abiertas.get_children())
        for l in e.abiertas:
            g = l.ganancia_no_realizada
            self.tbl_abiertas.insert("", "end", tags=("gana" if (g or 0) > 0 else "pierde" if (g or 0) < 0 else "neutro",), values=(
                l.empresa, fmt_cantidad(l.acciones), l.compra.fecha.isoformat(), fmt_cop(l.costo),
                fmt_cop(l.valor_actual), fmt_cop(g, True), fmt_porcentaje(l.rentabilidad),
                l.fecha_venta_prevista.isoformat() if l.fecha_venta_prevista else "—"))

        self.tbl_historial.delete(*self.tbl_historial.get_children())
        lotes = {l.compra.id: l for l in e.lotes}
        for op in sorted(self.cartera.portafolio.operaciones, key=lambda o: (o.fecha, o.es_compra), reverse=True):
            if op.es_compra:
                lote = lotes.get(op.id)
                estado = (f"Abierta (venta: {op.fecha_venta_prevista})" if lote is None or lote.abierta else "Cerrada")
                resultado, etiqueta, nombre = "—", "neutro", lote.empresa if lote else op.simbolo
            else:
                lote = lotes.get(op.compra_id)
                g = lote.ganancia_realizada if lote else None
                resultado, etiqueta = fmt_cop(g, True), ("gana" if (g or 0) > 0 else "pierde" if (g or 0) < 0 else "neutro")
                estado, nombre = "Vendida (realizada)", lote.empresa if lote else op.simbolo
            self.tbl_historial.insert("", "end", tags=(etiqueta,), values=(
                op.fecha.isoformat(), "Compra" if op.es_compra else "Venta", nombre, fmt_cantidad(op.cantidad),
                fmt_cop(op.precio), fmt_cop(op.flujo_caja, True), resultado, estado))

        if e.fuente and e.consultado_en:
            self.estado_barra.config(text=f"Fuente de precios: {e.fuente} · consultado el {e.consultado_en:%Y-%m-%d %H:%M} · "
                                          "cierres diarios, no es tiempo real")
        else:
            self.estado_barra.config(text="Precios: Yahoo Finance (yfinance) · se consultan al elegir una empresa o al comprar")
        self._mostrar_posicion()
