package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
)

// enviador es todo lo que la capa de aplicación necesita del resto del
// programa: entregar un texto y recibir la respuesta.
//
// El cajero no sabe que existen bits, CRC, ruido ni sockets. Recibe esta
// función ya armada desde el main y la usa a ciegas. Esa es la separación de
// capas: si mañana el mensaje viajara por una paloma mensajera, este archivo no
// cambiaría ni una línea.
type enviador func(texto string) (resultado, error)

// respuestaBanco es la forma de lo que contesta el servidor bancario. JSON es
// el protocolo de aplicación entre el cajero y el banco, así que se arma y se
// interpreta aquí, no en las capas de abajo.
type respuestaBanco struct {
	Action string `json:"action"`
	Data   struct {
		Message string  `json:"message"`
		Amount  float64 `json:"amount"`
		Balance float64 `json:"balance"`
	} `json:"data"`
}

var entrada = bufio.NewScanner(os.Stdin)

// leerLinea pide una línea al usuario. Devuelve io.EOF cuando ya no hay más
// entrada (Ctrl+D, o una tubería que se acabó).
func leerLinea(prompt string) (string, error) {
	fmt.Print(prompt)

	if !entrada.Scan() {
		if err := entrada.Err(); err != nil {
			return "", err
		}
		fmt.Println()
		return "", io.EOF
	}

	return strings.TrimRight(entrada.Text(), "\r\n"), nil
}

// solicitarParametros pregunta con qué algoritmo y con cuánto ruido se manda
// este mensaje.
//
// Se pregunta en cada envío, no una vez por sesión: el enunciado pide que la
// tasa de error se solicite "al momento de enviar un mensaje". El tamaño de
// bloque solo aplica a Hamming; con CRC-32 el overhead es fijo en 32 bits y el
// campo viaja en cero.
func solicitarParametros() (algoritmo string, tamBloque int, p float64, err error) {
	fmt.Println("\n--- parámetros del envío ---")

	for {
		var linea string
		if linea, err = leerLinea("Algoritmo (CRC/HAM): "); err != nil {
			return
		}
		algoritmo = strings.ToUpper(strings.TrimSpace(linea))
		if algoritmo == "CRC" || algoritmo == "HAM" {
			break
		}
		fmt.Println(">> Escribe CRC o HAM.")
	}

	if algoritmo == "HAM" {
		for {
			var linea string
			if linea, err = leerLinea("Tamaño de bloque (4, 8, 16, 32): "); err != nil {
				return
			}
			tamBloque, err = strconv.Atoi(strings.TrimSpace(linea))
			if err == nil && tamBloque > 0 {
				break
			}
			err = nil
			fmt.Println(">> Tiene que ser un entero positivo.")
		}
	}

	for {
		var linea string
		if linea, err = leerLinea("Tasa de error por bit (0.0 a 1.0): "); err != nil {
			return
		}
		p, err = strconv.ParseFloat(strings.TrimSpace(linea), 64)
		if err == nil && p >= 0 && p <= 1 {
			break
		}
		err = nil
		fmt.Println(">> Tiene que ser un número entre 0.0 y 1.0.")
	}

	return
}

// peticion arma el mensaje que se le manda al banco.
func peticion(action string, data map[string]any) (string, error) {
	crudo, err := json.Marshal(map[string]any{"action": action, "data": data})
	if err != nil {
		return "", err
	}
	return string(crudo), nil
}

// mostrarEstado avisa cómo le fue a la trama en el camino. Devuelve false si el
// mensaje se perdió y no hay respuesta que interpretar.
func mostrarEstado(res resultado) bool {
	switch res.estado {
	case "ok":
		return true

	case "corregido":
		fmt.Println(">> (la trama llegó con errores y el receptor los corrigió)")
		return true

	default:
		fmt.Println(">> ERROR: el receptor detectó un error que no se pudo corregir.")
		fmt.Println("   El mensaje se descartó. Intenta de nuevo.")
		return false
	}
}

// consultar manda una operación al banco y devuelve la respuesta ya
// interpretada. El segundo valor es false si la trama se descartó por errores.
func consultar(enviar enviador, action string, data map[string]any) (respuestaBanco, bool, error) {
	var resp respuestaBanco

	texto, err := peticion(action, data)
	if err != nil {
		return resp, false, err
	}

	res, err := enviar(texto)
	if err != nil {
		return resp, false, err
	}

	if !mostrarEstado(res) {
		return resp, false, nil
	}

	if err := json.Unmarshal([]byte(res.respuesta), &resp); err != nil {
		return resp, false, fmt.Errorf("el banco contestó algo que no se entiende (%q): %w", res.respuesta, err)
	}

	return resp, true, nil
}

