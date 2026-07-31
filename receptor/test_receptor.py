"""Tests del receptor. Se corren con:  python3 -m unittest -v  (desde receptor/)"""

import json
import random
import unittest
import zlib

from algoritmos.crc32 import BITS_CRC, _calcular_crc, crc32_verify
from enlace import verificar_integridad
from main import subir_por_las_capas
from presentacion import decodificar_mensaje


def a_bits(texto):
    """Texto a bits, igual que la capa de presentacion del emisor."""
    return "".join(f"{octeto:08b}" for octeto in texto.encode("utf-8"))


def armar_trama(texto):
    """Arma la trama como la mandaria el emisor: bits + 32 de CRC."""
    bits = a_bits(texto)
    return bits + format(_calcular_crc(texto.encode("utf-8")), "032b")


def voltear(trama, posicion):
    volteado = "1" if trama[posicion] == "0" else "0"
    return trama[:posicion] + volteado + trama[posicion + 1:]


class TestCRC32(unittest.TestCase):
    def test_vector_obligatorio(self):
        """El que exige instrucciones.md. Si falla, no coincide con el emisor."""
        self.assertEqual(_calcular_crc(b"123456789"), 0xCBF43926)

    def test_valores_conocidos(self):
        for entrada, esperado in [
            (b"", 0x00000000),
            (b"a", 0xE8B7BE43),
            (b"abc", 0x352441C2),
            (b"A", 0xD3D99E8B),
        ]:
            with self.subTest(entrada=entrada):
                self.assertEqual(_calcular_crc(entrada), esperado)

    def test_coincide_con_zlib(self):
        """zlib como oraculo: confirma que la receta es la estandar.

        No se usa en la implementacion, el algoritmo va a mano.
        """
        azar = random.Random(1)  # semilla fija: el test es reproducible

        for _ in range(500):
            datos = bytes(azar.randrange(256) for _ in range(azar.randrange(64)))
            self.assertEqual(_calcular_crc(datos), zlib.crc32(datos) & 0xFFFFFFFF)

    def test_trama_limpia(self):
        bits, estado = crc32_verify(armar_trama("hola"))
        self.assertEqual(estado, "ok")
        self.assertEqual(bits, a_bits("hola"))

    def test_detecta_un_bit_volteado(self):
        """Cualquier bit, incluidos los del CRC: el ruido no distingue."""
        trama = armar_trama("hola")

        for posicion in range(len(trama)):
            with self.subTest(posicion=posicion):
                _, estado = crc32_verify(voltear(trama, posicion))
                self.assertEqual(estado, "error")

    def test_detecta_dos_bits_volteados(self):
        trama = armar_trama("mensaje de prueba")
        azar = random.Random(7)

        for _ in range(200):
            i, j = azar.randrange(len(trama)), azar.randrange(len(trama))
            if i == j:
                continue
            _, estado = crc32_verify(voltear(voltear(trama, i), j))
            self.assertEqual(estado, "error")

    def test_nunca_devuelve_corregido(self):
        """CRC-32 solo detecta. Si algun dia devuelve 'corregido', hay un bug."""
        for trama in [armar_trama("hola"), voltear(armar_trama("hola"), 3), "", "0" * 40]:
            _, estado = crc32_verify(trama)
            self.assertIn(estado, ("ok", "error"))

    def test_tramas_invalidas(self):
        for trama in ["", "0" * 31, "0" * 36, "x" * 40, "0" * 39 + "x"]:
            with self.subTest(trama=trama[:10]):
                _, estado = crc32_verify(trama)
                self.assertEqual(estado, "error")


