"""Servidor BANK: no es un router, recibe operaciones del ATM a través de su
gateway y responde por el mismo camino. La lógica de negocio (cuentas,
login, retiro) está portada de ``receptor/aplicacion.py`` del Lab2.

A diferencia del Lab2, aquí no hay una conexión TCP persistente por cliente
(cada mensaje es su propia conexión de una línea), así que la sesión se
guarda en memoria por remitente (``from``) en vez de por conexión.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse

from comun.configuracion import cargar_topologia, config_endpoint, direccion_router
from comun.protocolo import crear_trama, leer_trama
from comun.transporte import ServidorLineas, enviar_trama

NOMBRE = "BANK"
TTL_INICIAL = 16

# Base de datos de mentira, la misma del laboratorio anterior.
CUENTAS = {
    "4111111111111111": {"pin": "1234", "balance": 500.00},
    "5500005555555559": {"pin": "0000", "balance": 1200.50},
    "23201": {"pin": "6767", "balance": 1600.00},
}


class Banco:
    def __init__(self, topologia):
        self.topologia = topologia
        config = config_endpoint(topologia, NOMBRE)
        self.ip, self.puerto = config["ip"], config["puerto"]
        self.gateway = config["gateway"]
        self.sesiones = {}
        self.servidor = ServidorLineas(self.ip, self.puerto, self._al_recibir)

    def iniciar(self):
        self.servidor.iniciar()
        print(f"[BANCO] escuchando en {self.ip}:{self.puerto} (gateway {self.gateway})")

    def _al_recibir(self, trama):
        try:
            mensaje, usa_hamming, correcciones = leer_trama(trama)
        except ValueError as error:
            print(f"[BANCO] trama descartada: {error}")
            return
        if correcciones:
            print(f"[BANCO] Hamming corrigió {correcciones} bit(s)")
        if mensaje.get("type") != "message":
            return

        remitente, payload = mensaje.get("from"), mensaje.get("payload")
        if not isinstance(remitente, str) or not isinstance(payload, dict):
            return

        respuesta = self._procesar(payload, remitente)
        if respuesta is not None:
            self._responder(remitente, respuesta, usa_hamming)

    def _procesar(self, payload, remitente):
        accion, data = payload.get("action"), payload.get("data", {})
        sesion = self.sesiones.setdefault(remitente, {"tarjeta": None})

        if accion == "message":
            print(f"[BANCO] >>> MENSAJE DE {remitente}: {data.get('text', '')}")
            return None
        if accion == "login":
            return self._login(data, sesion)
        if accion == "withdraw":
            return self._retirar(data, sesion)
        if accion == "logout":
            sesion["tarjeta"] = None
            return _respuesta("logout_ok", {"message": "Hasta luego"})
        return _respuesta("error", {"message": "Acción desconocida"})

    def _login(self, data, sesion):
        tarjeta = data.get("card")
        cuenta = CUENTAS.get(tarjeta)
        if cuenta and cuenta["pin"] == data.get("pin"):
            sesion["tarjeta"] = tarjeta
            return _respuesta("login_ok", {"message": "Autenticación exitosa"})
        return _respuesta("login_denied", {"message": "Tarjeta o PIN inválidos"})

    def _retirar(self, data, sesion):
        if sesion["tarjeta"] is None:
            return _respuesta("error", {"message": "No autenticado"})

        cuenta = CUENTAS[sesion["tarjeta"]]
        monto = data.get("amount", 0)
        if not isinstance(monto, (int, float)) or monto <= 0:
            return _respuesta("error", {"message": "Monto inválido"})
        if monto > cuenta["balance"]:
            return _respuesta("error", {"message": "Fondos insuficientes"})

        cuenta["balance"] -= monto
        return _respuesta("withdraw_ok", {"amount": monto, "balance": cuenta["balance"]})

    def _responder(self, destino, payload, usa_hamming):
        mensaje = {
            "type": "message",
            "from": NOMBRE,
            "to": destino,
            "ttl": TTL_INICIAL,
            "hops": [NOMBRE],
            "payload": payload,
        }
        ip, puerto = direccion_router(self.topologia, self.gateway)
        trama = crear_trama(mensaje, con_hamming=usa_hamming)
        if not enviar_trama(ip, puerto, trama):
            print(f"[BANCO] no se pudo responder a {destino}")


def _respuesta(accion, data):
    return {"action": accion, "data": data}


def main():
    parser = argparse.ArgumentParser(description="Servidor BANK")
    parser.add_argument("--topologia", default="config/topologia.json")
    args = parser.parse_args()

    banco = Banco(cargar_topologia(args.topologia))
    banco.iniciar()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
