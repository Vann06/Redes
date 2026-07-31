# Contexto del proyecto
 
Laboratorio de Redes (UVG). Simulación de transmisión de datos sobre un canal
ruidoso, con detección y corrección de errores, usando una arquitectura de capas.
 
El escenario simulado es la comunicación entre un **cajero automático** (emisor)
y el **servidor de un banco** (receptor).
 
## Restricciones no negociables del enunciado
 
1. El emisor y el receptor deben estar en **lenguajes de programación distintos**,
   y al menos uno de los dos **no puede ser Python**.
   - Emisor (cajero): **Go**
   - Receptor (servidor bancario): **Python**
2. Se implementan **dos algoritmos**: uno de corrección y uno de detección.
   - Corrección: **Hamming** (bloques configurables, default (7,4))
   - Detección: **CRC-32** (polinomio IEEE 802.3, `0x04C11DB7`)
3. Cada algoritmo debe existir **en ambos lados** (encode en el emisor, decode o
   verificación en el receptor). No es que cada programa tenga las 4 funciones:
   son 4 funciones repartidas en 2 programas.
4. El ruido se aplica **a la trama completa**, incluidos los bits de redundancia.
5. El receptor debe estar **siempre escuchando** (loop infinito de `accept()`).
6. La tasa de error se solicita al usuario **en el momento de enviar**, no está
   hardcodeada.
7. Cuando el CRC detecta un error, el receptor debe **responder al emisor**
   avisando que la trama falló (requisito adicional del catedrático).
## Arquitectura de capas
 
Cada capa es una función independiente. Una capa **no debe saber nada** de las
demás. La capa de transmisión no sabe qué algoritmo se usó; la capa de enlace no
sabe que existen sockets. Esto se califica explícitamente (20% de la nota).
 
### Emisor (Go), 5 capas
 
| Capa | Servicio | Entrada | Salida |
|---|---|---|---|
| Aplicación | `ejecutarCajero(enviar)` | (operaciones del usuario) | mensajes JSON al banco |
| Aplicación | `solicitarParametros()` | (input del usuario) | algoritmo, tamaño de bloque, tasa de error |
| Aplicación | `mostrarEstado(resultado)` | veredicto del receptor | (avisa al usuario si se descartó) |
| Presentación | `codificarMensaje(texto)` | `"A"` | `"01000001"` |
| Enlace | `calcularIntegridad(bits, alg, tamBloque)` | `"01000001"` | bits + redundancia |
| Enlace | `interpretarRespuesta(linea)` | `"ACK\|{...}"` | estado + respuesta del banco |
| Ruido | `aplicarRuido(trama, p)` | trama limpia | trama con bits volteados |
| Transmisión | `enviarInformacion(trama)` | trama | línea de respuesta del receptor |

La aplicación es el **cajero automático**: login, retiro y logout, tal como en el
laboratorio anterior. Cada operación produce un mensaje JSON que baja por las
capas. El cajero recibe la función de envío desde el `main` y no sabe que
existen bits, CRC, ruido ni sockets — por eso se puede probar sin red.

El `tamBloque` solo lo usa Hamming. Con CRC-32 el overhead es fijo en 32 bits, así
que la capa de aplicación no lo pregunta y el campo viaja en cero, tal como
aparece en el formato del cable.

Ese `if` vive en la capa de aplicación, que es la que habla con el usuario y
legítimamente sabe qué está preguntando. Lo que no puede tener un `if` por
algoritmo es la capa de enlace, que es solo un despachador.
 
### Receptor (Python), 4 capas (no hay capa de ruido)
 
| Capa | Servicio | Qué hace |
|---|---|---|
| Transmisión | `escuchar(puerto, crear_manejador)` | socket servidor, entrega tramas completas |
| Enlace | `verificar_integridad(trama, alg, tam_bloque, longitud)` | recalcula, compara, corrige si puede |
| Presentación | `decodificar_mensaje(bits)` | binario a texto |
| Aplicación | `mostrar_mensaje(texto, estado)` | imprime el mensaje o el error |
 
### Flujo completo
 
