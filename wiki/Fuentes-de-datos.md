# Fuentes de datos

| Dato | Fuente | Clave | Notas |
|---|---|---|---|
| Precios de acciones | Yahoo Finance (`yfinance`) | No | No oficial; puede fallar o limitar el acceso |
| Tasa USD/COP | Yahoo Finance (`COP=X`) | No | Tasa de mercado de Yahoo, no la TRM oficial |
| Tasa de CDT | La escribe el usuario | — | Con fuente y fecha; el programa no inventa tasas |

Son cierres diarios, no tiempo real. Si la fuente falla se muestra un error y no se usan datos inventados. Alpha Vantage queda en el código pero no está conectado (no entrega la tasa de cambio).
