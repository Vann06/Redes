import unittest

from comun.hamming import N, codificar_bytes, codificar_nibble, decodificar_bits, decodificar_bloque


def voltear(bits, posicion):
    """Voltea un bit de un string de bits."""
    lista = list(bits)
    lista[posicion] = "1" if lista[posicion] == "0" else "0"
    return "".join(lista)


class CodificarNibbleTests(unittest.TestCase):
    def test_produce_siete_bits(self):
        self.assertEqual(len(codificar_nibble("1011")), N)

    def test_rechaza_nibble_invalido(self):
        for nibble in ("101", "10111", "10x1", 1011):
            with self.subTest(nibble=nibble):
                with self.assertRaises(ValueError):
                    codificar_nibble(nibble)


class DecodificarBloqueTests(unittest.TestCase):
    def test_sin_error(self):
        datos, corregido = decodificar_bloque(codificar_nibble("1011"))
        self.assertEqual(datos, "1011")
        self.assertFalse(corregido)

    def test_corrige_cualquier_bit_del_bloque(self):
        codificado = codificar_nibble("1011")
        for posicion in range(N):
            with self.subTest(posicion=posicion):
                datos, corregido = decodificar_bloque(voltear(codificado, posicion))
                self.assertEqual(datos, "1011")
                self.assertTrue(corregido)

    def test_rechaza_bloque_de_longitud_invalida(self):
        with self.assertRaises(ValueError):
            decodificar_bloque("101")

    def test_rechaza_caracteres_invalidos(self):
        with self.assertRaises(ValueError):
            decodificar_bloque("011001x")


class CodificarBytesRoundTripTests(unittest.TestCase):
    def test_roundtrip_ascii(self):
        original = "Hola, red!".encode("utf-8")
        recuperado, correcciones = decodificar_bits(codificar_bytes(original))
        self.assertEqual(recuperado, original)
        self.assertEqual(correcciones, 0)

    def test_roundtrip_utf8_multibyte(self):
        original = "ñandú-ü".encode("utf-8")
        recuperado, correcciones = decodificar_bits(codificar_bytes(original))
        self.assertEqual(recuperado, original)
        self.assertEqual(correcciones, 0)

    def test_corrige_un_bit_por_bloque_en_varios_bloques(self):
        original = b"AB"
        bits = codificar_bytes(original)
        danado = bits
        for bloque in range(len(bits) // N):
            danado = voltear(danado, bloque * N)
        recuperado, correcciones = decodificar_bits(danado)
        self.assertEqual(recuperado, original)
        self.assertEqual(correcciones, len(bits) // N)

    def test_rechaza_longitud_no_multiplo_de_siete(self):
        with self.assertRaises(ValueError):
            decodificar_bits("01100110")

    def test_rechaza_caracteres_invalidos(self):
        with self.assertRaises(ValueError):
            decodificar_bits("011001x")


if __name__ == "__main__":
    unittest.main()