El `main` de cada lado debe leerse como la lista de capas, nada más:
 
```go
// emisor/main.go   (manejo de errores omitido para que se vea el flujo)
//
// El cajero llama a esto una vez por cada operación bancaria.
func bajarPorLasCapas(conexion *canal, texto string) resultado {
	algoritmo, tamBloque, p := solicitarParametros()
	bits := codificarMensaje(texto)
	trama := calcularIntegridad(bits, algoritmo, tamBloque)
	sucia := aplicarRuido(trama, p)
	linea := fmt.Sprintf("%s|%d|%d|%s", algoritmo, tamBloque, len(bits), sucia)
	respuesta := conexion.enviarInformacion(linea)
	return interpretarRespuesta(respuesta)
}
```
 
```python
# receptor/main.py
def subir_por_las_capas(linea, sesion):
    algoritmo, tam_bloque, longitud, trama = linea.split("|", 3)
    bits, estado = verificar_integridad(trama, algoritmo, int(tam_bloque), int(longitud))
    if estado == "error":
        mostrar_mensaje("no se pudo recuperar el mensaje", "error")
        return "NAK"

    texto = decodificar_mensaje(bits)
    mostrar_mensaje(texto, estado)
    respuesta = procesar(texto, sesion)

    prefijo = "ACK|CORREGIDO" if estado == "corregido" else "ACK"
    return prefijo if respuesta is None else f"{prefijo}|{respuesta}"
 
escuchar(5000, crear_manejador)
```

`crear_manejador()` se llama **una vez por conexión** y devuelve la función que
atiende sus líneas. Así cada cliente arranca con su propia sesión (quién inició
sesión) sin que la capa de transmisión sepa qué es una sesión: para ella es una
caja negra.
 
## Contratos (firmas acordadas, no cambiar sin avisar)
 
Las tramas viajan **siempre como strings de caracteres `'0'` y `'1'`**, nunca como
bytes crudos. Es 8 veces menos eficiente pero evita problemas de padding (Hamming
produce tramas que no son múltiplo de 8), de endianness y de orden de bits entre
los dos lenguajes. Además se ve directo en Wireshark.
 
```go
// Emisor (Go), paquete emisor/algoritmos.
// Ambas reciben y devuelven strings de bits.
// Los nombres van en mayúscula porque algoritmos es un paquete aparte y en Go
// solo se exporta lo que empieza con mayúscula.
func CRC32Encode(bits string) string { ... }
func HammingEncode(bits string, tamBloque int) string { ... }   // rellena con ceros el último bloque
```

Go no tiene parámetros con valor por defecto, así que `tamBloque` siempre se pasa
explícito. El default de 4 vive en la capa de aplicación, que es quien se lo
pregunta al usuario.
 
```python
# Receptor (Python). Ambas devuelven (bits, estado).
# estado en {"ok", "corregido", "error"}
# CRC-32 solo detecta: nunca devuelve "corregido", solo "ok" o "error".
def crc32_verify(trama)   -> tuple[str, str]: ...
def hamming_decode(trama, tam_bloque=4, longitud=None) -> tuple[str, str]: ...
```

`longitud` es la cantidad de bits reales del mensaje. Sirve para recortar el
relleno que `hammingEncode` agregó al último bloque. Si es `None`, se devuelven
todos los bits decodificados sin recortar (útil solo en tests unitarios).
 
La capa de enlace es solo un despachador. **No hay dos flujos separados por
algoritmo**: el algoritmo es un parámetro en tiempo de ejecución.
 
```python
def verificar_integridad(trama, algoritmo, tam_bloque, longitud):
    if algoritmo == "CRC":
        return crc32_verify(trama)
    return hamming_decode(trama, tam_bloque, longitud)
```
 
## Formato en el cable
 
Del emisor sale **una sola línea de texto** terminada en `\n`:
 
```
CRC|0|8|110100101110001...
HAM|4|8|011001101100110...
 ^  ^ ^ ^
 |  | | +-- trama con redundancia, ya ensuciada por el ruido
 |  | +---- longitud real del mensaje en bits (antes de redundancia y relleno)
 |  +------ tamaño de bloque de Hamming (CRC manda 0 y lo ignora al recibir)
 +--------- algoritmo usado
```

