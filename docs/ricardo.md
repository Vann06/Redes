# Plano de datos y endpoints (asignado a Ricardo) - completado

## Objetivo

Completar la comunicación `ATM -> router gateway -> red -> router gateway -> BANK` y el camino de regreso. Los routers generan sus CSV y llaman a:

```python
Reenviador(nombre, topologia, directorio_tablas).procesar(mensaje, usa_hamming)
```

al recibir un mensaje cuyo `type` es `message`.

## Archivos y tareas

### 1. `src/comun/hamming.py` - hecho

Hamming(7,4) de paridad par, portado y adaptado del Lab2 (`receptor/algoritmos/hamming.py` + `pruebas/algoritmos_emisor.py`, ambos con `tam_bloque=4`).

- `codificar_nibble("d1d2d3d4")` produce `p1 p2 d1 p3 d2 d3 d4`.
- `codificar_bytes(datos)` convierte cada byte UTF-8 a dos nibbles (el más significativo primero) y produce 14 bits por byte.
- `decodificar_bits(bits)` calcula el síndrome por bloque de 7, corrige un error por bloque y devuelve `(datos, correcciones)`.
- Pruebas en `tests/test_hamming.py`.

### 2. `src/comun/protocolo.py` - hecho

El funcionamiento de `J|` no cambió.

- `crear_trama(mensaje, con_hamming=True)` devuelve `H|<bits>`.
- `leer_trama("H|...")` devuelve `(mensaje, True, correcciones)`.
- Mantiene la validación de JSON y los errores de tramas corruptas (`ValueError`).
- HELLO y LSA siguen siendo `J|` siempre.
- Pruebas en `tests/test_protocolo.py`.

### 3. `src/datos/forwarding.py` - hecho

`Reenviador.procesar`:

1. Valida `to`, `ttl` y `hops`; el `payload` no se inspecciona. Descarta sobres mal formados.
2. Descarta si el router ya está en `hops` (ciclo) o si TTL llegó a 0.
3. Resuelve el siguiente salto: si `to` es un router, consulta `runtime/<nodo>_tabla_enrutamiento.csv`; si `to` es un endpoint (`ATM`/`BANK`), entrega directo si soy su gateway, o enruta hacia el gateway si no.
4. Resta uno a TTL y agrega el router actual a `hops`.
5. Reenvía conservando si entró como `J|` o `H|`.

Pruebas en `tests/test_forwarding.py` (reenvío entre routers, entrega a endpoint, ciclo, TTL agotado, sobre mal formado, sin ruta).

### 4. `src/endpoints/atm_cliente.py` y `src/endpoints/banco_servidor.py` - hecho

- ATM: menú interactivo (login con reintento, retirar dinero, enviar mensaje libre, salir), estilo del `emisor` del Lab2. Escucha su propia IP/puerto para recibir respuestas asíncronas (cada envío es una conexión de una sola línea, la respuesta llega como un mensaje independiente). Flag `--hamming` para usar framing `H|`.
- BANK: cuentas de prueba y lógica de login/retiro/logout portadas de `receptor/aplicacion.py` del Lab2, adaptadas a sesión en memoria por remitente (no hay conexión persistente). Responde por su gateway preservando si la solicitud llegó como `J|` o `H|`.
- Ninguno de los dos se agrega al grafo de routers A-I.

**Nota:** existe un protocolo conjunto acordado con las otras dos parejas (`docs/protocolo_conjunto.md`) que difiere de lo de arriba en el framing (sin prefijos `J|`/`H|`) y en el payload (`op` en vez de `action`/`data`). Ese documento es solo referencia por ahora — migrar el código a ese formato es trabajo pendiente, no se ha tocado la implementación todavía.

## Bug encontrado y corregido en el plano de control

Al probar el flujo completo end-to-end (9 routers + BANK + ATM como procesos reales) se detectó que la red no siempre convergía a la ruta óptima: `router.py` solo reemitía el LSA propio cuando cambiaba la lista de vecinos activos, y `_inundar` manda cada copia por una conexión TCP nueva sin reintentos. Si una sola copia se perdía en tránsito (esperable con varios routers arrancando y floodeando casi al mismo tiempo), esa pérdida era permanente porque nada la volvía a mandar.

Se agregó un refresco periódico del LSA propio cada 20 segundos (`Router._ciclo_lsa`, igual que el refresco periódico de OSPF real), para que la red se autorepare sin depender de que cambie algún vecino.

## Pruebas

- `tests/test_hamming.py`: UTF-8 sin error y bits alterados que se corrigen (uno y varios bloques).
- `tests/test_protocolo.py`: round-trip con `J|` y `H|`, HELLO/LSA siguen en `J|`.
- `tests/test_forwarding.py`: reenvío entre routers, entrega directa a endpoint, reenvío hacia el gateway de un endpoint, y descartes (ciclo, TTL agotado, sobre mal formado, sin ruta) sin lanzar excepciones.

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## Criterios de terminado

1. ✅ La red ya convergida entrega `login`/`withdraw` y retorna una respuesta al ATM (verificado end-to-end con los 9 routers + BANK + ATM como procesos reales).
2. ✅ Un retiro con `--hamming` llega al BANK y se recibe una respuesta.
3. ✅ Un único bit alterado se reporta como corregido (`tests/test_hamming.py`, `tests/test_protocolo.py`).
4. ✅ TTL y ciclos se descartan sin detener ningún router (`tests/test_forwarding.py`).
5. ✅ Todos los tests pasan (27/27).
