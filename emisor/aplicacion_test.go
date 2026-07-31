package main

import (
	"bufio"
	"encoding/json"
	"strings"
	"testing"
)

// guionar reemplaza la entrada del usuario por un guion fijo, para poder correr
// el cajero sin teclado.
func guionar(t *testing.T, lineas ...string) {
	t.Helper()
	entrada = bufio.NewScanner(strings.NewReader(strings.Join(lineas, "\n") + "\n"))
}

// bancoFalso responde lo que se le indique y va guardando lo que recibe.
type bancoFalso struct {
	respuestas []resultado
	recibidos  []string
}

func (b *bancoFalso) enviar(texto string) (resultado, error) {
	b.recibidos = append(b.recibidos, texto)

	if len(b.respuestas) == 0 {
		return resultado{estado: "error"}, nil
	}

	res := b.respuestas[0]
	b.respuestas = b.respuestas[1:]
	return res, nil
}

func ack(json string) resultado {
	return resultado{estado: "ok", respuesta: json}
}

func TestInterpretarRespuesta(t *testing.T) {
	casos := []struct {
		linea     string
		estado    string
		respuesta string
	}{
		{"ACK", "ok", ""},
		{`ACK|{"action":"login_ok"}`, "ok", `{"action":"login_ok"}`},
		{"ACK|CORREGIDO", "corregido", ""},
		{`ACK|CORREGIDO|{"a":1}`, "corregido", `{"a":1}`},
		{"NAK", "error", ""},
		// La respuesta del banco puede traer '|' adentro: solo el prefijo
		// delimita, así que el resto tiene que llegar entero.
		{`ACK|{"message":"a|b"}`, "ok", `{"message":"a|b"}`},
	}

	for _, caso := range casos {
		res, err := interpretarRespuesta(caso.linea)
		if err != nil {
			t.Errorf("%q: error inesperado: %v", caso.linea, err)
			continue
		}
		if res.estado != caso.estado || res.respuesta != caso.respuesta {
			t.Errorf("%q: se obtuvo (%q, %q), se esperaba (%q, %q)",
				caso.linea, res.estado, res.respuesta, caso.estado, caso.respuesta)
		}
	}
}

func TestInterpretarRespuestaDesconocida(t *testing.T) {
	for _, linea := range []string{"", "OK", "ack", "NAK|algo"} {
		if _, err := interpretarRespuesta(linea); err == nil {
			t.Errorf("%q: se esperaba un error y no hubo", linea)
		}
	}
}

func TestPeticion(t *testing.T) {
	texto, err := peticion("login", map[string]any{"card": "23201", "pin": "6767"})
	if err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	var armado struct {
		Action string `json:"action"`
		Data   struct {
			Card string `json:"card"`
			Pin  string `json:"pin"`
		} `json:"data"`
	}
	if err := json.Unmarshal([]byte(texto), &armado); err != nil {
		t.Fatalf("no produjo JSON válido: %v", err)
	}

	if armado.Action != "login" || armado.Data.Card != "23201" || armado.Data.Pin != "6767" {
		t.Errorf("el mensaje quedó mal armado: %s", texto)
	}
}

// La sesión completa del cajero, sin sockets ni bits: la capa de aplicación
// solo necesita una forma de mandar texto. Esto es la separación de capas
// funcionando.
func TestSesionCompleta(t *testing.T) {
	guionar(t, "23201", "6767", "1", "100", "3")

	banco := &bancoFalso{respuestas: []resultado{
		ack(`{"action":"login_ok","data":{"message":"Autenticacion exitosa"}}`),
		ack(`{"action":"withdraw_ok","data":{"amount":100,"balance":1500}}`),
		ack(`{"action":"logout_ok","data":{"message":"Hasta luego"}}`),
	}}

	if err := ejecutarCajero(banco.enviar); err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	if len(banco.recibidos) != 3 {
		t.Fatalf("se mandaron %d mensajes, se esperaban 3", len(banco.recibidos))
	}

	for i, esperado := range []string{"login", "withdraw", "logout"} {
		if !strings.Contains(banco.recibidos[i], `"action":"`+esperado+`"`) {
			t.Errorf("mensaje %d: se esperaba %q, se mandó %s", i, esperado, banco.recibidos[i])
		}
	}
}

