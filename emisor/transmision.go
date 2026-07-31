package main

import (
	"bufio"
	"io"
	"net"
	"strconv"
	"strings"
)

const (
	hostReceptor   = "127.0.0.1"
	puertoReceptor = 5000
)

// canal es la conexión con el servidor bancario.
//
// Se mantiene abierta durante toda la sesión del cajero, no una conexión por
// mensaje: el banco necesita recordar quién inició sesión. De paso, esto hace
// que el framing importe de verdad, porque varias tramas viajan por la misma
// conexión una tras otra.
type canal struct {
	conn net.Conn

	// El lector se crea una sola vez y se reutiliza. Si se creara uno nuevo en
	// cada lectura, los bytes que ya quedaron en su buffer interno (por ejemplo
	// el inicio de la siguiente respuesta) se perderían.
	lector *bufio.Reader
}

func conectar() (*canal, error) {
	direccion := net.JoinHostPort(hostReceptor, strconv.Itoa(puertoReceptor))

	conn, err := net.Dial("tcp", direccion)
	if err != nil {
		return nil, err
	}

	return &canal{conn: conn, lector: bufio.NewReader(conn)}, nil
}

func (c *canal) cerrar() error {
	return c.conn.Close()
}

// enviarInformacion manda la línea y espera la respuesta del receptor.
//
// Esta capa no sabe qué algoritmo se usó ni qué trae la línea: recibe un string
// ya armado y lo manda tal cual. Lo único que le importa es el framing.
//
// El '\n' del final no es decorativo. TCP es un flujo de bytes y no respeta los
// límites de los mensajes: sin un delimitador, el receptor no tiene forma de
// saber dónde termina una trama. Por eso también se lee la respuesta hasta su
// propio '\n' en vez de conformarse con lo que traiga la primera lectura.
//
// La conexión no se cierra aquí: hay que esperar el ACK/NAK, y además la sesión
// del cajero sigue viva para el siguiente mensaje.
func (c *canal) enviarInformacion(linea string) (string, error) {
	if _, err := io.WriteString(c.conn, linea+"\n"); err != nil {
		return "", err
	}

	respuesta, err := c.lector.ReadString('\n')
	if err != nil {
		return "", err
	}

	return strings.TrimRight(respuesta, "\r\n"), nil
}
