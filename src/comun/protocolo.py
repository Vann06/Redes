"""Framing de tramas: JSON plano (control) y Hamming(7,4) (datos)."""

import json

from comun import hamming

PREFIJO_JSON = "J|"
PREFIJO_HAMMING = "H|"


def crear_trama(mensaje, con_hamming=False):
    """Serializa un mensaje como trama de una línea.

    Con ``con_hamming=False`` (HELLO/LSA del plano de control) antepone
    ``J|`` al JSON. Con ``con_hamming=True`` (datos, una vez la red
    convergió) codifica el JSON UTF-8 con Hamming(7,4) y antepone ``H|``.
    """
    payload = json.dumps(mensaje, ensure_ascii=False, separators=(",", ":"))
    if con_hamming:
        return PREFIJO_HAMMING + hamming.codificar_bytes(payload.encode("utf-8"))
    return PREFIJO_JSON + payload


def leer_trama(trama):
    """Lee una trama de control (``J|``) o de datos (``H|``).

    Devuelve ``(mensaje, usa_hamming, correcciones)``. Cualquier trama
    corrupta o mal formada levanta ``ValueError`` para que quien la reciba
    pueda descartarla sin detener el proceso.
    """
    trama = trama.strip()
    if trama.startswith(PREFIJO_HAMMING):
        bits = trama[len(PREFIJO_HAMMING) :]
        try:
            datos, correcciones = hamming.decodificar_bits(bits)
            mensaje = json.loads(datos.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as error:
            raise ValueError("Trama H| corrupta o mal formada") from error
        if not isinstance(mensaje, dict):
            raise ValueError("Cada trama debe contener un objeto JSON")
        return mensaje, True, correcciones
    if not trama.startswith(PREFIJO_JSON):
        raise ValueError("Prefijo inválido: se esperaba J| o H|")
    try:
        mensaje = json.loads(trama[len(PREFIJO_JSON) :])
    except json.JSONDecodeError as error:
        raise ValueError("El contenido de la trama no es JSON válido") from error
    if not isinstance(mensaje, dict):
        raise ValueError("Cada trama debe contener un objeto JSON")
    return mensaje, False, 0


def es_control(mensaje):
    return mensaje.get("type") in {"HELLO", "LSA"}
