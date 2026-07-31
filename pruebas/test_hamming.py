"""Pruebas de Hamming dentro del arnés de simulación.

Ejecutar desde la carpeta pruebas:

    python3 -m unittest -v
"""

import unittest

from algoritmos_emisor import (
    calcular_r,
    hamming_encode,
)
from simulacion import (
    correr,
    verificar,
)


def voltear(trama, posicion):
    bits = list(trama)

    bits[posicion] = (
        "1"
        if bits[posicion] == "0"
        else "0"
    )

    return "".join(bits)


class TestHammingEmisorSimulacion(unittest.TestCase):
    def test_vector_hamming_74(self):
        self.assertEqual(
            hamming_encode("1011", 4),
            "0110011",
        )

    def test_calcular_r(self):
        self.assertEqual(
            [calcular_r(m) for m in (4, 8, 16, 32)],
            [3, 4, 5, 6],
        )

    def test_forma_de_la_trama(self):
        casos = (
            (4, 8, 14),
            (8, 8, 12),
            (16, 8, 21),
            (32, 8, 38),
        )

        bits = "10110010"

        for tam_bloque, longitud, esperado in casos:
            with self.subTest(
                tam_bloque=tam_bloque
            ):
                trama = hamming_encode(
                    bits[:longitud],
                    tam_bloque,
                )

                self.assertEqual(
                    len(trama),
                    esperado,
                )

                self.assertEqual(
                    trama.strip("01"),
                    "",
                )

    def test_receptor_acepta_trama_limpia(self):
        originales = "10110010"

        for tam_bloque in (4, 8, 16, 32):
            with self.subTest(
                tam_bloque=tam_bloque
            ):
                trama = hamming_encode(
                    originales,
                    tam_bloque,
                )

                recuperados, estado = verificar(
                    "HAM",
                    trama,
                    tam_bloque,
                    len(originales),
                )

                self.assertEqual(
                    recuperados,
                    originales,
                )
                self.assertEqual(
                    estado,
                    "ok",
                )

    def test_corrige_cualquier_bit(self):
        originales = "10110010"
        trama = hamming_encode(
            originales,
            4,
        )

        for posicion in range(len(trama)):
            with self.subTest(posicion=posicion):
                danada = voltear(
                    trama,
                    posicion,
                )

                recuperados, estado = verificar(
                    "HAM",
                    danada,
                    4,
                    len(originales),
                )

                self.assertEqual(
                    recuperados,
                    originales,
                )
                self.assertEqual(
                    estado,
                    "corregido",
                )

    def test_padding_se_elimina(self):
        originales = "10110"
        trama = hamming_encode(
            originales,
            4,
        )

        recuperados, estado = verificar(
            "HAM",
            trama,
            4,
            len(originales),
        )

        self.assertEqual(
            recuperados,
            originales,
        )
        self.assertEqual(
            estado,
            "ok",
        )

    def test_sin_ruido_todo_llega(self):
        for tam_bloque in (4, 8, 16, 32):
            with self.subTest(
                tam_bloque=tam_bloque
            ):
                fila = correr(
                    "HAM",
                    bits_mensaje=64,
                    p=0.0,
                    tam_bloque=tam_bloque,
                    repeticiones=100,
                )

                self.assertEqual(
                    fila["ok"],
                    100,
                )
                self.assertEqual(
                    fila["corregido"],
                    0,
                )
                self.assertEqual(
                    fila["detectado"],
                    0,
                )
                self.assertEqual(
                    fila["falso_negativo"],
                    0,
                )

    def test_overhead_por_tamano_de_bloque(self):
        esperados = {
            4: {
                "bits_trama": 112,
                "overhead": 0.75,
            },
            8: {
                "bits_trama": 96,
                "overhead": 0.50,
            },
            16: {
                "bits_trama": 84,
                "overhead": 0.3125,
            },
            32: {
                "bits_trama": 76,
                "overhead": 0.1875,
            },
        }

        for tam_bloque, esperado in esperados.items():
            with self.subTest(
                tam_bloque=tam_bloque
            ):
                fila = correr(
                    "HAM",
                    bits_mensaje=64,
                    p=0.0,
                    tam_bloque=tam_bloque,
                    repeticiones=5,
                )

                self.assertEqual(
                    fila["bits_trama"],
                    esperado["bits_trama"],
                )

                self.assertAlmostEqual(
                    fila["overhead"],
                    esperado["overhead"],
                    places=4,
                )

    def test_conteos_suman_repeticiones(self):
        fila = correr(
            "HAM",
            bits_mensaje=64,
            p=0.01,
            tam_bloque=4,
            repeticiones=200,
        )

        total = (
            fila["ok"]
            + fila["corregido"]
            + fila["detectado"]
            + fila["falso_negativo"]
        )

        self.assertEqual(total, 200)

    def test_rechaza_entradas_invalidas(self):
        with self.assertRaises(ValueError):
            hamming_encode("101x", 4)

        with self.assertRaises(ValueError):
            hamming_encode("1011", 0)


if __name__ == "__main__":
    unittest.main()