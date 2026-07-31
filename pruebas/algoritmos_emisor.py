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
    """Agrega 32 bits de CRC-32 a un string de bits."""
    if not isinstance(bits, str):
        raise ValueError(
            "bits debe ser un string"
        )

    if any(bit not in "01" for bit in bits):
        raise ValueError(
            "el mensaje contiene caracteres que no son bits"
        )

    if len(bits) % 8 != 0:
        raise ValueError(
            "CRC-32 necesita múltiplo de 8 bits, "
            f"llegaron {len(bits)}"
        )

    octetos = bytes(
        int(bits[i:i + 8], 2)
        for i in range(0, len(bits), 8)
    )

    return (
        bits
        + format(
            calcular_crc(octetos),
            "032b",
        )
    )

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


def calcular_r(m):
    """Devuelve el mínimo r que cumple m + r + 1 <= 2**r."""
    if (
        not isinstance(m, int)
        or isinstance(m, bool)
        or m <= 0
    ):
        raise ValueError(
            "tam_bloque debe ser un entero positivo"
        )

    r = 1

    while (m + r + 1) > 2 ** r:
        r += 1

    return r

def _es_potencia_de_dos(valor):
    return (
        valor > 0
        and (valor & (valor - 1)) == 0
    )

def hamming_encode(bits, tam_bloque):
    """Codifica un string de bits utilizando código de Hamming.

    Esta función produce la misma trama que HammingEncode
    del emisor implementado en Go.
    """
    # Las validaciones deben ejecutarse antes de cualquier división o módulo.
    if not isinstance(bits, str):
        raise ValueError("bits debe ser un string")

    if (
        not isinstance(tam_bloque, int)
        or isinstance(tam_bloque, bool)
        or tam_bloque <= 0
    ):
        raise ValueError(
            "tam_bloque debe ser un entero positivo"
        )

    if any(bit not in "01" for bit in bits):
        raise ValueError(
            "el mensaje contiene caracteres que no son bits"
        )

    if bits == "":
        return ""

    r = calcular_r(tam_bloque)
    n = tam_bloque + r

    relleno = (
        tam_bloque - len(bits) % tam_bloque
    ) % tam_bloque

    bits_rellenos = bits + ("0" * relleno)
    salida = []

    for inicio in range(
        0,
        len(bits_rellenos),
        tam_bloque,
    ):
        datos = bits_rellenos[
            inicio:inicio + tam_bloque
        ]

        bloque = ["0"] * n
        indice_dato = 0

        # Colocar datos en posiciones que no sean potencias de dos.
        for posicion in range(1, n + 1):
            if _es_potencia_de_dos(posicion):
                continue

            bloque[posicion - 1] = datos[indice_dato]
            indice_dato += 1

        # Calcular paridad par.
        posicion_paridad = 1

        while posicion_paridad <= n:
            paridad = 0

            for posicion in range(1, n + 1):
                if (
                    posicion & posicion_paridad
                    and bloque[posicion - 1] == "1"
                ):
                    paridad ^= 1

            bloque[posicion_paridad - 1] = str(paridad)
            posicion_paridad <<= 1

        salida.extend(bloque)

    return "".join(salida)

def calcular_r(m):
    """Bits de paridad que necesita un bloque de m bits de datos."""
    r = 1
    while (m + r + 1) > 2 ** r:
        r += 1
    return r
