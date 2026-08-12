"""Punto de entrada para iniciar un router Link State."""

import argparse
import time

from comun.configuracion import cargar_topologia
from control.router import Router


def main():
    parser = argparse.ArgumentParser(description="Nodo router Link State")
    parser.add_argument("nombre", help="Identificador del router (A-I)")
    parser.add_argument("--topologia", default="config/topologia.json")
    parser.add_argument("--runtime", default="runtime")
    args = parser.parse_args()
    router = Router(args.nombre, cargar_topologia(args.topologia), args.runtime)
    router.iniciar()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        router.detener()


if __name__ == "__main__":
    main()
