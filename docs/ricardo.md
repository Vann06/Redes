# Trabajo asignado a Ric

## Objetivo

Completar la comunicación `ATM -> router gateway -> red -> router gateway -> BANK` y el camino de regreso. Los routers ya generan sus CSV y llaman a:

```python
Reenviador(nombre, topologia, directorio_tablas).procesar(mensaje, usa_hamming)
```

al recibir un mensaje cuyo `type` es `message`.

## Archivos y tareas

### 1. `src/hamming.py` - crear

Implementar Hamming(7,4) de paridad par.

- `codificar_nibble("d1d2d3d4")` debe producir `p1 p2 d1 p3 d2 d3 d4`.
- Convertir el JSON UTF-8 a bytes y cada byte a dos nibbles, primero el más significativo.
- Cada byte debe producir 14 bits.
- Al decodificar, calcular el síndrome y corregir un error de un bit por bloque de 7.
- Devolver los bytes reconstruidos y cuántos bits fueron corregidos.

### 2. `src/protocolo.py` - completar

No modificar el funcionamiento actual de `J|`, porque lo usa el plano de control de Vianka.

- Implementar `crear_trama(mensaje, con_hamming=True)` para devolver `H|<bits>`.
- Implementar `leer_trama("H|...")` para devolver `(mensaje, True, correcciones)`.
- Mantener la validación de JSON y los errores de tramas corruptas.
- HELLO y LSA deben seguir siendo `J|`, incluso si el plano de datos ya usa Hamming.

### 3. `src/forwarding.py` - reemplazar el esqueleto

Implementar `Reenviador.procesar`:

1. Validar `to`, `ttl` y `hops`; el `payload` no se inspecciona.
2. Descartar si el router ya está en `hops` o si TTL llegó a 0.
3. Restar uno a TTL y agregar el router actual a `hops`.
4. Leer `runtime/<nodo>_tabla_enrutamiento.csv` y obtener IP/puerto del siguiente salto.
5. Si `to` es un endpoint (`ATM` o `BANK`), enrutar hacia su gateway; el gateway debe entregar al endpoint configurado.
6. Reenviar conservando si entró como `J|` o `H|`.

### 4. `src/atm_cliente.py` y `src/banco_servidor.py` - crear

- ATM se conecta al gateway definido en `endpoints.ATM` y envía `auth`, `withdraw` y `logout`.
- BANK escucha en el puerto definido en `endpoints.BANK`, procesa las operaciones y responde a ATM por su gateway.
- ATM y BANK **no** son routers y no deben agregarse al grafo A-I.

## Pruebas que debe agregar

Crear al menos:

- `tests/test_hamming.py`: UTF-8 sin error y un bit alterado que se corrige.
- `tests/test_protocolo.py`: round-trip con `J|` y `H|`.
- `tests/test_forwarding.py` o una prueba de integración: ATM llega a BANK con Hamming por `A -> I -> D -> E`.

El comando debe pasar desde la raíz:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## Criterios de terminado

1. La red ya convergida entrega `auth` y retorna una respuesta al ATM.
2. Un retiro con `--hamming` llega al BANK y se recibe una respuesta.
3. Un único bit alterado se reporta como corregido.
4. TTL y ciclos se descartan sin detener ningún router.
5. Todos los tests pasan y Ricardo crea su commit con un mensaje como `feat: implementar plano de datos y hamming`.
