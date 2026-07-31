"""Capa de aplicacion del receptor: el servidor bancario."""

import json

# Base de datos de mentira, la misma del laboratorio anterior.
CUENTAS = {
    "4111111111111111": {"pin": "1234", "balance": 500.00},
    "5500005555555559": {"pin": "0000", "balance": 1200.50},
    "23201": {"pin": "6767", "balance": 1600.00},
}


def mostrar_mensaje(texto, estado):
    """Muestra el mensaje recibido, o el error si no se pudo recuperar."""
    if estado == "error":
        detalle = f": {texto}" if texto else ""
        print(f"[BANCO] ERROR, no se pudo recuperar el mensaje{detalle}")
        return

    if estado == "corregido":
        print("[BANCO] la trama llego con errores y el algoritmo los corrigio")

    print(f"[BANCO] mensaje recibido: {texto}")


def procesar(texto, sesion):
    """Atiende la operacion que mando el cajero.

    Devuelve el JSON de respuesta, o None cuando no hay nada que contestar: el
    mensaje libre solo se muestra, y de vuelta viaja un ACK pelado.

    sesion es el estado de esta conexion; ahi se recuerda quien inicio sesion.
    Levanta ValueError si el texto no es una operacion valida.
    """
    mensaje = json.loads(texto)  # JSONDecodeError hereda de ValueError
    accion = mensaje.get("action")
    data = mensaje.get("data", {})

    if accion == "message":
        print(f"[BANCO] >>> MENSAJE DEL CAJERO: {data.get('text', '')}")
        return None

    if accion == "login":
        return _login(data, sesion)

    if accion == "withdraw":
        return _retirar(data, sesion)

    if accion == "logout":
        sesion["tarjeta"] = None
        return _respuesta("logout_ok", {"message": "Hasta luego"})

    return _respuesta("error", {"message": "Accion desconocida"})


def _login(data, sesion):
    tarjeta = data.get("card")
    cuenta = CUENTAS.get(tarjeta)

    if cuenta and cuenta["pin"] == data.get("pin"):
        sesion["tarjeta"] = tarjeta
        return _respuesta("login_ok", {"message": "Autenticacion exitosa"})

    return _respuesta("login_denied", {"message": "Tarjeta o PIN invalidos"})


def _retirar(data, sesion):
    if sesion["tarjeta"] is None:
        return _respuesta("error", {"message": "No autenticado"})

    monto = data.get("amount", 0)
    cuenta = CUENTAS[sesion["tarjeta"]]

    if not isinstance(monto, (int, float)) or monto <= 0:
        return _respuesta("error", {"message": "Monto invalido"})

    if monto > cuenta["balance"]:
        return _respuesta("error", {"message": "Fondos insuficientes"})

    cuenta["balance"] -= monto
    return _respuesta("withdraw_ok", {"amount": monto, "balance": cuenta["balance"]})


def _respuesta(accion, data):
    return json.dumps({"action": accion, "data": data})
