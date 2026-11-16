"""Error que se lanza cuando no se pueden obtener precios reales."""


class ErrorPrecios(Exception):
    """La fuente de datos falló o no conoce el símbolo.

    El programa nunca sustituye precios reales por datos inventados: ante este
    error se muestra el mensaje al usuario y el cálculo afectado no se realiza.
    """
