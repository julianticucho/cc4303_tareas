#!/bin/bash
# test_forwarding_v1.sh :: ejemplo 1 del enunciado: R1 y R2 conectados entre si.
# Demuestra: mensaje dirigido al propio router (se imprime), forwarding hacia
# el otro router, y descarte de un destino sin ruta (8884).
# Logs del escenario en logs/forwarding_v1/

pkill -f "router.py" 2>/dev/null
sleep 0.5

LOGDIR=logs/forwarding_v1
mkdir -p "$LOGDIR"

python3 -u router.py 127.0.0.1 8881 rutas/rutas_R1_v1.txt > "$LOGDIR/R1.log" 2>&1 &
python3 -u router.py 127.0.0.1 8882 rutas/rutas_R2_v1.txt > "$LOGDIR/R2.log" 2>&1 &
sleep 1

python3 enviar.py 127.0.0.1 8881 "hola R1!" 127.0.0.1 8881
python3 enviar.py 127.0.0.1 8882 "hola R2!" 127.0.0.1 8881
python3 enviar.py 127.0.0.1 8884 "nadie me conoce" 127.0.0.1 8881
sleep 1

echo "=== R1 ==="; cat "$LOGDIR/R1.log"
echo "=== R2 ==="; cat "$LOGDIR/R2.log"

pkill -f "router.py" 2>/dev/null
