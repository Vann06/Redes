package main

import "math/rand"

// aplicarRuido simula el canal ruidoso: recorre la trama bit por bit y voltea
// cada uno con probabilidad p, de forma independiente.
//
// p es la probabilidad POR BIT, no la probabilidad de que la trama traiga algún
// error. Con p = 0.01 y una trama de 200 bits se esperan ~2 bits dañados, no un
// 1% de tramas dañadas.
//
// El ruido se aplica a la trama completa, incluidos los bits de redundancia:
// el canal no sabe cuáles son datos y cuáles son paridad. La cabecera queda
// fuera porque no viaja por aquí, la arma el main después.
func aplicarRuido(trama string, p float64) string {
	bits := []byte(trama)

	for i := range bits {
		if rand.Float64() < p {
			if bits[i] == '0' {
				bits[i] = '1'
			} else {
				bits[i] = '0'
			}
		}
	}

	return string(bits)
}