Los tres campos de metadata quedan **FUERA del cálculo de integridad y fuera del
ruido**. El header es el mismo para los dos algoritmos aunque CRC no use el campo
de bloque: así hay un solo parser y el despachador no necesita saber qué forma de
header trae cada algoritmo.

El header lo arma el `main`, no la capa de transmisión. `enviarInformacion` recibe
una línea ya hecha y no sabe qué algoritmo se usó.
 
El receptor responde por la **misma conexión**, también terminado en `\n`:
 
| Respuesta | Significado |
|---|---|
| `ACK\|<json>` | trama recibida sin errores, más lo que contesta el banco |
| `ACK\|CORREGIDO\|<json>` | hubo error, se corrigió (Hamming), más la respuesta |
| `NAK` | error detectado, mensaje descartado (CRC), sin respuesta |

El `<json>` es la respuesta del servidor bancario (`login_ok`, `withdraw_ok`,
etc.), la misma que ya mandaba el `server.py` del laboratorio anterior. Va
después del prefijo y **no se parte por `|`**: el JSON puede traer ese carácter
adentro, así que el emisor compara por prefijo y se queda con todo el resto.

La respuesta del banco viaja en texto plano, sin capas. Solo baja por las capas
lo que manda el cajero; de regreso, el `ACK`/`NAK` ya es el veredicto de
integridad del receptor. **El flujo de capas es de ida**, no hay pila inversa.

Las operaciones que el cajero manda son las del laboratorio anterior más una:

| `action` | Qué hace el receptor | Qué contesta |
|---|---|---|
| `login` | valida tarjeta y PIN | `ACK\|{...}` |
| `withdraw` | descuenta del saldo | `ACK\|{...}` |
| `logout` | cierra la sesión | `ACK\|{...}` |
| `message` | **solo muestra el texto** | `ACK` pelado, sin JSON |

`message` lleva el texto en `data.text` y existe para ver el recorrido completo
de un mensaje cualquiera por las capas. Como no necesita respuesta del banco, el
receptor contesta `ACK` sin payload y el cajero solo reporta si se envió o si se
descartó.

El emisor mantiene **una sola conexión** durante toda la sesión del cajero, no
una por mensaje: el banco necesita recordar quién inició sesión. Por eso el
framing importa de verdad — varias tramas viajan por la misma conexión.
 
## Trampas conocidas
 
Estas ya nos costaron tiempo. Respetarlas.
 
### Framing obligatorio
 
TCP es un flujo de bytes y **no preserva los límites de los mensajes**. Dos
tramas enviadas seguidas pueden llegar pegadas en un solo `recv()`, o una sola
trama puede llegar partida en pedazos. Si se le calcula el CRC a media trama, el
receptor va a reportar "error detectado" aunque el algoritmo esté perfecto.
 
Solución: cada trama termina en `\n`, y el receptor acumula en un buffer hasta
encontrarlo. Nunca asumir que un `recv()` equivale a un mensaje.
 
```python
buffer += datos.decode()
while "\n" in buffer:
    trama, _, buffer = buffer.partition("\n")
    procesar(trama)
```
 
### El emisor NO cierra la conexión al enviar
 
Como ahora hay respuesta ACK/NAK, el emisor debe esperar antes de cerrar. Nada de
un `conn.Close()` inmediatamente después del `Write()`; el `defer conn.Close()`
va en `enviarInformacion` y se ejecuta hasta que la función termina de leer.

En Go la lectura es bloqueante, así que esperar la respuesta es directo y el
framing sale gratis:

```go
respuesta, err := bufio.NewReader(conn).ReadString('\n')
```
 
### El ruido es por bit, no por trama

`p` es la probabilidad **independiente de cada bit** de voltearse, no la
probabilidad de que la trama traiga algún error. `aplicarRuido` recorre la trama
posición por posición y en cada una decide. Con `p = 0.01` y una trama de 200
bits se esperan ~2 bits dañados, no un 1% de tramas dañadas.