class TestPresentacion(unittest.TestCase):
    def test_decodifica(self):
        self.assertEqual(decodificar_mensaje("01000001"), "A")
        self.assertEqual(decodificar_mensaje(a_bits("hola")), "hola")
        self.assertEqual(decodificar_mensaje(""), "")

    def test_ida_y_vuelta(self):
        for texto in ["a", "hola como estas", "cajero automatico", "ñandú"]:
            with self.subTest(texto=texto):
                self.assertEqual(decodificar_mensaje(a_bits(texto)), texto)

    def test_avisa_del_error(self):
        with self.assertRaises(ValueError):
            decodificar_mensaje("0100000")  # no es multiplo de 8
        with self.assertRaises(ValueError):
            decodificar_mensaje("0100000x")  # no son bits
        with self.assertRaises(ValueError):
            decodificar_mensaje("11111111")  # no es UTF-8 valido


class TestEnlace(unittest.TestCase):
    def test_despacha_crc(self):
        bits, estado = verificar_integridad(armar_trama("hola"), "CRC", 0, 32)
        self.assertEqual(estado, "ok")
        self.assertEqual(bits, a_bits("hola"))

    def test_hamming_pendiente(self):
        with self.assertRaises(ValueError):
            verificar_integridad(armar_trama("hola"), "HAM", 4, 32)

    def test_rechaza_lo_desconocido(self):
        for algoritmo in ["", "crc", "CRC32", "otro"]:
            with self.subTest(algoritmo=algoritmo):
                with self.assertRaises(ValueError):
                    verificar_integridad(armar_trama("hola"), algoritmo, 0, 32)


class TestFlujoCompleto(unittest.TestCase):
    """Las cuatro capas juntas, sin sockets."""

    def setUp(self):
        self.sesion = {"tarjeta": None}

    def linea(self, texto, ruido=None):
        trama = armar_trama(texto)
        if ruido is not None:
            trama = voltear(trama, ruido)
        return f"CRC|0|{len(a_bits(texto))}|{trama}"

    def test_login_correcto(self):
        peticion = json.dumps({"action": "login",
                               "data": {"card": "23201", "pin": "6767"}})

        respuesta = subir_por_las_capas(self.linea(peticion), self.sesion)

        self.assertTrue(respuesta.startswith("ACK|"))
        self.assertEqual(json.loads(respuesta[len("ACK|"):])["action"], "login_ok")
        self.assertEqual(self.sesion["tarjeta"], "23201")

    def test_login_con_pin_malo(self):
        peticion = json.dumps({"action": "login",
                               "data": {"card": "23201", "pin": "0000"}})

        respuesta = subir_por_las_capas(self.linea(peticion), self.sesion)

        self.assertEqual(json.loads(respuesta[len("ACK|"):])["action"], "login_denied")
        self.assertIsNone(self.sesion["tarjeta"])

    def test_retiro_sin_autenticar(self):
        peticion = json.dumps({"action": "withdraw", "data": {"amount": 100}})

        respuesta = subir_por_las_capas(self.linea(peticion), self.sesion)

        self.assertEqual(json.loads(respuesta[len("ACK|"):])["data"]["message"],
                         "No autenticado")

    def test_mensaje_libre_contesta_ack_pelado(self):
        peticion = json.dumps({"action": "message",
                               "data": {"text": "hola como estas"}})

        respuesta = subir_por_las_capas(self.linea(peticion), self.sesion)

        self.assertEqual(respuesta, "ACK")

    def test_trama_danada_da_nak(self):
        peticion = json.dumps({"action": "login",
                               "data": {"card": "23201", "pin": "6767"}})

        respuesta = subir_por_las_capas(self.linea(peticion, ruido=10), self.sesion)

        self.assertEqual(respuesta, "NAK")
        self.assertIsNone(self.sesion["tarjeta"])  # no se proceso nada

    def test_cabecera_rota_da_nak(self):
        for linea in ["", "CRC", "CRC|0|8", "CRC|x|8|0100", "|||"]:
            with self.subTest(linea=linea):
                self.assertEqual(subir_por_las_capas(linea, self.sesion), "NAK")

    def test_texto_que_no_es_operacion(self):
        respuesta = subir_por_las_capas(self.linea("hola sin json"), self.sesion)
        self.assertEqual(respuesta, "NAK")


if __name__ == "__main__":
    unittest.main()
