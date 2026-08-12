"""Framing mínimo de control; la extensión Hamming es tarea de Ricardo."""

import json

PREFIJO_JSON = "J|"
PREFIJO_HAMMING = "H|"


def crear_trama(mensaje, con_hamming=False):
    """Serializa control como JSON por línea.

    TODO(Ricardo): cuando ``con_hamming`` sea True, codificar el JSON UTF-8
    con Hamming(7,4) y anteponer ``H|``.
    """
    if con_hamming:
        raise NotImplementedError("Hamming(7,4) pendiente: ver docs/ricardo.md")
    return PREFIJO_JSON + json.dumps(mensaje, ensure_ascii=False, separators=(",", ":"))


def leer_trama(trama):
    """Lee una trama JSON de control.

    TODO(Ricardo): decodificar ``H|`` y devolver ``usa_hamming=True`` junto
    con el número de correcciones realizadas.
    """
    trama = trama.strip()
    if trama.startswith(PREFIJO_HAMMING):
        raise ValueError("Trama H| no implementada todavía")
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
