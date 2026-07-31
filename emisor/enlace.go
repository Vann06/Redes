package main

import (
	"fmt"
	"strings"

	"emisor/algoritmos"
)

// calcularIntegridad es solo un despachador.
//
// No sabe cómo funciona ninguno de los dos algoritmos, solo cuál toca. El
// algoritmo es un parámetro de tiempo de ejecución: no hay dos flujos separados
// ni un if por algoritmo repartido por el resto del programa.
func calcularIntegridad(bits, algoritmo string, tamBloque int) (string, error) {
	switch algoritmo {
	case "CRC":
		return algoritmos.CRC32Encode(bits)

	case "HAM":
		return algoritmos.HammingEncode(bits, tamBloque)
	default:
		return "", fmt.Errorf("algoritmo desconocido: %q (usa CRC o HAM)", algoritmo)
	}
}

// resultado es el veredicto que manda el receptor después de verificar la
// trama, junto con lo que haya contestado el servidor bancario.
type resultado struct {
	estado    string // "ok", "corregido" o "error"
	respuesta string // respuesta del banco; vacía si la trama se descartó
}

// interpretarRespuesta traduce la línea que contesta el receptor:
//
//	ACK|<respuesta>              la trama llegó sin errores
//	ACK|CORREGIDO|<respuesta>    llegó con error y el receptor lo corrigió
//	NAK                          error detectado, la trama se descartó
//
// Se compara por prefijo y no se parte por '|' porque la respuesta del banco es
// JSON y podría traer '|' adentro. Solo los prefijos son delimitadores.
func interpretarRespuesta(linea string) (resultado, error) {
	switch {
	case linea == "NAK":
		return resultado{estado: "error"}, nil

	case strings.HasPrefix(linea, "ACK|CORREGIDO|"):
		return resultado{
			estado:    "corregido",
			respuesta: strings.TrimPrefix(linea, "ACK|CORREGIDO|"),
		}, nil

	case linea == "ACK|CORREGIDO":
		return resultado{estado: "corregido"}, nil

	case strings.HasPrefix(linea, "ACK|"):
		return resultado{
			estado:    "ok",
			respuesta: strings.TrimPrefix(linea, "ACK|"),
		}, nil

	case linea == "ACK":
		return resultado{estado: "ok"}, nil

	default:
		return resultado{}, fmt.Errorf("respuesta desconocida del receptor: %q", linea)
	}
}
