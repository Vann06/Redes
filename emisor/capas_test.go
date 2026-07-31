package main

import (
	"strings"
	"testing"

	"emisor/algoritmos"
)

func TestCodificarMensaje(t *testing.T) {
	casos := []struct {
		entrada  string
		esperado string
	}{
		{"", ""},
		{"A", "01000001"},
		{"AB", "0100000101000010"},
		{"0", "00110000"},
	}

	for _, caso := range casos {
		if obtenido := codificarMensaje(caso.entrada); obtenido != caso.esperado {
			t.Errorf("codificarMensaje(%q) = %q, se esperaba %q", caso.entrada, obtenido, caso.esperado)
		}
	}
}

// El texto se recorre como bytes, no como runas: una "ñ" son dos bytes en UTF-8
// y por lo tanto 16 bits. Si esto se rompe, el receptor arma mal los caracteres.
func TestCodificarMensajeNoASCII(t *testing.T) {
	bits := codificarMensaje("ñ")

	if len(bits) != 16 {
		t.Errorf("\"ñ\" produjo %d bits, se esperaban 16", len(bits))
	}
	if strings.Trim(bits, "01") != "" {
		t.Error("la salida tiene caracteres que no son '0' ni '1'")
	}
}

// La salida de presentación siempre es múltiplo de 8. De eso depende la
// precondición de CRC32Encode.
func TestCodificarMensajeSiempreMultiploDe8(t *testing.T) {
	for _, texto := range []string{"a", "hola", "1234567", "ñañaña", "cajero automático"} {
		if bits := codificarMensaje(texto); len(bits)%8 != 0 {
			t.Errorf("%q produjo %d bits, no es múltiplo de 8", texto, len(bits))
		}
	}
}

func TestRuidoSinRuido(t *testing.T) {
	trama := codificarMensaje("mensaje de prueba")

	if sucia := aplicarRuido(trama, 0); sucia != trama {
		t.Error("con p = 0 la trama no debería cambiar")
	}
}

func TestRuidoTotal(t *testing.T) {
	trama := codificarMensaje("mensaje de prueba")
	sucia := aplicarRuido(trama, 1)

	if len(sucia) != len(trama) {
		t.Fatalf("la trama cambió de tamaño: %d -> %d", len(trama), len(sucia))
	}

	for i := range trama {
		if sucia[i] == trama[i] {
			t.Fatalf("con p = 1 todos los bits deberían voltearse, el %d no cambió", i)
		}
	}
}

// El ruido tiene que ser por bit e independiente. Con 10000 bits y p = 0.1 se
// esperan ~1000 volteados; las cotas son anchas (más de 6 sigma) para que el
// test no falle por azar.
func TestRuidoEsPorBit(t *testing.T) {
	trama := strings.Repeat("01", 5000)
	sucia := aplicarRuido(trama, 0.1)

	if len(sucia) != len(trama) {
		t.Fatalf("la trama cambió de tamaño: %d -> %d", len(trama), len(sucia))
	}
	if strings.Trim(sucia, "01") != "" {
		t.Fatal("la trama sucia tiene caracteres que no son '0' ni '1'")
	}

	volteados := 0
	for i := range trama {
		if sucia[i] != trama[i] {
			volteados++
		}
	}

	if volteados < 800 || volteados > 1200 {
		t.Errorf("se voltearon %d de 10000 bits, se esperaban ~1000", volteados)
	}
}

func TestEnlaceDespachaCRC(t *testing.T) {
	bits := codificarMensaje("hola")

	trama, err := calcularIntegridad(bits, "CRC", 0)
	if err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	esperado, err := algoritmos.CRC32Encode(bits)
	if err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	if trama != esperado {
		t.Error("el despachador no devolvió lo mismo que CRC32Encode")
	}
}

func TestEnlaceRechazaLoDesconocido(t *testing.T) {
	bits := codificarMensaje("hola")

	for _, algoritmo := range []string{"", "crc", "CRC32", "otro"} {
		if _, err := calcularIntegridad(bits, algoritmo, 4); err == nil {
			t.Errorf("algoritmo %q: se esperaba un error y no hubo", algoritmo)
		}
	}
}
