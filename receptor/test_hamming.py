"""Pruebas unitarias del decodificador Hamming.

Ejecutar desde la carpeta receptor con:

    python3 -m unittest -v
"""

import unittest

from algoritmos.hamming import (
    calcular_r,
    hamming_decode,
)
from enlace import verificar_integridad


def voltear(trama, posicion):
    """Voltea un bit de la trama."""
    bits = list(trama)

    bits[posicion] = (
        "1"
        if bits[posicion] == "0"
        else "0"
    )

    return "".join(bits)


def codificar_para_prueba(bits, tam_bloque):
    """Codificador auxiliar utilizado únicamente por las pruebas."""
    r = calcular_r(tam_bloque)
    n = tam_bloque + r

    relleno = (
        tam_bloque - len(bits) % tam_bloque
    ) % tam_bloque

    bits = bits + ("0" * relleno)
    salida = []

    for inicio in range(0, len(bits), tam_bloque):
        datos = bits[inicio:inicio + tam_bloque]
        bloque = ["0"] * n
        indice_dato = 0

        for posicion in range(1, n + 1):
            es_paridad = (
                posicion > 0
                and (
                    posicion
                    & (posicion - 1)
                ) == 0
            )

            if not es_paridad:
                bloque[posicion - 1] = (
                    datos[indice_dato]
                )
                indice_dato += 1

        posicion_paridad = 1

        while posicion_paridad <= n:
            paridad = 0

            for posicion in range(1, n + 1):
                if (
                    posicion & posicion_paridad
                    and bloque[posicion - 1] == "1"
                ):
                    paridad ^= 1

            bloque[posicion_paridad - 1] = str(
                paridad
            )

            posicion_paridad <<= 1

        salida.extend(bloque)

    return "".join(salida)


class TestCalcularR(unittest.TestCase):
    def test_valores_esperados(self):
        self.assertEqual(calcular_r(4), 3)
        self.assertEqual(calcular_r(8), 4)
        self.assertEqual(calcular_r(16), 5)
        self.assertEqual(calcular_r(32), 6)

    def test_es_el_valor_minimo(self):
        for m in range(1, 65):
            r = calcular_r(m)

            self.assertLessEqual(
                m + r + 1,
                2 ** r,
            )

            self.assertGreater(
                m + (r - 1) + 1,
                2 ** (r - 1),
            )

    def test_rechaza_tamanos_invalidos(self):
        for valor in (0, -1, 1.5, True):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    calcular_r(valor)


class TestHammingDecode(unittest.TestCase):
    def test_vector_hamming_74(self):
        bits, estado = hamming_decode(
            "0110011",
            tam_bloque=4,
            longitud=4,
        )

        self.assertEqual(bits, "1011")
        self.assertEqual(estado, "ok")

    def test_corrige_cualquier_bit_del_bloque(self):
        trama = "0110011"

        for posicion in range(len(trama)):
            with self.subTest(posicion=posicion):
                danada = voltear(
                    trama,
                    posicion,
                )

                bits, estado = hamming_decode(
                    danada,
                    tam_bloque=4,
                    longitud=4,
                )

                self.assertEqual(bits, "1011")
                self.assertEqual(
                    estado,
                    "corregido",
                )

    def test_corrige_bits_en_varios_bloques(self):
        originales = "10110010"
        trama = codificar_para_prueba(
            originales,
            4,
        )

        for posicion in range(len(trama)):
            with self.subTest(posicion=posicion):
                danada = voltear(
                    trama,
                    posicion,
                )

                bits, estado = hamming_decode(
                    danada,
                    tam_bloque=4,
                    longitud=len(originales),
                )

                self.assertEqual(
                    bits,
                    originales,
                )
                self.assertEqual(
                    estado,
                    "corregido",
                )

    def test_retirar_relleno(self):
        originales = "10110"
        trama = codificar_para_prueba(
            originales,
            4,
        )

        bits, estado = hamming_decode(
            trama,
            tam_bloque=4,
            longitud=len(originales),
        )

        self.assertEqual(bits, originales)
        self.assertEqual(estado, "ok")

    def test_varios_tamanos_de_bloque(self):
        originales = "1011001010110101"

        for tam_bloque in (4, 8, 16, 32):
            with self.subTest(
                tam_bloque=tam_bloque
            ):
                trama = codificar_para_prueba(
                    originales,
                    tam_bloque,
                )

                bits, estado = hamming_decode(
                    trama,
                    tam_bloque=tam_bloque,
                    longitud=len(originales),
                )

                self.assertEqual(
                    bits,
                    originales,
                )
                self.assertEqual(
                    estado,
                    "ok",
                )

    def test_mensaje_vacio(self):
        self.assertEqual(
            hamming_decode(
                "",
                tam_bloque=4,
                longitud=0,
            ),
            ("", "ok"),
        )

    def test_rechaza_tramas_invalidas(self):
        casos = (
            "01100x1",
            "011001",
            "abc",
        )

        for trama in casos:
            with self.subTest(trama=trama):
                bits, estado = hamming_decode(
                    trama,
                    tam_bloque=4,
                    longitud=4,
                )

                self.assertEqual(bits, "")
                self.assertEqual(
                    estado,
                    "error",
                )

    def test_longitud_mayor_a_datos_recuperados(self):
        bits, estado = hamming_decode(
            "0110011",
            tam_bloque=4,
            longitud=20,
        )

        self.assertEqual(bits, "")
        self.assertEqual(estado, "error")


class TestIntegracionEnlace(unittest.TestCase):
    def test_despachador_hamming(self):
        bits, estado = verificar_integridad(
            "0110011",
            "HAM",
            4,
            4,
        )

        self.assertEqual(bits, "1011")
        self.assertEqual(estado, "ok")

    def test_despachador_hamming_corrige(self):
        trama_danada = voltear(
            "0110011",
            3,
        )

        bits, estado = verificar_integridad(
            trama_danada,
            "HAM",
            4,
            4,
        )

        self.assertEqual(bits, "1011")
        self.assertEqual(
            estado,
            "corregido",
        )


if __name__ == "__main__":
    unittest.main()