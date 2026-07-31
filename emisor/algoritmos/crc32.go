// Package algoritmos contiene los algoritmos de integridad del emisor.
// Solo la parte de codificación: la verificación vive en el receptor, en Python.
package algoritmos

import (
	"fmt"
	"strconv"
)

// polinomioReflejado es el polinomio IEEE 802.3 (0x04C11DB7) escrito al revés.
//
// La variante reflejada del CRC-32 procesa cada byte empezando por el bit menos
// significativo. Con el polinomio invertido, eso se implementa corriendo a la
// derecha en vez de a la izquierda, que es más simple y más rápido.
const polinomioReflejado uint32 = 0xEDB88320

// BitsCRC son los bits de redundancia que agrega CRC-32. Siempre 32, sin
// importar el tamaño del mensaje: por eso el overhead de CRC es fijo y la única
// forma de variarlo en las pruebas es cambiando el bloque de Hamming.
const BitsCRC = 32

// CRC32Encode recibe un string de bits ('0' y '1') y devuelve ese mismo string
// con 32 bits de CRC pegados al final.
//
// Precondición: la entrada tiene que ser múltiplo de 8, porque el CRC se
// calcula sobre bytes. codificarMensaje siempre cumple eso (8 bits por
// carácter); si no se cumple es un error de programación y se reporta.
//
// Los 32 bits del CRC se escriben con el bit más significativo primero, igual
// que el resto de la trama. El receptor en Python tiene que leerlos con esa
// misma convención o los residuos no van a coincidir nunca.
func CRC32Encode(bits string) (string, error) {
	datos, err := bitsABytes(bits)
	if err != nil {
		return "", err
	}
	return bits + fmt.Sprintf("%032b", calcularCRC(datos)), nil
}

// calcularCRC implementa CRC-32 en la variante que usan Ethernet, PNG y zip:
// init en 0xFFFFFFFF, entrada y salida reflejadas, XOR final con 0xFFFFFFFF.
//
// Existen varias recetas del "mismo" algoritmo y son incompatibles entre sí, así
// que esta es la que tiene que replicar el receptor. Vector de control:
// "123456789" -> 0xCBF43926.
func calcularCRC(datos []byte) uint32 {
	crc := ^uint32(0) // 0xFFFFFFFF

	for _, octeto := range datos {
		crc ^= uint32(octeto)
		for i := 0; i < 8; i++ {
			if crc&1 != 0 {
				crc = (crc >> 1) ^ polinomioReflejado
			} else {
				crc >>= 1
			}
		}
	}

	return ^crc // XOR final contra 0xFFFFFFFF
}

// bitsABytes agrupa el string de bits de 8 en 8, con el bit más significativo
// primero. Es el inverso exacto de lo que hace la capa de presentación.
func bitsABytes(bits string) ([]byte, error) {
	if len(bits)%8 != 0 {
		return nil, fmt.Errorf("CRC-32 necesita un múltiplo de 8 bits, llegaron %d", len(bits))
	}

	datos := make([]byte, 0, len(bits)/8)
	for i := 0; i < len(bits); i += 8 {
		octeto, err := strconv.ParseUint(bits[i:i+8], 2, 8)
		if err != nil {
			return nil, fmt.Errorf("la trama tiene algo que no son bits: %q", bits[i:i+8])
		}
		datos = append(datos, byte(octeto))
	}

	return datos, nil
}
