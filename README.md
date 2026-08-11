# Laboratorio 3 - Protocolos de Enrutamiento

Simulación de una red de routers que aprende rutas con **Link State** y calcula rutas mínimas con **Dijkstra**. El plano de control está implementado; el plano de datos queda deliberadamente asignado a Ricardo en [docs/ricardo.md](docs/ricardo.md).

## Qué se resuelve

El sistema tiene dos planos independientes que corren en paralelo dentro de cada router:

| Plano | Responsabilidad |
| --- | --- |
| Control | HELLO, detección de vecinos, LSA, flooding, LSDB, Dijkstra y tablas CSV. |
| Datos | Hamming, TTL/hops, consulta de CSV y reenvío. **Pendiente - Ricardo.** |

Los endpoints externos `ATM` y `BANK` no son routers. Cada uno usa un router como gateway: ATM usa A y BANK usa E. Esto evita confundirlos con los routers A-I de la topología.

## Requisitos

- Python 3.10 o superior.
- Para pruebas distribuidas: Tailscale instalado y los seis integrantes en la misma red privada.

## Inicio rápido local

Abra nueve terminales desde la raíz del repositorio y ejecute un router en cada una:

```powershell
python src/main.py A
python src/main.py B
python src/main.py C
python src/main.py D
python src/main.py E
python src/main.py F
python src/main.py G
python src/main.py H
python src/main.py I
```

Espere unos segundos. Cada router creará su tabla en `runtime/<nodo>_tabla_enrutamiento.csv`.

Detenga cada proceso con `Ctrl+C`. Cuando Ricardo complete el plano de datos, añadirá aquí los comandos de ATM/BANK y el modo Hamming.

## Comprobar que la red convergió

Abra, por ejemplo, `runtime/A_tabla_enrutamiento.csv`. La ruta de A a E debe comenzar por I y tener costo 8:

```csv
destino,siguiente_salto,costo,ip,puerto
E,I,8,127.0.0.1,6009
```

Para probar convergencia ante una caída, termine el proceso de un router. Pasados 15 segundos, sus vecinos lo eliminan de sus LSAs y regeneran las tablas. Al levantarlo de nuevo, los HELLO lo reactivan.

## Configuración para Tailscale

Edite únicamente [config/topologia.json](config/topologia.json):

1. Sustituya las IP `127.0.0.1` de cada router por la IP Tailscale de quien ejecute ese router.
2. Mantenga los nombres A-I, puertos y costos acordados por las tres parejas.
3. Actualice también las IP de `ATM` y `BANK`.
4. Compartan el mismo archivo de configuración entre los seis integrantes antes de probar.

Cada pareja solo debe levantar los routers que le asignen. El archivo puede listar toda la topología: cada router necesita conocer las direcciones de sus vecinos para poder enviarles HELLO y LSA, pero empieza con conocimiento local de sus propios vecinos.

## Protocolo de interoperabilidad

La especificación completa está en [docs/protocolo.md](docs/protocolo.md). Resumen:

- Toda trama termina en `\n`.
- `J|` contiene JSON UTF-8; se usa siempre en HELLO y LSA.
- `H|` contiene los bits de Hamming(7,4) del JSON UTF-8; se usa solo en mensajes de datos cuando la red ya estabilizó.
- Un LSA solo se acepta si trae un `seq` mayor que la versión conocida para ese `origin`.
- El TTL limita el flooding y `hops` evita ciclos de datos.

## Archivos principales

| Archivo | Contenido | Responsable inicial |
| --- | --- | --- |
| `src/router.py` | Control Link State, LSDB, persistencia de seq y CSV. | Vianka |
| `src/dijkstra.py` | Rutas más cortas y siguiente salto. | Vianka |
| `src/transporte.py` | Servidor TCP por líneas y envío de tramas. | Vianka |
| `src/hamming.py` | Debe ser creado: codificación y corrección Hamming(7,4). | Ricardo |
| `src/protocolo.py` | JSON de control listo; completar soporte `H|`. | Ricardo |
| `src/forwarding.py` | Esqueleto; implementar reenvío de datos usando CSV. | Ricardo |
| `src/atm_cliente.py`, `src/banco_servidor.py` | Deben ser creados como extremos no-router. | Ricardo |

La responsabilidad no impide revisar o integrar en pareja: cualquier cambio al formato de trama o `topologia.json` debe acordarse antes entre ambos y con las otras parejas.

## Pruebas

Por ahora las pruebas cubren Dijkstra. Ricardo agregará las pruebas de Hamming, framing y forwarding:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Antes de entregar, repitan las pruebas locales y al menos una ejecución entre las tres parejas mediante Tailscale. Documenten resultados, rutas observadas, fallos simulados y conclusiones en el reporte.
