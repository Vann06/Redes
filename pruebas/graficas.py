"""Genera las graficas del reporte a partir de resultados/metricas.csv

Uso:
    python3 simulacion.py      # primero, para producir el CSV
    python3 graficas.py        # despues

Requiere matplotlib. Si no esta:
    pip install --user matplotlib
"""

import csv
import os
import sys
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use("Agg")  # sin ventana, solo archivos
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit("Falta matplotlib.  Instalalo con:  pip install --user matplotlib")

AQUI = os.path.dirname(os.path.abspath(__file__))
ENTRADA = os.path.join(AQUI, "resultados", "metricas.csv")
SALIDA = os.path.join(AQUI, "resultados")

# Tamano de mensaje y bloque que usan las graficas que fijan uno solo.
TAMANO_REFERENCIA = 64
BLOQUE_REFERENCIA = 4  # Hamming(7,4), el default

# Paleta categorica en orden FIJO. Nunca se cicla ni se reasigna: cada serie
# conserva su color aunque desaparezcan otras de la grafica.
#
# Validada para daltonismo: peor par adyacente delta-E 9.1 (protan), piso de
# vision normal 19.6. Tres de los colores quedan por debajo de 3:1 de contraste
# contra el fondo, asi que ademas de color cada serie lleva un marcador distinto
# y los datos crudos quedan en metricas.csv.
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
MARCADORES = ["o", "s", "^", "D", "v"]

TINTA = "#0b0b0b"
TINTA_SUAVE = "#52514e"
REJILLA = "#d8d7d2"


def configurar_estilo():
    plt.rcParams.update({
        "figure.figsize": (8, 5),
        "figure.dpi": 150,
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": REJILLA,
        "axes.labelcolor": TINTA_SUAVE,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlecolor": TINTA,
        "axes.grid": True,
        "axes.axisbelow": True,          # la rejilla va DETRAS de los datos
        "grid.color": REJILLA,
        "grid.linewidth": 0.6,
        "text.color": TINTA,
        "xtick.color": TINTA_SUAVE,
        "ytick.color": TINTA_SUAVE,
        "legend.frameon": False,
        "lines.linewidth": 2,
        "lines.markersize": 6,
    })


def limpiar(ejes):
    """Quita el marco de arriba y de la derecha: menos tinta, mismo dato."""
    ejes.spines["top"].set_visible(False)
    ejes.spines["right"].set_visible(False)


def titular(ejes, titulo, subtitulo):
    """Titulo y subtitulo alineados a la izquierda, sin encimarse."""
    ejes.set_title(titulo, loc="left", pad=30)
    ejes.text(0.0, 1.02, subtitulo, transform=ejes.transAxes,
              color=TINTA_SUAVE, fontsize=9, va="bottom")


def nota_algoritmos(filas):
    """Que algoritmos hay en los datos, para dejarlo dicho en cada grafica.

    Se lee del CSV en vez de escribirlo a mano: cuando entre Hamming, la nota
    cambia sola y ninguna grafica queda diciendo algo que ya no es cierto.
    """
    algoritmos = {fila["algoritmo"] for fila in filas}

    if algoritmos == {"CRC"}:
        return "algoritmo: CRC-32 (Hamming pendiente)"
    if algoritmos == {"HAM"}:
        return "algoritmo: Hamming"
    return "algoritmos: CRC-32 y Hamming"


def leer():
    if not os.path.exists(ENTRADA):
        sys.exit(f"No existe {ENTRADA}.  Corre primero:  python3 simulacion.py")

    with open(ENTRADA) as archivo:
        filas = list(csv.DictReader(archivo))

    for fila in filas:
        for columna in ("tam_bloque", "bits_mensaje", "repeticiones",
                        "ok", "corregido", "detectado", "falso_negativo", "bits_trama"):
            fila[columna] = int(fila[columna])
        for columna in ("p", "overhead", "us_encode", "us_verify"):
            fila[columna] = float(fila[columna])

    return filas


def nombre_serie(fila):
    """CRC no tiene tamano de bloque; Hamming se distingue por el suyo."""
    if fila["algoritmo"] == "CRC":
        return "CRC-32"
    return f"Hamming (bloque {fila['tam_bloque']})"


def series_ordenadas(filas):
    """Orden fijo de series, para que el color no dependa de los datos."""
    orden = ["CRC-32"] + [f"Hamming (bloque {b})" for b in (4, 8, 16, 32)]
    presentes = {nombre_serie(fila) for fila in filas}
    return [nombre for nombre in orden if nombre in presentes]


def estilo_de(nombre, filas):
    """Color y marcador segun la posicion FIJA de la serie, no su rango."""
    orden = ["CRC-32"] + [f"Hamming (bloque {b})" for b in (4, 8, 16, 32)]
    i = orden.index(nombre)
    return PALETA[i % len(PALETA)], MARCADORES[i % len(MARCADORES)]


def guardar(figura, archivo):
    ruta = os.path.join(SALIDA, archivo)
    figura.savefig(ruta, bbox_inches="tight")
    plt.close(figura)
    print(f"  {ruta}")


