"""Tests del arnes de simulacion. Se corren con:  python3 -m unittest -v

Verifican las dos piezas que la simulacion NO le pide prestadas al receptor y
que, sin estos tests, nadie estaria comprobando:

  - crc32_encode, que es una copia en Python de lo que hace el emisor en Go.
    Una copia se puede desincronizar del original sin que nadie se entere, y
    las graficas seguirian saliendo igual de bonitas con numeros equivocados.
  - aplicar_ruido, que es el canal. Si tuviera un sesgo, TODAS las metricas
    estarian mal y no habria forma de notarlo mirando las graficas.

Tambien se prueba clasificar(), que es donde se decide que cuenta como falso
negativo: si esa funcion esta mal, la metrica mas importante del laboratorio
esta mal.
"""

import random
import unittest
import zlib

from algoritmos_emisor import calcular_r, calcular_crc, crc32_encode
from simulacion import aplicar_ruido, clasificar, correr

# La simulacion ya metio receptor/ en el path al importarla.
from algoritmos.crc32 import crc32_verify  # noqa: E402


def a_bits(datos):
    return "".join(f"{octeto:08b}" for octeto in datos)


class TestCRC32Emisor(unittest.TestCase):
    """La copia en Python tiene que dar lo mismo que el original en Go."""

    def test_vector_obligatorio(self):
        self.assertEqual(calcular_crc(b"123456789"), 0xCBF43926)

    def test_valores_conocidos(self):
        for entrada, esperado in [
            (b"", 0x00000000),
            (b"a", 0xE8B7BE43),
            (b"abc", 0x352441C2),
            (b"A", 0xD3D99E8B),  # el mismo que produjo el emisor en Go
        ]:
            with self.subTest(entrada=entrada):
                self.assertEqual(calcular_crc(entrada), esperado)

    def test_coincide_con_zlib(self):
        azar = random.Random(1)

        for _ in range(500):
            datos = bytes(azar.randrange(256) for _ in range(azar.randrange(64)))
            self.assertEqual(calcular_crc(datos), zlib.crc32(datos) & 0xFFFFFFFF)

    def test_el_receptor_acepta_lo_que_produce(self):
        """Cierra el circulo: encode de pruebas -> verify del receptor.

        Si estas dos se desincronizan, este test se cae.
        """
        azar = random.Random(2)

        for _ in range(200):
            datos = bytes(azar.randrange(256) for _ in range(1 + azar.randrange(32)))
            bits = a_bits(datos)

            self.assertEqual(crc32_verify(crc32_encode(bits)), (bits, "ok"))

    def test_forma_de_la_trama(self):
        bits = a_bits(b"hola")
        trama = crc32_encode(bits)

        self.assertEqual(len(trama), len(bits) + 32)
        self.assertTrue(trama.startswith(bits))
        self.assertEqual(trama.strip("01"), "")

    def test_rechaza_entradas_invalidas(self):
        for entrada in ["0100000", "0100000x"]:
            with self.subTest(entrada=entrada):
                with self.assertRaises(ValueError):
                    crc32_encode(entrada)

    def test_calcular_r(self):
        """r es el minimo tal que m + r + 1 <= 2**r."""
        self.assertEqual([calcular_r(m) for m in (4, 8, 16, 32)], [3, 4, 5, 6])

        for m in range(1, 65):
            r = calcular_r(m)
            self.assertLessEqual(m + r + 1, 2 ** r)
            self.assertGreater(m + (r - 1) + 1, 2 ** (r - 1))  # es el minimo


