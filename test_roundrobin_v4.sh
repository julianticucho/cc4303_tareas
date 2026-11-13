#!/bin/bash
# test_roundrobin_v4.sh :: red de 7 routers con R0 (8880) conectado a R1 y R2,
# y R6 (8886) conectado a R2 y R3.
# Demuestra: round-robin por area en R2, envios intercalados R1->R5 (ida) y
# R5->R1 (vuelta); cada area cicla con su propio contador.
# Logs del escenario en logs/roundrobin_v4/

pkill -f "router.py" 2>/dev/null
sleep 0.5

LOGDIR=logs/roundrobin_v4
mkdir -p "$LOGDIR"

python3 -u router.py 127.0.0.1 8880 rutas/rutas_R0_v4.txt > "$LOGDIR/R0.log" 2>&1 &
python3 -u router.py 127.0.0.1 8881 rutas/rutas_R1_v4.txt > "$LOGDIR/R1.log" 2>&1 &
python3 -u router.py 127.0.0.1 8882 rutas/rutas_R2_v4.txt > "$LOGDIR/R2.log" 2>&1 &
python3 -u router.py 127.0.0.1 8883 rutas/rutas_R3_v4.txt > "$LOGDIR/R3.log" 2>&1 &
python3 -u router.py 127.0.0.1 8884 rutas/rutas_R4_v4.txt > "$LOGDIR/R4.log" 2>&1 &
python3 -u router.py 127.0.0.1 8885 rutas/rutas_R5_v4.txt > "$LOGDIR/R5.log" 2>&1 &
python3 -u router.py 127.0.0.1 8886 rutas/rutas_R6_v4.txt > "$LOGDIR/R6.log" 2>&1 &
sleep 1

python3 enviar.py 127.0.0.1 8885 "ida 1" 127.0.0.1 8881
python3 enviar.py 127.0.0.1 8881 "vuelta 1" 127.0.0.1 8885
python3 enviar.py 127.0.0.1 8885 "ida 2" 127.0.0.1 8881
python3 enviar.py 127.0.0.1 8881 "vuelta 2" 127.0.0.1 8885
python3 enviar.py 127.0.0.1 8885 "ida 3" 127.0.0.1 8881
python3 enviar.py 127.0.0.1 8881 "vuelta 3" 127.0.0.1 8885
sleep 2

echo "=== R2 (ciclo independiente por area) ==="; cat "$LOGDIR/R2.log"

pkill -f "router.py" 2>/dev/null
