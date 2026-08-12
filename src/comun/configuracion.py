"""Carga y consultas de la configuración de la topología."""

import json


def cargar_topologia(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        topologia = json.load(archivo)
    if "routers" not in topologia:
        raise ValueError("La configuración debe contener el objeto 'routers'")
    return topologia


def routers(topologia):
    return topologia["routers"]


def config_nodo(topologia, nombre):
    try:
        return routers(topologia)[nombre]
    except KeyError as error:
        raise KeyError(f"El router {nombre!r} no existe en la topología") from error


def direccion_router(topologia, nombre):
    nodo = config_nodo(topologia, nombre)
    return nodo["ip"], nodo["puerto"]


def config_endpoint(topologia, nombre):
    try:
        return topologia.get("endpoints", {})[nombre]
    except KeyError as error:
        raise KeyError(f"El endpoint {nombre!r} no existe en la topología") from error