# --- 1. Tasa de exito vs probabilidad de error ------------------------------

def grafica_exito(filas):
    datos = [f for f in filas if f["bits_mensaje"] == TAMANO_REFERENCIA]
    if not datos:
        return

    figura, ejes = plt.subplots()
    limpiar(ejes)

    por_serie = defaultdict(list)
    for fila in datos:
        por_serie[nombre_serie(fila)].append(fila)

    nombres = series_ordenadas(datos)
    for nombre in nombres:
        puntos = sorted(por_serie[nombre], key=lambda f: f["p"])
        color, marcador = estilo_de(nombre, datos)

        x = [f["p"] for f in puntos]
        y = [100 * (f["ok"] + f["corregido"]) / f["repeticiones"] for f in puntos]

        ejes.plot(x, y, color=color, marker=marcador, label=nombre)

        # Etiqueta directa cuando hay pocas series: identidad sin depender
        # solo del color.
        if len(nombres) <= 4:
            ejes.annotate(nombre, (x[-1], y[-1]), textcoords="offset points",
                          xytext=(8, 0), color=color, fontsize=9,
                          va="center", fontweight="bold")

    ejes.set_xscale("log")
    ejes.set_xlabel("Probabilidad de error por bit")
    ejes.set_ylabel("Mensajes entregados correctamente (%)")
    ejes.set_ylim(-2, 102)
    titular(ejes, "Tasa de exito vs ruido del canal",
            f"{nota_algoritmos(datos)} · mensajes de {TAMANO_REFERENCIA} bits, "
            f"{datos[0]['repeticiones']} repeticiones por punto")

    if len(nombres) > 1:
        ejes.legend(loc="lower left")

    guardar(figura, "1_exito_vs_ruido.png")


# --- 2. Overhead vs tamano del mensaje --------------------------------------

def grafica_overhead(filas):
    figura, ejes = plt.subplots()
    limpiar(ejes)

    por_serie = defaultdict(dict)
    for fila in filas:
        por_serie[nombre_serie(fila)][fila["bits_mensaje"]] = fila["overhead"]

    nombres = series_ordenadas(filas)
    for nombre in nombres:
        tamanos = sorted(por_serie[nombre])
        color, marcador = estilo_de(nombre, filas)

        y = [100 * por_serie[nombre][t] for t in tamanos]
        ejes.plot(tamanos, y, color=color, marker=marcador, label=nombre)

        if len(nombres) <= 4:
            ejes.annotate(nombre, (tamanos[-1], y[-1]), textcoords="offset points",
                          xytext=(8, 0), color=color, fontsize=9,
                          va="center", fontweight="bold")

    ejes.set_xscale("log", base=2)
    ejes.set_xticks(sorted({f["bits_mensaje"] for f in filas}))
    ejes.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ejes.set_xlabel("Tamano del mensaje (bits)")
    ejes.set_ylabel("Bits de redundancia sobre el mensaje (%)")
    titular(ejes, "Overhead vs tamano del mensaje",
            f"{nota_algoritmos(filas)} · CRC-32 agrega 32 bits fijos, asi que "
            f"su costo relativo cae conforme crece el mensaje")

    if len(nombres) > 1:
        ejes.legend()

    guardar(figura, "2_overhead.png")


# --- 3. Hamming: correcciones buenas vs malas -------------------------------

def grafica_correcciones(filas):
    # Se fija UN tamano de bloque. Sin esto, los cuatro bloques caerian sobre
    # la misma x y la linea saldria en zigzag.
    datos = [f for f in filas
             if f["algoritmo"] == "HAM"
             and f["bits_mensaje"] == TAMANO_REFERENCIA
             and f["tam_bloque"] == BLOQUE_REFERENCIA]

    if not datos:
        print("  (3 saltada: no hay datos de Hamming todavia)")
        return

    figura, ejes = plt.subplots()
    limpiar(ejes)

    puntos = sorted(datos, key=lambda f: f["p"])
    x = [f["p"] for f in puntos]

    ejes.plot(x, [f["corregido"] for f in puntos], color=PALETA[2], marker="^",
              label="Corregido bien")
    ejes.plot(x, [f["falso_negativo"] for f in puntos], color=PALETA[1], marker="s",
              label="Corregido MAL (falso negativo)")

    ejes.set_xscale("log")
    ejes.set_xlabel("Probabilidad de error por bit")
    ejes.set_ylabel(f"Tramas (de {puntos[0]['repeticiones']} por punto)")
    titular(ejes, "Hamming: donde deja de reparar y empieza a arruinar",
            f"mensajes de {TAMANO_REFERENCIA} bits, bloque {BLOQUE_REFERENCIA}; "
            f"el cruce marca donde empeora las tramas en vez de repararlas")
    ejes.legend()

    guardar(figura, "3_hamming_correcciones.png")


# --- 4. Falsos negativos por algoritmo --------------------------------------

