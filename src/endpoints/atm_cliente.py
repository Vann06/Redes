"""Cliente ATM (cajero automático): no es un router, habla con la red a
través de su gateway. Portado del menú interactivo del emisor del Lab2
(login con reintento + retirar/enviar mensaje/salir), sin las partes que ya
no aplican aquí (elegir algoritmo o simular ruido): el framing (J|/H|) se
fija una vez por sesión con --hamming.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import queue

from comun.configuracion import cargar_topologia, config_endpoint, direccion_router
from comun.protocolo import crear_trama, leer_trama
from comun.transporte import ServidorLineas, enviar_trama

NOMBRE = "ATM"
DESTINO = "BANK"
TTL_INICIAL = 16
TIMEOUT_RESPUESTA = 5


class Cajero:
    """Envía operaciones al banco y espera su respuesta.

    A diferencia del Lab2 (donde la respuesta llegaba en la misma conexión
    TCP), aquí cada envío es una conexión de una sola línea y la respuesta
    vuelve como un mensaje independiente reenviado por la red. Por eso el
    cajero también escucha en su propio socket y usa una cola para casar
    cada respuesta con quien la está esperando.
    """

    def __init__(self, topologia, con_hamming):
        self.topologia = topologia
        self.con_hamming = con_hamming
        config = config_endpoint(topologia, NOMBRE)
        self.ip, self.puerto = config["ip"], config["puerto"]
        self.gateway = config["gateway"]
        self.respuestas = queue.Queue()
        self.servidor = ServidorLineas(self.ip, self.puerto, self._al_recibir)

    def iniciar(self):
        self.servidor.iniciar()
        print(f"[CAJERO] escuchando respuestas en {self.ip}:{self.puerto} (gateway {self.gateway})")

    def _al_recibir(self, trama):
        try:
            mensaje, usa_hamming, correcciones = leer_trama(trama)
        except ValueError as error:
            print(f"[CAJERO] trama descartada: {error}")
            return
        if correcciones:
            print(f"[CAJERO] Hamming corrigió {correcciones} bit(s)")
        if mensaje.get("type") == "message":
            self.respuestas.put(mensaje.get("payload", {}))

    def enviar(self, payload):
        mensaje = {
            "type": "message",
            "from": NOMBRE,
            "to": DESTINO,
            "ttl": TTL_INICIAL,
            "hops": [NOMBRE],
            "payload": payload,
        }
        ip, puerto = direccion_router(self.topologia, self.gateway)
        trama = crear_trama(mensaje, con_hamming=self.con_hamming)
        return enviar_trama(ip, puerto, trama)

    def consultar(self, accion, data):
        """Manda una operación al banco y espera la respuesta. Devuelve ``(respuesta, ok)``."""
        if not self.enviar({"action": accion, "data": data}):
            print("[CAJERO] no se pudo contactar al router gateway")
            return None, False
        try:
            respuesta = self.respuestas.get(timeout=TIMEOUT_RESPUESTA)
        except queue.Empty:
            print("[CAJERO] no llegó respuesta del banco (¿la red ya convergió?)")
            return None, False
        return respuesta, True


def login(cajero):
    while True:
        tarjeta = input("\nNúmero de tarjeta: ").strip()
        pin = input("PIN: ").strip()
        respuesta, ok = cajero.consultar("login", {"card": tarjeta, "pin": pin})
        if not ok:
            continue
        print(">> " + respuesta.get("data", {}).get("message", ""))
        if respuesta.get("action") == "login_ok":
            return True
        print("   Intenta de nuevo.")


def menu(cajero):
    while True:
        print("\n--- CAJERO ---")
        print("1) Retirar dinero")
        print("2) Enviar mensaje")
        print("3) Salir")
        opcion = input("Elige una opción: ").strip()

        if opcion == "1":
            retirar(cajero)
        elif opcion == "2":
            enviar_mensaje_libre(cajero)
        elif opcion == "3":
            respuesta, ok = cajero.consultar("logout", {})
            if ok:
                print(">> " + respuesta.get("data", {}).get("message", ""))
            return
        else:
            print(">> Opción inválida.")


def retirar(cajero):
    linea = input("Monto a retirar: ").strip()
    try:
        monto = float(linea)
    except ValueError:
        print(">> El monto tiene que ser un número.")
        return

    respuesta, ok = cajero.consultar("withdraw", {"amount": monto})
    if not ok:
        return

    data = respuesta.get("data", {})
    if respuesta.get("action") == "withdraw_ok":
        print(f">> Toma tus ${data.get('amount', 0):.2f}")
        print(f">> Saldo restante: ${data.get('balance', 0):.2f}")
    else:
        print(">> " + data.get("message", ""))


def enviar_mensaje_libre(cajero):
    """Manda un texto libre; el banco solo lo muestra, no hay respuesta que esperar."""
    texto = input("Mensaje a enviar: ").strip()
    if not texto:
        print(">> El mensaje no puede estar vacío.")
        return
    if not cajero.enviar({"action": "message", "data": {"text": texto}}):
        print(">> No se pudo enviar el mensaje.")
        return
    print(">> Mensaje enviado.")


def main():
    parser = argparse.ArgumentParser(description="Cliente ATM (cajero automático)")
    parser.add_argument("--topologia", default="config/topologia.json")
    parser.add_argument("--hamming", action="store_true", help="Usar framing H| (Hamming 7,4) en el plano de datos")
    args = parser.parse_args()

    topologia = cargar_topologia(args.topologia)
    cajero = Cajero(topologia, args.hamming)
    cajero.iniciar()

    try:
        if login(cajero):
            menu(cajero)
    except (KeyboardInterrupt, EOFError):
        print("\n[CAJERO] hasta luego")


if __name__ == "__main__":
    main()
