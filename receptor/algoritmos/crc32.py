"""CRC-32 del lado del receptor: solo verificacion.

La codificacion vive en el emisor, en Go. Aqui se recalcula el CRC sobre los
datos recibidos y se compara contra los 32 bits que vienen pegados al final de
la trama.

Se implementa a mano a proposito. La stdlib trae zlib.crc32, pero el punto del
laboratorio es escribir el algoritmo; zlib solo se usa en los tests como oraculo.
"""

# Polinomio IEEE 802.3 (0x04C11DB7) escrito al reves.
#
# La variante reflejada del CRC-32 procesa cada byte empezando por el bit menos
# significativo. Con el polinomio invertido eso se implementa corriendo a la
# derecha en vez de a la izquierda.
#
# Tiene que ser EXACTAMENTE la misma receta que usa el emisor: init 0xFFFFFFFF,
# entrada y salida reflejadas, XOR final. Si una de las dos implementaciones usa
# otra variante, los residuos no coinciden nunca aunque las dos esten "bien".
# Vector de control: "123456789" -> 0xCBF43926.
POLINOMIO_REFLEJADO = 0xEDB88320

# Bits de redundancia que agrega CRC-32. Siempre 32, sin importar el mensaje.
BITS_CRC = 32


def crc32_verify(trama):
    """Verifica la trama y devuelve (bits_de_datos, estado).

    estado es "ok" o "error". CRC-32 solo detecta, nunca corrige, asi que
    nunca devuelve "corregido".

    La trama son los datos con 32 bits de CRC al final. Se recalcula el CRC de
    los datos y se compara contra los 32 bits recibidos.
    """
    if len(trama) <= BITS_CRC:
        return "", "error"

    datos, recibido = trama[:-BITS_CRC], trama[-BITS_CRC:]

    # El emisor manda multiplos de 8 bits (8 por caracter). Si no lo es, el
    # ruido o el framing rompieron la trama.
    if len(datos) % 8 != 0:
        return "", "error"

    try:
        octetos = _bits_a_bytes(datos)
        int(recibido, 2)
    except ValueError:
        return "", "error"

    calculado = format(_calcular_crc(octetos), "032b")
    if calculado != recibido:
        return "", "error"

    return datos, "ok"


def _calcular_crc(datos):
    """CRC-32 reflejado sobre una secuencia de bytes."""
    crc = 0xFFFFFFFF

    for octeto in datos:
        crc ^= octeto
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ POLINOMIO_REFLEJADO
            else:
                crc >>= 1

    return crc ^ 0xFFFFFFFF  # XOR final


def _bits_a_bytes(bits):
    """Agrupa el string de bits de 8 en 8, con el mas significativo primero.

    Es el inverso exacto de lo que hace la capa de presentacion del emisor.
    Levanta ValueError si hay algo que no sea '0' o '1'.
    """
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