def grafica_falsos_negativos(filas):
    por_serie = defaultdict(lambda: [0, 0])
    for fila in filas:
        por_serie[nombre_serie(fila)][0] += fila["falso_negativo"]
        por_serie[nombre_serie(fila)][1] += fila["repeticiones"]

    nombres = series_ordenadas(filas)
    alturas = [por_serie[n][0] for n in nombres]

    # Un solo numero no es una grafica. Si nadie tuvo falsos negativos, un
    # grafico de barras es un lienzo vacio con un "0" perdido abajo; se reporta
    # como cifra destacada, que es lo que de verdad se quiere leer.
    if max(alturas, default=0) == 0:
        grafica_falsos_negativos_cero(nombres, por_serie, nota_algoritmos(filas))
        return

    figura, ejes = plt.subplots()
    limpiar(ejes)
    ejes.grid(axis="x", visible=False)

    colores = [estilo_de(n, filas)[0] for n in nombres]

    # Los nombres completos se enciman en el eje X; se parten en dos lineas.
    etiquetas = [n.replace(" (bloque ", "\nbloque ").rstrip(")") for n in nombres]
    barras = ejes.bar(etiquetas, alturas, color=colores, width=0.55)

    # Etiqueta directa sobre cada barra: el numero exacto importa mas que la
    # altura relativa cuando las magnitudes son tan distintas.
    for barra, altura in zip(barras, alturas):
        ejes.annotate(f"{altura}", (barra.get_x() + barra.get_width() / 2, altura),
                      textcoords="offset points", xytext=(0, 4),
                      ha="center", color=TINTA, fontweight="bold")

    total = por_serie[nombres[0]][1]
    ejes.set_ylabel("Tramas corruptas aceptadas como buenas")
    ejes.set_ylim(0, max(alturas) * 1.25)
    titular(ejes, "Falsos negativos por algoritmo",
            f"{nota_algoritmos(filas)} · {total} corridas por algoritmo; se "
            f"cuenta comparando los bits recuperados contra los originales")

    guardar(figura, "4_falsos_negativos.png")


def grafica_falsos_negativos_cero(nombres, por_serie, nota):
    """Cifra destacada para el caso en que ningun algoritmo fallo callado."""
    figura, ejes = plt.subplots(figsize=(8, 3.6))
    ejes.axis("off")

    detalle = " · ".join(f"{n}: {por_serie[n][1]} corridas" for n in nombres)

    ejes.text(0.5, 0.92, "Falsos negativos", ha="center", va="center",
              fontsize=13, fontweight="bold", color=TINTA)
    ejes.text(0.5, 0.78, nota, ha="center", va="center", fontsize=9,
              color=TINTA_SUAVE)
    ejes.text(0.5, 0.48, "0", ha="center", va="center", fontsize=68,
              fontweight="bold", color=PALETA[0])
    ejes.text(0.5, 0.20, "ninguna trama corrupta paso como buena", ha="center",
              va="center", fontsize=11, color=TINTA)
    ejes.text(0.5, 0.05, detalle, ha="center", va="center", fontsize=9,
              color=TINTA_SUAVE)

    guardar(figura, "4_falsos_negativos.png")


# --- 5. Tiempo de verificacion ----------------------------------------------

def grafica_tiempos(filas):
    figura, ejes = plt.subplots()
    limpiar(ejes)

    por_serie = defaultdict(lambda: defaultdict(list))
    for fila in filas:
        por_serie[nombre_serie(fila)][fila["bits_mensaje"]].append(fila["us_verify"])

    nombres = series_ordenadas(filas)
    for nombre in nombres:
        tamanos = sorted(por_serie[nombre])
        color, marcador = estilo_de(nombre, filas)

        y = [sum(por_serie[nombre][t]) / len(por_serie[nombre][t]) for t in tamanos]
        ejes.plot(tamanos, y, color=color, marker=marcador, label=nombre)

        if len(nombres) <= 4:
            ejes.annotate(nombre, (tamanos[-1], y[-1]), textcoords="offset points",
                          xytext=(8, 0), color=color, fontsize=9,
                          va="center", fontweight="bold")

    ejes.set_xscale("log", base=2)
    ejes.set_xticks(sorted({f["bits_mensaje"] for f in filas}))
    ejes.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ejes.set_xlabel("Tamano del mensaje (bits)")
    ejes.set_ylabel("Tiempo de verificacion (microsegundos)")
    titular(ejes, "Costo de verificar la integridad",
            f"{nota_algoritmos(filas)} · promedio por trama, implementacion "
            f"en Python")

    if len(nombres) > 1:
        ejes.legend()

    guardar(figura, "5_tiempo_verificacion.png")


def main():
    configurar_estilo()
    filas = leer()

    print(f"{len(filas)} filas leidas de {ENTRADA}")
    print("Graficas:")

    grafica_exito(filas)
    grafica_overhead(filas)
    grafica_correcciones(filas)
    grafica_falsos_negativos(filas)
    grafica_tiempos(filas)

    algoritmos = {f["algoritmo"] for f in filas}
    if "HAM" not in algoritmos:
        print("\nATENCION: solo hay datos de CRC-32. Las curvas de Hamming "
              "aparecen cuando el algoritmo este implementado.")


if __name__ == "__main__":
    main()
