"""Receptor del laboratorio: el servidor bancario.

El flujo sube por las capas, al reves que en el emisor:

    transmision -> enlace -> presentacion -> aplicacion

Cada capa es una funcion independiente que no sabe nada de las demas. Aqui no
hay capa de ruido: el ruido ya se aplico en el emisor, en el canal.
"""

from aplicacion import mostrar_mensaje, procesar
from enlace import verificar_integridad
from presentacion import decodificar_mensaje
from transmision import escuchar

PUERTO = 5000


def crear_manejador():
    """Arma el manejador de una conexion nueva, con su propia sesion.

    El banco necesita recordar quien inicio sesion, y el emisor manda varias
    tramas por la misma conexion.
    """
    sesion = {"tarjeta": None}

    def al_recibir(linea):
        return subir_por_las_capas(linea, sesion)

    return al_recibir


def subir_por_las_capas(linea, sesion):
    """El flujo del receptor, una capa por bloque.

    Devuelve la linea de respuesta:
        ACK|<json>              la trama llego bien
        ACK|CORREGIDO|<json>    llego con error y se corrigio
        ACK / ACK|CORREGIDO     igual, pero sin respuesta del banco
        NAK                     no se pudo recuperar el mensaje
    """
    # La cabecera es metadata: queda fuera del calculo de integridad y del ruido.
    try:
        algoritmo, tam_bloque, longitud, trama = linea.split("|", 3)
        tam_bloque, longitud = int(tam_bloque), int(longitud)
    except ValueError:
        mostrar_mensaje("la linea no trae la cabecera esperada", "error")
        return "NAK"

    # ENLACE
    try:
        bits, estado = verificar_integridad(trama, algoritmo, tam_bloque, longitud)
    except ValueError as error:
        mostrar_mensaje(str(error), "error")
        return "NAK"

    if estado == "error":
        mostrar_mensaje("el algoritmo detecto un error que no pudo corregir", "error")
        return "NAK"

    # PRESENTACION
    try:
        texto = decodificar_mensaje(bits)
    except ValueError as error:
        # Con CRC esto no deberia pasar: una trama corrupta se rechaza antes.
        # Con Hamming si, cuando "corrige" mal una trama con dos errores.
        mostrar_mensaje(str(error), "error")
        return "NAK"

    # APLICACION
    mostrar_mensaje(texto, estado)

    try:
        respuesta = procesar(texto, sesion)
    except ValueError as error:
        mostrar_mensaje(f"no es una operacion valida ({error})", "error")
        return "NAK"

    prefijo = "ACK|CORREGIDO" if estado == "corregido" else "ACK"
    return prefijo if respuesta is None else f"{prefijo}|{respuesta}"


if __name__ == "__main__":
    escuchar(PUERTO, crear_manejador)
