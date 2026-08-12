# Protocolo conjunto — acordado con las tres parejas

Este es el protocolo tal como se acordó entre las tres parejas de la topología (seis integrantes), para que las implementaciones de cada quien interoperen por Tailscale. Es el documento de referencia para el wire format real. `docs/protocolo.md` es la versión interna/de trabajo de esta pareja y no se modifica — este archivo es la fuente de verdad para lo que se comparte con los demás grupos.

## 1. Formato de trama

Todos los mensajes son JSON. El plano de control (HELLO y LSA) viaja como una línea de texto UTF-8 terminada en `\n`, sin ninguna marca extra, mientras las tablas de ruteo se construyen.

El plano de datos (mensajes entre el ATM y el banco) va **siempre** codificado con Hamming(7,4): como todos los nodos lo saben, cada uno decodifica Hamming, obtiene los bits de datos ya sin redundancia y de ahí reconstruye el JSON, sin necesidad de ninguna marca extra tampoco.

Un campo que no se reconoce se ignora, no se descarta la trama por eso.

## 2. Paquete HELLO

```json
{ "proto": "LinkState", "type": "HELLO", "from": "A", "ttl": 1 }
```

Descubre vecinos y confirma que siguen vivos. Se manda cada cinco segundos y se da por caído al vecino a los quince, momento en el que se emite un LSA propio con el `seq` aumentado y sin ese enlace. El `ttl` vale uno porque un HELLO nunca se reenvía. Los costos no se miden, se leen de la topología compartida y son simétricos.

## 3. Paquete LSA y flooding

```json
{ "proto": "LinkState", "type": "LSA", "origin": "A", "seq": 3,
  "links": { "B": 7, "I": 1, "C": 7 }, "from": "A", "ttl": 8 }
```

- `origin`: nodo dueño del anuncio, no cambia nunca.
- `seq`: número de secuencia creciente que identifica la versión.
- `links`: vecinos del origen con su costo, como objeto y no como lista.
- `from`: vecino que lo reenvió, sí cambia en cada salto.
- `ttl`: arranca en ocho.

Un nodo que se reinicia no vuelve a numerar desde cero: arranca en el último valor conocido más uno.

## 4. Manejo de ciclos

El ciclo se corta con el número de secuencia. Cada nodo guarda el mayor `seq` visto de cada origen, descarta sin reenviar el LSA que trae uno menor o igual, y si trae uno mayor lo guarda, actualiza el grafo y lo reenvía a todos los vecinos menos al que se lo mandó. Como respaldo se resta uno al `ttl` antes de reenviar y se descarta en cero, lo que cubre al nodo que reinicia con un `seq` bajo.

Los mensajes de datos no llevan `seq`; ahí se usa el `ttl` propio y la lista `hops`, y si un nodo se encuentra a sí mismo en `hops` descarta por bucle de ruteo.

Con el grafo completo cada nodo corre Dijkstra y escribe su tabla.

## 5. Sobre de datos, ATM y servidor bancario

```json
{ "type": "message", "from": "A", "to": "E", "ttl": 16, "hops": ["A"], "payload": {...} }
```

- Autenticación: `{ ..., "payload": { "op": "auth", "user": "...", "pin": "..." } }`
- Retiro: `{ ..., "payload": { "op": "withdraw", "amount": 500 } }`
- Error: `{ ..., "payload": { "op": "error", "code": "...", "msg": "..." } }`
- Logout: `{ ..., "payload": { "op": "logout" } }`

El `from` es el nodo del ATM y el `to` el del servidor bancario; ninguno es router y cada uno se conecta por sockets a su puerta de enlace. La capa de red solo lee `to`; el `payload` es el JSON del laboratorio 2 sin cambios, que ningún router abre. La operación va en `op` para no chocar con el `type` del sobre.

El sobre completo se codifica siempre con Hamming(7,4) antes de mandarlo por el socket: se pasa el JSON a bytes UTF-8, se parte cada byte en dos nibbles desde el más significativo, y por cada nibble `d1 d2 d3 d4` se produce el bloque `p1 p2 d1 p3 d2 d3 d4` con paridad par — catorce bits exactos por byte. El nodo que recibe decodifica Hamming, recupera los bytes de datos y con ellos reconstruye el JSON.

## 6. Costos de enlace

```
A-B 7   A-I 1   A-C 7   B-F 2   I-D 6   C-D 5
F-D 1   F-H 4   F-G 3   D-E 1   E-G 4
```

## Puntos aclarados con el resto del grupo (no estaban explícitos en el texto de arriba)

- **Identidad de ATM/BANK**: aunque el ejemplo del sobre usa letras de router (`"from":"A","to":"E"`), se confirmó que ATM y BANK se identifican con su propio nombre (`"ATM"`/`"BANK"`), no con la letra de su gateway. Cada uno se conecta a su gateway por sockets, y el router gateway resuelve la entrega.
- **Formato de las respuestas exitosas**: el texto acordado solo define el `payload` de `auth`/`withdraw`/`logout`/`error` (las peticiones del ATM y el caso de error). El formato de una respuesta exitosa del banco (`auth_ok`, `withdraw_ok`, `logout_ok`) **no está acordado entre las tres parejas** — es una convención propia de esta implementación, ver `docs/protocolo.md` y `src/endpoints/banco_servidor.py`. Si al conectar con las otras parejas por Tailscale sus bancos esperan otro formato de éxito, hay que negociarlo antes de la prueba conjunta.

## Estado de esta implementación frente al protocolo conjunto

| Punto | Estado |
| --- | --- |
| Framing sin prefijos (control JSON plano, datos siempre Hamming) | ✅ implementado en `src/comun/protocolo.py` |
| HELLO / LSA / manejo de ciclos con seq y ttl | ✅ ya coincidía, sin cambios |
| Sobre de datos (`type`, `from`, `to`, `ttl`, `hops`, `payload`) | ✅ ya coincidía |
| Payload con `op` (auth/withdraw/logout/error) | ✅ implementado en `src/endpoints/atm_cliente.py` y `banco_servidor.py` |
| Costos de enlace | ✅ ya coincidían exactos en `config/topologia.json` |
| IPs reales de Tailscale en `config/topologia.json` | ⏳ pendiente hasta tener el mapeo real de quién corre qué router |
