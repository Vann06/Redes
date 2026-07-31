package main

import (
	"fmt"
	"strings"
)

// codificarMensaje traduce el texto a un string de bits, 8 por byte y con el
// bit más significativo primero.
//
// Se recorre el texto como bytes y no como runas a propósito: lo que viaja por
// el cable son octetos. Un carácter fuera de ASCII ocupa varios bytes en UTF-8
// y produce varios grupos de 8 bits, que es exactamente lo que el receptor va a
// volver a juntar.
func codificarMensaje(texto string) string {
	var bits strings.Builder
	bits.Grow(len(texto) * 8)

	for _, octeto := range []byte(texto) {
		fmt.Fprintf(&bits, "%08b", octeto)
	}

	return bits.String()
}
