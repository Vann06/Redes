import unittest

from comun.protocolo import crear_trama, es_control, leer_trama


class TramaJsonTests(unittest.TestCase):
    def test_roundtrip_control(self):
        mensaje = {"proto": "LinkState", "type": "HELLO", "from": "A", "ttl": 1}
        trama = crear_trama(mensaje)
        self.assertTrue(trama.startswith("J|"))
        recuperado, usa_hamming, correcciones = leer_trama(trama)
        self.assertEqual(recuperado, mensaje)
        self.assertFalse(usa_hamming)
        self.assertEqual(correcciones, 0)

    def test_rechaza_prefijo_invalido(self):
        with self.assertRaises(ValueError):
            leer_trama("X|{}")

    def test_rechaza_json_invalido(self):
        with self.assertRaises(ValueError):
            leer_trama("J|no es json")

    def test_es_control(self):
        self.assertTrue(es_control({"type": "LSA"}))
        self.assertFalse(es_control({"type": "message"}))


class TramaHammingTests(unittest.TestCase):
    def _mensaje(self):
        return {
            "type": "message",
            "from": "ATM",
            "to": "BANK",
            "ttl": 16,
            "hops": ["ATM"],
            "payload": {"op": "auth", "user": "usuario", "pin": "1234"},
        }

    def test_roundtrip_datos(self):
        mensaje = self._mensaje()
        trama = crear_trama(mensaje, con_hamming=True)
        self.assertTrue(trama.startswith("H|"))
        recuperado, usa_hamming, correcciones = leer_trama(trama)
        self.assertEqual(recuperado, mensaje)
        self.assertTrue(usa_hamming)
        self.assertEqual(correcciones, 0)

    def test_corrige_un_bit_alterado(self):
        mensaje = self._mensaje()
        trama = crear_trama(mensaje, con_hamming=True)
        bits = list(trama[2:])
        bits[0] = "1" if bits[0] == "0" else "0"
        danada = "H|" + "".join(bits)

        recuperado, usa_hamming, correcciones = leer_trama(danada)
        self.assertEqual(recuperado, mensaje)
        self.assertTrue(usa_hamming)
        self.assertEqual(correcciones, 1)

    def test_rechaza_trama_hamming_corrupta(self):
        with self.assertRaises(ValueError):
            leer_trama("H|011")

    def test_hello_y_lsa_siguen_usando_json_plano(self):
        hello = {"proto": "LinkState", "type": "HELLO", "from": "A", "ttl": 1}
        lsa = {"proto": "LinkState", "type": "LSA", "origin": "A", "seq": 1, "links": {"B": 7}, "from": "A", "ttl": 8}
        for mensaje in (hello, lsa):
            with self.subTest(tipo=mensaje["type"]):
                trama = crear_trama(mensaje)
                self.assertTrue(trama.startswith("J|"))


if __name__ == "__main__":
    unittest.main()
