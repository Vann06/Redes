import unittest

from dijkstra import caminos_mas_cortos, siguiente_salto


class DijkstraTests(unittest.TestCase):
    def test_ruta_a_e(self):
        grafo = {"A": {"I": 1, "B": 7}, "I": {"D": 6}, "D": {"E": 1}, "B": {"D": 20}}
        distancias, previos = caminos_mas_cortos(grafo, "A")
        self.assertEqual(distancias["E"], 8)
        self.assertEqual(siguiente_salto(previos, "A", "E"), "I")


if __name__ == "__main__":
    unittest.main()
