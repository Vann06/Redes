"""Algoritmo de Dijkstra y reconstrucción del siguiente salto."""

import heapq


def caminos_mas_cortos(grafo, origen):
    """Devuelve ``(distancias, previos)`` para un grafo dirigido ponderado."""
    distancias = {origen: 0}
    previos = {}
    cola = [(0, origen)]
    visitados = set()

    while cola:
        distancia, nodo = heapq.heappop(cola)
        if nodo in visitados:
            continue
        visitados.add(nodo)
        for vecino, costo in grafo.get(nodo, {}).items():
            nueva_distancia = distancia + costo
            if nueva_distancia < distancias.get(vecino, float("inf")):
                distancias[vecino] = nueva_distancia
                previos[vecino] = nodo
                heapq.heappush(cola, (nueva_distancia, vecino))
    return distancias, previos


def siguiente_salto(previos, origen, destino):
    """Obtiene el vecino inmediato desde ``origen`` para llegar a ``destino``."""
    actual = destino
    while actual in previos:
        anterior = previos[actual]
        if anterior == origen:
            return actual
        actual = anterior
    return None
