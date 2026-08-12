#!/usr/bin/env bash
# Detiene todos los procesos levantados por scripts/levantar_red.sh.

set -uo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f logs/pids.txt ]]; then
    echo "[detener_red] no hay logs/pids.txt (¿ya está todo apagado?)"
    exit 0
fi

while read -r pid; do
    [[ -z "$pid" ]] && continue
    if kill "$pid" 2>/dev/null; then
        echo "[detener_red] proceso $pid detenido"
    fi
done < logs/pids.txt

rm -f logs/pids.txt
echo "[detener_red] listo"
