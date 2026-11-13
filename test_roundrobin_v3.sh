#!/bin/bash
# test_roundrobin_v3.sh :: red de 5 routers (rombo): R1-R2-(R3,R4)-R5.
# Demuestra: round-robin en R2, los paquetes que van de R1 a R5 alternan
# el camino por R3 y por R4. Mirar el log de R2.
# Logs del escenario en logs/roundrobin_v3/

pkill -f "router.py" 2>/dev/null
sleep 0.5

LOGDIR=logs/roundrobin_v3
mkdir -p "$LOGDIR"

python3 -u router.py 127.0.0.1 8881 rutas/rutas_R1_v3.txt > "$LOGDIR/R1.log" 2>&1 &
python3 -u router.py 127.0.0.1 8882 rutas/rutas_R2_v3.txt > "$LOGDIR/R2.log" 2>&1 &
python3 -u router.py 127.0.0.1 8883 rutas/rutas_R3_v3.txt > "$LOGDIR/R3.log" 2>&1 &
python3 -u router.py 127.0.0.1 8884 rutas/rutas_R4_v3.txt > "$LOGDIR/R4.log" 2>&1 &
python3 -u router.py 127.0.0.1 8885 rutas/rutas_R5_v3.txt > "$LOGDIR/R5.log" 2>&1 &
sleep 1

python3 enviar.py 127.0.0.1 8885 "paquete 1" 127.0.0.1 8881
python3 enviar.py 127.0.0.1 8885 "paquete 2" 127.0.0.1 8881
python3 enviar.py 127.0.0.1 8885 "paquete 3" 127.0.0.1 8881
python3 enviar.py 127.0.0.1 8885 "paquete 4" 127.0.0.1 8881
sleep 2

echo "=== R2 (el que alterna) ==="; cat "$LOGDIR/R2.log"
echo "=== R5 (destino final) ==="; cat "$LOGDIR/R5.log"

pkill -f "router.py" 2>/dev/null
