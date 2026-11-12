# Instalación y uso

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # Windows sin pip en PATH: python -m pip install -r requirements.txt
python main.py
```
Requiere Python 3.9+, tkinter e internet. No se necesita clave API ni pago. En Linux: `sudo apt install python3-tk`.

## Pestaña Invertir
1. Elija la empresa: aparece su precio actual en COP.
2. Escriba cuántas acciones, la fecha de compra y la fecha de venta prevista (AAAA-MM-DD).
3. **Confirmar compra**: se descuenta del saldo y aparece la gráfica. Haga clic en la línea para ver el precio de ese día.
4. Si la venta es futura, la posición queda **abierta** y no hay venta registrada hasta que llegue la fecha.

## Pestaña Resumen e historial
Tarjetas con saldo, posiciones abiertas, valor total, ganancia realizada y no realizada; tablas de posiciones e historial; y la sección CDT.

## CDT
Monto, tasa efectiva anual (%), fuente de la tasa y su fecha. Se muestra la rentabilidad diaria y una estimación anual. No afecta el saldo de las acciones.

## Errores frecuentes
| Mensaje | Qué hacer |
|---|---|
| "No se pudieron obtener precios reales…" | Revise internet y reintente; Yahoo Finance es no oficial |
| "Saldo insuficiente…" | Compre menos acciones |
| "La fecha de venta prevista debe ser posterior…" | Corrija las fechas |
