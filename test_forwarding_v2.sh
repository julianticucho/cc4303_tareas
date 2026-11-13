#!/bin/bash
# test_forwarding_v2.sh :: ejemplo 2 del enunciado: R1 - R2 - R3 en linea.
# Demuestra: la cadena de saltos R1 -> R2 -> R3, el camino inverso R3 -> R1,
# y el descarte de un destino fuera de la red (8884).
# Logs del escenario en logs/forwarding_v2/

pkill -f "router.py" 2>/dev/null
sleep 0.5

LOGDIR=logs/forwarding_v2
mkdir -p "$LOGDIR"

python3 -u router.py 127.0.0.1 8881 rutas/rutas_R1_v2.txt > "$LOGDIR/R1.log" 2>&1 &
python3 -u router.py 127.0.0.1 8882 rutas/rutas_R2_v2.txt > "$LOGDIR/R2.log" 2>&1 &
python3 -u router.py 127.0.0.1 8883 rutas/rutas_R3_v2.txt > "$LOGDIR/R3.log" 2>&1 &
sleep 1

python3 enviar.py 127.0.0.1 8883 "hola desde R1" 127.0.0.1 8881
python3 enviar.py 127.0.0.1 8881 "hola desde R3" 127.0.0.1 8883
python3 enviar.py 127.0.0.1 8884 "a nadie" 127.0.0.1 8881
sleep 1

echo "=== R1 ==="; cat "$LOGDIR/R1.log"
echo "=== R2 ==="; cat "$LOGDIR/R2.log"
echo "=== R3 ==="; cat "$LOGDIR/R3.log"

pkill -f "router.py" 2>/dev/null