La diferencia no es cosmética: es lo que hace que Hamming se vea bien con `p`
chica y empiece a romper tramas conforme `p` sube, que es justo la gráfica 3.

### El relleno de Hamming necesita que viaje la longitud

Si el mensaje no es múltiplo del tamaño de bloque, `hammingEncode` rellena el
último bloque con ceros. Un mensaje de 8 bits con bloques de 32 lleva 24 bits de
relleno. El receptor no tiene forma de distinguir relleno de datos, así que sin
la longitud real devolvería caracteres fantasma al final del mensaje.

Por eso la longitud viaja en el header, y `hamming_decode` recorta a esos bits
antes de devolver. El relleno sí participa en la codificación y sí recibe ruido,
igual que cualquier otro bit de la trama.

### CRC-32 tiene variantes incompatibles
 
Existen varias recetas del mismo algoritmo (con o sin reflexión de bits, `init` en
ceros o en `0xFFFFFFFF`, XOR final). Si Go usa una y Python otra, los residuos
nunca van a coincidir aunque ambas implementaciones estén "bien".
 
Vector de prueba obligatorio antes de integrar nada:
 
```
entrada: "123456789"
CRC-32 (IEEE, reflejado): 0xCBF43926
```
 
Ambas implementaciones deben dar ese valor. En Go se declara `crc` como `uint32`
y los corrimientos se comportan como uno espera. (Este fue uno de los motivos
para elegir Go sobre JavaScript: en JS los operadores bit a bit convierten a
entero de 32 bits **con signo**, y hay que acordarse de `>>>` en vez de `>>` y de
cerrar con `>>> 0`, o el resultado sale negativo.)

De paso, Go trae `hash/crc32` en la stdlib. No se usa en la implementación —hay
que escribir el algoritmo a mano— pero sirve como oráculo para contrastar.
 
### Hamming clásico casi nunca puede mandar NAK
 
Con distancia mínima 3, cualquier síndrome distinto de cero se interpreta como un
error de 1 bit y se "corrige", aunque en realidad hayan sido 2. El algoritmo no
tiene forma de saber que se equivocó, así que entrega datos corruptos con `ACK`.
Esto es esperado, no es un bug: es el falso negativo que hay que medir.
 
(Opcional: Hamming extendido / SECDED agrega un bit de paridad global, sube la
distancia a 4 y sí permite distinguir "corregí uno" de "hay dos, no puedo".)
 
### Tamaño de bloque de Hamming es parámetro, no constante
 
El enunciado pide variar el **overhead** en las pruebas. En CRC-32 el overhead es
fijo (32 bits siempre), así que la única forma de variarlo es cambiando el tamaño
de bloque de Hamming. Debe ser un argumento con default, nunca hardcodeado.
 
Fórmula de bits de paridad: el mínimo `r` tal que `m + r + 1 <= 2^r`.
 
```python
def calcular_r(m):
    r = 1
    while (m + r + 1) > 2 ** r:
        r += 1
    return r
```
 
Default: bloques de 4 bits, o sea Hamming(7,4). Se eligió porque es el más
robusto de los alineados con ASCII (4 divide a 8, sin padding), es un código
perfecto (usa exactamente los 8 síndromes disponibles) y es verificable a mano
contra la tabla de síndromes del libro.
 
## Estructura de archivos
 
```
emisor/                      (Go, package main)
  go.mod                     module emisor
  main.go                    flujo de 5 lineas
  aplicacion.go
  presentacion.go
  enlace.go                  despachador
  ruido.go
  transmision.go             SOCKET cliente
  algoritmos/                (package algoritmos)
    hamming.go
    crc32.go
 
receptor/                    (Python)
  main.py                    flujo de 4 capas
  transmision.py             SOCKET servidor
  enlace.py                  despachador
  presentacion.py
  aplicacion.py              el banco
  test_receptor.py           python3 -m unittest
  algoritmos/
    hamming.py
    crc32.py
 
pruebas/                     (Python, SIN sockets)
  algoritmos_emisor.py       encode en Python, solo para simular
  simulacion.py
  graficas.py
  resultados/
```
 
