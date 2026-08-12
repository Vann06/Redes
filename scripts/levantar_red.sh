#!/usr/bin/env bash
# Levanta los 9 routers (y opcionalmente el banco) en background, cada uno
# con su propio log en logs/. El flooding y el cálculo de rutas son
# automáticos: en cuanto dos o más routers están corriendo, ya se están
# mandando HELLO y LSA entre sí.
#
# Uso:
#   scripts/levantar_red.sh                 # solo los 9 routers
#   scripts/levantar_red.sh --con-banco      # routers + banco_servidor.py
#   scripts/levantar_red.sh A B C            # solo esos routers
#   scripts/levantar_red.sh A B C --con-banco
#
# Para bajar todo: scripts/detener_red.sh

set -euo pipefail
cd "$(dirname "$0")/.."

if command -v python >/dev/null 2>&1; then
    PYTHON=python
elif command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v py >/dev/null 2>&1; then
    PYTHON=py
else
    echo "[levantar_red] no encontré 'python', 'python3' ni 'py' en el PATH de esta terminal." >&2
    echo "  Si venías de PowerShell con 'bash script.sh', abre Git Bash directamente y probá de nuevo." >&2
    exit 1
fi

export PYTHONPATH=src
mkdir -p logs runtime

con_banco=0
nodos=()
for arg in "$@"; do
    if [[ "$arg" == "--con-banco" ]]; then
        con_banco=1
    else
        nodos+=("$arg")
    fi
done
if [[ ${#nodos[@]} -eq 0 ]]; then
    nodos=(A B C D E F G H I)
fi

: > logs/pids.txt

for n in "${nodos[@]}"; do
    "$PYTHON" src/main.py "$n" > "logs/$n.log" 2>&1 &
    disown
    echo "$!" >> logs/pids.txt
    echo "[levantar_red] router $n -> PID $!"
done

if [[ "$con_banco" -eq 1 ]]; then
    "$PYTHON" src/endpoints/banco_servidor.py > logs/banco.log 2>&1 &
    disown
    echo "$!" >> logs/pids.txt
    echo "[levantar_red] banco -> PID $!"
fi

echo "[levantar_red] esperando convergencia (~12s)..."
sleep 12

echo "[levantar_red] listo. Tabla de ${nodos[0]}:"
cat "runtime/${nodos[0]}_tabla_enrutamiento.csv" 2>/dev/null || echo "(todavía no existe, dale unos segundos más)"

echo
echo "Cliente ATM:   python src/endpoints/atm_cliente.py [--hamming]"
echo "Bajar todo:    scripts/detener_red.sh"
echo "Ver un log:    tail -f logs/A.log"
