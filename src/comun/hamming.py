"""Hamming(7,4) de paridad par para el plano de datos.

Cada byte UTF-8 se separa en dos nibbles de 4 bits (el más significativo
primero) y cada nibble se codifica como un bloque de 7 bits con el layout
``p1 p2 d1 p3 d2 d3 d4``. Es la misma receta que ya se probó en el
laboratorio anterior (``receptor/algoritmos/hamming.py`` con
``tam_bloque=4``), fijada aquí a 7,4 porque es el único tamaño que usa este
protocolo.
"""

TAM_BLOQUE = 4
R = 3
N = TAM_BLOQUE + R


def _es_potencia_de_dos(valor):
    return valor > 0 and (valor & (valor - 1)) == 0


def _calcular_sindrome(bloque):
    sindrome = 0
    posicion_paridad = 1
    while posicion_paridad <= len(bloque):
        paridad = 0
        for posicion, bit in enumerate(bloque, start=1):
            if posicion & posicion_paridad and bit == "1":
                paridad ^= 1
        if paridad:
            sindrome += posicion_paridad
        posicion_paridad <<= 1
    return sindrome


def codificar_nibble(nibble):
    """Codifica 4 bits de datos (``"d1d2d3d4"``) en un bloque de 7 bits."""
    if not isinstance(nibble, str) or len(nibble) != TAM_BLOQUE or any(bit not in "01" for bit in nibble):
        raise ValueError(f"se esperaban {TAM_BLOQUE} bits ('0'/'1'), llegó {nibble!r}")

    bloque = ["0"] * N
    indice_dato = 0
    for posicion in range(1, N + 1):
        if _es_potencia_de_dos(posicion):
            continue
        bloque[posicion - 1] = nibble[indice_dato]
        indice_dato += 1

    posicion_paridad = 1
    while posicion_paridad <= N:
        paridad = 0
        for posicion in range(1, N + 1):
            if posicion & posicion_paridad and bloque[posicion - 1] == "1":
                paridad ^= 1
        bloque[posicion_paridad - 1] = str(paridad)
        posicion_paridad <<= 1

    return "".join(bloque)


def decodificar_bloque(bloque):
    """Corrige y decodifica un bloque de 7 bits.

    Devuelve ``(nibble_datos, hubo_correccion)``. Lanza ``ValueError`` si el
    bloque no mide 7 bits, trae caracteres que no son ``0``/``1``, o el
    síndrome calculado no corresponde a ninguna posición del bloque.
    """
    if not isinstance(bloque, str) or len(bloque) != N or any(bit not in "01" for bit in bloque):
        raise ValueError(f"se esperaba un bloque de {N} bits ('0'/'1'), llegó {bloque!r}")

    bits = list(bloque)
    sindrome = _calcular_sindrome(bits)
    hubo_correccion = False
    if sindrome:
        if sindrome > N:
            raise ValueError("síndrome fuera de rango: el bloque no puede corregirse de forma segura")
        indice = sindrome - 1
        bits[indice] = "1" if bits[indice] == "0" else "0"
        hubo_correccion = True

    datos = [bit for posicion, bit in enumerate(bits, start=1) if not _es_potencia_de_dos(posicion)]
    return "".join(datos), hubo_correccion


def codificar_bytes(datos):
    """Codifica una secuencia de bytes en un string de bits Hamming(7,4)."""
    if not isinstance(datos, (bytes, bytearray)):
        raise ValueError("datos debe ser bytes")

    bloques = []
    for byte in datos:
        binario = format(byte, "08b")
        bloques.append(codificar_nibble(binario[:4]))
        bloques.append(codificar_nibble(binario[4:]))
    return "".join(bloques)


def decodificar_bits(bits):
    """Corrige y decodifica un string de bits Hamming(7,4) a bytes.

    Devuelve ``(datos, correcciones)``, donde ``correcciones`` es la
    cantidad de bloques que necesitaron corregir un bit (Hamming(7,4)
    corrige como máximo un bit por bloque, así que equivale a la cantidad
    de bits corregidos). Lanza ``ValueError`` ante una trama corrupta o mal
    formada.
    """
    if not isinstance(bits, str) or any(bit not in "01" for bit in bits):
        raise ValueError("bits debe ser un string compuesto únicamente de '0'/'1'")
    if len(bits) % N != 0:
        raise ValueError(f"la cantidad de bits debe ser múltiplo de {N}, llegaron {len(bits)}")

    num_bloques = len(bits) // N
    if num_bloques % 2 != 0:
        raise ValueError("cantidad impar de nibbles: no se pueden reconstruir bytes completos")

    nibbles = []
    correcciones = 0
    for inicio in range(0, len(bits), N):
        nibble, hubo_correccion = decodificar_bloque(bits[inicio : inicio + N])
        nibbles.append(nibble)
        if hubo_correccion:
            correcciones += 1

    salida = bytearray()
    for indice in range(0, len(nibbles), 2):
        salida.append(int(nibbles[indice] + nibbles[indice + 1], 2))
    return bytes(salida), correcciones