// Si el receptor contesta NAK, el mensaje se descartó y el cajero tiene que
// volver a pedir los datos, no seguir como si nada.
func TestReintentaTrasNAK(t *testing.T) {
	guionar(t, "23201", "6767", "23201", "6767", "3")

	banco := &bancoFalso{respuestas: []resultado{
		{estado: "error"}, // el primer login se perdió en el canal
		ack(`{"action":"login_ok","data":{"message":"Autenticacion exitosa"}}`),
		ack(`{"action":"logout_ok","data":{"message":"Hasta luego"}}`),
	}}

	if err := ejecutarCajero(banco.enviar); err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	if len(banco.recibidos) != 3 {
		t.Fatalf("se mandaron %d mensajes, se esperaban 3 (login, login, logout)", len(banco.recibidos))
	}
}

// El mensaje libre no espera respuesta del banco: el receptor solo lo muestra y
// contesta ACK pelado, sin JSON. El flujo de capas es de ida.
func TestEnviarMensajeLibre(t *testing.T) {
	guionar(t, "23201", "6767", "2", "hola como estas", "3")

	banco := &bancoFalso{respuestas: []resultado{
		ack(`{"action":"login_ok","data":{"message":"Autenticacion exitosa"}}`),
		{estado: "ok"}, // ACK pelado: sin respuesta del banco
		ack(`{"action":"logout_ok","data":{"message":"Hasta luego"}}`),
	}}

	if err := ejecutarCajero(banco.enviar); err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	if len(banco.recibidos) != 3 {
		t.Fatalf("se mandaron %d mensajes, se esperaban 3", len(banco.recibidos))
	}

	if !strings.Contains(banco.recibidos[1], `"action":"message"`) {
		t.Errorf("el segundo mensaje no es un message: %s", banco.recibidos[1])
	}
	if !strings.Contains(banco.recibidos[1], "hola como estas") {
		t.Errorf("el texto no viajó en el mensaje: %s", banco.recibidos[1])
	}
}

// Si la trama del mensaje se descarta, el cajero avisa que falló pero la sesión
// sigue viva: se vuelve al menú, no se cierra nada.
func TestMensajeFallidoNoTumbaLaSesion(t *testing.T) {
	guionar(t, "23201", "6767", "2", "hola como estas", "3")

	banco := &bancoFalso{respuestas: []resultado{
		ack(`{"action":"login_ok","data":{"message":"Autenticacion exitosa"}}`),
		{estado: "error"}, // NAK: la trama se perdió
		ack(`{"action":"logout_ok","data":{"message":"Hasta luego"}}`),
	}}

	if err := ejecutarCajero(banco.enviar); err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	if len(banco.recibidos) != 3 {
		t.Fatalf("se mandaron %d mensajes, se esperaban 3 (login, message, logout)", len(banco.recibidos))
	}
}

// Una trama corregida por Hamming sí trae respuesta útil: el cajero debe
// avisar del error pero seguir operando.
func TestCorregidoSigueSiendoUtil(t *testing.T) {
	guionar(t, "23201", "6767", "3")

	banco := &bancoFalso{respuestas: []resultado{
		{estado: "corregido", respuesta: `{"action":"login_ok","data":{"message":"Autenticacion exitosa"}}`},
		ack(`{"action":"logout_ok","data":{"message":"Hasta luego"}}`),
	}}

	if err := ejecutarCajero(banco.enviar); err != nil {
		t.Fatalf("error inesperado: %v", err)
	}

	if len(banco.recibidos) != 2 {
		t.Fatalf("se mandaron %d mensajes, se esperaban 2", len(banco.recibidos))
	}
}
