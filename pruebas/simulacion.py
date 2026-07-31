"""Barrido de parametros sobre el canal ruidoso. Escribe resultados/metricas.csv

SIN SOCKETS: importa las funciones directamente y corre todo en memoria. Se
necesitan miles de repeticiones por combinacion, y abrir miles de conexiones TCP
seria lentisimo y fragil.

Uso:
    python3 simulacion.py                 # 1000 repeticiones por combinacion
    python3 simulacion.py 200             # mas rapido, para probar
"""

import csv
import os
import random
import sys
from time import perf_counter

# El verify se importa del receptor de verdad, no se reimplementa: asi la
# simulacion mide el mismo codigo que corre en produccion.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "receptor"))

from algoritmos.crc32 import crc32_verify  # noqa: E402

from algoritmos_emisor import crc32_encode  # noqa: E402

# --- parametros del barrido -------------------------------------------------

TAMANOS = [8, 16, 32, 64, 128, 256]          # bits de mensaje
PROBABILIDADES = [0.0001, 0.001, 0.01, 0.05, 0.1]
BLOQUES_HAMMING = [4, 8, 16, 32]
REPETICIONES = 1000
SEMILLA = 20260731  # fija: el barrido es reproducible

SALIDA = os.path.join(os.path.dirname(__file__), "resultados", "metricas.csv")

COLUMNAS = [
    "algoritmo", "tam_bloque", "bits_mensaje", "p", "repeticiones",
    "ok", "corregido", "detectado", "falso_negativo",
    "bits_trama", "overhead", "us_encode", "us_verify",
]


def mensaje_aleatorio(azar, bits):
    return "".join(azar.choice("01") for _ in range(bits))


def aplicar_ruido(azar, trama, p):
    """Voltea cada bit con probabilidad p, de forma independiente.

    Mismo modelo que ruido.go: p es POR BIT, no por trama. El ruido cae sobre
    la trama completa, bits de redundancia incluidos.
    """
    return "".join(
        ("1" if bit == "0" else "0") if azar.random() < p else bit
        for bit in trama
    )


def clasificar(estado, recuperados, originales):
    """Clasifica una corrida.

    El falso negativo NO se detecta preguntandole al algoritmo, porque el
    algoritmo cree que le fue bien. Se detecta comparando los bits recuperados
    contra los originales. Es la metrica mas importante del laboratorio.
    """
    if estado == "error":
        return "detectado"

    if recuperados != originales:
        return "falso_negativo"

    return "corregido" if estado == "corregido" else "ok"


def correr(algoritmo, bits_mensaje, p, tam_bloque, repeticiones):
    """Corre una combinacion y devuelve su fila de metricas."""
    # La semilla se arma como string, NO con hash(): Python aleatoriza el hash
    # de los strings en cada proceso, asi que hash() daria una semilla distinta
    # en cada corrida y el barrido no seria reproducible. random.Random() si
    # acepta un string y lo deriva de forma determinista.
    azar = random.Random(f"{SEMILLA}|{algoritmo}|{bits_mensaje}|{p}|{tam_bloque}")

    conteo = {"ok": 0, "corregido": 0, "detectado": 0, "falso_negativo": 0}
    total_encode = 0.0
    total_verify = 0.0
    bits_trama = 0

    for _ in range(repeticiones):
        mensaje = mensaje_aleatorio(azar, bits_mensaje)

        inicio = perf_counter()
        trama = codificar(algoritmo, mensaje, tam_bloque)
        total_encode += perf_counter() - inicio

        bits_trama = len(trama)
        sucia = aplicar_ruido(azar, trama, p)

        inicio = perf_counter()
        recuperados, estado = verificar(algoritmo, sucia, tam_bloque, bits_mensaje)
        total_verify += perf_counter() - inicio

        conteo[clasificar(estado, recuperados, mensaje)] += 1

    return {
        "algoritmo": algoritmo,
        "tam_bloque": tam_bloque,
        "bits_mensaje": bits_mensaje,
        "p": p,
        "repeticiones": repeticiones,
        **conteo,
        "bits_trama": bits_trama,
        "overhead": round((bits_trama - bits_mensaje) / bits_mensaje, 4),
        "us_encode": round(total_encode / repeticiones * 1e6, 3),
        "us_verify": round(total_verify / repeticiones * 1e6, 3),
    }


def codificar(algoritmo, mensaje, tam_bloque):
    if algoritmo == "CRC":
        return crc32_encode(mensaje)
    from algoritmos_emisor import hamming_encode
    return hamming_encode(mensaje, tam_bloque)


def verificar(algoritmo, trama, tam_bloque, longitud):
    if algoritmo == "CRC":
        return crc32_verify(trama)
    from algoritmos.hamming import hamming_decode
    return hamming_decode(trama, tam_bloque, longitud)


def combinaciones():
    """Todas las combinaciones del barrido.

    CRC-32 no tiene tamano de bloque (su overhead es fijo en 32 bits), asi que
    se corre una sola vez por (tamano, p). Hamming se corre por cada bloque.
    """
    for bits_mensaje in TAMANOS:
        for p in PROBABILIDADES:
            yield ("CRC", bits_mensaje, p, 0)

            for bloque in BLOQUES_HAMMING:
                yield ("HAM", bits_mensaje, p, bloque)


def main():
    repeticiones = int(sys.argv[1]) if len(sys.argv) > 1 else REPETICIONES

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)

    filas = []
    saltadas = 0
    todas = list(combinaciones())

    print(f"{len(todas)} combinaciones x {repeticiones} repeticiones")

    for i, (algoritmo, bits_mensaje, p, bloque) in enumerate(todas, 1):
        etiqueta = f"{algoritmo:3} bloque={bloque:<2} mensaje={bits_mensaje:<3} p={p}"

        try:
            fila = correr(algoritmo, bits_mensaje, p, bloque, repeticiones)
        except NotImplementedError:
            saltadas += 1
            continue

        filas.append(fila)
        print(f"  [{i:3}/{len(todas)}] {etiqueta}  "
              f"ok={fila['ok']:<4} corr={fila['corregido']:<4} "
              f"det={fila['detectado']:<4} FN={fila['falso_negativo']}")

    with open(SALIDA, "w", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(filas)

    print(f"\n{len(filas)} filas escritas en {SALIDA}")

    if saltadas:
        # No se puede reportar "cobertura completa" si media tabla no corrio.
        print(f"ATENCION: {saltadas} combinaciones saltadas porque Hamming "
              f"todavia no esta implementado.")


if __name__ == "__main__":
    main()