class TestRuido(unittest.TestCase):
    """El canal. Un sesgo aqui invalida todas las graficas."""

    def test_sin_ruido(self):
        trama = "01" * 100
        self.assertEqual(aplicar_ruido(random.Random(1), trama, 0), trama)

    def test_ruido_total(self):
        trama = "01" * 100
        sucia = aplicar_ruido(random.Random(1), trama, 1)

        self.assertEqual(len(sucia), len(trama))
        for i, (antes, despues) in enumerate(zip(trama, sucia)):
            self.assertNotEqual(antes, despues, f"el bit {i} no se volteo")

    def test_conserva_la_forma(self):
        trama = "01" * 500
        sucia = aplicar_ruido(random.Random(3), trama, 0.3)

        self.assertEqual(len(sucia), len(trama))
        self.assertEqual(sucia.strip("01"), "")

    def test_tasa_es_por_bit(self):
        """Con 10000 bits y p = 0.1 se esperan ~1000 volteados.

        Las cotas son anchas (mas de 6 sigma) para que no falle por azar.
        """
        trama = "01" * 5000
        sucia = aplicar_ruido(random.Random(4), trama, 0.1)

        volteados = sum(1 for a, b in zip(trama, sucia) if a != b)
        self.assertGreater(volteados, 800)
        self.assertLess(volteados, 1200)

    def test_el_ruido_cae_parejo(self):
        """Cazaria un bug donde solo se ensucia parte de la trama.

        Se parte en cuatro y cada cuarto debe recibir su parte del ruido.
        """
        trama = "01" * 5000
        sucia = aplicar_ruido(random.Random(5), trama, 0.1)

        for cuarto in range(4):
            inicio, fin = cuarto * 2500, (cuarto + 1) * 2500
            volteados = sum(1 for a, b in zip(trama[inicio:fin], sucia[inicio:fin])
                            if a != b)
            self.assertGreater(volteados, 180, f"cuarto {cuarto} con poco ruido")
            self.assertLess(volteados, 320, f"cuarto {cuarto} con mucho ruido")

    def test_es_reproducible(self):
        """Con la misma semilla, el mismo ruido. De eso depende que el barrido
        se pueda repetir y dar lo mismo."""
        trama = "01" * 500

        primera = aplicar_ruido(random.Random(7), trama, 0.1)
        segunda = aplicar_ruido(random.Random(7), trama, 0.1)

        self.assertEqual(primera, segunda)


class TestClasificar(unittest.TestCase):
    """Donde se decide que es un falso negativo."""

    def test_detectado(self):
        self.assertEqual(clasificar("error", "", "0101"), "detectado")

    def test_ok(self):
        self.assertEqual(clasificar("ok", "0101", "0101"), "ok")

    def test_corregido(self):
        self.assertEqual(clasificar("corregido", "0101", "0101"), "corregido")

    def test_falso_negativo_diciendo_ok(self):
        """El algoritmo dice que todo bien, pero los bits no son los mismos."""
        self.assertEqual(clasificar("ok", "0100", "0101"), "falso_negativo")

    def test_falso_negativo_diciendo_corregido(self):
        """Hamming "corrigio" y quedo peor. Este es el caso interesante."""
        self.assertEqual(clasificar("corregido", "0100", "0101"), "falso_negativo")


class TestCorrida(unittest.TestCase):
    """El arnes completo, sobre CRC-32."""

    def test_sin_ruido_todo_llega(self):
        fila = correr("CRC", 64, 0.0, 0, repeticiones=100)

        self.assertEqual(fila["ok"], 100)
        self.assertEqual(fila["detectado"], 0)
        self.assertEqual(fila["falso_negativo"], 0)

    def test_con_mucho_ruido_todo_se_detecta(self):
        fila = correr("CRC", 64, 0.3, 0, repeticiones=100)

        self.assertEqual(fila["detectado"], 100)
        self.assertEqual(fila["falso_negativo"], 0)

    def test_overhead_de_crc(self):
        """CRC-32 agrega 32 bits fijos, sin importar el mensaje."""
        for bits_mensaje, overhead in [(8, 4.0), (32, 1.0), (64, 0.5), (256, 0.125)]:
            with self.subTest(bits=bits_mensaje):
                fila = correr("CRC", bits_mensaje, 0.0, 0, repeticiones=5)

                self.assertEqual(fila["bits_trama"], bits_mensaje + 32)
                self.assertAlmostEqual(fila["overhead"], overhead, places=4)

    def test_el_barrido_es_reproducible(self):
        """Valores fijos, calculados en otro proceso y anotados aqui.

        Este test existe por un bug real: la semilla se derivaba con hash()
        sobre una tupla con strings, y Python aleatoriza el hash de los strings
        en cada proceso. El barrido daba numeros distintos en cada corrida
        (85, 83 y 67 aciertos sobre 200) mientras el codigo decia "semilla fija".

        Como el valor esperado se calculo en OTRO proceso, si la semilla vuelve
        a depender del proceso este test se cae.
        """
        fila = correr("CRC", 64, 0.01, 0, repeticiones=200)

        self.assertEqual(fila["ok"], 100)
        self.assertEqual(fila["detectado"], 100)

    def test_los_conteos_suman(self):
        fila = correr("CRC", 32, 0.01, 0, repeticiones=200)

        total = (fila["ok"] + fila["corregido"]
                 + fila["detectado"] + fila["falso_negativo"])
        self.assertEqual(total, 200)


if __name__ == "__main__":
    unittest.main()
