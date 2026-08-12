import csv
import socket
import tempfile
import threading
import unittest
from pathlib import Path

from comun.protocolo import leer_trama
from comun.transporte import ServidorLineas
from datos.forwarding import Reenviador


def _puerto_libre():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    puerto = s.getsockname()[1]
    s.close()
    return puerto


class _ListenerDePrueba:
    """Simula el siguiente salto: captura la primera trama que recibe."""

    def __init__(self):
        self.puerto = _puerto_libre()
        self.recibido = threading.Event()
        self.mensaje = None
        self.servidor = ServidorLineas("127.0.0.1", self.puerto, self._callback)
        self.servidor.iniciar()

    def _callback(self, trama):
        self.mensaje, _, _ = leer_trama(trama)
        self.recibido.set()

    def esperar(self, timeout=2):
        if not self.recibido.wait(timeout):
            raise AssertionError("no llegó ninguna trama al siguiente salto")
        return self.mensaje

    def detener(self):
        self.servidor.detener()


def _escribir_csv(directorio, nombre, filas):
    ruta = Path(directorio) / f"{nombre}_tabla_enrutamiento.csv"
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["destino", "siguiente_salto", "costo", "ip", "puerto"])
        for fila in filas:
            escritor.writerow(fila)
    return ruta


class ReenviadorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.directorio = self._tmp.name
        self._listeners = []

    def tearDown(self):
        for listener in self._listeners:
            listener.detener()
        self._tmp.cleanup()

    def _nuevo_listener(self):
        listener = _ListenerDePrueba()
        self._listeners.append(listener)
        return listener

    def test_reenvia_entre_routers_decrementando_ttl_y_agregando_hop(self):
        listener = self._nuevo_listener()
        topologia = {"routers": {"A": {}, "B": {}}, "endpoints": {}}
        _escribir_csv(self.directorio, "A", [["C", "B", 5, "127.0.0.1", listener.puerto]])
        reenviador = Reenviador("A", topologia, self.directorio)

        mensaje = {"type": "message", "to": "C", "ttl": 5, "hops": ["X"]}
        resultado = reenviador.procesar(mensaje, usa_hamming=False)

        recibido = listener.esperar()
        self.assertEqual(recibido["ttl"], 4)
        self.assertEqual(recibido["hops"], ["X", "A"])
        self.assertEqual(recibido["to"], "C")
        self.assertIn("reenviado", resultado)

    def test_entrega_directa_a_endpoint_cuando_es_el_gateway(self):
        listener = self._nuevo_listener()
        topologia = {
            "routers": {"B": {}},
            "endpoints": {"BANK": {"gateway": "B", "ip": "127.0.0.1", "puerto": listener.puerto}},
        }
        reenviador = Reenviador("B", topologia, self.directorio)

        mensaje = {"type": "message", "to": "BANK", "ttl": 3, "hops": ["A"]}
        reenviador.procesar(mensaje, usa_hamming=False)

        recibido = listener.esperar()
        self.assertEqual(recibido["to"], "BANK")
        self.assertEqual(recibido["hops"], ["A", "B"])
        self.assertEqual(recibido["ttl"], 2)

    def test_reenvia_hacia_el_gateway_de_un_endpoint_cuando_no_es_el_gateway(self):
        listener = self._nuevo_listener()
        topologia = {
            "routers": {"A": {}, "B": {}},
            "endpoints": {"BANK": {"gateway": "B", "ip": "127.0.0.1", "puerto": 9999}},
        }
        _escribir_csv(self.directorio, "A", [["B", "B", 1, "127.0.0.1", listener.puerto]])
        reenviador = Reenviador("A", topologia, self.directorio)

        mensaje = {"type": "message", "to": "BANK", "ttl": 5, "hops": []}
        reenviador.procesar(mensaje, usa_hamming=False)

        recibido = listener.esperar()
        self.assertEqual(recibido["to"], "BANK")
        self.assertEqual(recibido["hops"], ["A"])

    def test_descarta_ciclo_sin_lanzar_excepcion(self):
        reenviador = Reenviador("A", {"routers": {"A": {}}, "endpoints": {}}, self.directorio)
        mensaje = {"type": "message", "to": "C", "ttl": 5, "hops": ["X", "A"]}
        resultado = reenviador.procesar(mensaje, usa_hamming=False)
        self.assertIn("ciclo", resultado)

    def test_descarta_ttl_agotado(self):
        reenviador = Reenviador("A", {"routers": {"A": {}}, "endpoints": {}}, self.directorio)
        mensaje = {"type": "message", "to": "C", "ttl": 0, "hops": []}
        resultado = reenviador.procesar(mensaje, usa_hamming=False)
        self.assertIn("ttl", resultado)

    def test_descarta_sobre_mal_formado(self):
        reenviador = Reenviador("A", {"routers": {"A": {}}, "endpoints": {}}, self.directorio)
        casos = ({"ttl": 5, "hops": []}, {"to": "C", "hops": []}, {"to": "C", "ttl": 5})
        for mensaje in casos:
            with self.subTest(mensaje=mensaje):
                resultado = reenviador.procesar(mensaje, usa_hamming=False)
                self.assertIn("mal formado", resultado)

    def test_descarta_sin_ruta(self):
        reenviador = Reenviador("A", {"routers": {"A": {}}, "endpoints": {}}, self.directorio)
        mensaje = {"type": "message", "to": "Z", "ttl": 5, "hops": []}
        resultado = reenviador.procesar(mensaje, usa_hamming=False)
        self.assertIn("sin ruta", resultado)


if __name__ == "__main__":
    unittest.main()
