"""Capa de presentacion del receptor: de bits a texto."""


def decodificar_mensaje(bits):
    """Convierte el string de bits a texto, 8 bits por caracter.

    Es el inverso de codificarMensaje del emisor: se agrupa de 8 en 8 con el
    bit mas significativo primero y se interpreta como UTF-8.

    Levanta ValueError si los bits no se pueden convertir a texto. Eso es la
    forma de "indicar el error a la capa de aplicacion" que pide el enunciado:
    con CRC no deberia pasar nunca, porque una trama corrupta se rechaza antes
    de llegar aqui; con Hamming si puede pasar, cuando el algoritmo "corrige"
    mal una trama con dos errores y entrega basura creyendo que esta bien.
    """
    if len(bits) % 8 != 0:
        raise ValueError(f"se esperaban bits en grupos de 8, llegaron {len(bits)}")

    # int(..., 2) levanta ValueError si hay algo que no sea '0' o '1', y
    # UnicodeDecodeError (que hereda de ValueError) si los bytes no son UTF-8.
    octetos = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
    return octetos.decode("utf-8")
