package algoritmos

import (
	"strings"
	"testing"
)

func TestCalcularR(t *testing.T) {
	casos := map[int]int{
		4:  3,
		8:  4,
		16: 5,
		32: 6,
	}

	for m, esperado := range casos {
		if obtenido := calcularR(m); obtenido != esperado {
			t.Errorf(
				"calcularR(%d) = %d; se esperaba %d",
				m,
				obtenido,
				esperado,
			)
		}
	}
}

func TestHammingEncodeVector74(t *testing.T) {
	obtenido, err := HammingEncode("1011", 4)
	if err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	// Posiciones:
	// 1=P1, 2=P2, 3=1, 4=P4, 5=0, 6=1, 7=1
	// Resultado con paridad par: 0110011
	esperado := "0110011"

	if obtenido != esperado {
		t.Errorf(
			"HammingEncode(\"1011\", 4) = %q; se esperaba %q",
			obtenido,
			esperado,
		)
	}
}

func TestHammingEncodeAgregaRelleno(t *testing.T) {
	// 10110 se divide así:
	// 1011
	// 0000, porque el último 0 se completa con tres ceros.
	obtenido, err := HammingEncode("10110", 4)
	if err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	esperado := "01100110000000"

	if obtenido != esperado {
		t.Errorf(
			"HammingEncode con relleno = %q; se esperaba %q",
			obtenido,
			esperado,
		)
	}
}

func TestHammingEncodeLongitudes(t *testing.T) {
	casos := []struct {
		tamBloque     int
		bits          string
		longitudTrama int
	}{
		{4, "10110010", 14},
		{8, "10110010", 12},
		{16, "10110010", 21},
		{32, "10110010", 38},
	}

	for _, caso := range casos {
		obtenido, err := HammingEncode(caso.bits, caso.tamBloque)
		if err != nil {
			t.Fatalf(
				"bloque %d produjo error: %v",
				caso.tamBloque,
				err,
			)
		}

		if len(obtenido) != caso.longitudTrama {
			t.Errorf(
				"bloque %d produjo %d bits; se esperaban %d",
				caso.tamBloque,
				len(obtenido),
				caso.longitudTrama,
			)
		}

		if strings.Trim(obtenido, "01") != "" {
			t.Errorf(
				"bloque %d produjo caracteres que no son bits",
				caso.tamBloque,
			)
		}
	}
}

func TestHammingEncodeMensajeVacio(t *testing.T) {
	obtenido, err := HammingEncode("", 4)
	if err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	if obtenido != "" {
		t.Errorf("se esperaba cadena vacía, se obtuvo %q", obtenido)
	}
}

func TestHammingEncodeRechazaEntradasInvalidas(t *testing.T) {
	if _, err := HammingEncode("01012", 4); err == nil {
		t.Error("se esperaba error por mensaje con caracteres inválidos")
	}

	if _, err := HammingEncode("0101", 0); err == nil {
		t.Error("se esperaba error por tamaño de bloque cero")
	}

	if _, err := HammingEncode("0101", -1); err == nil {
		t.Error("se esperaba error por tamaño de bloque negativo")
	}
}