## Pruebas y gráficas
 
**El script de pruebas NO usa sockets.** Importa las funciones directamente y
corre todo en memoria. Se necesitan miles de repeticiones por combinación y abrir
miles de conexiones TCP sería lentísimo y frágil.
 
Esto implica tener también el lado *encode* en Python (en `pruebas/`), aunque la
aplicación real lo tenga en Go. No es desperdicio: sirve además para verificar que
las dos implementaciones de CRC-32 coinciden entre lenguajes.
 
Variables a barrer:
 
| Variable | Valores |
|---|---|
| Algoritmo | Hamming, CRC-32 |
| Tamaño del mensaje | 8, 16, 32, 64, 128, 256 bits |
| Probabilidad de error | 0.0001, 0.001, 0.01, 0.05, 0.1 |
| Tamaño de bloque (Hamming) | 4, 8, 16, 32 |
| Repeticiones | 1000 por combinación |
 
Métricas a contar en cada corrida:
 
- `ok`: llegó limpia
- `corregido`: hubo error y se reparó bien
- `detectado`: se detectó y se rechazó (NAK)
- `falso_negativo`: **llegó corrupta y el algoritmo dijo que estaba bien**
El falso negativo es la métrica más importante del laboratorio y casi nadie la
reporta. Se detecta comparando los bits recuperados contra los originales, no
confiando en el estado que devuelve el algoritmo.
 
Gráficas mínimas:
 
1. Tasa de éxito vs probabilidad de error (eje X logarítmico, una curva por algoritmo)
2. Overhead vs tamaño del mensaje
3. Hamming: correcciones exitosas vs correcciones erróneas conforme sube `p`
4. Falsos negativos por algoritmo
La 3 es la más valiosa: muestra el punto donde Hamming empieza a empeorar las
tramas en lugar de repararlas.
 
## Cómo se corre
 
Dos terminales, **siempre el receptor primero**:
 
```bash
# terminal 1
python receptor/main.py
 
# terminal 2
cd emisor && go run .
```

Los tests de Go se corren con `go test ./...` desde `emisor/`.
 
Si se arranca el emisor primero: `ConnectionRefusedError` (no hay nadie
escuchando). Si sale `Address already in use`, quedó un proceso viejo pegado al
puerto; el `SO_REUSEADDR` ya está en el código.
 
## Instrucciones de trabajo
 
- **Un paso a la vez.** No generar el proyecto completo de una sola pasada.
- **Los algoritmos primero, con tests unitarios**, antes de tocar sockets.
  Depurar Hamming y sockets al mismo tiempo es una pesadilla.
- El socket se prueba por separado mandando un `"hola"` pelado, sin capas
  encima, hasta verlo llegar a la otra terminal.
- **No romper la separación de capas** por conveniencia. Si una función necesita
  saber el puerto y el algoritmo al mismo tiempo, algo se hizo mal.
- Código y comentarios en español.
- Sin dependencias externas para la lógica (`net` en Go y `socket` en Python son
  de la stdlib). Solo `matplotlib` y `numpy` para las gráficas. El `go.mod` del
  emisor no debe tener ni un `require`.
- Preguntar antes de asumir. Si algo del enunciado es ambiguo, mejor consultarlo
  que inventar una interpretación.
## Reparto del trabajo
 
| | Ricardo | Compañera |
|---|---|---|
| Algoritmo | CRC-32 (en Go y en Python) | Hamming (en Go y en Python) |
| Andamiaje | capas del emisor | capas del receptor |
 
## Evaluación
 
| Rubro | Peso |
|---|---|
| Implementación de la arquitectura | 20% |
| Algoritmo de detección + comunicación con el receptor | 30% |
| Reporte: formato | 5% |
| Reporte: pruebas | 15% |
| Reporte: discusión | 20% |
| Reporte: conclusiones | 10% |
 
El reporte vale la mitad de la nota. El código sin reporte reprueba.