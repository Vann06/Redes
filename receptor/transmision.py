"""Capa de transmision del receptor: el socket servidor."""

import socket

HOST = "127.0.0.1"


def escuchar(puerto, crear_manejador):
    """Escucha para siempre en el puerto y atiende una conexion a la vez.

    crear_manejador() se llama una vez por conexion y devuelve la funcion
    manejar(linea) -> respuesta. Asi cada cliente arranca con su propio estado
    sin que esta capa sepa que es una sesion: para ella es una caja negra.

    Esta capa no sabe que traen las lineas ni que algoritmo se uso. Lo unico
    que le importa es el framing y que el servidor nunca se caiga.
    """
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Sin esto, reiniciar el receptor da "Address already in use" mientras el
    # puerto sigue en TIME_WAIT.
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, puerto))
    servidor.listen(1)

    print(f"[RECEPTOR] escuchando en {HOST}:{puerto}")

    while True:  # el receptor siempre esta escuchando
        conn, direccion = servidor.accept()
        print(f"[RECEPTOR] conexion desde {direccion[0]}:{direccion[1]}")

        try:
            with conn:
                _atender(conn, crear_manejador())
        except (ConnectionResetError, BrokenPipeError, OSError) as error:
            # Que un cliente se caiga no puede tumbar al servidor.
            print(f"[RECEPTOR] se corto la conexion: {error}")

        print("[RECEPTOR] conexion cerrada, esperando la siguiente")


def _atender(conn, manejar):
    """Lee tramas completas de una conexion y contesta cada una."""
    buffer = ""

    while True:
        datos = conn.recv(4096)
        if not datos:
            return  # el cliente cerro

        buffer += datos.decode("utf-8", errors="replace")

        # TCP es un flujo de bytes y NO respeta los limites de los mensajes:
        # dos tramas pueden llegar pegadas en un solo recv, o una sola trama
        # puede llegar partida en pedazos. Si se le calculara el CRC a media
        # trama, el receptor reportaria error aunque el algoritmo este perfecto.
        # Por eso se acumula en el buffer hasta encontrar el '\n'.
        while "\n" in buffer:
            linea, _, buffer = buffer.partition("\n")
            respuesta = manejar(linea)
            conn.sendall((respuesta + "\n").encode("utf-8"))
