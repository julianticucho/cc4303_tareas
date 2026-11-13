#!/bin/bash
# test_ttl.sh :: red de 3 routers (v2) con headers de 7 bytes.
# Demuestra: un paquete con TTL=1 desde R1 hacia R3 es reenviado por R1 (que lo
# deja en TTL=0) y descartado en R3; con TTL=255 la cadena R1->R2->R3 funciona.
# Logs del escenario en logs/ttl/

pkill -f "router.py" 2>/dev/null
sleep 0.5

LOGDIR=logs/ttl
mkdir -p "$LOGDIR"

python3 -u router.py 127.0.0.1 8881 rutas/rutas_R1_v2.txt > "$LOGDIR/R1.log" 2>&1 &
python3 -u router.py 127.0.0.1 8882 rutas/rutas_R2_v2.txt > "$LOGDIR/R2.log" 2>&1 &
python3 -u router.py 127.0.0.1 8883 rutas/rutas_R3_v2.txt > "$LOGDIR/R3.log" 2>&1 &
sleep 1

# TTL=1: R1 lo forwardea (TTL pasa a 0), R3 lo descarta al recibirlo
python3 enviar.py 127.0.0.1 8883 "no llego" 127.0.0.1 8881 1
# TTL=255: la cadena completa funciona y R3 imprime
python3 enviar.py 127.0.0.1 8883 "si llego" 127.0.0.1 8881 255
sleep 1

echo "=== R1 ==="; cat "$LOGDIR/R1.log"
echo "=== R2 ==="; cat "$LOGDIR/R2.log"
echo "=== R3 ==="; cat "$LOGDIR/R3.log"

pkill -f "router.py" 2>/dev/null
