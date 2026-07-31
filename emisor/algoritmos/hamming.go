// Package algoritmos contiene los algoritmos de integridad del emisor.
package algoritmos

import (
	"fmt"
	"strings"
)

// HammingEncode divide el mensaje en bloques de tamBloque bits y agrega
// los bits de paridad necesarios para formar un código de Hamming.
//
// Las posiciones se numeran desde 1. Los bits de paridad se colocan en
// posiciones que son potencias de dos: 1, 2, 4, 8, 16, etc.
//
// Se utiliza paridad par.
//
// Si el último bloque no está completo, se rellena con ceros. La longitud
// original del mensaje viaja en la cabecera para que el receptor pueda
// retirar ese relleno.
func HammingEncode(bits string, tamBloque int) (string, error) {
	if tamBloque <= 0 {
		return "", fmt.Errorf("tamBloque debe ser un entero positivo")
	}

	if strings.Trim(bits, "01") != "" {
		return "", fmt.Errorf("el mensaje contiene caracteres que no son bits")
	}

	if bits == "" {
		return "", nil
	}

	r := calcularR(tamBloque)
	n := tamBloque + r

	relleno := (tamBloque - len(bits)%tamBloque) % tamBloque
	bitsRellenos := bits + strings.Repeat("0", relleno)

	var salida strings.Builder
	salida.Grow((len(bitsRellenos) / tamBloque) * n)

	for inicio := 0; inicio < len(bitsRellenos); inicio += tamBloque {
		bloque := bitsRellenos[inicio : inicio+tamBloque]
		codificado := make([]byte, n)
		indiceDato := 0

		// Primero se colocan los datos en las posiciones que no son
		// potencias de dos. Las posiciones de paridad se inicializan en 0.
		for posicion := 1; posicion <= n; posicion++ {
			if esPotenciaDeDos(posicion) {
				codificado[posicion-1] = '0'
				continue
			}

			codificado[posicion-1] = bloque[indiceDato]
			indiceDato++
		}

		// Se calculan los bits de paridad par.
		for posicionParidad := 1; posicionParidad <= n; posicionParidad <<= 1 {
			paridad := byte(0)

			for posicion := 1; posicion <= n; posicion++ {
				if posicion&posicionParidad != 0 &&
					codificado[posicion-1] == '1' {
					paridad ^= 1
				}
			}

			codificado[posicionParidad-1] = '0' + paridad
		}

		salida.Write(codificado)
	}

	return salida.String(), nil
}

// calcularR devuelve el número mínimo de bits de paridad que cumple:
//
//	m + r + 1 <= 2^r
func calcularR(m int) int {
	r := 1

	for m+r+1 > 1<<r {
		r++
	}

	return r
}

func esPotenciaDeDos(valor int) bool {
	return valor > 0 && valor&(valor-1) == 0
}
