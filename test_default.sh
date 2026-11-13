#!/bin/bash
# test_default.sh :: red de 7 routers (v5) + router default en (127.0.0.1, 7000).
# Demuestra: un paquete con destino fuera de la red (9999) es enviado al router
# default, que lo descarta; y las rutas especificas siguen ganando sobre la
# default (el round-robin de R2 sigue ciclando).
# Logs del escenario en logs/default/

pkill -f "router.py" 2>/dev/null
sleep 0.5

LOGDIR=logs/default
mkdir -p "$LOGDIR"

python3 -u router.py 127.0.0.1 8880 rutas/rutas_R0_v5.txt > "$LOGDIR/R0.log" 2>&1 &
python3 -u router.py 127.0.0.1 8881 rutas/rutas_R1_v5.txt > "$LOGDIR/R1.log" 2>&1 &
python3 -u router.py 127.0.0.1 8882 rutas/rutas_R2_v5.txt > "$LOGDIR/R2.log" 2>&1 &
python3 -u router.py 127.0.0.1 8883 rutas/rutas_R3_v5.txt > "$LOGDIR/R3.log" 2>&1 &
python3 -u router.py 127.0.0.1 8884 rutas/rutas_R4_v5.txt > "$LOGDIR/R4.log" 2>&1 &
python3 -u router.py 127.0.0.1 8885 rutas/rutas_R5_v5.txt > "$LOGDIR/R5.log" 2>&1 &
python3 -u router.py 127.0.0.1 8886 rutas/rutas_R6_v5.txt > "$LOGDIR/R6.log" 2>&1 &
python3 -u router.py 127.0.0.1 7000 rutas/rutas_default_v5.txt > "$LOGDIR/default.log" 2>&1 &
sleep 1

python3 enviar.py 127.0.0.1 9999 "hola internet?" 127.0.0.1 8881
python3 enviar.py 127.0.0.1 8885 "ida 1" 127.0.0.1 8881
python3 enviar.py 127.0.0.1 8881 "vuelta 1" 127.0.0.1 8885
sleep 2

echo "=== R1 (manda al default) ==="; cat "$LOGDIR/R1.log"
echo "=== default (descarta) ==="; cat "$LOGDIR/default.log"
echo "=== R2 (round-robin intacto) ==="; cat "$LOGDIR/R2.log"

pkill -f "router.py" 2>/dev/null
