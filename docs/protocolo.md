# Protocolo de interoperabilidad - Laboratorio 3

Este documento es el contrato que deben compartir las tres parejas antes de ejecutar pruebas por Tailscale. Un campo adicional desconocido se ignora; una trama mal formada se descarta sin detener el proceso.

## 1. Framing

Una trama es una línea UTF-8 terminada en `\n`.

| Prefijo | Contenido | Uso |
| --- | --- | --- |
| `J|` | Objeto JSON UTF-8 directo. | Control y datos antes de converger. |
| `H|` | Cadena de `0`/`1`, Hamming(7,4) del JSON UTF-8. | Solo plano de datos después de converger. |

Los routers deben aceptar los dos prefijos. HELLO y LSA siempre deben transmitirse como `J|`.

## 2. HELLO

```json
{"proto":"LinkState","type":"HELLO","from":"A","ttl":1}
```

Se transmite a cada vecino configurado cada 5 segundos. No se reenvía. Si no llega un HELLO de un vecino durante 15 segundos, se considera caído. Cuando vuelva a llegar, el enlace se considera recuperado.

## 3. LSA y flooding

```json
{"proto":"LinkState","type":"LSA","origin":"A","seq":3,"links":{"B":7,"I":1,"C":7},"from":"A","ttl":8}
```

- `origin`: router dueño del anuncio; nunca cambia en tránsito.
- `seq`: entero creciente por origin. Debe sobrevivir reinicios; se persiste localmente.
- `links`: vecinos activos del origin y costo del enlace.
- `from`: vecino que lo envió en este salto; se actualiza al reenviar.
- `ttl`: inicia en 8 y se decrementa antes de cada reenvío.

Un router guarda el mayor `seq` de cada origin. Si el nuevo `seq` es menor o igual, descarta el LSA. Si es mayor, actualiza la LSDB, recalcula Dijkstra y reenvía a los vecinos activos excepto a `from` mientras TTL sea positivo.

## 4. Tabla de enrutamiento

Después de actualizar su LSDB, cada router crea `runtime/<nodo>_tabla_enrutamiento.csv`:

```csv
destino,siguiente_salto,costo,ip,puerto
E,I,8,100.64.0.9,6009
```

`ip` y `puerto` siempre pertenecen al **siguiente salto**, no al destino final.

## 5. Sobre de datos

```json
{
  "type":"message",
  "from":"ATM",
  "to":"BANK",
  "ttl":16,
  "hops":["ATM"],
  "payload":{"op":"auth","user":"usuario","pin":"1234"}
}
```

Los routers solo inspeccionan `to`, `ttl` y `hops`. No deben interpretar ni modificar `payload`.

Al recibir un dato, un router:

1. Corrige Hamming si el prefijo es `H|`.
2. Descarta si ya aparece en `hops` o si TTL es 0.
3. Reduce TTL y agrega su identificador a `hops`.
4. Busca el destino en su CSV y transmite la misma clase de trama al siguiente salto.
5. Si es el gateway del endpoint destino, entrega la trama al endpoint.

## 6. Hamming(7,4)

Cada byte UTF-8 se divide en dos nibbles, empezando por el nibble más significativo. Para cada `d1 d2 d3 d4` se genera:

```text
p1 p2 d1 p3 d2 d3 d4
```

Se usa paridad par; por lo tanto, cada byte se convierte en 14 bits. El receptor calcula el síndrome y corrige un bit por bloque de 7 antes de reconstruir el JSON.

## 7. Endpoints

`ATM` y `BANK` son procesos externos y no pertenecen al grafo A-I. Cada endpoint tiene un gateway en `topologia.json`. La respuesta del banco es otro sobre de datos dirigido a ATM y se enruta de vuelta por la red.
