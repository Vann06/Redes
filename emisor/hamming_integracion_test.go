package main

import "testing"

func TestEnlaceDespachaHamming(t *testing.T) {
	obtenido, err := calcularIntegridad("1011", "HAM", 4)
	if err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	esperado := "0110011"

	if obtenido != esperado {
		t.Errorf(
			"calcularIntegridad con HAM = %q; se esperaba %q",
			obtenido,
			esperado,
		)
	}
}

func TestEnlaceHammingConVariosBloques(t *testing.T) {
	obtenido, err := calcularIntegridad("10110010", "HAM", 4)
	if err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	if len(obtenido) != 14 {
		t.Errorf(
			"se esperaban 14 bits para dos bloques Hamming(7,4), se obtuvieron %d",
			len(obtenido),
		)
	}
}
