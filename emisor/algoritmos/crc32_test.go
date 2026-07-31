package algoritmos

import (
	"fmt"
	"hash/crc32"
	"math/rand"
	"strconv"
	"strings"
	"testing"
)

// aBits convierte texto a string de bits, igual que la capa de presentación.
// Se repite aquí porque presentacion.go vive en el paquete main y los tests del
// algoritmo no deben depender de las capas.
func aBits(texto string) string {
	var b strings.Builder
	for _, octeto := range []byte(texto) {
		fmt.Fprintf(&b, "%08b", octeto)
	}
	return b.String()
}

// crcDeLaTrama saca los últimos 32 bits de la trama y los devuelve como número.
func crcDeLaTrama(t *testing.T, trama string) uint32 {
	t.Helper()

	if len(trama) < BitsCRC {
		t.Fatalf("la trama es más corta que el CRC: %d bits", len(trama))
	}

	valor, err := strconv.ParseUint(trama[len(trama)-BitsCRC:], 2, 32)
	if err != nil {
		t.Fatalf("los últimos %d bits no son binario: %v", BitsCRC, err)
	}
	return uint32(valor)
}

// TestVectorObligatorio es el que exige instrucciones.md. Si este falla, la
// implementación de Python nunca va a coincidir aunque "se vea bien".
func TestVectorObligatorio(t *testing.T) {
	trama, err := CRC32Encode(aBits("123456789"))
	if err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	if obtenido := crcDeLaTrama(t, trama); obtenido != 0xCBF43926 {
		t.Errorf("CRC-32 de \"123456789\" = 0x%08X, se esperaba 0xCBF43926", obtenido)
	}
}

func TestValoresConocidos(t *testing.T) {
	casos := []struct {
		entrada  string
		esperado uint32
	}{
		{"", 0x00000000},
		{"a", 0xE8B7BE43},
		{"abc", 0x352441C2},
		{"123456789", 0xCBF43926},
	}

	for _, caso := range casos {
		trama, err := CRC32Encode(aBits(caso.entrada))
		if err != nil {
			t.Errorf("%q: error inesperado: %v", caso.entrada, err)
			continue
		}

		if obtenido := crcDeLaTrama(t, trama); obtenido != caso.esperado {
			t.Errorf("%q: CRC = 0x%08X, se esperaba 0x%08X", caso.entrada, obtenido, caso.esperado)
		}
	}
}

// TestCoincideConLaStdlib usa hash/crc32 como oráculo. No se puede usar en la
// implementación (hay que escribir el algoritmo a mano), pero sí para verificar
// que la receta elegida es la estándar y no una variante parecida.
func TestCoincideConLaStdlib(t *testing.T) {
	azar := rand.New(rand.NewSource(1)) // semilla fija: el test es reproducible

	for caso := 0; caso < 500; caso++ {
		datos := make([]byte, azar.Intn(64))
		for i := range datos {
			datos[i] = byte(azar.Intn(256))
		}

		trama, err := CRC32Encode(aBits(string(datos)))
		if err != nil {
			t.Fatalf("error inesperado con %d bytes: %v", len(datos), err)
		}

		esperado := crc32.ChecksumIEEE(datos)
		if obtenido := crcDeLaTrama(t, trama); obtenido != esperado {
			t.Fatalf("con %d bytes: CRC = 0x%08X, la stdlib dice 0x%08X", len(datos), obtenido, esperado)
		}
	}
}

// TestFormaDeLaTrama verifica el contrato: los bits originales quedan intactos
// al inicio y la redundancia son exactamente 32 bits pegados al final.
func TestFormaDeLaTrama(t *testing.T) {
	bits := aBits("hola")

	trama, err := CRC32Encode(bits)
	if err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	if len(trama) != len(bits)+BitsCRC {
		t.Errorf("la trama mide %d bits, se esperaban %d", len(trama), len(bits)+BitsCRC)
	}

	if !strings.HasPrefix(trama, bits) {
		t.Error("la trama no empieza con los bits originales")
	}

	if strings.Trim(trama, "01") != "" {
		t.Error("la trama tiene caracteres que no son '0' ni '1'")
	}
}

func TestEntradasInvalidas(t *testing.T) {
	casos := []struct {
		nombre  string
		entrada string
	}{
		{"no es múltiplo de 8", "0100000"},
		{"trae caracteres raros", "0100000x"},
		{"trae un espacio", "01000 01"},
	}

	for _, caso := range casos {
		if _, err := CRC32Encode(caso.entrada); err == nil {
			t.Errorf("%s: se esperaba un error y no hubo", caso.nombre)
		}
	}
}
