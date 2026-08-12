"""Punto de extensión del plano de datos (asignado a Ricardo)."""


class Reenviador:
    """Interfaz que el router invoca al recibir un sobre ``type: message``.

    Ricardo debe reemplazar este esqueleto por la consulta al CSV, la lógica
    TTL/hops y el envío hacia el siguiente salto. Ver docs/ricardo.md.
    """

    def __init__(self, nombre, topologia, directorio_tablas="runtime"):
        self.nombre = nombre
        self.topologia = topologia
        self.directorio_tablas = directorio_tablas

    def procesar(self, mensaje, usa_hamming):
        return "pendiente: plano de datos asignado a Ricardo"
