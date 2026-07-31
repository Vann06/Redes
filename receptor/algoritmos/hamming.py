"""Código de Hamming del lado receptor.

Este módulo recibe una trama dividida en bloques Hamming, calcula el síndrome,
corrige un error de un bit por bloque y recupera los bits de datos.

El algoritmo implementado es Hamming clásico con paridad par. No incluye un bit
de paridad global adicional, por lo que no puede detectar de forma confiable
todos los errores dobles.
"""


def calcular_r(m):
    """Devuelve el menor r que cumple m + r + 1 <= 2**r."""
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
    """Indica si una posición corresponde a un bit de paridad."""
    return (
        valor > 0
        and (valor & (valor - 1)) == 0
    )


def _calcular_sindrome(bloque):
    """Calcula el síndrome de un bloque Hamming.

    El resultado cero significa que no se encontró un error.

    Un resultado distinto de cero indica la posición, comenzando en 1,
    del bit que debe voltearse.
    """
    sindrome = 0
    posicion_paridad = 1

    while posicion_paridad <= len(bloque):
        paridad = 0

        for posicion, bit in enumerate(
            bloque,
            start=1,
        ):
            if (
                posicion & posicion_paridad
                and bit == "1"
            ):
                paridad ^= 1

        if paridad:
            sindrome += posicion_paridad

        posicion_paridad <<= 1

    return sindrome


def hamming_decode(
    trama,
    tam_bloque=4,
    longitud=None,
):
    """Verifica, corrige y decodifica una trama Hamming.

    Args:
        trama:
            String compuesto únicamente por caracteres "0" y "1".

        tam_bloque:
            Cantidad de bits de datos por bloque.

        longitud:
            Cantidad real de bits del mensaje antes de agregar relleno.

    Returns:
        Una tupla:

            (bits_recuperados, estado)

        estado puede ser:

            "ok"
            "corregido"
            "error"

    Hamming clásico corrige un error de un bit por bloque. Cuando existen
    varios errores en un mismo bloque puede ocurrir una corrección incorrecta.
    Esa situación debe medirse como falso negativo durante las simulaciones.
    """
    r = calcular_r(tam_bloque)
    n = tam_bloque + r

    if longitud is not None:
        if (
            not isinstance(longitud, int)
            or isinstance(longitud, bool)
            or longitud < 0
        ):
            raise ValueError(
                "longitud debe ser un entero no negativo"
            )

    if not isinstance(trama, str):
        raise ValueError(
            "la trama debe ser un string de bits"
        )

    if any(bit not in "01" for bit in trama):
        return "", "error"

    if trama == "":
        if longitud in (None, 0):
            return "", "ok"

        return "", "error"

    if len(trama) % n != 0:
        return "", "error"

    datos_recuperados = []
    hubo_correccion = False

    for inicio in range(0, len(trama), n):
        bloque = list(
            trama[inicio:inicio + n]
        )

        sindrome = _calcular_sindrome(bloque)

        if sindrome:
            # En un error simple, el síndrome siempre corresponde a una
            # posición válida. Un síndrome mayor al bloque indica que la
            # trama no puede corregirse de forma segura.
            if sindrome > n:
                return "", "error"

            indice = sindrome - 1

            bloque[indice] = (
                "1"
                if bloque[indice] == "0"
                else "0"
            )

            hubo_correccion = True

        # Se retiran los bits colocados en posiciones 1, 2, 4, 8, etc.
        for posicion, bit in enumerate(
            bloque,
            start=1,
        ):
            if not _es_potencia_de_dos(posicion):
                datos_recuperados.append(bit)

    recuperados = "".join(datos_recuperados)

    if longitud is not None:
        if longitud > len(recuperados):
            return "", "error"

        recuperados = recuperados[:longitud]

    estado = (
        "corregido"
        if hubo_correccion
        else "ok"
    )

    return recuperados, estado