"""Plano de datos: reenvío de mensajes usando la tabla de enrutamiento CSV."""

import csv
from pathlib import Path

from comun.configuracion import config_endpoint
from comun.protocolo import crear_trama
from comun.transporte import enviar_trama


class Reenviador:
    """Reenvía sobres de datos (``type: message``) hacia su destino final.

    El mismo camino sirve para reenviar entre routers y para la entrega
    final a un endpoint (ATM/BANK): en ambos casos se resuelve una IP y
    puerto y se les manda la trama tal cual, sin distinguir casos.
    """

    def __init__(self, nombre, topologia, directorio_tablas="runtime"):
        self.nombre = nombre
        self.topologia = topologia
        self.directorio_tablas = Path(directorio_tablas)

    def procesar(self, mensaje, usa_hamming):
        destino = mensaje.get("to")
        ttl = mensaje.get("ttl")
        hops = mensaje.get("hops")

        if not isinstance(destino, str) or not isinstance(ttl, int) or not isinstance(hops, list):
            return "descartado: sobre mal formado"
        if self.nombre in hops:
            return "descartado: ciclo detectado"
        if ttl <= 0:
            return "descartado: ttl agotado"

        siguiente = self._resolver_siguiente_salto(destino)
        if siguiente is None:
            return f"descartado: sin ruta hacia {destino}"

        reenvio = dict(mensaje, ttl=ttl - 1, hops=hops + [self.nombre])
        ip, puerto = siguiente
        trama = crear_trama(reenvio, con_hamming=usa_hamming)
        if not enviar_trama(ip, puerto, trama):
            return f"error: no se pudo contactar a {ip}:{puerto}"
        return f"reenviado hacia {destino} vía {ip}:{puerto}"

    def _resolver_siguiente_salto(self, destino):
        """IP y puerto a los que hay que mandar la trama para acercarla a ``destino``."""
        try:
            endpoint = config_endpoint(self.topologia, destino)
        except KeyError:
            endpoint = None

        if endpoint is not None:
            if endpoint["gateway"] == self.nombre:
                return endpoint["ip"], endpoint["puerto"]
            destino_ruta = endpoint["gateway"]
        else:
            destino_ruta = destino

        return self._consultar_csv(destino_ruta)

    def _consultar_csv(self, destino):
        ruta = self.directorio_tablas / f"{self.nombre}_tabla_enrutamiento.csv"
        try:
            with ruta.open(newline="", encoding="utf-8") as archivo:
                for fila in csv.DictReader(archivo):
                    if fila["destino"] == destino:
                        return fila["ip"], int(fila["puerto"])
        except FileNotFoundError:
            return None
        return None
