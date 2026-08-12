"""Transporte TCP de tramas de una línea, independiente del protocolo."""

import socket
import threading

FIN_DE_LINEA = b"\n"


class ServidorLineas:
    def __init__(self, ip, puerto, callback):
        self.ip, self.puerto, self.callback = ip, puerto, callback
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._activo = False

    def iniciar(self):
        self._socket.bind((self.ip, self.puerto))
        self._socket.listen()
        self._activo = True
        threading.Thread(target=self._aceptar, daemon=True).start()

    def detener(self):
        self._activo = False
        self._socket.close()

    def _aceptar(self):
        while self._activo:
            try:
                conexion, _ = self._socket.accept()
            except OSError:
                return
            threading.Thread(target=self._atender, args=(conexion,), daemon=True).start()

    def _atender(self, conexion):
        buffer = b""
        with conexion:
            while True:
                try:
                    datos = conexion.recv(4096)
                except OSError:
                    return
                if not datos:
                    return
                buffer += datos
                while FIN_DE_LINEA in buffer:
                    linea, buffer = buffer.split(FIN_DE_LINEA, 1)
                    if linea.strip():
                        try:
                            self.callback(linea.decode("utf-8"))
                        except UnicodeDecodeError:
                            pass


def enviar_trama(ip, puerto, trama, timeout=3):
    """Envía una trama completa por TCP y devuelve si la conexión tuvo éxito."""
    try:
        with socket.create_connection((ip, puerto), timeout=timeout) as conexion:
            conexion.sendall(trama.encode("utf-8") + FIN_DE_LINEA)
        return True
    except OSError:
        return False
