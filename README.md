# Laboratorio 2 - Esquemas de detección y corrección de errores

Proyecto del curso **CC3067 Redes** de la Universidad del Valle de Guatemala.

## Integrantes

- Vianka - 23201
- Ricardo - 23247

## Descripción

Este proyecto simula la comunicación entre un **cajero automático** y el **servidor de una entidad bancaria** a través de un canal no confiable.

La solución utiliza una arquitectura por capas para:

1. Solicitar y mostrar mensajes.
2. Codificar texto a binario.
3. Agregar y verificar información de integridad.
4. Aplicar ruido a la trama.
5. Transmitir información mediante sockets TCP.
6. Detectar errores con CRC-32.
7. Corregir errores mediante código de Hamming.

El emisor y el receptor están desarrollados en lenguajes distintos, conforme a los requisitos del laboratorio:

- **Emisor o cajero automático:** Go.
- **Receptor o servidor bancario:** Python.

## Arquitectura

### Emisor

El mensaje baja por las siguientes capas:

```text
Aplicación
    ↓
Presentación
    ↓
Enlace
    ↓
Ruido
    ↓
Transmisión TCP
```

### Receptor

La trama recibida sube por las siguientes capas:

```text
Transmisión TCP
    ↓
Enlace
    ↓
Presentación
    ↓
Aplicación
```

## Servicios por capa

### Aplicación

- Solicitar los datos de la operación.
- Solicitar el algoritmo de integridad.
- Solicitar la probabilidad de error por bit.
- Mostrar el resultado de la transmisión.
- Simular operaciones de inicio de sesión, retiro, envío de mensaje y cierre de sesión.

### Presentación

- Codificar texto UTF-8 como una cadena de bits.
- Decodificar los bits recibidos nuevamente a texto.

### Enlace

- Calcular información de integridad.
- Verificar la integridad de la trama.
- Corregir errores cuando el algoritmo lo permita.
- Generar respuestas `ACK`, `ACK|CORREGIDO` o `NAK`.

### Ruido

- Recorrer la trama completa.
- Voltear cada bit de forma independiente según la probabilidad indicada.
- Aplicar ruido tanto a los datos como a los bits de redundancia.

### Transmisión

- Enviar y recibir tramas mediante sockets TCP.
- Mantener la conexión durante la sesión del cajero.
- Utilizar `\n` como delimitador de cada trama.
- Mantener al receptor escuchando en el puerto configurado.

## Algoritmos

### CRC-32

Algoritmo de detección de errores implementado con la variante IEEE reflejada:

- Polinomio reflejado: `0xEDB88320`.
- Valor inicial: `0xFFFFFFFF`.
- XOR final: `0xFFFFFFFF`.
- Overhead fijo: 32 bits.
- Vector de comprobación:

```text
Entrada: 123456789
CRC-32 esperado: CBF43926
```

### Código de Hamming

Algoritmo de corrección de errores por bloques.

Para un bloque de `m` bits de datos se calcula el menor número `r` de bits de paridad que cumpla:

```text
m + r + 1 <= 2^r
```

Tamaños de bloque previstos:

- 4 bits.
- 8 bits.
- 16 bits.
- 32 bits.

El tamaño predeterminado es 4, correspondiente a Hamming(7,4).

## Formato de la trama

El emisor transmite una línea de texto con el siguiente formato:

```text
ALGORITMO|TAMAÑO_BLOQUE|LONGITUD_ORIGINAL|TRAMA
```

Ejemplos:

```text
CRC|0|8|01000001...
HAM|4|8|0100110...
```

Los campos de metadata no reciben ruido. El ruido se aplica únicamente a la trama con sus datos y redundancia.

## Respuestas del receptor

| Respuesta | Significado |
|---|---|
| `ACK` | La trama se recibió correctamente y no hay respuesta adicional. |
| `ACK|<json>` | La trama se recibió correctamente y el banco respondió. |
| `ACK|CORREGIDO` | El receptor corrigió un error y no hay respuesta adicional. |
| `ACK|CORREGIDO|<json>` | El receptor corrigió un error y el banco respondió. |
| `NAK` | Se detectó un error que no pudo corregirse. |

## Estructura del repositorio

```text
.
├── emisor/
│   ├── algoritmos/
│   │   ├── crc32.go
│   │   └── hamming.go
│   ├── aplicacion.go
│   ├── enlace.go
│   ├── main.go
│   ├── presentacion.go
│   ├── ruido.go
│   ├── transmision.go
│   └── go.mod
├── receptor/
│   ├── algoritmos/
│   │   ├── crc32.py
│   │   └── hamming.py
│   ├── aplicacion.py
│   ├── enlace.py
│   ├── main.py
│   ├── presentacion.py
│   ├── transmision.py
│   └── test_receptor.py
├── pruebas/
│   ├── algoritmos_emisor.py
│   ├── simulacion.py
│   ├── graficas.py
│   ├── test_pruebas.py
│   └── resultados/
├── Makefile
├── instrucciones.md
└── README.md
```

> Los archivos `hamming.go` y `hamming.py` deben existir al completar la implementación del algoritmo de corrección.

## Requisitos

- Go 1.21 o superior.
- Python 3.
- `matplotlib` para generar las gráficas.

Instalación de la dependencia para gráficas:

```bash
python3 -m pip install matplotlib
```

En Windows también puede utilizarse:

```powershell
py -m pip install matplotlib
```

## Ejecución

Deben abrirse dos terminales y ejecutar primero el receptor.

### 1. Iniciar el receptor

Desde la raíz del repositorio:

```bash
python3 receptor/main.py
```

En Windows:

```powershell
py receptor/main.py
```

El receptor queda escuchando en:

```text
127.0.0.1:5000
```

### 2. Iniciar el emisor

En otra terminal:

```bash
cd emisor
go run .
```

## Pruebas

### Pruebas del emisor en Go

```bash
cd emisor
go test ./...
```

### Pruebas del receptor en Python

```bash
cd receptor
python3 -m unittest -v
```

En Windows:

```powershell
cd receptor
py -m unittest -v
```

### Pruebas del simulador

```bash
cd pruebas
python3 -m unittest -v
```

## Simulación y gráficas

El barrido experimental varía:

- Algoritmo.
- Tamaño del mensaje.
- Probabilidad de error por bit.
- Tamaño de bloque de Hamming.
- Overhead.
- Tiempo de codificación y verificación.

Para generar los resultados:

```bash
cd pruebas
python3 simulacion.py
python3 graficas.py
```

Para una prueba rápida con menos repeticiones:

```bash
python3 simulacion.py 200
python3 graficas.py
```

Los resultados se almacenan en:

```text
pruebas/resultados/
```

Las gráficas:

1. Tasa de éxito frente a probabilidad de error.
2. Overhead frente a tamaño del mensaje.
3. Correcciones correctas e incorrectas de Hamming.
4. Falsos negativos por algoritmo.
5. Tiempo de verificación.


## Consideraciones

- El receptor debe iniciarse antes que el emisor.
- La probabilidad de error se solicita para cada mensaje.
- El ruido debe aplicarse también a los bits de redundancia.
- CRC-32 detecta errores, pero no los corrige.
- Hamming puede corregir un error por bloque; varios errores en el mismo bloque pueden producir una corrección incorrecta.
- Los resultados experimentales deben compararse con los bits originales para identificar falsos negativos.