// ejecutarCajero es la sesión completa: autenticarse y operar.
func ejecutarCajero(enviar enviador) error {
	autenticado, err := login(enviar)
	if err != nil || !autenticado {
		return err
	}
	return menu(enviar)
}

// login pide tarjeta y PIN, reintentando hasta autenticarse.
func login(enviar enviador) (bool, error) {
	for {
		card, err := leerLinea("\nNúmero de tarjeta: ")
		if err != nil {
			return false, err
		}
		pin, err := leerLinea("PIN: ")
		if err != nil {
			return false, err
		}

		resp, ok, err := consultar(enviar, "login", map[string]any{"card": card, "pin": pin})
		if err != nil {
			return false, err
		}
		if !ok {
			continue // la trama se perdió, se vuelve a intentar
		}

		fmt.Println(">> " + resp.Data.Message)

		if resp.Action == "login_ok" {
			return true, nil
		}

		fmt.Println("   Intenta de nuevo.")
	}
}

// menu muestra las opciones del cajero y atiende lo que elija el usuario.
func menu(enviar enviador) error {
	for {
		fmt.Println("\n--- CAJERO ---")
		fmt.Println("1) Retirar dinero")
		fmt.Println("2) Enviar mensaje")
		fmt.Println("3) Salir")

		opcion, err := leerLinea("Elige una opción: ")
		if err != nil {
			return err
		}

		switch strings.TrimSpace(opcion) {
		case "1":
			if err := retirar(enviar); err != nil {
				return err
			}

		case "2":
			if err := enviarMensajeLibre(enviar); err != nil {
				return err
			}

		case "3":
			resp, ok, err := consultar(enviar, "logout", map[string]any{})
			if err != nil {
				return err
			}
			if ok {
				fmt.Println(">> " + resp.Data.Message)
			}
			return nil

		default:
			fmt.Println(">> Opción inválida.")
		}
	}
}

// enviarMensajeLibre manda un texto cualquiera al servidor bancario, que solo
// lo muestra.
//
// A diferencia del resto de operaciones, aquí no se espera respuesta del banco:
// el flujo de capas es de ida, del emisor al receptor. Lo único que vuelve es el
// veredicto de integridad, y eso es lo que decide si el mensaje se dio por
// enviado o por perdido. Por eso no se usa consultar(), que además interpreta
// el JSON de vuelta.
func enviarMensajeLibre(enviar enviador) error {
	texto, err := leerLinea("Mensaje a enviar: ")
	if err != nil {
		return err
	}

	if strings.TrimSpace(texto) == "" {
		fmt.Println(">> El mensaje no puede estar vacío.")
		return nil
	}

	mensaje, err := peticion("message", map[string]any{"text": texto})
	if err != nil {
		return err
	}

	res, err := enviar(mensaje)
	if err != nil {
		return err
	}

	switch res.estado {
	case "corregido":
		fmt.Println(">> Mensaje enviado con éxito (llegó con errores y el receptor los corrigió).")
	case "error":
		fmt.Println(">> Mensaje fallido: el receptor detectó un error y lo descartó.")
	default:
		fmt.Println(">> Mensaje enviado con éxito.")
	}

	return nil
}

func retirar(enviar enviador) error {
	linea, err := leerLinea("Monto a retirar: ")
	if err != nil {
		return err
	}

	monto, err := strconv.ParseFloat(strings.TrimSpace(linea), 64)
	if err != nil {
		fmt.Println(">> El monto tiene que ser un número.")
		return nil
	}

	resp, ok, err := consultar(enviar, "withdraw", map[string]any{"amount": monto})
	if err != nil {
		return err
	}
	if !ok {
		return nil
	}

	if resp.Action == "withdraw_ok" {
		fmt.Printf(">> Toma tus $%.2f\n", resp.Data.Amount)
		fmt.Printf(">> Saldo restante: $%.2f\n", resp.Data.Balance)
	} else {
		fmt.Println(">> " + resp.Data.Message)
	}

	return nil
}
