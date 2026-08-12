# Laboratorio 3 - Protocolos de Enrutamiento

Simulación de una red de routers que aprende rutas con **Link State** y calcula rutas mínimas con **Dijkstra**. El plano de control y el plano de datos están implementados, incluyendo los procesos ATM y BANK.

## Qué se resuelve

El sistema tiene dos planos independientes que corren en paralelo dentro de cada router:

| Plano | Responsabilidad |
| --- | --- |
| Control | HELLO, detección de vecinos, LSA (con reemisión periódica), flooding, LSDB, Dijkstra y tablas CSV. |
| Datos | Hamming(7,4), TTL/hops, consulta de CSV y reenvío. |

Los endpoints externos `ATM` y `BANK` no son routers. Cada uno usa un router como gateway: ATM usa A y BANK usa E. Esto evita confundirlos con los routers A-I de la topología.

## Requisitos

- Python 3.10 o superior.
- Para pruebas distribuidas: Tailscale instalado y los seis integrantes en la misma red privada.

## Estructura del código

```
src/
  main.py           entry point de un router: python src/main.py <NOMBRE>
  comun/            compartido por control y datos
    configuracion.py, protocolo.py, transporte.py, hamming.py
  control/          plano de control (Link State)
    router.py, dijkstra.py
  datos/            plano de datos
    forwarding.py
  endpoints/        procesos no-router
    atm_cliente.py, banco_servidor.py
```

Todo el código importa con rutas de paquete (`comun.X`, `control.X`, `datos.X`). `main.py` corre sin nada especial porque vive en `src/`; los scripts de `endpoints/` agregan `src/` a `sys.path` automáticamente al iniciar, así que también se ejecutan directo sin configurar variables de entorno. Los tests sí necesitan `PYTHONPATH=src` (ver más abajo).

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

**Atajo:** en vez de abrir nueve terminales a mano, `scripts/levantar_red.sh` levanta los 9 routers en background (cada uno con su log en `logs/`) y espera la convergencia:

```bash
./scripts/levantar_red.sh                # los 9 routers
./scripts/levantar_red.sh --con-banco     # routers + banco_servidor.py
./scripts/levantar_red.sh A B C           # solo esos routers (para probar por partes)
./scripts/detener_red.sh                  # baja todo lo que levantó el script
```

El flooding y el cálculo de rutas son automáticos: no hay que "activarlos", pasan solos en cuanto dos o más routers están corriendo (ver `docs/guia_arquitectura.md` para el detalle de cómo).

Con la red arriba, en dos terminales adicionales:

```powershell
python src/endpoints/banco_servidor.py
python src/endpoints/atm_cliente.py
```

`atm_cliente.py` pide tarjeta y PIN (ver cuentas de prueba en `src/endpoints/banco_servidor.py`) y luego muestra un menú: retirar dinero, enviar un mensaje libre, o salir. Agregue `--hamming` para que el ATM mande sus mensajes de datos codificados con Hamming(7,4) (`H|`) en vez de JSON plano (`J|`):

```powershell
python src/endpoints/atm_cliente.py --hamming
```

Detenga cada proceso con `Ctrl+C`.

## Comprobar que la red convergió

Abra, por ejemplo, `runtime/A_tabla_enrutamiento.csv`. La ruta de A a E debe comenzar por I y tener costo 8:

```csv
destino,siguiente_salto,costo,ip,puerto
E,I,8,127.0.0.1,6009
```

Para probar convergencia ante una caída, termine el proceso de un router. Pasados 15 segundos, sus vecinos lo eliminan de sus LSAs y regeneran las tablas. Al levantarlo de nuevo, los HELLO lo reactivan. Además de reemitirse cuando cambian los vecinos, cada router repite su propio LSA cada 20 segundos (como el refresco periódico de OSPF), para que la red se autorepare si algún LSA se perdió en tránsito.

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

Hay además un protocolo conjunto acordado con las otras dos parejas de la topología, documentado por separado en [docs/protocolo_conjunto.md](docs/protocolo_conjunto.md) — todavía no está implementado en el código, es solo la referencia para cuando se migre.

## Archivos principales

| Archivo | Contenido |
| --- | --- |
| `src/control/router.py` | Control Link State, LSDB, persistencia de seq, reemisión periódica y CSV. |
| `src/control/dijkstra.py` | Rutas más cortas y siguiente salto. |
| `src/comun/transporte.py` | Servidor TCP por líneas y envío de tramas. |
| `src/comun/hamming.py` | Codificación y corrección Hamming(7,4). |
| `src/comun/protocolo.py` | Framing `J|` (control) y `H|` (datos, Hamming). |
| `src/datos/forwarding.py` | Reenvío de datos: TTL/hops, consulta de CSV, entrega a endpoints. |
| `src/endpoints/atm_cliente.py` | Cliente ATM (menú interactivo: login, retiro, mensaje). |
| `src/endpoints/banco_servidor.py` | Servidor BANK (cuentas de prueba, login/retiro/logout). |

## Pruebas

Las pruebas cubren Dijkstra, Hamming(7,4), el framing `J|`/`H|`, y el reenvío de datos (`forwarding`, incluyendo entrega a endpoints, ciclos, TTL agotado y sobres mal formados):

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Antes de entregar, repitan las pruebas locales y al menos una ejecución entre las tres parejas mediante Tailscale. Documenten resultados, rutas observadas, fallos simulados y conclusiones en el reporte.
