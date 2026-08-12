"""Router Link State con control concurrente y plano de datos separado."""

import csv
import threading
import time
from pathlib import Path

from comun.configuracion import config_nodo, direccion_router
from comun.protocolo import crear_trama, leer_trama
from comun.transporte import ServidorLineas, enviar_trama
from control.dijkstra import caminos_mas_cortos, siguiente_salto
from datos.forwarding import Reenviador

INTERVALO_HELLO = 5
TIEMPO_CAIDA = 15
TTL_LSA = 8
INTERVALO_LSA = 20


class Router:
    def __init__(self, nombre, topologia, directorio_runtime="runtime"):
        self.nombre, self.topologia = nombre, topologia
        config = config_nodo(topologia, nombre)
        self.ip, self.puerto = config["ip"], config["puerto"]
        self.costos_vecinos = dict(config["vecinos"])
        # Un enlace solo pasa a activo después de recibir HELLO. Así el arranque
        # de procesos en distinto orden no publica vecinos que aún no existen.
        self.vecinos_activos = set()
        self.ultimo_hello = {}
        self.lsdb, self.mayor_seq = {}, {}
        self.candado = threading.Lock()
        self.runtime = Path(directorio_runtime)
        (self.runtime / "state").mkdir(parents=True, exist_ok=True)
        self.seq = self._cargar_seq()
        self.reenviador = Reenviador(nombre, topologia, self.runtime)
        self.servidor = ServidorLineas(self.ip, self.puerto, self.procesar_trama)

    def _ruta_seq(self):
        return self.runtime / "state" / f"{self.nombre}_seq.txt"

    def _cargar_seq(self):
        try:
            return int(self._ruta_seq().read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return 0

    def _guardar_seq(self):
        self._ruta_seq().write_text(str(self.seq), encoding="utf-8")

    def iniciar(self):
        self.ultimo_hello = {}
        self.servidor.iniciar()
        threading.Thread(target=self._ciclo_hello, daemon=True).start()
        threading.Thread(target=self._vigilar_vecinos, daemon=True).start()
        threading.Thread(target=self._ciclo_lsa, daemon=True).start()
        with self.candado:
            self._emitir_lsa()
        print(f"[{self.nombre}] escuchando en {self.ip}:{self.puerto}")

    def detener(self):
        self.servidor.detener()

    def procesar_trama(self, trama):
        try:
            mensaje, usa_hamming, correcciones = leer_trama(trama)
        except ValueError as error:
            print(f"[{self.nombre}] trama descartada: {error}")
            return
        if correcciones:
            print(f"[{self.nombre}] Hamming corrigió {correcciones} bit(s)")
        tipo = mensaje.get("type")
        if tipo == "HELLO":
            self._procesar_hello(mensaje)
        elif tipo == "LSA":
            self._procesar_lsa(mensaje)
        elif tipo == "message":
            resultado = self.reenviador.procesar(mensaje, usa_hamming)
            print(f"[{self.nombre}] datos: {resultado}")

    def _ciclo_hello(self):
        while True:
            hello = {"proto": "LinkState", "type": "HELLO", "from": self.nombre, "ttl": 1}
            for vecino in self.costos_vecinos:
                ip, puerto = direccion_router(self.topologia, vecino)
                enviar_trama(ip, puerto, crear_trama(hello))
            time.sleep(INTERVALO_HELLO)

    def _procesar_hello(self, mensaje):
        vecino = mensaje.get("from")
        if vecino not in self.costos_vecinos:
            return
        with self.candado:
            self.ultimo_hello[vecino] = time.time()
            if vecino not in self.vecinos_activos:
                self.vecinos_activos.add(vecino)
                self._emitir_lsa()

    def _vigilar_vecinos(self):
        while True:
            time.sleep(1)
            with self.candado:
                ahora = time.time()
                caidos = [v for v in self.vecinos_activos if ahora - self.ultimo_hello.get(v, 0) > TIEMPO_CAIDA]
                if caidos:
                    self.vecinos_activos.difference_update(caidos)
                    self._emitir_lsa()

    def _ciclo_lsa(self):
        """Vuelve a emitir mi LSA cada cierto tiempo, no solo cuando cambian mis vecinos.

        ``_inundar`` manda cada copia por una conexión TCP nueva sin
        reintentos: si una sola falla en tránsito (algo esperable cuando
        muchos routers arrancan y floodean casi al mismo tiempo), esa copia
        se pierde para siempre y algunos nodos quedan con una vista
        incompleta de mis enlaces. Este refresco periódico (igual que el
        de OSPF real) hace que la red se autorepare sin depender de que
        vuelva a cambiar algún vecino.
        """
        while True:
            time.sleep(INTERVALO_LSA)
            with self.candado:
                self._emitir_lsa()

    def _emitir_lsa(self):
        self.seq += 1
        self._guardar_seq()
        enlaces = {v: c for v, c in self.costos_vecinos.items() if v in self.vecinos_activos}
        lsa = {"proto": "LinkState", "type": "LSA", "origin": self.nombre,
               "seq": self.seq, "links": enlaces, "from": self.nombre, "ttl": TTL_LSA}
        self.lsdb[self.nombre] = enlaces
        self.mayor_seq[self.nombre] = self.seq
        self._recalcular()
        self._inundar(lsa, excepto=None)

    def _procesar_lsa(self, mensaje):
        origen, seq, enlaces, emisor = (mensaje.get(k) for k in ("origin", "seq", "links", "from"))
        if not isinstance(origen, str) or not isinstance(seq, int) or not isinstance(enlaces, dict):
            return
        with self.candado:
            if seq <= self.mayor_seq.get(origen, -1):
                return
            self.mayor_seq[origen], self.lsdb[origen] = seq, dict(enlaces)
            self._recalcular()
            ttl = mensaje.get("ttl", TTL_LSA) - 1
            if ttl > 0:
                reenvio = dict(mensaje, ttl=ttl, **{"from": self.nombre})
                self._inundar(reenvio, excepto=emisor)

    def _inundar(self, mensaje, excepto):
        trama = crear_trama(mensaje)
        for vecino in self.vecinos_activos:
            if vecino != excepto:
                enviar_trama(*direccion_router(self.topologia, vecino), trama)

    def _recalcular(self):
        distancias, previos = caminos_mas_cortos(self.lsdb, self.nombre)
        ruta = self.runtime / f"{self.nombre}_tabla_enrutamiento.csv"
        with ruta.open("w", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(["destino", "siguiente_salto", "costo", "ip", "puerto"])
            for destino in sorted(distancias):
                if destino == self.nombre:
                    continue
                salto = siguiente_salto(previos, self.nombre, destino)
                if salto:
                    ip, puerto = direccion_router(self.topologia, salto)
                    escritor.writerow([destino, salto, distancias[destino], ip, puerto])
