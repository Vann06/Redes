"""Lado emisor de los algoritmos, en Python, SOLO para la simulacion.

La aplicacion real codifica en Go. Esto es una segunda implementacion escrita
aparte, y por eso sirve para dos cosas a la vez:

  1. Permite simular sin sockets: se necesitan miles de repeticiones por
     combinacion, y abrir miles de conexiones TCP seria lentisimo y fragil.
  2. Es una verificacion cruzada. Si esta implementacion y la de Go dan el
     mismo CRC para el mismo mensaje, la receta es la correcta en los dos
     lenguajes.
"""

POLINOMIO_REFLEJADO = 0xEDB88320
BITS_CRC = 32


def crc32_encode(bits):
    """Recibe un string de bits y devuelve ese string con 32 bits de CRC.

    Espejo exacto de CRC32Encode del emisor en Go.
    """
    if len(bits) % 8 != 0:
        raise ValueError(f"CRC-32 necesita multiplo de 8 bits, llegaron {len(bits)}")

    octetos = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
    return bits + format(calcular_crc(octetos), "032b")


def calcular_crc(datos):
    """CRC-32 reflejado: init 0xFFFFFFFF, entrada y salida reflejadas, XOR final."""
    crc = 0xFFFFFFFF

    for octeto in datos:
        crc ^= octeto
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ POLINOMIO_REFLEJADO
            else:
                crc >>= 1

    return crc ^ 0xFFFFFFFF


def hamming_encode(bits, tam_bloque):
    """Pendiente. Contrato acordado:

        hamming_encode(bits, tam_bloque) -> string de bits

    Parte el mensaje en bloques de tam_bloque, agrega r bits de paridad a cada
    uno con r el minimo tal que m + r + 1 <= 2**r, y rellena con ceros el
    ultimo bloque si el mensaje no alcanza.
    """
    raise NotImplementedError("Hamming todavia no esta implementado")


def calcular_r(m):
    """Bits de paridad que necesita un bloque de m bits de datos."""
    r = 1
    while (m + r + 1) > 2 ** r:
        r += 1
    return r
