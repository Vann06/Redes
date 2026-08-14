"""Framing interoperable acordado entre las tres parejas.

Plano de control:
    HELLO y LSA viajan como JSON UTF-8 plano, sin prefijos.

Plano de datos:
    Los mensajes ATM/BANK viajan codificados con Hamming(7,4),
    también sin prefijos adicionales.
"""

import json

from comun import hamming


def crear_trama(mensaje, con_hamming=False):
    """
    Serializa un mensaje según el protocolo conjunto.

    - HELLO / LSA: JSON plano.
    - Datos: Hamming(7,4).
    """
    payload = json.dumps(
        mensaje,
        ensure_ascii=False,
        separators=(",", ":")
    )

    if con_hamming:
        return hamming.codificar_bytes(payload.encode("utf-8"))

    return payload


def leer_trama(trama):
    """
    Recibe una trama.

    Si comienza con '{', se interpreta como JSON plano
    del plano de control.

    De lo contrario, se intenta decodificar como Hamming(7,4)
    para el plano de datos.

    Devuelve:
        (mensaje, usa_hamming, correcciones)
    """

    trama = trama.strip()

    if not trama:
        raise ValueError("Trama vacía")

    # ==========================================
    # PLANO DE CONTROL: JSON PLANO
    # ==========================================
    if trama.startswith("{"):
        try:
            mensaje = json.loads(trama)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"JSON de control inválido: {trama[:100]!r}"
            ) from error

        if not isinstance(mensaje, dict):
            raise ValueError(
                "Cada trama debe contener un objeto JSON"
            )

        return mensaje, False, 0

    # ==========================================
    # PLANO DE DATOS: HAMMING(7,4)
    # ==========================================
    try:
        datos, correcciones = hamming.decodificar_bits(trama)

        mensaje = json.loads(
            datos.decode("utf-8")
        )

    except (
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError
    ) as error:

        # Esto nos permite ver qué están mandando
        # los otros nodos si usan otro formato.
        raise ValueError(
            f"Trama inválida: {trama[:100]!r}"
        ) from error

    if not isinstance(mensaje, dict):
        raise ValueError(
            "Cada trama debe contener un objeto JSON"
        )

    return mensaje, True, correcciones


def es_control(mensaje):
    """
    Indica si el mensaje pertenece al plano de control.
    """
    return mensaje.get("type") in {
        "HELLO",
        "LSA"
    }