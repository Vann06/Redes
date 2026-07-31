"""Capa de enlace del receptor: verificar la integridad de la trama."""

from algoritmos.crc32 import crc32_verify


def verificar_integridad(trama, algoritmo, tam_bloque, longitud):
    """Devuelve (bits, estado), con estado en {"ok", "corregido", "error"}.

    Es solo un despachador: no sabe como funciona ninguno de los dos
    algoritmos, solo cual toca. El algoritmo es un parametro de tiempo de
    ejecucion, no dos flujos separados.

    Levanta ValueError si el algoritmo no se reconoce.
    """
    if algoritmo == "CRC":
        # CRC-32 no usa tam_bloque (su overhead es fijo) ni longitud (el
        # emisor no rellena nada, los datos son multiplo de 8).
        return crc32_verify(trama)

    if algoritmo == "HAM":
        # Pendiente. Contrato acordado con el emisor:
        #   hamming_decode(trama, tam_bloque, longitud) -> (bits, estado)
        # longitud recorta el relleno que hammingEncode agrego al ultimo bloque.
        raise ValueError("Hamming todavia no esta implementado")

    raise ValueError(f"algoritmo desconocido: {algoritmo!r} (se espera CRC o HAM)")
