// Emisor del laboratorio: el cajero automático.
//
// La aplicación es el cajero; sus mensajes bajan por las capas hasta el socket.
// Cada capa es una función independiente que no sabe nada de las demás: la de
// transmisión no sabe qué algoritmo se usó, la de enlace no sabe que existen
// sockets, y el cajero no sabe que existen los bits.
package main

import (
	"errors"
	"fmt"
	"io"
	"os"
)

func main() {
	conexion, err := conectar()
	if err != nil {
		salir(fmt.Errorf("no se pudo conectar con el servidor bancario: %w", err))
	}
	defer conexion.cerrar()

	fmt.Printf("[CAJERO] Conectado al servidor bancario en %s:%d\n", hostReceptor, puertoReceptor)

	// La capa de aplicación recibe la forma de mandar un mensaje, no los
	// detalles de cómo viaja.
	err = ejecutarCajero(func(texto string) (resultado, error) {
		return bajarPorLasCapas(conexion, texto)
	})

	// Que se acabe la entrada no es un error: es el usuario cerrando el cajero.
	if err != nil && !errors.Is(err, io.EOF) {
		salir(err)
	}
}

// bajarPorLasCapas es el flujo del emisor, una capa por línea.
func bajarPorLasCapas(conexion *canal, texto string) (resultado, error) {
	algoritmo, tamBloque, p, err := solicitarParametros()
	if err != nil {
		return resultado{}, err
	}

	bits := codificarMensaje(texto)

	trama, err := calcularIntegridad(bits, algoritmo, tamBloque)
	if err != nil {
		return resultado{}, err
	}

	sucia := aplicarRuido(trama, p)

	// La cabecera se arma aquí, no en la capa de transmisión: así esa capa
	// sigue sin saber qué algoritmo se usó. Los tres campos son metadata y
	// quedan fuera del cálculo de integridad y fuera del ruido.
	linea := fmt.Sprintf("%s|%d|%d|%s", algoritmo, tamBloque, len(bits), sucia)

	respuesta, err := conexion.enviarInformacion(linea)
	if err != nil {
		return resultado{}, err
	}

	return interpretarRespuesta(respuesta)
}

func salir(err error) {
	fmt.Fprintf(os.Stderr, "[CAJERO] %v\n", err)
	os.Exit(1)
}
